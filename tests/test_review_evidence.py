import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.review_evidence import assess_evidence


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


if __name__ == "__main__":
    unittest.main()
