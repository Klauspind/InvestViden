import hashlib
import json
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.intake import InputRegistry, _readable, apply_input, plan_input
from investkb.repository import KnowledgeBase
from investkb.validation import ValidationError
from investkb.web_app import create_server


class _GuardedPath:
    def __init__(self, resolved: Path, *, linked: bool = False, flags: int = 0, size: int = 1):
        self._resolved = resolved
        self._linked = linked
        self._flags = flags
        self._size = size

    def resolve(self):
        return self._resolved

    def is_symlink(self):
        return self._linked

    def is_junction(self):
        return False

    def stat(self):
        return SimpleNamespace(st_file_attributes=self._flags, st_size=self._size)


class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database_path = self.root / "database" / "kb.sqlite"
        self.kb = KnowledgeBase(self.database_path)
        self.kb.initialize()
        self.workspace = self.root / "intake-workspace"
        self.registry = InputRegistry(self.workspace)

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def register(self, folder: Path, *, permission: str = "ask", format: str = "text"):
        return self.registry.register(
            str(folder), "report", permission, "Testudgiver", "da", format
        )

    def episode_json(self, folder: Path) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "2026-09-10 Syntetisk episode.json"
        data = {
            "schema_version": "2.0",
            "id": "synthetic-episode-1",
            "source": {
                "filename": "2026-09-10 Syntetisk episode.mp3",
                "duration_seconds": 65.2,
                "language": "da",
                "podcast": "Testpodcast",
                "title": "Syntetisk episode",
                "published": "2026-09-10",
                "processing": {
                    "timestamp": "20260910_120000",
                    "processor": "synthetic-test",
                },
            },
            "transcription": {"provider": "test", "model": "synthetic"},
            "quality": {"score": 95, "grade": "A"},
            "segments": [
                {"id": 1, "start": 1.2, "end": 3.1, "text": "Første udsagn."},
                {"id": 2, "start": 61.0, "end": 65.2, "text": "Andet udsagn."},
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_registry_persists_and_rejects_workspace_or_overlapping_roots(self):
        private = self.root / "private"
        private.mkdir()
        registered = self.register(private)

        self.assertEqual([registered], self.registry.roots())
        self.assertEqual("ask", registered["permission"])
        self.assertEqual("report", registered["source_type"])

        with self.assertRaisesRegex(ValidationError, "arbejdsmappe"):
            self.register(self.workspace)

        child = private / "child"
        child.mkdir()
        with self.assertRaisesRegex(ValidationError, "overlapper"):
            self.register(child)

    def test_text_preview_selected_import_policy_and_backup(self):
        private = self.root / "private"
        private.mkdir()
        first = private / "2026-09-01 Første rapport.txt"
        duplicate = private / "kopi.md"
        second = private / "2026-09-02 Anden rapport.md"
        first.write_text("Syntetisk indhold A", encoding="utf-8")
        duplicate.write_text("Syntetisk indhold A", encoding="utf-8")
        second.write_text("Syntetisk indhold B", encoding="utf-8")
        before = {path: path.read_bytes() for path in (first, duplicate, second)}

        plan = plan_input(self.kb, self.register(private))
        self.assertEqual([], plan["errors"])
        self.assertEqual(["duplicate", "new", "new"], sorted(item.status for item in plan["items"]))
        selected = [index for index, item in enumerate(plan["items"]) if item.status == "new"]
        result = apply_input(self.kb, plan, selected, self.workspace)

        self.assertEqual(2, len(result["imported"]))
        self.assertEqual([], result["errors"])
        self.assertEqual("ok", result["backup"]["integrity"])
        self.assertTrue(Path(result["backup"]["path"]).is_file())
        self.assertEqual(2, len(self.kb.source_policies()))
        self.assertEqual({"ask"}, {row["ai_permission"] for row in self.kb.source_policies()})
        self.assertEqual(0, self.kb.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0])
        self.assertEqual(before, {path: path.read_bytes() for path in before})

        second_plan = plan_input(self.kb, plan["root"])
        self.assertEqual({"existing"}, {item.status for item in second_plan["items"]})

    def test_changed_file_aborts_before_any_import_or_backup(self):
        private = self.root / "private"
        private.mkdir()
        source = private / "2026-09-03 Stabil rapport.txt"
        source.write_text("Før preview", encoding="utf-8")
        plan = plan_input(self.kb, self.register(private))

        source.write_text("Ændret efter preview", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "ændret"):
            apply_input(self.kb, plan, [0], self.workspace)

        self.assertEqual(0, self.kb.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
        self.assertFalse((self.workspace / "backups").exists())

    def test_existing_input_path_with_changed_content_is_a_version_conflict(self):
        private = self.root / "private"
        private.mkdir()
        source = private / "2026-09-04 Versionskilde.txt"
        source.write_text("Version et", encoding="utf-8")
        root = self.register(private)
        first_plan = plan_input(self.kb, root)
        apply_input(self.kb, first_plan, [0], self.workspace)

        source.write_text("Version to", encoding="utf-8")
        conflict_plan = plan_input(self.kb, root)
        self.assertEqual("conflict", conflict_plan["items"][0].status)
        with self.assertRaisesRegex(ValidationError, "Kun nye filer"):
            apply_input(self.kb, conflict_plan, [0], self.workspace)
        self.assertEqual(1, self.kb.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])

    def test_all_ai_permissions_are_enforced_for_imported_sources(self):
        imported = {}
        for index, permission in enumerate(("allow", "ask", "local_only", "blocked")):
            private = self.root / f"private-{permission}"
            private.mkdir()
            (private / f"2026-09-{index + 5:02d} Kilde.txt").write_text(
                f"Syntetisk {permission}", encoding="utf-8"
            )
            plan = plan_input(self.kb, self.register(private, permission=permission))
            source_id = apply_input(self.kb, plan, [0], self.workspace)["imported"][0]
            policy = next(row for row in self.kb.source_policies() if row["id"] == source_id)
            imported[permission] = (source_id, policy["sha256"])

        allow_id, allow_hash = imported["allow"]
        self.assertTrue(self.kb.external_ai_allowed(allow_id, allow_hash))
        ask_id, ask_hash = imported["ask"]
        self.assertFalse(self.kb.external_ai_allowed(ask_id, ask_hash))
        self.assertTrue(self.kb.external_ai_allowed(ask_id, ask_hash, {ask_id: ask_hash}))
        self.assertFalse(self.kb.external_ai_allowed(ask_id, ask_hash, {ask_id: "0" * 64}))
        for permission in ("local_only", "blocked"):
            source_id, source_hash = imported[permission]
            self.assertFalse(self.kb.external_ai_allowed(source_id, source_hash, {source_id: source_hash}))

    def test_podcast_json_import_renders_timestamps_and_records_provenance(self):
        private = self.root / "podcasts"
        source = self.episode_json(private)
        original = source.read_bytes()
        plan = plan_input(self.kb, self.register(private, permission="allow", format="podcast_json"))

        self.assertEqual([], plan["errors"])
        self.assertEqual("new", plan["items"][0].status)
        result = apply_input(self.kb, plan, [0], self.workspace)
        source_id = result["imported"][0]
        provenance = self.kb.conn.execute(
            "SELECT * FROM source_provenance WHERE source_id=?", (source_id,)
        ).fetchone()
        stored_path = Path(self.kb.source_by_hash(hashlib.sha256(plan["items"][0].content).hexdigest())["stored_path"])

        self.assertIsNotNone(provenance)
        self.assertEqual("testpodcast|2026-09-10|synthetic-episode-1", provenance["episode_key"])
        self.assertIn("[00:00:01–00:00:04] Første udsagn.", stored_path.read_text(encoding="utf-8"))
        self.assertEqual(original, source.read_bytes())

    def test_links_and_cloud_only_placeholders_are_rejected(self):
        inside = self.root / "private" / "source.txt"
        inside.parent.mkdir()
        with self.assertRaisesRegex(ValidationError, "Links"):
            _readable(_GuardedPath(inside, linked=True), inside.parent)
        with self.assertRaisesRegex(ValidationError, "kun i skyen"):
            _readable(_GuardedPath(inside, flags=0x1000), inside.parent)

    def test_http_flow_registers_previews_and_imports_without_ai(self):
        self.kb.close()
        private = self.root / "http-private"
        private.mkdir()
        source = private / "2026-09-12 HTTP rapport.txt"
        original = b"Syntetisk HTTP-kilde"
        source.write_bytes(original)
        server, app = create_server(self.database_path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            register_payload = urlencode({
                "csrf_token": app.csrf_token,
                "action": "register",
                "path": str(private),
                "format": "text",
                "source_type": "report",
                "publisher": "Testudgiver",
                "language": "da",
                "permission": "local_only",
            }).encode("utf-8")
            with urlopen(Request(base_url + "/inputs", data=register_payload), timeout=5) as response:
                self.assertIn("Inputmappen er registreret", response.read().decode("utf-8"))

            root_id = app.inputs.roots()[0]["id"]
            scan_payload = urlencode({
                "csrf_token": app.csrf_token,
                "action": "scan",
                "root_id": root_id,
            }).encode("utf-8")
            with urlopen(Request(base_url + "/inputs", data=scan_payload), timeout=5) as response:
                preview = response.read().decode("utf-8")
            self.assertIn("Ingen filer er importeret endnu", preview)
            self.assertIn("Kun lokal AI", preview)
            plan_id = re.search(r'name="plan_id" value="([^"]+)"', preview).group(1)

            import_payload = urlencode([
                ("csrf_token", app.csrf_token),
                ("action", "import"),
                ("plan_id", plan_id),
                ("selected", "0"),
            ]).encode("utf-8")
            with urlopen(Request(base_url + "/inputs", data=import_payload), timeout=5) as response:
                result = response.read().decode("utf-8")
            self.assertIn("1 nye kilder importeret", result)
            self.assertIn("Der er ikke sendt tekst til AI", result)
            self.assertIn("Integritet: ok", result)
            self.assertEqual(original, source.read_bytes())

            with KnowledgeBase(self.database_path) as check:
                check.initialize()
                policies = check.source_policies()
                self.assertEqual(1, len(policies))
                self.assertEqual("local_only", policies[0]["ai_permission"])
                self.assertEqual(0, check.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            self.kb = KnowledgeBase(self.database_path)


if __name__ == "__main__":
    unittest.main()
