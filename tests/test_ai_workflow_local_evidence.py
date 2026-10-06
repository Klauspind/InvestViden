import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_workflow import process_ai_inbox
from investkb.repository import KnowledgeBase
from investkb.validation import ValidationError


class LocalTimestampEvidenceWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "episode.txt"
        self.source.write_text(
            "[00:00:01–00:00:03] Gælden er høj, og investorer kræver en højere rente.\n"
            "[00:00:03–00:00:06] Væksten i USA er bedre og er med til at drive renten op.\n"
            "[00:00:06–00:00:09] Den tiårige rente ligger nu omkring fem procent.\n",
            encoding="utf-8",
        )
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        self.source_id, _ = self.kb.import_source(
            self.source,
            "podcast_transcript",
            title="Syntetisk podcast",
            published_at="2026-10-06",
            source_store=self.root / "sources",
        )
        self.incoming = self.root / "incoming"
        self.archive = self.root / "processed"
        self.incoming.mkdir()

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def extraction(self, start_ref="00:00:01", end_ref="00:00:06") -> dict:
        return {
            "schema_version": "0.1",
            "source_id": self.source_id,
            "provider": "mistral",
            "model": "mistral-large-2512",
            "extracted_at": "2026-10-06T09:00:00+00:00",
            "claims": [
                {
                    "claim_type": "macroeconomic",
                    "summary": "Amerikansk gæld og bedre vækst bidrager til højere renter.",
                    "speaker": None,
                    "sentiment": "neutral",
                    "action": "none",
                    "time_horizon": "unspecified",
                    "discussion_depth": "moderate",
                    "confidence": 0.9,
                    "review_status": "ai_extracted",
                    "companies": [],
                    "themes": ["renter"],
                    "thesis": [],
                    "risks": [],
                    "catalysts": [],
                    "conditions": [],
                    "evidence": {
                        "excerpt": "AI-parafrase som ikke findes i kilden.",
                        "start_ref": start_ref,
                        "end_ref": end_ref,
                    },
                }
            ],
        }

    def write_incoming(self, extraction: dict) -> Path:
        path = self.incoming / "mistral-test.json"
        path.write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def test_process_ai_uses_local_passage_but_archives_raw_ai_output(self):
        path = self.write_incoming(self.extraction())
        original_bytes = path.read_bytes()

        preview = process_ai_inbox(self.kb, self.incoming, self.archive, dry_run=True)
        self.assertEqual(1, preview["local_evidence_derived"])
        self.assertEqual(0, preview["local_evidence_missing"])
        self.assertEqual([], self.kb.claims())
        self.assertEqual(original_bytes, path.read_bytes())

        result = process_ai_inbox(self.kb, self.incoming, self.archive)
        self.assertEqual(1, result["local_evidence_derived"])
        claim_id = self.kb.claims()[0]["id"]
        detail = self.kb.claim_detail(claim_id)
        self.assertIn("[00:00:01–00:00:03]", detail["excerpt"])
        self.assertIn("[00:00:03–00:00:06]", detail["excerpt"])
        self.assertNotIn("AI-parafrase", detail["excerpt"])

        self.kb.set_review(claim_id, "approved", "Kontrolleret mod den lokale passage")
        self.assertEqual("approved", self.kb.claim_detail(claim_id)["review_status"])

        archived = Path(result["archived"][0])
        self.assertEqual(original_bytes, archived.read_bytes())
        raw_output = json.loads(archived.read_text(encoding="utf-8"))
        self.assertEqual(
            "AI-parafrase som ikke findes i kilden.",
            raw_output["claims"][0]["evidence"]["excerpt"],
        )

    def test_missing_timestamp_passage_stays_blocked(self):
        self.write_incoming(self.extraction("00:00:20", "00:00:25"))
        result = process_ai_inbox(self.kb, self.incoming, self.archive)
        self.assertEqual(0, result["local_evidence_derived"])
        self.assertEqual(1, result["local_evidence_missing"])
        claim_id = self.kb.claims()[0]["id"]
        with self.assertRaises(ValidationError):
            self.kb.set_review(claim_id, "approved", "Skal blokeres")
        self.assertEqual("ai_extracted", self.kb.claim_detail(claim_id)["review_status"])

    def test_hash_mismatch_fails_before_ingest(self):
        self.write_incoming(self.extraction())
        stored = self.kb.conn.execute(
            "SELECT stored_path FROM source_versions WHERE id=?", (self.source_id,)
        ).fetchone()["stored_path"]
        Path(stored).write_text("ændret kildekopi", encoding="utf-8")

        with self.assertRaises(ValidationError):
            process_ai_inbox(self.kb, self.incoming, self.archive, dry_run=True)
        self.assertEqual([], self.kb.claims())


if __name__ == "__main__":
    unittest.main()
