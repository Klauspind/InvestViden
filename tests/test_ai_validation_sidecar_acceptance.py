import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase
from scripts.verify_ai_validation_sidecar_acceptance import run_acceptance


class AIValidationSidecarAcceptanceTest(unittest.TestCase):
    def test_acceptance_keeps_knowledgebase_unchanged_and_cleans_ephemeral_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.txt"
            source.write_text("[00:01] Meta ad demand remains strong.\n", encoding="utf-8")
            database = root / "knowledgebase.sqlite"

            with KnowledgeBase(database) as kb:
                kb.initialize()
                source_id, _ = kb.import_source(
                    source,
                    "podcast_transcript",
                    title="Synthetic Meta source",
                    published_at="2026-10-10",
                    source_store=root / "sources",
                )
                kb.ingest(
                    {
                        "schema_version": "0.1",
                        "source_id": source_id,
                        "provider": "mistral",
                        "model": "synthetic",
                        "extracted_at": "2026-10-10T12:00:00+00:00",
                        "claims": [
                            {
                                "claim_type": "company_view",
                                "summary": "Meta ad demand remains strong.",
                                "speaker": None,
                                "sentiment": "positive",
                                "action": "none",
                                "time_horizon": "short_term",
                                "discussion_depth": "brief",
                                "confidence": 0.8,
                                "review_status": "ai_extracted",
                                "companies": [{"name": "Meta", "ticker": "META", "role": "primary"}],
                                "themes": ["advertising"],
                                "thesis": [],
                                "risks": [],
                                "catalysts": [],
                                "conditions": [],
                                "evidence": {
                                    "excerpt": "Meta ad demand remains strong.",
                                    "start_ref": "00:01",
                                    "end_ref": "00:01",
                                },
                            }
                        ],
                    }
                )
                claim_id = str(kb.claims()[0]["id"])

            result = run_acceptance(database)

            self.assertTrue(result["ok"])
            self.assertEqual(4, result["knowledgebase_schema"])
            self.assertTrue(result["knowledgebase_read_only"])
            self.assertTrue(result["knowledgebase_sha256_unchanged"])
            self.assertEqual(claim_id, result["selected_claim_id"])
            self.assertEqual("ai_extracted", result["review_status_before"])
            self.assertEqual("ai_extracted", result["review_status_after"])
            self.assertTrue(result["review_status_unchanged"])
            self.assertFalse(result["production_sidecar_existed_before"])
            self.assertTrue(result["production_sidecar_exists_after"])
            self.assertEqual(1, result["production_sidecar_schema"])
            self.assertEqual(0, result["production_validation_count"])
            self.assertEqual("ai_controlled", result["ephemeral_quality_status"])
            self.assertEqual(1, result["ephemeral_reopen_schema"])
            self.assertTrue(result["ephemeral_sidecar_deleted"])
            self.assertEqual(0, result["external_ai_calls"])

            self.assertTrue((root / "ai_validation.sqlite").is_file())
            self.assertEqual([], list(root.glob("ai_validation.acceptance-*.sqlite")))

            conn = sqlite3.connect(database)
            try:
                self.assertEqual(
                    "ai_extracted",
                    conn.execute("SELECT review_status FROM claims WHERE id=?", (claim_id,)).fetchone()[0],
                )
                self.assertEqual(4, conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
            finally:
                conn.close()

    def test_acceptance_refuses_non_schema4_database_before_creating_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "knowledgebase.sqlite"
            conn = sqlite3.connect(database)
            try:
                conn.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
                conn.execute("INSERT INTO schema_version(version, applied_at) VALUES(3, '2026-10-10T12:00:00+00:00')")
                conn.commit()
            finally:
                conn.close()

            with self.assertRaisesRegex(RuntimeError, "schema 4"):
                run_acceptance(database)
            self.assertFalse((root / "ai_validation.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
