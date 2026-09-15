import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_workflow import process_ai_inbox
from investkb.mistral_api import (
    mistral_output_schema,
    run_mistral_extractions,
    verify_mistral_access,
)
from investkb.openai_api import (
    openai_status,
    plan_openai_extractions,
    run_openai_extractions,
    strict_output_schema,
)
from investkb.outputs import write_ai_package, write_dashboard, write_export, write_report, write_tasks
from investkb.inbox import scan_inbox
from investkb.podcast_sync import apply_podcast_sync, plan_podcast_sync
from investkb.repository import KnowledgeBase
from investkb.schema import SCHEMA_SQL
from investkb.validation import ValidationError, validate_extraction
from investkb.web_app import create_server


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        self.source = self.root / "source.txt"
        self.source.write_text("[00:01] En dokumenteret investeringspåstand.", encoding="utf-8")
        self.source_id, created = self.kb.import_source(
            self.source, "podcast_transcript", source_store=self.root / "sources"
        )
        self.assertTrue(created)

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def extraction(self):
        data = json.loads((ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8"))
        data["source_id"] = self.source_id
        return data

    def podcast_json(self, root, podcast="Macro Mondays", published="2026-08-17"):
        folder = root / podcast
        folder.mkdir(parents=True)
        path = folder / f"{published} Testepisode.json"
        data = {
            "schema_version": "2.0",
            "id": "episode-123",
            "source": {
                "filename": f"{published} Testepisode.mp3",
                "duration_seconds": 65.2,
                "language": "en",
                "podcast": podcast,
                "title": "Testepisode om markeder",
                "published": published,
                "processing": {"timestamp": "20260821_120000", "processor": "post_processor v2.0"},
            },
            "transcription": {"provider": "faster-whisper", "model": "large-v3"},
            "quality": {"score": 91.5, "grade": "B"},
            "segments": [
                {"id": 1, "start": 1.2, "end": 3.1, "text": "First complete statement."},
                {"id": 2, "start": 61.0, "end": 65.2, "text": "Second complete statement."},
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_end_to_end_and_idempotent_source(self):
        same_id, created = self.kb.import_source(
            self.source, "podcast_transcript", source_store=self.root / "sources"
        )
        self.assertEqual(self.source_id, same_id)
        self.assertFalse(created)
        _, count = self.kb.ingest(self.extraction())
        self.assertEqual(2, count)
        self.assertEqual(2, len(self.kb.claims()))

        tasks = self.root / "tasks.jsonl"
        report = self.root / "report.md"
        dashboard = self.root / "dashboard.html"
        export = self.root / "export.jsonl"
        self.assertEqual(1, write_tasks(self.kb, tasks, all_sources=True))
        self.assertEqual(2, write_report(self.kb, report))
        self.assertEqual(2, write_dashboard(self.kb, dashboard))
        self.assertEqual(2, write_export(self.kb, export))
        self.assertIn("Eksempel Energi", report.read_text(encoding="utf-8"))
        self.assertIn("InvestViden – kontroloversigt", dashboard.read_text(encoding="utf-8"))

        priority_tasks = self.root / "priority-tasks.jsonl"
        write_tasks(
            self.kb,
            priority_tasks,
            all_sources=True,
            preferences={"extraction_priorities": {"events": ["regnskaber"]}},
        )
        task = json.loads(priority_tasks.read_text(encoding="utf-8"))
        self.assertEqual(["regnskaber"], task["priorities"]["events"])

    def test_review_preserved_on_reingest(self):
        self.kb.ingest(self.extraction())
        claim_id = self.kb.claims()[0]["id"]
        self.kb.set_review(claim_id, "approved", "Kontrolleret")
        self.kb.ingest(self.extraction())
        status = {c["id"]: c["review_status"] for c in self.kb.claims()}[claim_id]
        self.assertEqual("approved", status)

    def test_schema_v3_records_claim_versions_and_review_events(self):
        self.kb.ingest(self.extraction())
        claim_id = self.kb.claims()[0]["id"]
        self.assertEqual(
            1,
            self.kb.conn.execute(
                "SELECT COUNT(*) FROM claim_versions WHERE claim_id=?", (claim_id,)
            ).fetchone()[0],
        )
        self.kb.set_review(claim_id, "approved", "Kontrolleret mod evidensen")
        event = self.kb.conn.execute(
            """SELECT previous_status, new_status, note, reviewer
               FROM review_events WHERE claim_id=? ORDER BY created_at DESC LIMIT 1""",
            (claim_id,),
        ).fetchone()
        self.assertEqual("ai_extracted", event["previous_status"])
        self.assertEqual("approved", event["new_status"])
        self.assertEqual("Kontrolleret mod evidensen", event["note"])
        self.assertEqual("owner", event["reviewer"])
        self.kb.ingest(self.extraction())
        self.assertEqual(
            1,
            self.kb.conn.execute(
                "SELECT COUNT(*) FROM claim_versions WHERE claim_id=?", (claim_id,)
            ).fetchone()[0],
        )

    def test_correction_is_versioned_and_full_text_searchable(self):
        self.kb.ingest(self.extraction())
        claim_id = self.kb.claims()[0]["id"]
        self.kb.correct_claim(
            claim_id,
            "En dokumenteret rettelse om grøn energi",
            "Præciseret mod kildepassagen",
        )
        detail = self.kb.claim_detail(claim_id)
        self.assertEqual("corrected", detail["review_status"])
        self.assertEqual("En dokumenteret rettelse om grøn energi", detail["summary"])
        self.assertEqual("claim_corrected", detail["history"][0]["event_type"])
        self.assertEqual(
            2,
            self.kb.conn.execute(
                "SELECT COUNT(*) FROM claim_versions WHERE claim_id=?", (claim_id,)
            ).fetchone()[0],
        )
        results = self.kb.search_claims("grøn energi")
        self.assertEqual([claim_id], [row["id"] for row in results])

    def test_local_ui_lists_and_approves_a_candidate(self):
        self.kb.ingest(self.extraction())
        claim_id = self.kb.claims()[0]["id"]
        server, app = create_server(self.kb.db_path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(base_url + "/review", timeout=5) as response:
                page = response.read().decode("utf-8")
            self.assertIn("Gennemgå nye signaler", page)
            self.assertIn(claim_id, page)
            payload = urlencode({
                "csrf_token": app.csrf_token,
                "claim_id": claim_id,
                "action": "approve",
                "note": "Kontrolleret i UI-test",
            }).encode("utf-8")
            request = Request(base_url + "/review", data=payload, method="POST")
            with urlopen(request, timeout=5) as response:
                self.assertIn("godkendt", response.read().decode("utf-8"))
            status = self.kb.conn.execute(
                "SELECT review_status FROM claims WHERE id=?", (claim_id,)
            ).fetchone()[0]
            self.assertEqual("approved", status)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_schema_v3_migrates_v2_database_without_losing_rows(self):
        path = self.root / "legacy-v2.sqlite"
        connection = sqlite3.connect(path)
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            "INSERT INTO schema_version(version, applied_at) VALUES(1, '2026-08-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO schema_version(version, applied_at) VALUES(2, '2026-08-02T00:00:00+00:00')"
        )
        connection.execute(
            """INSERT INTO sources
               (id, source_type, title, publisher, published_at, language,
                original_path, stored_path, sha256, imported_at)
               VALUES ('src-legacy', 'other', 'Legacy knowledge', NULL, NULL, 'da',
                       'legacy.json', 'legacy.json', ?, '2026-08-01T00:00:00+00:00')""",
            ("a" * 64,),
        )
        connection.execute(
            """INSERT INTO extraction_runs
               (id, source_id, provider, model, schema_version, extracted_at, imported_at)
               VALUES ('run-legacy', 'src-legacy', 'legacy-knowledge-base-migration', NULL,
                       '0.1', '2026-08-01T00:00:00+00:00', '2026-08-01T00:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO claims
               (id, source_id, run_id, fingerprint, claim_type, summary, speaker,
                sentiment, action, time_horizon, discussion_depth, confidence,
                review_status, review_note, created_at, updated_at)
               VALUES ('claim-legacy', 'src-legacy', 'run-legacy', 'fingerprint',
                       'theme', 'Historisk udsagn', NULL, 'neutral', 'none',
                       'unspecified', 'brief', 0.5, 'uncertain', 'Legacy',
                       '2026-08-01T00:00:00+00:00', '2026-08-01T00:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO evidence(claim_id, excerpt, start_ref, end_ref)
               VALUES ('claim-legacy', 'Historisk evidens', 'legacy', NULL)"""
        )
        connection.commit()
        connection.close()

        with KnowledgeBase(path) as protected:
            with self.assertRaises(RuntimeError):
                protected.initialize()
            self.assertEqual(
                2,
                protected.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0],
            )

        with KnowledgeBase(path) as migrated:
            migrated.initialize(allow_migration=True)
            self.assertEqual(
                4,
                migrated.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0],
            )
            self.assertEqual(1, migrated.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
            self.assertEqual(
                1, migrated.conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0]
            )
            logical = migrated.conn.execute(
                "SELECT dataset, ai_permission FROM sources"
            ).fetchone()
            self.assertEqual("legacy", logical["dataset"])
            self.assertEqual("local_only", logical["ai_permission"])
            self.assertEqual(
                1, migrated.conn.execute("SELECT COUNT(*) FROM claim_versions").fetchone()[0]
            )
            review = migrated.conn.execute(
                "SELECT new_status, note FROM review_events"
            ).fetchone()
            self.assertEqual("uncertain", review["new_status"])
            self.assertEqual("Legacy", review["note"])
            self.assertEqual(
                1, migrated.conn.execute("SELECT COUNT(*) FROM claims_fts").fetchone()[0]
            )

    def test_invalid_confidence_is_rejected(self):
        data = self.extraction()
        data["claims"][0]["confidence"] = 1.5
        with self.assertRaises(ValidationError):
            validate_extraction(data)

    def test_status_and_priority_report(self):
        self.kb.ingest(self.extraction())
        stats = self.kb.stats(0.95)
        self.assertEqual(1, stats["low_confidence"])
        report = self.root / "priority.md"
        write_report(
            self.kb,
            report,
            preferences={"portfolio": {"stocks": ["Eksempel Energi"], "watchlist": []}},
        )
        text = report.read_text(encoding="utf-8")
        self.assertIn("Relevans for din portefølje", text)
        self.assertIn("### Eksempel Energi", text)

        focused = self.root / "focused.md"
        self.assertEqual(
            2,
            write_report(self.kb, focused, review_statuses={"ai_extracted"}),
        )
        self.kb.set_review(self.kb.claims()[0]["id"], "approved", "Test")
        self.assertEqual(
            1,
            write_report(self.kb, focused, review_statuses={"ai_extracted"}),
        )

    def test_remove_source_cascades(self):
        self.kb.ingest(self.extraction())
        self.kb.remove_source(self.source_id)
        self.assertEqual(0, self.kb.stats()["sources"])
        self.assertEqual(0, self.kb.stats()["claims"])

    def test_bulk_review(self):
        self.kb.ingest(self.extraction())
        with self.assertRaises(ValidationError):
            self.kb.set_review_all("approved", "ai_extracted", "Godkendt i samlet kontrol")
        count = self.kb.set_review_all("uncertain", "ai_extracted", "Kræver individuel kontrol")
        self.assertEqual(2, count)
        self.assertEqual({"uncertain": 2}, self.kb.stats()["review_counts"])

    def test_scan_inbox_dry_run_import_and_duplicate_location(self):
        inbox = self.root / "inbox"
        correct = inbox / "transskriptioner" / "Macro Mondays"
        wrong = inbox / "transskriptioner" / "Millionærklubben"
        correct.mkdir(parents=True)
        wrong.mkdir(parents=True)
        filename = "2026-07-20 China Macro Mondays.txt"
        (correct / filename).write_text("The same transcript.", encoding="utf-8")
        (wrong / filename).write_text("The same transcript.", encoding="utf-8")
        settings = {
            "inbox": {
                "podcast_publishers": {"Macro Mondays": "Macro Mondays / Real Vision"},
                "podcast_languages": {"Macro Mondays": "en"},
            }
        }

        preview = scan_inbox(
            self.kb, inbox, settings, dry_run=True, source_store=self.root / "stored"
        )
        self.assertEqual(1, preview["new"])
        self.assertEqual(1, len(preview["duplicate_locations"]))
        self.assertEqual(1, self.kb.stats()["sources"])

        imported = scan_inbox(
            self.kb, inbox, settings, source_store=self.root / "stored"
        )
        self.assertEqual(1, imported["new"])
        row = self.kb.conn.execute(
            "SELECT publisher, published_at, language, title FROM sources WHERE title=?",
            ("China Macro Mondays",),
        ).fetchone()
        self.assertEqual("Macro Mondays / Real Vision", row["publisher"])
        self.assertEqual("2026-07-20", row["published_at"])
        self.assertEqual("en", row["language"])

        repeated = scan_inbox(
            self.kb, inbox, settings, source_store=self.root / "stored"
        )
        self.assertEqual(0, repeated["new"])
        self.assertEqual(1, repeated["existing"])

    def test_podcast_sync_renders_full_timestamps_and_records_provenance(self):
        upstream = self.root / "podcast-output"
        source_json = self.podcast_json(upstream)
        original_bytes = source_json.read_bytes()
        target = self.root / "inbox" / "transskriptioner"
        settings = {
            "inbox": {
                "podcast_publishers": {"Macro Mondays": "Macro Mondays / Real Vision"},
                "podcast_languages": {"Macro Mondays": "en"},
            }
        }

        preview = plan_podcast_sync(self.kb, upstream, target, settings)
        self.assertEqual({"new": 1}, preview["counts"])
        self.assertFalse(preview["items"][0].target_path.exists())
        self.assertEqual(original_bytes, source_json.read_bytes())

        applied = apply_podcast_sync(preview)
        self.assertEqual(1, len(applied["written"]))
        self.assertEqual(1, len(applied["sidecars"]))
        self.assertEqual([], applied["errors"])
        rendered = preview["items"][0].target_path.read_text(encoding="utf-8")
        self.assertIn("Kilde-JSON-SHA256:", rendered)
        self.assertIn("[00:00:01–00:00:04] First complete statement.", rendered)
        self.assertIn("[00:01:01–00:01:06] Second complete statement.", rendered)
        self.assertEqual(original_bytes, source_json.read_bytes())

        imported = scan_inbox(self.kb, self.root / "inbox", settings, source_store=self.root / "stored")
        self.assertEqual(1, imported["new"])
        provenance = self.kb.conn.execute("SELECT * FROM source_provenance").fetchone()
        self.assertIsNotNone(provenance)
        self.assertEqual("episode-123", provenance["upstream_episode_id"])
        self.assertEqual("investviden-timestamped-transcript/1.0", provenance["renderer_version"])
        imported_source = self.kb.conn.execute(
            "SELECT title, publisher, published_at, language FROM source_versions WHERE id=?",
            (provenance["source_id"],),
        ).fetchone()
        self.assertEqual("Testepisode om markeder", imported_source["title"])
        self.assertEqual("Macro Mondays / Real Vision", imported_source["publisher"])
        self.assertEqual("2026-08-17", imported_source["published_at"])
        self.assertEqual("en", imported_source["language"])
        recorded_at = provenance["recorded_at"]

        rescanned = scan_inbox(self.kb, self.root / "inbox", settings, source_store=self.root / "stored")
        self.assertEqual(1, rescanned["existing"])
        self.assertEqual(
            recorded_at,
            self.kb.conn.execute("SELECT recorded_at FROM source_provenance").fetchone()[0],
        )

        repeated = plan_podcast_sync(self.kb, upstream, target, settings)
        self.assertEqual({"registered": 1}, repeated["counts"])

    def test_podcast_sync_blocks_an_existing_episode_with_different_text(self):
        upstream = self.root / "podcast-output"
        self.podcast_json(upstream, podcast="Millionærklubben", published="2026-08-18")
        existing = self.root / "old-version.txt"
        existing.write_text("En ældre transskriptionsversion.", encoding="utf-8")
        self.kb.import_source(
            existing,
            "podcast_transcript",
            "Testepisode",
            "Millionærklubben / Euroinvestor",
            "2026-08-18",
            source_store=self.root / "stored",
        )
        settings = {
            "inbox": {
                "podcast_publishers": {"Millionærklubben": "Millionærklubben / Euroinvestor"}
            }
        }

        preview = plan_podcast_sync(
            self.kb, upstream, self.root / "inbox" / "transskriptioner", settings
        )
        self.assertEqual({"existing_episode": 1}, preview["counts"])
        applied = apply_podcast_sync(preview)
        self.assertEqual([], applied["written"])
        self.assertFalse(preview["items"][0].target_path.exists())

    def test_verified_backup_and_retention(self):
        self.kb.ingest(self.extraction())
        backup_dir = self.root / "backups"
        first = self.kb.backup_database(backup_dir)
        self.assertEqual("ok", first["integrity"])
        with KnowledgeBase(first["path"]) as restored:
            self.assertEqual(2, restored.stats()["claims"])

        second = self.kb.backup_database(backup_dir, keep=1)
        self.assertEqual("ok", second["integrity"])
        self.assertEqual(1, len(list(backup_dir.glob("investviden-*.sqlite"))))
        self.assertEqual(1, len(second["removed"]))

    def test_upload_ready_ai_package(self):
        package = self.root / "ai-pakke"
        package.mkdir()
        stale = package / "opgave-gammel.md"
        stale.write_text("gammel", encoding="utf-8")
        paths = write_ai_package(
            self.kb,
            package,
            ROOT / "schemas" / "extraction-v0.1.schema.json",
        )
        self.assertEqual(1, len(paths))
        self.assertFalse(stale.exists())
        task = paths[0].read_text(encoding="utf-8")
        self.assertIn(self.source_id, task)
        self.assertIn("En dokumenteret investeringspåstand", task)
        self.assertIn('"review_status"', task)
        self.assertIn("Returnér udelukkende ét gyldigt JSON-objekt", task)
        self.assertIn("process-ai", (package / "START-HER.md").read_text(encoding="utf-8"))

    def test_openai_strict_schema_keeps_runtime_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "extraction-v0.1.schema.json").read_text(encoding="utf-8")
        )
        strict = strict_output_schema(schema, self.source_id, "gpt-5.6-terra")
        self.assertNotIn("$schema", strict)
        self.assertEqual(self.source_id, strict["properties"]["source_id"]["const"])
        self.assertEqual("openai", strict["properties"]["provider"]["const"])
        self.assertIn("model", strict["required"])
        claim = strict["$defs"]["claim"]
        self.assertIn("claim_id", claim["required"])
        self.assertIn("speaker", claim["required"])
        self.assertEqual(["ai_extracted"], claim["properties"]["review_status"]["enum"])
        evidence = strict["$defs"]["evidence"]
        self.assertNotIn("anyOf", evidence)
        self.assertEqual(
            {"excerpt", "start_ref", "end_ref"},
            set(evidence["required"]),
        )

    def test_openai_api_pilot_is_previewed_validated_and_audited(self):
        incoming = self.root / "incoming"
        audit_dir = self.root / "audit"
        tasks = plan_openai_extractions(self.kb, incoming, limit=1)
        self.assertEqual(1, len(tasks))
        self.assertGreater(tasks[0].estimated_input_tokens, 0)
        self.assertFalse(incoming.exists())

        captured = {}
        extraction = self.extraction()
        extraction["provider"] = "forkert"
        extraction["model"] = "forkert"
        extraction["claims"][0]["review_status"] = "approved"

        def fake_transport(payload, api_key, timeout):
            captured["payload"] = payload
            captured["api_key"] = api_key
            captured["timeout"] = timeout
            return {
                "id": "resp_test_123",
                "status": "completed",
                "model": "gpt-5.6-terra-2026-08-01",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(extraction, ensure_ascii=False),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 125, "output_tokens": 75, "total_tokens": 200},
            }

        result = run_openai_extractions(
            self.kb,
            ROOT / "schemas" / "extraction-v0.1.schema.json",
            incoming,
            audit_dir,
            preferences={"extraction_priorities": {"events": ["regnskab"]}},
            limit=1,
            api_key="test-key-not-a-real-secret",
            transport=fake_transport,
        )
        self.assertEqual(1, result["sent"])
        self.assertEqual([], result["errors"])
        self.assertEqual(200, result["usage"]["total_tokens"])
        self.assertFalse(captured["payload"]["store"])
        self.assertTrue(captured["payload"]["text"]["format"]["strict"])
        self.assertEqual(self.source_id, captured["payload"]["metadata"]["source_id"])
        self.assertNotIn("test-key-not-a-real-secret", json.dumps(captured["payload"]))

        answer = json.loads(result["files"][0].read_text(encoding="utf-8"))
        self.assertEqual("openai", answer["provider"])
        self.assertEqual("gpt-5.6-terra-2026-08-01", answer["model"])
        self.assertEqual(
            {"ai_extracted"},
            {claim["review_status"] for claim in answer["claims"]},
        )
        validate_extraction(answer)

        audit = json.loads(result["audits"][0].read_text(encoding="utf-8"))
        self.assertEqual("resp_test_123", audit["response_id"])
        self.assertFalse(audit["store"])
        self.assertNotIn("test-key-not-a-real-secret", json.dumps(audit))
        self.assertEqual(0, len(plan_openai_extractions(self.kb, incoming, limit=1)))
        status = openai_status(self.kb, incoming)
        self.assertEqual(1, status["pending"])
        self.assertEqual(0, status["ready"])

        preview = process_ai_inbox(self.kb, incoming, self.root / "processed", dry_run=True)
        self.assertEqual(2, preview["claims"])
        self.assertEqual(0, len(self.kb.claims()))

    def test_mistral_api_pilot_uses_json_schema_and_never_approves(self):
        incoming = self.root / "mistral-incoming"
        audit_dir = self.root / "mistral-audit"
        schema = json.loads(
            (ROOT / "schemas" / "extraction-v0.1.schema.json").read_text(encoding="utf-8")
        )
        strict = mistral_output_schema(schema, self.source_id, "mistral-large-2512")
        self.assertEqual("mistral", strict["properties"]["provider"]["const"])

        captured = {}
        extraction = self.extraction()
        extraction["provider"] = "forkert"
        extraction["model"] = "forkert"
        extraction["claims"][0]["review_status"] = "approved"

        def fake_transport(payload, api_key, timeout):
            captured["payload"] = payload
            captured["api_key"] = api_key
            captured["timeout"] = timeout
            return {
                "id": "cmpl_mistral_test_123",
                "object": "chat.completion",
                "model": "mistral-large-2512",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(extraction, ensure_ascii=False),
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 50,
                    "total_tokens": 200,
                },
            }

        result = run_mistral_extractions(
            self.kb,
            ROOT / "schemas" / "extraction-v0.1.schema.json",
            incoming,
            audit_dir,
            preferences={"extraction_priorities": {"events": ["regnskab"]}},
            limit=1,
            api_key="test-mistral-key-not-real",
            transport=fake_transport,
        )
        self.assertEqual(1, result["sent"])
        self.assertEqual([], result["errors"])
        self.assertEqual(200, result["usage"]["total_tokens"])
        response_format = captured["payload"]["response_format"]
        self.assertEqual("json_schema", response_format["type"])
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(0.0, captured["payload"]["temperature"])
        self.assertNotIn("test-mistral-key-not-real", json.dumps(captured["payload"]))

        answer = json.loads(result["files"][0].read_text(encoding="utf-8"))
        self.assertEqual("mistral", answer["provider"])
        self.assertEqual("mistral-large-2512", answer["model"])
        self.assertEqual(
            {"ai_extracted"},
            {claim["review_status"] for claim in answer["claims"]},
        )
        validate_extraction(answer)

        audit = json.loads(result["audits"][0].read_text(encoding="utf-8"))
        self.assertEqual("mistral", audit["provider"])
        self.assertEqual("cmpl_mistral_test_123", audit["response_id"])
        self.assertNotIn("test-mistral-key-not-real", json.dumps(audit))

        preview = process_ai_inbox(self.kb, incoming, self.root / "processed", dry_run=True)
        self.assertEqual(2, preview["claims"])
        self.assertEqual(0, len(self.kb.claims()))

        verification = verify_mistral_access(
            "mistral-large-2512",
            api_key="test-mistral-key-not-real",
            transport=lambda api_key, timeout: {
                "data": [
                    {"id": "mistral-large-2512"},
                    {"id": "mistral-small-latest"},
                ]
            },
        )
        self.assertEqual(2, verification["models"])
        self.assertTrue(verification["model_available"])

    def test_process_ai_inbox_validates_ingests_and_archives(self):
        incoming = self.root / "incoming"
        processed = self.root / "processed"
        incoming.mkdir()
        answer = incoming / "ai-svar.json"
        answer.write_text(json.dumps(self.extraction(), ensure_ascii=False), encoding="utf-8")

        preview = process_ai_inbox(self.kb, incoming, processed, dry_run=True)
        self.assertEqual(2, preview["claims"])
        self.assertTrue(answer.exists())
        self.assertEqual(0, len(self.kb.claims()))

        result = process_ai_inbox(self.kb, incoming, processed)
        self.assertEqual(1, result["files"])
        self.assertEqual(2, result["claims"])
        self.assertFalse(answer.exists())
        self.assertTrue((processed / "ai-svar.json").exists())
        self.assertEqual(2, len(self.kb.claims()))

    def test_process_ai_inbox_rejects_batch_before_any_ingest(self):
        incoming = self.root / "incoming"
        incoming.mkdir()
        (incoming / "gyldig.json").write_text(
            json.dumps(self.extraction(), ensure_ascii=False), encoding="utf-8"
        )
        invalid = self.extraction()
        invalid["claims"][0]["confidence"] = 2
        (incoming / "ugyldig.json").write_text(
            json.dumps(invalid, ensure_ascii=False), encoding="utf-8"
        )

        with self.assertRaises(ValidationError):
            process_ai_inbox(self.kb, incoming, self.root / "processed")
        self.assertEqual(0, len(self.kb.claims()))
        self.assertEqual(2, len(list(incoming.glob("*.json"))))


if __name__ == "__main__":
    unittest.main()
