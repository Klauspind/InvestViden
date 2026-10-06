import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_workflow import process_ai_inbox
from investkb.operational_navigation import _add_pending_recovery
from investkb.repository import KnowledgeBase


def claim(summary: str, claim_id: str | None = None) -> dict:
    result = {
        "claim_type": "company_view",
        "summary": summary,
        "speaker": None,
        "sentiment": "neutral",
        "action": "watch",
        "time_horizon": "medium_term",
        "discussion_depth": "moderate",
        "confidence": 0.9,
        "review_status": "ai_extracted",
        "companies": [{"name": "Novo Nordisk", "ticker": "NOVO-B", "role": "primary"}],
        "themes": ["Novo"],
        "thesis": [],
        "risks": [],
        "catalysts": [],
        "conditions": [],
        "evidence": {"excerpt": "Novo evidence.", "start_ref": "p1", "end_ref": "p1"},
    }
    if claim_id is not None:
        result["claim_id"] = claim_id
    return result


class ExternalClaimIdRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        first = self.root / "first.txt"
        first.write_text("First source.", encoding="utf-8")
        second = self.root / "second.txt"
        second.write_text("Second source.", encoding="utf-8")
        self.first_id, _ = self.kb.import_source(
            first, "report", title="First", publisher="Test", published_at="2026-10-05",
            source_store=self.root / "sources", ai_permission="ask",
        )
        self.second_id, _ = self.kb.import_source(
            second, "report", title="Second", publisher="Test", published_at="2026-10-06",
            source_store=self.root / "sources", ai_permission="ask",
        )

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def test_model_claim_id_collision_is_ignored_without_rewriting_raw_response(self):
        collision = "claim-model-provided-collision"
        self.kb.ingest({
            "schema_version": "0.1",
            "source_id": self.first_id,
            "provider": "manual_demo",
            "model": None,
            "extracted_at": "2026-10-06T18:00:00+00:00",
            "claims": [claim("Existing local claim.", collision)],
        })
        incoming = self.root / "incoming"
        archive = self.root / "processed"
        incoming.mkdir()
        payload = {
            "schema_version": "0.1",
            "source_id": self.second_id,
            "provider": "mistral",
            "model": "mistral-small-2603",
            "extracted_at": "2026-10-06T19:00:00+00:00",
            "claims": [claim("Fresh Mistral claim.", collision)],
        }
        raw_path = incoming / f"mistral-{self.second_id}.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        original_raw = raw_path.read_bytes()

        result = process_ai_inbox(self.kb, incoming, archive, False)

        self.assertEqual(1, result["claims"])
        rows = self.kb.conn.execute(
            "SELECT id, source_id, summary FROM claims ORDER BY created_at, id"
        ).fetchall()
        self.assertEqual(2, len(rows))
        new = next(row for row in rows if row["source_id"] == self.second_id)
        self.assertNotEqual(collision, new["id"])
        archived = list(archive.glob("*.json"))
        self.assertEqual(1, len(archived))
        self.assertEqual(original_raw, archived[0].read_bytes())
        self.assertEqual(collision, json.loads(archived[0].read_text(encoding="utf-8"))["claims"][0]["claim_id"])

    def test_pending_recovery_banner_is_local_only_and_visible_on_mistral_page(self):
        body = b"<h1>Mistral-job</h1><p>Jobs</p>"
        rendered = _add_pending_recovery(body, "csrf-test", True).decode("utf-8")
        self.assertIn("Indlæs ventende valideret svar", rendered)
        self.assertIn('name="action" value="recover"', rendered)
        self.assertIn("sender ikke noget nyt til Mistral", rendered)
        self.assertEqual(body, _add_pending_recovery(body, "csrf-test", False))


if __name__ == "__main__":
    unittest.main()
