"""Synthetic end-to-end tests for isolated morning consumer acceptance."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_morning_consumer_flow.py"


def episode_data() -> dict:
    return {
        "schema_version": "2.0",
        "id": "synthetic-morning-consumer",
        "source": {
            "podcast": "Synthetic",
            "title": "Synthetic morning episode",
            "published": "2026-09-25",
            "language": "da",
        },
        "segments": [
            {"id": 1, "start": 1.0, "end": 2.0, "text": "Private synthetic marker 7QX."}
        ],
        "derivation": {
            "schema_version": "podcast-legacy-derivation-v1",
            "package_id": "trpkg-synthetic-morning",
            "source_sha256": "a" * 64,
            "transcript_sha256": "b" * 64,
            "postprocess_input_sha256": "c" * 64,
            "canonical_schema_version": "1.0",
            "canonical_segment_count": 1,
        },
        "segment_accounting": {
            "input": 1,
            "kept": 1,
            "removed": 0,
            "advertisement": 0,
            "empty_after_cleaning": 0,
        },
    }


class MorningConsumerFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.delivery = self.root / "delivery"
        self.episode_dir = self.delivery / "Synthetic"
        self.episode_dir.mkdir(parents=True)
        self.episode = self.episode_dir / "2026-09-25 episode.json"
        self.episode.write_text(json.dumps(episode_data(), ensure_ascii=False), encoding="utf-8")
        self.original = self.episode.read_bytes()
        self.work = self.root / "accept"

    def run_script(self):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--episode-root",
                str(self.delivery),
                "--work-dir",
                str(self.work),
            ],
            capture_output=True,
            text=True,
            cwd=self.root,
        )

    def test_full_flow_imports_provenance_and_creates_only_local_draft(self):
        run = self.run_script()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(4, result["schema_version"])
        self.assertTrue(result["source_imported"])
        self.assertTrue(result["provenance_preserved"])
        self.assertEqual("ok", result["intake_backup_integrity"])
        self.assertEqual("allow", result["ai_permission"])
        self.assertEqual("draft", result["ai_job_status"])
        self.assertEqual(1, result["ai_job_items"])
        self.assertEqual(0, result["ai_attempts"])
        self.assertTrue(result["estimated_cost_within_limit"])
        self.assertEqual("existing", result["repeat_intake_status"])
        self.assertTrue(result["original_source_unchanged"])
        self.assertEqual(0, result["external_ai_calls"])
        self.assertFalse(result["active_database_used"])
        self.assertEqual(self.original, self.episode.read_bytes())
        self.assertNotIn("Private synthetic marker 7QX", run.stdout + run.stderr)
        self.assertNotIn(str(self.episode), run.stdout + run.stderr)

    def test_nonempty_work_dir_fails_closed_without_private_output(self):
        self.work.mkdir()
        (self.work / "keep.txt").write_text("do not overwrite", encoding="utf-8")
        run = self.run_script()
        self.assertNotEqual(0, run.returncode)
        self.assertNotIn("Private synthetic marker 7QX", run.stdout + run.stderr)
        self.assertEqual("do not overwrite", (self.work / "keep.txt").read_text(encoding="utf-8"))

    def test_multiple_episode_jsons_fail_closed(self):
        second = self.episode_dir / "2026-09-25 second.json"
        second.write_text(json.dumps(episode_data()), encoding="utf-8")
        run = self.run_script()
        self.assertNotEqual(0, run.returncode)
        self.assertFalse(self.work.exists())


if __name__ == "__main__":
    unittest.main()
