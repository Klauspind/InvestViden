"""Tests for the persistent Transskribinator -> InvestViden consumer."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPT = ROOT / "scripts" / "run_transskribinator_consumer.py"
sys.path.insert(0, str(SRC))

from investkb.intake import apply_input, plan_input
from investkb.repository import KnowledgeBase


def episode_data(identifier: str, title: str, text: str, package: str) -> dict:
    return {
        "schema_version": "2.0",
        "id": identifier,
        "source": {
            "podcast": "Synthetic",
            "title": title,
            "published": "2026-09-29",
            "language": "da",
        },
        "segments": [
            {"id": 1, "start": 1.0, "end": 2.0, "text": text}
        ],
        "derivation": {
            "schema_version": "podcast-legacy-derivation-v1",
            "package_id": package,
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


class TransskribinatorConsumerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.delivery = self.root / "delivery"
        self.state = self.root / "state"
        self.episode_dir = self.delivery / "Synthetic"
        self.episode_dir.mkdir(parents=True)

    def write_episode(self, name: str, data: dict) -> Path:
        path = self.episode_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def run_script(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--delivery-root",
                str(self.delivery),
                "--state-root",
                str(self.state),
                *extra,
            ],
            capture_output=True,
            text=True,
            cwd=self.root,
        )

    def test_first_run_imports_all_and_second_run_is_idempotent(self):
        first_path = self.write_episode(
            "first.json",
            episode_data("episode-1", "First", "Synthetic alpha.", "trpkg-alpha"),
        )
        second_path = self.write_episode(
            "second.json",
            episode_data("episode-2", "Second", "Synthetic beta.", "trpkg-beta"),
        )
        originals = {first_path: first_path.read_bytes(), second_path: second_path.read_bytes()}

        first = self.run_script()
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        result = json.loads(first.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(4, result["database_schema"])
        self.assertEqual("ok", result["database_integrity"])
        self.assertEqual(2, result["delivery_episodes"])
        self.assertEqual(2, result["new_imported"])
        self.assertEqual(0, result["existing"])
        self.assertEqual(2, result["draft_jobs_created"])
        self.assertEqual(2, result["total_sources"])
        self.assertEqual(2, result["total_ai_jobs"])
        self.assertEqual(2, result["total_ai_job_items"])
        self.assertEqual(0, result["ai_attempts"])
        self.assertEqual(0, result["claims"])
        self.assertEqual("ok", result["backup_integrity"])
        self.assertTrue(result["original_sources_unchanged"])
        self.assertEqual(0, result["external_ai_calls"])
        self.assertFalse(result["active_database_used"])
        for path, original in originals.items():
            self.assertEqual(original, path.read_bytes())

        second = self.run_script()
        self.assertEqual(0, second.returncode, second.stdout + second.stderr)
        repeat = json.loads(second.stdout)
        self.assertEqual(0, repeat["new_imported"])
        self.assertEqual(2, repeat["existing"])
        self.assertEqual(0, repeat["draft_jobs_created"])
        self.assertEqual(2, repeat["total_sources"])
        self.assertEqual(2, repeat["total_ai_jobs"])
        self.assertEqual(2, repeat["total_ai_job_items"])
        self.assertEqual(0, repeat["ai_attempts"])
        self.assertIsNone(repeat["backup_integrity"])

    def test_check_is_read_only_when_state_does_not_exist(self):
        self.write_episode(
            "episode.json",
            episode_data("episode-check", "Check", "Synthetic check.", "trpkg-check"),
        )
        run = self.run_script("--check")
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual("check", result["mode"])
        self.assertEqual(1, result["delivery_episodes"])
        self.assertFalse(result["state_database_exists"])
        self.assertFalse(self.state.exists())
        self.assertEqual(0, result["external_ai_calls"])
        self.assertFalse(result["active_database_used"])

    def test_check_does_not_modify_existing_consumer_database(self):
        self.write_episode(
            "episode.json",
            episode_data("episode-readonly", "Readonly", "Synthetic readonly.", "trpkg-readonly"),
        )
        first = self.run_script()
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        database = self.state / "knowledgebase.sqlite"
        before = database.read_bytes()

        check = self.run_script("--check")
        self.assertEqual(0, check.returncode, check.stdout + check.stderr)
        result = json.loads(check.stdout)
        self.assertTrue(result["state_database_exists"])
        self.assertEqual(4, result["database_schema"])
        self.assertEqual("ok", result["database_integrity"])
        self.assertEqual(1, result["sources"])
        self.assertEqual(1, result["draft_jobs"])
        self.assertEqual(before, database.read_bytes())

    def test_recovery_creates_missing_draft_for_already_imported_source(self):
        self.write_episode(
            "episode.json",
            episode_data("episode-recovery", "Recovery", "Synthetic recovery.", "trpkg-recovery"),
        )
        self.state.mkdir()
        database = self.state / "knowledgebase.sqlite"
        workspace = self.state / "workspace"
        root = {
            "path": str(self.delivery.resolve()),
            "format": "podcast_json",
            "source_type": "podcast_transcript",
            "permission": "allow",
            "publisher": "",
            "language": "da",
        }
        with KnowledgeBase(database) as kb:
            kb.initialize()
            plan = plan_input(kb, root)
            selected = [index for index, item in enumerate(plan["items"]) if item.status == "new"]
            applied = apply_input(kb, plan, selected, workspace)
            self.assertEqual(1, len(applied["imported"]))
            self.assertEqual(0, kb.conn.execute("SELECT COUNT(*) FROM ai_jobs").fetchone()[0])

        run = self.run_script()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(0, result["new_imported"])
        self.assertEqual(1, result["existing"])
        self.assertEqual(1, result["draft_jobs_created"])
        self.assertEqual(1, result["total_ai_jobs"])
        self.assertEqual(0, result["ai_attempts"])

    def test_changed_episode_identity_fails_without_new_import_or_draft(self):
        path = self.write_episode(
            "episode.json",
            episode_data("episode-conflict", "Conflict", "Original text.", "trpkg-conflict"),
        )
        first = self.run_script()
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)

        changed = episode_data("episode-conflict", "Conflict", "Changed text.", "trpkg-conflict-v2")
        path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
        second = self.run_script()
        self.assertNotEqual(0, second.returncode)
        failure = json.loads(second.stdout)
        self.assertFalse(failure["ok"])
        self.assertEqual("ValidationError", failure["error_type"])

        with sqlite3.connect(self.state / "knowledgebase.sqlite") as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM ai_jobs").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM ai_job_items").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
