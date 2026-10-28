"""Synthetic batch discovery plus the unchanged handoff and consumer."""
import copy
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

    def test_consumer_identity_conflict_blocks_before_database_write(self):
        self.initialize()
        self.package("run-a", identifier="first", text="First version")
        self.assertTrue(self.sync(import_requested=True)["ok"])
        original = (self.state / "knowledgebase.sqlite").read_bytes()
        # A distinct JSON filename, but the same episode identity in the DB.
        payload = episode_data("first", "first", "Changed transcript", "trpkg-different")
        (self.delivery / "Synthetic/second.json").write_text(json.dumps(payload))
        result = self.sync(import_requested=True)
        self.assertFalse(result["ok"])
        self.assertIn("Consumer preview", result["import_error"])
        self.assertEqual(original, (self.state / "knowledgebase.sqlite").read_bytes())

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
