import html
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase
from investkb.validation import ValidationError
from investkb.web_app import create_server, _source_context


class LegacyReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "review-copy.sqlite")
        self.kb.initialize()
        self.source = self.root / "original.txt"
        self.source.write_text("[00:01] Dokumenteret udsagn om energi.\n[00:02] Mere kontekst.", encoding="utf-8")
        self.source_id, _ = self.kb.import_source(
            self.source, "podcast_transcript", title="Originalepisode",
            published_at="2026-05-05", source_store=self.root / "sources",
        )
        with self.kb.conn:
            self.kb.conn.execute("UPDATE sources SET dataset='legacy'")
        self.data = json.loads((ROOT / "examples/demo_extraction.json").read_text(encoding="utf-8"))
        self.data["source_id"] = self.source_id
        self.data["claims"] = self.data["claims"][:1]
        self.data["claims"][0].update(
            claim_id="legacy-test", summary="Dokumenteret udsagn om energi.", review_status="uncertain",
            evidence={"excerpt": "Dokumenteret udsagn om energi.", "start_ref": "00:01", "end_ref": None},
        )
        self.kb.ingest(self.data)
        self.claim_id = "legacy-test"

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def ids(self, lane, query="energi"):
        return [row["id"] for row in self.kb.search_claims(query, lane)]

    def snapshot(self):
        return {
            table: list(self.kb.conn.execute(f"SELECT * FROM {table}"))
            for table in ("claims", "claim_versions", "review_events", "evidence_locations", "claims_fts")
        }

    def test_approve_moves_legacy_to_active_and_preserves_origin_and_version(self):
        before = self.kb.claim_detail(self.claim_id)
        self.assertEqual([self.claim_id], self.ids("archive"))
        self.assertEqual([], self.ids("active"))
        self.kb.set_review(self.claim_id, "approved", "Læst mod originalpassagen")
        item = self.kb.claim_detail(self.claim_id)
        self.assertEqual("legacy", item["dataset"])
        self.assertEqual([self.claim_id], self.ids("active"))
        self.assertEqual([], self.ids("archive"))
        self.assertEqual([], self.ids("signals"))
        self.assertEqual(before["versions"], item["versions"])
        self.assertEqual(before["history"], item["history"][1:])
        self.assertEqual(item["versions"][0]["id"], item["history"][0]["claim_version_id"])

    def test_correction_creates_version_and_moves_to_active(self):
        before = self.kb.claim_detail(self.claim_id)
        self.kb.clarify_legacy(self.claim_id, True, "Genlæs originalpassagen")
        self.kb.correct_claim(self.claim_id, "Præciseret udsagn om energi.", "Præcisering mod originalen")
        item = self.kb.claim_detail(self.claim_id)
        self.assertEqual("corrected", item["review_status"])
        self.assertEqual([self.claim_id], self.ids("active", "Præciseret"))
        self.assertEqual([], self.ids("archive"))
        self.assertEqual([], self.ids("clarification", ""))
        self.assertEqual(2, len(item["versions"]))
        self.assertEqual(before["versions"][0]["payload_json"], item["versions"][1]["payload_json"])
        self.assertEqual("claim_corrected", item["history"][0]["event_type"])
        self.assertEqual(2, item["history"][0]["version_number"])
        self.assertEqual(item["versions"][0]["id"], item["history"][0]["claim_version_id"])
        self.assertEqual("legacy", item["dataset"])

    def test_requires_source_is_append_only_and_survives_reopen(self):
        before = self.kb.claim_detail(self.claim_id)
        with patch("investkb.repository.now_iso", return_value="2026-09-06T10:00:00+00:00"):
            self.kb.clarify_legacy(self.claim_id, True, "Find original lyd fra 24. oktober")
            self.kb.clarify_legacy(self.claim_id, True, "Find også tidskoden")
        self.kb.close()
        self.kb = KnowledgeBase(self.root / "review-copy.sqlite")
        item = self.kb.claim_detail(self.claim_id)
        self.assertTrue(item["requires_original_source"])
        self.assertEqual("Find også tidskoden", item["history"][0]["note"])
        self.assertEqual("Find original lyd fra 24. oktober", item["history"][1]["note"])
        self.assertEqual(before["history"], item["history"][2:])
        self.assertEqual(before["versions"], item["versions"])
        self.assertEqual([self.claim_id], self.ids("clarification", ""))
        self.assertEqual([self.claim_id], self.ids("archive"))
        self.assertEqual([], self.ids("active"))
        self.assertEqual([], self.ids("signals"))
        self.assertEqual(4, self.kb.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])

    def test_reject_and_leave_unresolved_keep_archive_and_close_clarification(self):
        with patch("investkb.repository.now_iso", return_value="2026-09-06T10:00:00+00:00"):
            self.kb.clarify_legacy(self.claim_id, True, "Mangler kilde")
            self.kb.set_review(self.claim_id, "rejected", "Reklame")
            self.assertEqual([], self.ids("clarification", ""))
            self.assertEqual([self.claim_id], self.ids("archive"))
            self.kb.clarify_legacy(self.claim_id, True, "Overvej igen med originalen")
            self.kb.clarify_legacy(self.claim_id, False)
        item = self.kb.claim_detail(self.claim_id)
        self.assertEqual("uncertain", item["review_status"])
        self.assertEqual("left_unresolved", item["history"][0]["event_type"])
        self.assertTrue(item["history"][0]["note"])
        self.assertEqual([], self.ids("clarification", ""))
        self.assertEqual([self.claim_id], self.ids("archive"))
        self.assertEqual([], self.ids("active"))

    def test_approval_closes_clarification_and_reopening_returns_to_archive(self):
        self.kb.clarify_legacy(self.claim_id, True, "Læs kilden igen")
        self.kb.set_review(self.claim_id, "approved")
        self.assertEqual([], self.ids("clarification", ""))
        self.kb.clarify_legacy(self.claim_id, False, "Behøver yderligere kontrol")
        self.assertEqual([], self.ids("active"))
        self.assertEqual([self.claim_id], self.ids("archive"))

    def test_invalid_decisions_do_not_write_partial_history(self):
        before = self.snapshot()
        for action in (
            lambda: self.kb.clarify_legacy(self.claim_id, True, "  "),
            lambda: self.kb.correct_claim(self.claim_id, "", "Begrundelse"),
            lambda: self.kb.correct_claim(self.claim_id, "Rettelse", ""),
            lambda: self.kb.correct_claim(self.claim_id, "Dokumenteret udsagn om energi.", "Ingen ændring"),
            lambda: self.kb.set_review(self.claim_id, "invented"),
        ):
            with self.assertRaises(ValidationError):
                action()
            self.assertEqual(before, self.snapshot())
        with self.kb.conn:
            self.kb.conn.execute("UPDATE sources SET dataset='active'")
        with self.assertRaises(ValidationError):
            self.kb.clarify_legacy(self.claim_id, True, "Mangler")

    def test_insufficient_evidence_blocks_approval_and_correction_atomically(self):
        mutations = [
            ("UPDATE evidence SET excerpt=NULL, start_ref=NULL, end_ref=NULL", ()),
            ("UPDATE evidence SET excerpt='Findes ikke i originalen'", ()),
            ("UPDATE extraction_runs SET provider='legacy-knowledge-base-migration'", ()),
            ("UPDATE evidence SET start_ref='2025-10-24'", ()),
        ]
        for sql, params in mutations:
            with self.subTest(sql=sql):
                self.kb.conn.execute("SAVEPOINT bad_evidence")
                self.kb.conn.execute(sql, params)
                before = self.snapshot()
                for action in (
                    lambda: self.kb.set_review(self.claim_id, "approved"),
                    lambda: self.kb.set_review(self.claim_id, "corrected"),
                    lambda: self.kb.correct_claim(self.claim_id, "Rettet energiudsagn", "Kontrolleret"),
                ):
                    with self.assertRaises(ValidationError):
                        action()
                    self.assertEqual(before, self.snapshot())
                self.kb.conn.execute("ROLLBACK TO bad_evidence")
                self.kb.conn.execute("RELEASE bad_evidence")

    def test_missing_or_changed_original_blocks_legacy_approval(self):
        item = self.kb.claim_detail(self.claim_id)
        stored = Path(item["stored_path"])
        original = stored.read_bytes()
        stored.write_bytes(original + b" modified")
        with self.assertRaisesRegex(ValidationError, "hash"):
            self.kb.set_review(self.claim_id, "approved")
        stored.unlink()
        with self.assertRaisesRegex(ValidationError, "ikke læses"):
            self.kb.set_review(self.claim_id, "approved")

    def test_archived_and_superseded_sources_are_only_in_archive(self):
        self.kb.set_review(self.claim_id, "approved")
        for table, field, value in (
            ("sources", "archived_at", "2026-09-06"),
            ("source_versions", "archived_at", "2026-09-06"),
            ("source_versions", "is_current", 0),
        ):
            with self.subTest(table=table, field=field):
                self.kb.conn.execute("SAVEPOINT archived")
                self.kb.conn.execute(f"UPDATE {table} SET {field}=?", (value,))
                self.assertEqual([], self.ids("active"))
                self.assertEqual([self.claim_id], self.ids("archive"))
                self.assertEqual([], self.ids("signals"))
                self.kb.conn.execute("ROLLBACK TO archived")
                self.kb.conn.execute("RELEASE archived")

    def test_restoring_duplicate_old_version_rolls_back_instead_of_corrupting_current(self):
        self.kb.correct_claim(self.claim_id, "Præciseret energiudsagn", "Præcisering")
        before = self.snapshot()
        with self.assertRaisesRegex(ValidationError, "tidligere version"):
            self.kb.correct_claim(self.claim_id, "Dokumenteret udsagn om energi.", "Tilbage til den gamle")
        self.assertEqual(before, self.snapshot())

    def test_http_all_actions_navigation_history_and_evidence_guard(self):
        server, app = create_server(self.kb.db_path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        context = {"origin": "search", "q": "energi & <test>", "lane": "archive"}

        def get(path):
            with urlopen(base + path, timeout=5) as response:
                return response.read().decode("utf-8")

        def post(action, **extra):
            fields = {"csrf_token": app.csrf_token, "claim_id": self.claim_id,
                      "action": action, "return_to": "claim", **context, **extra}
            with urlopen(Request(base + "/review", data=urlencode(fields).encode()), timeout=5) as response:
                self.assertTrue(response.url.startswith(base + "/claim?"))
                return response.read().decode("utf-8")

        try:
            page = get("/search?lane=archive&q=energi")
            self.assertIn("Legacy-oprindelse", page)
            self.assertIn("origin=search", html.unescape(page))
            page = get("/claim?" + urlencode({"id": self.claim_id, **context}))
            self.assertIn("Tilbage til arkivsøgning", page)
            self.assertIn(html.escape("/search?" + urlencode({"q": context["q"], "lane": "archive"})), page)
            for label in ("Godkend som aktiv viden", "Ret og godkend", "Afvis", "Kræver originalkilde", "Lad stå uafklaret"):
                self.assertIn(label, page)
            self.assertIn("Tilbage til gennemgang", get("/claim?id=legacy-test&origin=review"))
            self.assertIn("Tilbage til afklaringslisten", get("/claim?id=legacy-test&origin=search&lane=clarification"))
            for action in ("require_source", "leave_unresolved", "reject", "approve", "correct"):
                with self.subTest(action=action):
                    page = post(action, note="Find originalen <script>alert(1)</script>", summary="Præciseret energiudsagn")
                    self.assertIn("Tilbage til arkivsøgning", page)
                    self.assertIn("Legacy-oprindelse", page)
                    self.assertNotIn("<script>", page)
                    self.assertIn("&lt;script&gt;", page)
                    if action == "require_source":
                        self.assertIn("legacy-test", get("/search?lane=clarification"))
                        self.assertIn("Afklaringsnotat", get("/search?lane=clarification"))
            self.assertNotIn("legacy-test", get("/search?lane=archive&q=energi"))
            self.assertIn("Legacy-oprindelse", get("/search?" + urlencode({"lane": "active", "q": "Præciseret"})))
            self.assertIn("Version 2", page)
            with self.kb.conn:
                self.kb.conn.execute("UPDATE evidence SET start_ref='2025-10-24'")
                self.kb.conn.execute("UPDATE extraction_runs SET provider='legacy-knowledge-base-migration'")
            page = get("/claim?id=legacy-test")
            self.assertIn("2026-05-05", page)
            self.assertIn("2025-10-24", page)
            self.assertIn("Datouoverensstemmelse", page)
            self.assertIn('value="approve" disabled', page)
            self.assertIn('value="correct" disabled', page)
            before = self.snapshot()
            for action in ("approve", "correct"):
                with self.assertRaises(HTTPError) as error:
                    post(action, summary="Forkert godkendelse", note="Ignorer blokeringen")
                self.assertEqual(400, error.exception.code)
                error.exception.close()
            with self.assertRaises(HTTPError) as error:
                post("reject", csrf_token="wrong")
            self.assertEqual(403, error.exception.code)
            error.exception.close()
            self.assertEqual(before, self.snapshot())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_context_never_substitutes_unrelated_beginning_of_source(self):
        self.assertIsNone(_source_context(self.source, "Et manglende citat"))
        self.assertIn("Mere kontekst", _source_context(self.source, "Dokumenteret udsagn om energi."))
        self.source.write_text("Samme citat. Første dato. Samme citat. Anden dato.", encoding="utf-8")
        self.assertIn("placering og dato er ikke verificeret", _source_context(self.source, "Samme citat."))


if __name__ == "__main__":
    unittest.main()
