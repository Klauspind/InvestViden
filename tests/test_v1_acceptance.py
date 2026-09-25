import tempfile
import unittest
from pathlib import Path

from scripts.verify_v1_acceptance import run_acceptance


class V1AcceptanceTest(unittest.TestCase):
    def test_full_v1_chain_is_isolated_review_gated_and_rollbackable(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "iv005"
            result = run_acceptance(work)

            self.assertEqual(4, result["schema_version"])
            self.assertEqual("ai_extracted", result["candidate_started_as"])
            self.assertEqual("approved", result["human_review"])
            self.assertTrue(result["active_search"])
            self.assertEqual("ok", result["backup_integrity"])
            self.assertEqual("ok", result["rollback_integrity"])
            self.assertEqual([], result["rollback_foreign_key_errors"])
            self.assertTrue(result["original_source_unchanged"])
            self.assertEqual(0, result["external_ai_calls"])
            self.assertFalse(result["active_database_used"])

    def test_refuses_to_overwrite_nonempty_work_dir(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "iv005"
            work.mkdir()
            (work / "existing.txt").write_text("bevar", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_acceptance(work)
            self.assertEqual("bevar", (work / "existing.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
