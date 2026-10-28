"""Synthetic batch discovery plus the unchanged handoff and consumer."""
import copy
import hashlib
from collections import Counter
from contextlib import closing, nullcontext, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from test_transskribinator_consumer import episode_data

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sync_transskribinator_podcasts.py"
spec = importlib.util.spec_from_file_location("iv020_sync", SCRIPT)
syncer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(syncer)
from investkb.repository import KnowledgeBase
from investkb.mistral_jobs import create_mistral_job
from investkb.intake import plan_input
from investkb.podcast_sync import read_episode, render_episode


class PodcastSyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.app, self.data, self.delivery, self.state = [self.root / p for p in
                                                        ("app", "data", "delivery", "state")]
        self.app.mkdir()
        self.data.mkdir()
        paths = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), paths))
        modules = {name: types.ModuleType(name) for name in
                   ("tools.podcast_delivery", "transskribering.batch", "transskribering.service")}

        def verify(package):
            value = json.loads((package / "transcript.json").read_text())
            if value.get("corrupt"):
                raise ValueError("Synthetic corrupt package")
            return {"transcription": {"profile": value["profile"]}}

        def adapter(package, output):
            value = json.loads((package / "transcript.json").read_text())
            payload = copy.deepcopy(value["episode"])
            target = output / "Synthetic" / (payload["id"] + ".json")
            target.parent.mkdir()
            payload["source"].update(created_at=str(output), original_path=str(output))
            target.write_text(json.dumps(payload), encoding="utf-8")
            return "delivered"

        modules["transskribering.service"].verify_package = verify
        modules["transskribering.batch"].batch_lock = nullcontext
        modules["tools.podcast_delivery"].deliver_one = adapter
        context = patch.dict(sys.modules, modules)
        context.start()
        self.addCleanup(context.stop)
        no_transport = patch("socket.create_connection", side_effect=AssertionError("No external AI"))
        no_transport.start()
        self.addCleanup(no_transport.stop)

    def package(self, name, *, identifier=None, complete=True, profile="podcast-legacy", corrupt=False, text=None):
        package = self.data / name
        package.mkdir(parents=True)
        identifier = identifier or name.replace("/", "-")
        value = {"profile": {"id": profile, "version": "1"}, "corrupt": corrupt,
                 "episode": episode_data(identifier, identifier, text or f"Synthetic {identifier}.",
                                         f"trpkg-{identifier}")}
        (package / "transcript.json").write_text(json.dumps(value), encoding="utf-8")
        if complete:
            (package / "COMPLETE.json").write_text("{}", encoding="utf-8")
        return package

    def sync(self, **kwargs):
        return syncer.sync(self.app, self.data, self.delivery, self.state, **kwargs)

    def initialize(self):
        with KnowledgeBase(self.state / "knowledgebase.sqlite") as kb:
            kb.initialize()

    def test_discovery_repeat_and_no_implicit_import(self):
        self.package("results/run-a")
        self.package("podcasts/nested/run-b")
        self.package("results/run-unfinished", complete=False)
        self.package("results/.partial-hidden")
        self.package("results/run-general", profile="general-none")
        originals = {p: p.read_bytes() for p in self.data.rglob("*") if p.is_file()}
        with patch.object(syncer, "_import_deliveries", side_effect=AssertionError("No implicit import")):
            first = self.sync()
            delivered = {p: p.read_bytes() for p in self.delivery.rglob("*.json")}
            second = self.sync()
        self.assertTrue(first["ok"])
        self.assertEqual((2, 0, 1, 1), tuple(first[k] for k in
                         ("new_deliveries", "existing_deliveries", "incomplete_packages", "non_podcast_packages")))
        self.assertEqual((0, 2), (second["new_deliveries"], second["existing_deliveries"]))
        self.assertFalse(self.state.exists())
        self.assertEqual(delivered, {p: p.read_bytes() for p in delivered})
        self.assertEqual(originals, {p: p.read_bytes() for p in originals})

    def test_conflict_keeps_delivery_and_blocks_import(self):
        self.package("run-a", identifier="same")
        self.sync()
        target = next(self.delivery.rglob("*.json"))
        original = target.read_bytes()
        self.package("run-b", identifier="same", text="Different version of same episode.")
        with patch.object(syncer, "_import_deliveries", side_effect=AssertionError("No import on failure")):
            result = self.sync(import_requested=True)
        self.assertFalse(result["ok"])
        self.assertEqual(1, len(result["rejected_packages"]))
        self.assertEqual(original, target.read_bytes())
        self.assertFalse(self.state.exists())

    def test_corrupt_complete_package_is_reported_and_blocks_import(self):
        self.package("run-corrupt", corrupt=True)
        with patch.object(syncer, "_import_deliveries", side_effect=AssertionError("No import on failure")):
            result = self.sync(import_requested=True)
        self.assertFalse(result["ok"])
        self.assertEqual(1, len(result["rejected_packages"]))
        self.assertFalse(self.delivery.exists())

    def test_explicit_import_backup_drafts_and_idempotent_repeat(self):
        self.initialize()
        with KnowledgeBase(self.state / "knowledgebase.sqlite") as kb:
            source = self.root / "existing.txt"
            source.write_text("Synthetic existing source", encoding="utf-8")
            source_id, _ = kb.import_source(source, "report", source_store=self.state / "sources",
                                            ai_permission="allow")
            existing_job = create_mistral_job(kb, self.state / "incoming", source_ids=[source_id])
        self.package("run-a")
        self.package("run-b")
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = syncer.main(["--producer-app", str(self.app), "--data-root", str(self.data),
                                    "--delivery-root", str(self.delivery), "--state-root", str(self.state),
                                    "--import"])
        self.assertEqual(0, exit_code, output.getvalue())
        first = json.loads(output.getvalue())
        self.assertTrue(first["ok"], first)
        self.assertEqual((2, 2, 0), tuple(first["consumer"][k] for k in
                         ("new_imported", "draft_jobs_created", "external_ai_calls")))
        backup = first["consumer"]["preimport_backup"]
        self.assertEqual("ok", backup["integrity"])
        with closing(sqlite3.connect(backup["path"])) as connection:
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0])
        second = self.sync(import_requested=True)
        self.assertEqual((0, 2, 0), tuple(second["consumer"][k] for k in
                         ("new_imported", "existing", "draft_jobs_created")))
        self.assertEqual("not_needed", second["consumer"]["preimport_backup"])
        with KnowledgeBase(self.state / "knowledgebase.sqlite") as kb:
            self.assertEqual("draft", kb.ai_job(existing_job["id"])["status"])
            self.assertEqual({"draft"}, {job["status"] for job in kb.ai_jobs()})
            self.assertEqual(0, kb.conn.execute("SELECT SUM(attempt_count) FROM ai_job_items").fetchone()[0])

    def test_no_migration_or_implicit_database_creation(self):
        self.package("run-a")
        result = self.sync(import_requested=True)
        self.assertFalse(result["ok"])
        self.assertFalse(self.state.exists())
        self.state.mkdir()
        database = self.state / "knowledgebase.sqlite"
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
            connection.execute("INSERT INTO schema_version VALUES (1, 'synthetic')")
        original = database.read_bytes()
        result = self.sync(import_requested=True)
        self.assertFalse(result["ok"])
        self.assertEqual(original, database.read_bytes())

    def test_consumer_identity_conflict_is_skipped_without_database_write(self):
        self.initialize()
        self.package("run-a", identifier="first", text="First version")
        self.assertTrue(self.sync(import_requested=True)["ok"])
        original = (self.state / "knowledgebase.sqlite").read_bytes()
        # A distinct JSON filename, but the same episode identity in the DB.
        payload = episode_data("first", "first", "Changed transcript", "trpkg-different")
        (self.delivery / "Synthetic/second.json").write_text(json.dumps(payload))
        result = self.sync(import_requested=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual((0, 1, 1), tuple(result["consumer"][key] for key in
                                        ("new_imported", "existing", "conflicts")))
        self.assertEqual(original, (self.state / "knowledgebase.sqlite").read_bytes())

    def delivery_file(self, name, payload):
        self.delivery.mkdir(exist_ok=True)
        path = self.delivery / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_import_only_mixed_30_existing_32_new_29_conflicts_and_repeat(self):
        self.initialize()
        originals = [episode_data(f"old-{i}", f"Original {i}", f"Original text {i}.", f"trpkg-old-{i}")
                     for i in range(30)]
        for i, payload in enumerate(originals):
            self.delivery_file(f"old-{i:02}.json", payload)
        self.assertEqual(30, syncer.import_only(self.delivery, self.state)["consumer"]["new_imported"])
        database = self.state / "knowledgebase.sqlite"
        with KnowledgeBase(database) as kb:
            ids = [kb.source_by_episode_key(read_episode(self.delivery / f"old-{i:02}.json").episode_key)["id"]
                   for i in range(30)]
            for source_id, policy in zip(ids, ("ask", "local_only", "blocked")):
                kb.set_source_permission(source_id, policy)
            preserved = {table: [tuple(row) for row in kb.conn.execute(f"SELECT * FROM {table}")]
                         for table in ("sources", "source_versions", "source_provenance", "ai_jobs", "ai_job_items")}
        for i in range(32):
            payload = episode_data(f"new-{i}", f"New {i}", f"New text {i}.", f"trpkg-new-{i}")
            payload["source"]["published"] = "2026-10-01"
            self.delivery_file(f"new-{i:02}.json", payload)
        conflicts = []
        for i in range(29):
            payload = copy.deepcopy(originals[i])
            payload["segments"][0]["text"] = f"Conflicting alternative {i}."
            conflicts.append(self.delivery_file(f"conflict-{i:02}.json", payload))
        with KnowledgeBase(database) as kb:
            plan = plan_input(kb, syncer.consumer._root_config(self.delivery))
            self.assertEqual(Counter(existing=30, new=32, conflict=29), Counter(item.status for item in plan["items"]))
        files = {p: p.read_bytes() for p in self.delivery.rglob("*.json")}
        output = io.StringIO()
        with patch.object(syncer, "deliver", side_effect=AssertionError("No redelivery")), \
                patch.object(syncer, "_packages", side_effect=AssertionError("No producer scan")), redirect_stdout(output):
            code = syncer.main(["--import-only", "--delivery-root", str(self.delivery), "--state-root", str(self.state)])
        result = json.loads(output.getvalue())["consumer"]
        self.assertEqual(0, code, output.getvalue())
        self.assertEqual((32, 30, 29, 0, 32), tuple(result[key] for key in
                         ("new_imported", "existing", "conflicts", "rejected", "draft_jobs_created")))
        with closing(sqlite3.connect(result["preimport_backup"]["path"])) as connection:
            self.assertEqual(30, connection.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0])
            self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
        with KnowledgeBase(database) as kb:
            for table, rows in preserved.items():
                current = {tuple(row) for row in kb.conn.execute(f"SELECT * FROM {table}")}
                self.assertTrue(set(rows).issubset(current), table)
            for path in conflicts:
                digest = hashlib.sha256(render_episode(read_episode(path)).encode("utf-8")).hexdigest()
                self.assertIsNone(kb.source_by_hash(digest))
            for path in self.delivery.glob("new-*.json"):
                episode = read_episode(path)
                row = kb.source_by_episode_key(episode.episode_key)
                self.assertEqual(hashlib.sha256(render_episode(episode).encode("utf-8")).hexdigest(), row["sha256"])
                provenance = kb.conn.execute("SELECT * FROM source_provenance WHERE source_id=?", (row["id"],)).fetchone()
                self.assertEqual(episode.json_sha256, provenance["upstream_sha256"])
            self.assertEqual(0, kb.conn.execute("SELECT SUM(attempt_count) FROM ai_job_items").fetchone()[0])
        unchanged = database.read_bytes()
        repeat = syncer.import_only(self.delivery, self.state)["consumer"]
        self.assertEqual((0, 62, 29, 0), tuple(repeat[key] for key in
                         ("new_imported", "existing", "conflicts", "draft_jobs_created")))
        self.assertEqual("not_needed", repeat["preimport_backup"])
        self.assertEqual(unchanged, database.read_bytes())
        self.assertEqual(files, {path: path.read_bytes() for path in files})

    def test_repeated_identity_quarantines_first_new_and_duplicates(self):
        self.initialize()
        first = episode_data("same", "Same", "First variant", "trpkg-first")
        second = episode_data("same", "Same", "Second variant", "trpkg-second")
        self.delivery_file("a.json", first)
        self.delivery_file("b.json", second)
        self.delivery_file("c.json", first)
        self.delivery_file("safe.json", episode_data("safe", "Unrelated", "Safe text", "trpkg-safe"))
        result = syncer.import_only(self.delivery, self.state)["consumer"]
        self.assertEqual((1, 2, 1, 1), tuple(result[key] for key in
                         ("new_imported", "conflicts", "duplicates", "quarantined_new")))
        with KnowledgeBase(self.state / "knowledgebase.sqlite") as kb:
            self.assertIsNone(kb.source_by_episode_key(read_episode(self.delivery / "a.json").episode_key))
        repeat = syncer.import_only(self.delivery, self.state)["consumer"]
        self.assertEqual((0, 2, 1), tuple(repeat[key] for key in ("new_imported", "conflicts", "duplicates")))
        unchanged = (self.state / "knowledgebase.sqlite").read_bytes()
        self.delivery_file("another.json", episode_data("another", "Another", "New safe text", "trpkg-another"))
        (self.delivery / "unreadable.json").write_text("not valid JSON")
        rejected = syncer.import_only(self.delivery, self.state)["consumer"]
        self.assertFalse(rejected["ok"])
        self.assertEqual((0, 1, 1), tuple(rejected[key] for key in ("new_imported", "new_eligible", "rejected")))
        self.assertEqual(unchanged, (self.state / "knowledgebase.sqlite").read_bytes())

    def test_legacy_title_match_remains_a_conflict_without_provenance_key_match(self):
        self.initialize()
        with KnowledgeBase(self.state / "knowledgebase.sqlite") as kb:
            source = self.root / "legacy.txt"
            source.write_text("Legacy transcript", encoding="utf-8")
            kb.import_source(source, "podcast_transcript", title="Market outlook", publisher="Synthetic",
                             published_at="2026-09-29", source_store=self.state / "sources", ai_permission="ask")
        path = self.delivery_file("legacy-match.json", episode_data("fresh-id", "Market outlook for Europe",
                                                                  "Different text", "trpkg-fresh"))
        with KnowledgeBase(self.state / "knowledgebase.sqlite") as kb:
            self.assertIsNone(kb.source_by_episode_key(read_episode(path).episode_key))
            self.assertEqual("conflict", plan_input(kb, syncer.consumer._root_config(self.delivery))["items"][0].status)
        unchanged = (self.state / "knowledgebase.sqlite").read_bytes()
        result = syncer.import_only(self.delivery, self.state)["consumer"]
        self.assertEqual((0, 1, 0), tuple(result[key] for key in ("new_imported", "conflicts", "draft_jobs_created")))
        self.assertEqual(unchanged, (self.state / "knowledgebase.sqlite").read_bytes())

    def test_empty_root_is_a_noop_and_overlapping_paths_are_rejected(self):
        self.assertTrue(self.sync(import_requested=True)["ok"])
        self.assertFalse(self.state.exists())
        for delivery in (self.data, self.data / "nested", self.root):
            with self.subTest(delivery=delivery), self.assertRaises(ValueError):
                syncer.sync(self.app, self.data, delivery)
        with self.assertRaises(ValueError):
            syncer.sync(self.app, self.data, self.delivery, self.data / "state", import_requested=True)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell parser requires pwsh")
    def test_powershell_entrypoint_parses(self):
        script = str(ROOT / "SYNKRONISER_PODCASTS.ps1").replace("'", "''")
        result = subprocess.run(["pwsh", "-NoProfile", "-Command",
            f"$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$tokens, [ref]$errors) | Out-Null; if ($errors.Count) {{ $errors; exit 1 }}"],
            capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
