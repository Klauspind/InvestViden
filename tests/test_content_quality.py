import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_workflow import process_ai_inbox
from investkb.content_quality import is_promotional_noise
from investkb.repository import KnowledgeBase


PROMO = (
    "Hos Saxo Bank kan du også følge med i Millionærklubbens portefølje og blive "
    "inspireret af eksperterne; opret din aktiesparekonto gebyrfrit og bliv en af "
    "de 1,2 millioner kunder, der allerede investerer hos Saxo Bank."
)
LEGITIMATE = (
    "Forslaget om et højere loft på aktiesparekontoen vurderes positivt for "
    "langsigtede private investeringer."
)


class ContentQualityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        self.source = self.root / "source.txt"
        self.source.write_text(PROMO + "\n" + LEGITIMATE, encoding="utf-8")
        self.source_id, _ = self.kb.import_source(
            self.source, "podcast_transcript", source_store=self.root / "sources"
        )

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def extraction(self):
        data = json.loads((ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8"))
        data["source_id"] = self.source_id
        data["claims"][0]["summary"] = PROMO
        data["claims"][0]["evidence"]["excerpt"] = PROMO
        data["claims"][1]["summary"] = LEGITIMATE
        data["claims"][1]["evidence"]["excerpt"] = LEGITIMATE
        return data

    def test_classifier_is_precise_for_sponsor_boilerplate(self):
        variants = [
            PROMO,
            "Millionærklubben er sponsoreret af SaxoBank. Opret din aktiesparekonto gebyrfrit.",
            "Portefølje-/risikostyring: Følg med i Millionærklubbens portefølje og bliv inspireret af eksperterne.",
        ]
        for value in variants:
            with self.subTest(value=value):
                self.assertTrue(is_promotional_noise(value))
        self.assertFalse(is_promotional_noise(LEGITIMATE))
        self.assertFalse(is_promotional_noise("Saxo Bank sænker sin prognose for europæiske aktier."))
        self.assertFalse(is_promotional_noise("Millionærklubben diskuterer eksperternes porteføljer."))

    def test_ingest_omits_promotional_claim_but_keeps_legitimate_analysis(self):
        _, count = self.kb.ingest(self.extraction())
        self.assertEqual(1, count)
        claims = self.kb.claims()
        self.assertEqual([LEGITIMATE], [claim["summary"] for claim in claims])
        self.assertEqual("ai_extracted", claims[0]["review_status"])

    def test_process_ai_reports_filtered_claims_in_preview_and_apply(self):
        incoming = self.root / "incoming"
        processed = self.root / "processed"
        incoming.mkdir()
        (incoming / "result.json").write_text(
            json.dumps(self.extraction(), ensure_ascii=False), encoding="utf-8"
        )

        preview = process_ai_inbox(self.kb, incoming, processed, dry_run=True)
        self.assertEqual(1, preview["claims"])
        self.assertEqual(1, preview["promotional_filtered"])
        self.assertEqual(0, len(self.kb.claims()))

        result = process_ai_inbox(self.kb, incoming, processed)
        self.assertEqual(1, result["claims"])
        self.assertEqual(1, result["promotional_filtered"])
        self.assertEqual(1, len(self.kb.claims()))
        self.assertFalse((incoming / "result.json").exists())
        self.assertTrue((processed / "result.json").exists())

    def test_legacy_search_hides_promotions_but_exposes_a_noise_lane(self):
        with patch("investkb.repository.is_promotional_noise", return_value=False):
            self.kb.ingest(self.extraction())
        with self.kb.conn:
            self.kb.conn.execute("UPDATE sources SET dataset='legacy'")

        archive = self.kb.search_claims("Saxo", "archive")
        noise = self.kb.search_claims("Saxo", "noise")
        all_normal = self.kb.search_claims("Saxo", "all")

        self.assertEqual([], [row["summary"] for row in archive])
        self.assertEqual([PROMO], [row["summary"] for row in noise])
        self.assertEqual([], [row["summary"] for row in all_normal])
        self.assertEqual([LEGITIMATE], [row["summary"] for row in self.kb.search_claims("aktiesparekonto", "archive")])
        self.assertEqual([LEGITIMATE], [row["summary"] for row in self.kb.claims(include_rejected=True)])
        self.assertEqual(2, len(self.kb.claims(include_rejected=True, include_promotional=True)))


if __name__ == "__main__":
    unittest.main()
