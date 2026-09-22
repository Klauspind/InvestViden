"""Synthetic consumer contracts; never opens a user's database or network."""
import copy
import hashlib
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from investkb.intake import InputRegistry, apply_input, plan_input
from investkb.podcast_sync import apply_podcast_sync, plan_podcast_sync, read_episode
from investkb.repository import KnowledgeBase


def episode_data():
    return {
        "schema_version": "2.0", "id": "synthetic-derivation",
        "source": {"podcast": "Synthetic", "title": "Synthetic episode",
                   "published": "2026-09-22", "language": "da"},
        "segments": [{"id": 2, "start": 1, "end": 2, "text": "Synthetic text."}],
        "derivation": {
            "schema_version": "podcast-legacy-derivation-v1", "package_id": "trpkg-synthetic",
            "source_sha256": "a" * 64, "transcript_sha256": "b" * 64,
            "postprocess_input_sha256": "c" * 64, "canonical_schema_version": "1.0",
            "canonical_segment_count": 3,
        },
        "segment_accounting": {"input": 3, "kept": 1, "removed": 2,
                               "advertisement": 2, "empty_after_cleaning": 0},
    }


class PodcastDerivationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "fresh.sqlite")
        self.kb.initialize()
        self.workspace = self.root / "workspace"
        self.registry = InputRegistry(self.workspace)
        self.source = self.root / "episodes" / "Synthetic" / "2026-09-22 episode.json"
        self.source.parent.mkdir(parents=True)
        self.write(episode_data())

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def write(self, data):
        self.source.write_text(json.dumps(data), encoding="utf-8")

    def register(self, path, format="podcast_json"):
        return self.registry.register(str(path), "podcast_transcript", "local_only",
                                      "Synthetic", "da", format)

    def test_direct_import_preserves_chain_and_accounting_in_sqlite_and_is_idempotent(self):
        original = self.source.read_bytes()
        root = self.register(self.source.parent)
        plan = plan_input(self.kb, root)
        self.assertEqual([], plan["errors"])
        applied = apply_input(self.kb, plan, [0], self.workspace)
        self.assertEqual([], applied["errors"])
        self.assertEqual(1, len(applied["imported"]))
        row = self.kb.conn.execute("SELECT * FROM source_provenance").fetchone()
        upstream = json.loads(row["metadata_json"])["upstream"]
        self.assertEqual(episode_data()["derivation"], upstream["derivation"])
        self.assertEqual(episode_data()["segment_accounting"], upstream["segment_accounting"])
        self.assertEqual(hashlib.sha256(original).hexdigest(), row["upstream_sha256"])
        self.assertEqual("existing", plan_input(self.kb, root)["items"][0].status)
        self.assertEqual(1, self.kb.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
        self.assertEqual(0, self.kb.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0])
        self.assertEqual(original, self.source.read_bytes())

    def test_sync_sidecar_and_text_intake_preserve_chain_without_upstream_files(self):
        plan = plan_podcast_sync(self.kb, self.source.parent.parent, self.root / "rendered")
        result = apply_podcast_sync(plan)
        self.assertEqual([], result["errors"])
        sidecar = json.loads(Path(result["sidecars"][0]).read_text(encoding="utf-8"))
        self.assertEqual(episode_data()["derivation"], sidecar["upstream"]["derivation"])
        # Upstream hashes are carried claims; no original/canonical file is opened.
        self.source.unlink()
        text_root = self.register(self.root / "rendered", "text")
        intake = plan_input(self.kb, text_root)
        self.assertEqual([], intake["errors"])
        imported = apply_input(self.kb, intake, [0], self.workspace)
        self.assertEqual([], imported["errors"])
        stored = self.kb.conn.execute("SELECT metadata_json FROM source_provenance").fetchone()[0]
        self.assertEqual(sidecar, json.loads(stored))

    def test_legacy_episode_remains_importable_without_invented_derivation(self):
        data = episode_data()
        del data["derivation"]
        del data["segment_accounting"]
        self.write(data)
        plan = plan_input(self.kb, self.register(self.source.parent))
        self.assertEqual([], plan["errors"])
        self.assertNotIn("derivation", plan["items"][0].provenance["upstream"])
        self.assertNotIn("segment_accounting", plan["items"][0].provenance["upstream"])
        self.assertEqual([], apply_input(self.kb, plan, [0], self.workspace)["errors"])

    def test_invalid_producer_claims_rejected_before_import(self):
        cases = [("derivation", None), ("segment_accounting", []),
                 ("derivation.source_sha256", "invalid"),
                 ("derivation.postprocess_input_sha256", None),
                 ("derivation.schema_version", "future-unknown"),
                 ("derivation.canonical_segment_count", True),
                 ("derivation.canonical_segment_count", 4),
                 ("segment_accounting.kept", 2),
                 ("segment_accounting.removed", 3),
                 ("segment_accounting.advertisement", -1)]
        root = self.register(self.source.parent)
        for key, value in cases:
            with self.subTest(field=key, value=value):
                data = copy.deepcopy(episode_data())
                parts = key.split(".")
                target = data if len(parts) == 1 else data[parts[0]]
                target[parts[-1]] = value
                self.write(data)
                plan = plan_input(self.kb, root)
                self.assertTrue(plan["errors"])
                self.assertEqual([], plan["items"])
        self.assertEqual(0, self.kb.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])

    def test_malformed_sidecar_derivation_rejected_by_text_intake(self):
        sync = plan_podcast_sync(self.kb, self.source.parent.parent, self.root / "rendered")
        result = apply_podcast_sync(sync)
        sidecar_path = Path(result["sidecars"][0])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["upstream"]["derivation"]["transcript_sha256"] = "bad"
        sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
        plan = plan_input(self.kb, self.register(self.root / "rendered", "text"))
        self.assertTrue(plan["errors"])
        self.assertEqual([], plan["items"])

    def test_episode_hash_covers_the_exact_bytes_parsed_including_bom(self):
        raw = b"\xef\xbb\xbf" + self.source.read_bytes()
        self.source.write_bytes(raw)
        with patch("investkb.podcast_sync.file_sha256", side_effect=AssertionError("second read")):
            episode = read_episode(self.source)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), episode.json_sha256)

    def run_acceptance(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "verify_podcast_derivation_import.py"
        return subprocess.run([sys.executable, str(script), "--episode-root", str(self.source.parent),
                               "--expected-segments", "1", "--expected-canonical", "3"],
                              capture_output=True, text=True, cwd=self.root)

    def test_acceptance_cli_works_from_other_directory_without_private_output(self):
        original = self.source.read_bytes()
        run = self.run_acceptance()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn("PASS:", run.stdout)
        self.assertNotIn("Synthetic text.", run.stdout + run.stderr)
        self.assertNotIn(str(self.source), run.stdout + run.stderr)
        self.assertEqual(original, self.source.read_bytes())

    def test_acceptance_cli_fails_without_success_for_invalid_episode(self):
        self.source.write_text("private invalid json contents", encoding="utf-8")
        run = self.run_acceptance()
        self.assertNotEqual(0, run.returncode)
        self.assertNotIn("PASS:", run.stdout)
        self.assertNotIn("private invalid json contents", run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
