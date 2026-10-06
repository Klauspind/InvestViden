import html
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase
from investkb.web_app import create_server


class ResearchUsageTest(unittest.TestCase):
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
        extraction = {
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
                        "excerpt": "Demand for memory chips used in AI data centers was a key driver.",
                        "start_ref": "00:02",
                        "end_ref": "00:02",
                    },
                },
                {
                    "claim_type": "company_view",
                    "summary": "Micron has guaranteed AI-driven earnings growth.",
                    "speaker": None,
                    "sentiment": "positive",
                    "action": "none",
                    "time_horizon": "unspecified",
                    "discussion_depth": "moderate",
                    "confidence": 0.95,
                    "review_status": "ai_extracted",
                    "companies": [{"name": "Micron", "ticker": None, "role": "primary"}],
                    "themes": ["AI data centers"],
                    "thesis": [],
                    "risks": [],
                    "catalysts": [],
                    "conditions": [],
                    "evidence": {
                        "excerpt": "AI demand guarantees future earnings growth.",
                        "start_ref": "00:02",
                        "end_ref": "00:02",
                    },
                },
            ],
        }
        self.kb.ingest(extraction)
        self.claim_ids = {claim["summary"]: claim["id"] for claim in self.kb.claims()}
        self.good_id = self.claim_ids["Micron benefits from AI data-center memory demand."]
        self.bad_id = self.claim_ids["Micron has guaranteed AI-driven earnings growth."]

        self.server, self.app = create_server(self.kb.db_path, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.kb.close()
        self.temp.cleanup()

    def get(self, path: str) -> str:
        with urlopen(self.base + path, timeout=5) as response:
            return response.read().decode("utf-8")

    def post_review(self, claim_id: str, action: str, **extra: str) -> str:
        fields = {
            "csrf_token": self.app.csrf_token,
            "claim_id": claim_id,
            "action": action,
            "return_to": "claim",
            "origin": "review",
            **extra,
        }
        with urlopen(
            Request(self.base + "/review", data=urlencode(fields).encode("utf-8")), timeout=5
        ) as response:
            self.assertTrue(response.url.startswith(self.base + "/claim?"))
            return response.read().decode("utf-8")

    def test_default_research_search_uses_only_source_backed_ai_candidates(self):
        page = self.get("/search?q=Micron")
        self.assertIn("Research", page)
        self.assertIn("Kildeunderbygget · ikke menneskeligt verificeret", page)
        self.assertIn("Micron benefits from AI data-center memory demand.", page)
        self.assertNotIn("Micron has guaranteed AI-driven earnings growth.", page)

        signals = self.get("/search?lane=signals&q=Micron")
        self.assertIn("Micron benefits from AI data-center memory demand.", signals)
        self.assertIn("Micron has guaranteed AI-driven earnings growth.", signals)
        self.assertNotIn("Micron benefits from AI data-center memory demand.", self.get("/search?lane=active&q=Micron"))

    def test_current_claim_detail_has_review_actions_and_returns_to_same_review_position(self):
        page = self.get("/claim?" + urlencode({"id": self.good_id, "origin": "review"}))
        for label in ("Godkend som aktiv viden", "Afklar senere", "Afvis", "Ret og godkend"):
            self.assertIn(label, page)
        self.assertIn(html.escape(f"/review#{self.good_id}"), page)
        self.assertIn("Kildeunderbygget AI-kandidat", page)

        page = self.post_review(self.good_id, "approve", note="Kontrolleret mod kilden")
        self.assertIn("Godkendt", page)
        self.assertEqual("approved", self.kb.claim_detail(self.good_id)["review_status"])
        self.assertIn("Micron benefits from AI data-center memory demand.", self.get("/search?lane=active&q=Micron"))

    def test_non_verifiable_candidate_cannot_be_approved_from_detail_page(self):
        page = self.get("/claim?" + urlencode({"id": self.bad_id, "origin": "review"}))
        self.assertIn('value="approve" disabled', page)
        self.assertNotIn("Kildeunderbygget AI-kandidat", page)


if __name__ == "__main__":
    unittest.main()
