import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.source_priority import prioritize_sources, source_relevance


class SourcePriorityTest(unittest.TestCase):
    def setUp(self):
        self.entry = {
            "company_name": "Novo Nordisk",
            "ticker": "NOVO-B",
        }

    def test_whole_word_matching_filters_peripheral_substrings(self):
        score, reason = source_relevance(
            self.entry,
            {"title": "Novonesis løfter forventningerne", "publisher": "Synthetic"},
        )
        self.assertEqual(0, score)
        self.assertEqual("", reason)

        score, reason = source_relevance(
            self.entry,
            {"title": "Novo pipeline og nye produkter", "publisher": "Synthetic"},
        )
        self.assertGreater(score, 0)
        self.assertIn("novo", reason)

    def test_newer_relevant_sources_rank_before_old_historical_sources(self):
        rows = [
            {
                "id": "old-direct",
                "title": "Novo Nordisk: historisk analyse",
                "publisher": "Archive",
                "published_at": "2021-03-01",
            },
            {
                "id": "new-partial",
                "title": "Novo pipeline efter regnskabet",
                "publisher": "Current",
                "published_at": "2026-10-06",
            },
            {
                "id": "peripheral",
                "title": "Novonesis og biosolutions",
                "publisher": "Current",
                "published_at": "2026-10-07",
            },
        ]

        prioritized = prioritize_sources(self.entry, rows)
        self.assertEqual(["new-partial", "old-direct"], [row["id"] for row in prioritized])
        self.assertEqual("Sandsynlig relevans", prioritized[0]["relevance_label"])
        self.assertEqual("Høj relevans", prioritized[1]["relevance_label"])

    def test_company_publisher_can_make_generic_title_relevant(self):
        prioritized = prioritize_sources(
            self.entry,
            [{
                "id": "ir-release",
                "title": "Q3 results",
                "publisher": "Novo Nordisk",
                "published_at": "2026-10-01",
            }],
        )
        self.assertEqual(1, len(prioritized))
        self.assertIn("udgiver", prioritized[0]["relevance_reason"])


if __name__ == "__main__":
    unittest.main()
