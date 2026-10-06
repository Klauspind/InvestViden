import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase
from investkb.review_evidence import assess_evidence
from investkb.validation import ValidationError


class ReviewEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.txt"
        self.source.write_text(
            "[00:01] Micron reported strong revenue growth.\n"
            "[00:02] Demand for memory chips used in AI data centers was a key driver.\n",
            encoding="utf-8",
        )
        raw = self.source.read_bytes()
        self.base = {
            "excerpt": "Demand for memory chips used in AI data centers was a key driver.",
            "start_ref": "00:02",
            "end_ref": "00:02",
            "source_archived_at": None,
            "version_archived_at": None,
            "source_is_current": 1,
            "published_at": "2026-10-01",
            "dataset": "active",
            "provider": "mistral",
            "stored_path": str(self.source),
            "source_title": "Test episode",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_current_mistral_claim_requires_verbatim_evidence(self):
        item = dict(self.base)
        item["excerpt"] = "AI demand was strong and drove Micron's results."
        result = assess_evidence(item)
        self.assertFalse(result["can_approve"])
        self.assertTrue(any("kunne ikke genfindes ordret" in issue for issue in result["issues"]))

    def test_whitespace_only_differences_are_allowed(self):
        item = dict(self.base)
        item["excerpt"] = "Demand for memory chips used in AI data centers\nwas a key driver."
        result = assess_evidence(item)
        self.assertTrue(result["can_approve"], result["issues"])

    def test_refs_without_excerpt_are_not_enough_for_current_ai_claim(self):
        item = dict(self.base)
        item["excerpt"] = None
        result = assess_evidence(item)
        self.assertFalse(result["can_approve"])
        self.assertTrue(any("ordret evidensuddrag" in issue for issue in result["issues"]))

    def test_hash_mismatch_blocks_approval(self):
        item = dict(self.base)
        item["source_sha256"] = "0" * 64
        result = assess_evidence(item)
        self.assertFalse(result["can_approve"])
        self.assertTrue(any("hash stemmer ikke" in issue for issue in result["issues"]))


class RepositoryEvidenceGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.txt"
        self.source.write_text(
            "[00:01] Micron reported strong revenue growth.\n"
            "[00:02] Demand for memory chips used in AI data centers was a key driver.\n",
            encoding="utf-8",
        )
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        self.source_id, _ = self.kb.import_source(
            self.source,
            "podcast_transcript",
            title="Current podcast",
            published_at="2026-10-01",
            source_store=self.root / "sources",
        )

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def extraction(self, excerpt: str) -> dict:
        return {
            "schema_version": "0.1",
            "source_id": self.source_id,
            "provider": "mistral",
            "model": "mistral-large-2512",
            "extracted_at": "2026-10-06T08:00:00+00:00",
            "claims": [
                {
                    "claim_type": "company_view",
                    "summary": "Micron benefits from AI data-center memory demand.",
                    "speaker": None,
                    "sentiment": "positive",
                    "action": "none",
                    "time_horizon": "unspecified",
                    "discussion_depth": "moderate",
                    "confidence": 0.9,
                    "review_status": "ai_extracted",
                    "companies": [{"name": "Micron", "ticker": None, "role": "primary"}],
                    "themes": ["AI data centers"],
                    "thesis": [],
                    "risks": [],
                    "catalysts": [],
                    "conditions": [],
                    "evidence": {
                        "excerpt": excerpt,
                        "start_ref": "00:02",
                        "end_ref": "00:02",
                    },
                }
            ],
        }

    def test_set_review_blocks_paraphrased_mistral_evidence(self):
        _, count = self.kb.ingest(
            self.extraction("AI demand was strong and drove Micron's results.")
        )
        self.assertEqual(1, count)
        claim_id = self.kb.claims()[0]["id"]
        with self.assertRaises(ValidationError):
            self.kb.set_review(claim_id, "approved", "Kontrolleret")
        self.assertEqual("ai_extracted", self.kb.claim_detail(claim_id)["review_status"])

    def test_set_review_allows_source_verifiable_mistral_evidence(self):
        _, count = self.kb.ingest(
            self.extraction("Demand for memory chips used in AI data centers was a key driver.")
        )
        self.assertEqual(1, count)
        claim_id = self.kb.claims()[0]["id"]
        self.kb.set_review(claim_id, "approved", "Kontrolleret mod kilden")
        self.assertEqual("approved", self.kb.claim_detail(claim_id)["review_status"])


if __name__ == "__main__":
    unittest.main()
