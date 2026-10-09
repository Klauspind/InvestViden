import json
import sys
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from investkb.operational_navigation import create_operational_server
from investkb.portfolio import PortfolioStore
from investkb.repository import KnowledgeBase


class PortfolioFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "knowledgebase.sqlite")
        self.kb.initialize()
        self.recent_source_date = (date.today() - timedelta(days=2)).isoformat()
        self.current_pipeline_date = (date.today() - timedelta(days=1)).isoformat()
        self.historical_source_date = (date.today() - timedelta(days=500)).isoformat()

        source = self.root / "novo.txt"
        source_text = (
            "Novo Nordisk has strong demand, but competition and pricing pressure remain risks. "
            "A successful new indication could be a catalyst. The current regulatory setting is broadly stable. "
            "OpenAI delayed its planned listing while Novo Nordisk was mentioned only as broader market context."
        )
        source.write_text(source_text, encoding="utf-8")
        source_id, _ = self.kb.import_source(
            source,
            "report",
            title="Novo Nordisk research note",
            publisher="Synthetic Research",
            published_at=self.recent_source_date,
            source_store=self.root / "sources",
            ai_permission="ask",
        )
        self.kb.ingest({
            "schema_version": "0.1",
            "source_id": source_id,
            "provider": "mistral",
            "model": "mistral-small-2603",
            "extracted_at": "2026-10-06T20:00:00+00:00",
            "claims": [{
                "claim_type": "company_view",
                "summary": "Novo Nordisk has strong demand, while competition remains a risk.",
                "speaker": None,
                "sentiment": "positive",
                "action": "watch",
                "time_horizon": "long_term",
                "discussion_depth": "detailed",
                "confidence": 0.91,
                "review_status": "ai_extracted",
                "companies": [{"name": "Novo Nordisk", "ticker": "NOVO-B", "role": "primary"}],
                "themes": ["diabetes", "obesity"],
                "thesis": ["Strong demand supports the long-term case"],
                "risks": ["Competition and pricing pressure"],
                "catalysts": ["Successful new indication"],
                "conditions": ["Demand must remain strong"],
                "evidence": {
                    "excerpt": "Novo Nordisk has strong demand, but competition and pricing pressure remain risks.",
                    "start_ref": "p1",
                    "end_ref": "p1",
                },
            }, {
                "claim_type": "company_view",
                "summary": "Novo Nordisk's current regulatory setting is broadly stable.",
                "speaker": None,
                "sentiment": "neutral",
                "action": "none",
                "time_horizon": "medium_term",
                "discussion_depth": "brief",
                "confidence": 0.80,
                "review_status": "ai_extracted",
                "companies": [{"name": "Novo Nordisk", "ticker": "NOVO-B", "role": "discussed"}],
                "themes": ["regulation"],
                "thesis": [],
                "risks": [],
                "catalysts": [],
                "conditions": [],
                "evidence": {
                    "excerpt": "The current regulatory setting is broadly stable.",
                    "start_ref": "p1",
                    "end_ref": "p1",
                },
            }, {
                "claim_type": "company_view",
                "summary": "OpenAI delayed its planned listing.",
                "speaker": None,
                "sentiment": "negative",
                "action": "none",
                "time_horizon": "medium_term",
                "discussion_depth": "brief",
                "confidence": 0.82,
                "review_status": "ai_extracted",
                "companies": [
                    {"name": "OpenAI", "ticker": None, "role": "primary"},
                    {"name": "Novo Nordisk", "ticker": "NOVO-B", "role": "mention"},
                ],
                "themes": ["capital markets"],
                "thesis": [],
                "risks": [],
                "catalysts": [],
                "conditions": [],
                "evidence": {
                    "excerpt": "OpenAI delayed its planned listing while Novo Nordisk was mentioned only as broader market context.",
                    "start_ref": "p1",
                    "end_ref": "p1",
                },
            }],
        })

        unprocessed = self.root / "novo-pipeline.txt"
        unprocessed.write_text(
            "Novo pipeline discussion that has not been AI processed yet.",
            encoding="utf-8",
        )
        self.unprocessed_id, _ = self.kb.import_source(
            unprocessed,
            "podcast_transcript",
            title="Novo pipeline and future products",
            publisher="Synthetic Podcast",
            published_at=self.current_pipeline_date,
            source_store=self.root / "sources",
            ai_permission="ask",
        )

        historical = self.root / "novo-historical.txt"
        historical.write_text(
            "Older Novo context that remains available when explicitly needed.",
            encoding="utf-8",
        )
        self.historical_id, _ = self.kb.import_source(
            historical,
            "podcast_transcript",
            title="Novo historical context",
            publisher="Synthetic Podcast",
            published_at=self.historical_source_date,
            source_store=self.root / "sources",
            ai_permission="ask",
        )

        self.server, self.app = create_operational_server(self.kb.db_path, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.kb.close()
        self.temp.cleanup()

    def get(self, path):
        with urlopen(self.base + path, timeout=5) as response:
            return response.read().decode("utf-8")

    def post(self, values):
        payload = urlencode(values).encode("utf-8")
        request = Request(self.base + "/portfolio", data=payload)
        with urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8")

    def test_portfolio_is_local_and_builds_decision_view_from_research(self):
        overview = self.get("/")
        self.assertIn("Min portefølje", overview)

        empty = self.get("/portfolio")
        self.assertIn("Porteføljen er tom", empty)
        self.assertIn("brokeradgang", empty)

        page = self.post({
            "csrf_token": self.app.csrf_token,
            "action": "save",
            "entry_id": "",
            "company_name": "Novo",
            "ticker": "NOVO-B",
            "kind": "holding",
            "position_note": "120 aktier",
            "time_horizon": "long_term",
            "note": "Langsigtet position",
        })
        self.assertIn("Porteføljeposten er gemt lokalt", page)
        self.assertIn("Novo", page)
        self.assertIn("Beslutningsbillede", page)
        self.assertIn("Competition and pricing pressure", page)
        self.assertIn("Successful new indication", page)
        self.assertIn("Kildeunderbygget · ikke menneskeligt verificeret", page)
        self.assertIn("ikke en automatisk køb/hold/sælg-anbefaling", page)
        self.assertIn("Review-on-demand", page)
        self.assertIn("er ikke en restanceliste", page)

        self.assertIn("<span>Researchudsagn</span><b>3</b>", page)
        self.assertIn("Positiv / neutral / negativ / blandet/uklar", page)
        self.assertIn("<b>1 / 1 / 0 / 0</b>", page)
        self.assertIn("kun direkte selskabsudsagn", page)
        self.assertIn("Se udsagn og kilder", page)
        self.assertIn("Sentiment · direkte selskabsudsagn", page)
        self.assertIn("Positiv · 1", page)
        self.assertIn("Neutral · 1", page)
        self.assertIn("Negativ · 0", page)
        self.assertIn("Novo Nordisk has strong demand, while competition remains a risk.", page)
        self.assertIn("Novo Nordisk&#x27;s current regulatory setting is broadly stable.", page)
        self.assertIn(f"Novo Nordisk research note · {self.recent_source_date}", page)
        self.assertIn("Sentimentet tæller kun udsagn, hvor Novo er registreret som hovedemne eller direkte diskuteret", page)
        self.assertIn("Sentiment beskriver kildens udsagn, ikke InvestVidens egen anbefaling", page)
        self.assertIn("Kontekst fra relevante kilder · 1", page)
        self.assertIn("OpenAI delayed its planned listing.", page)
        self.assertIn("De tæller derfor ikke i selskabets sentiment", page)

        self.assertIn("Research-dækning", page)
        self.assertIn("<span>Relevante kilder</span><b>3</b>", page)
        self.assertIn("<span>AI-behandlede</span><b>1</b>", page)
        self.assertIn("<span>Aktuelle uden AI</span><b>1</b>", page)
        self.assertIn("<span>Historisk baggrund</span><b>1</b>", page)
        self.assertIn("Novo pipeline and future products", page)
        self.assertNotIn("Novo historical context</h3>", page)
        self.assertIn("Historisk baggrund:</strong> 1", page)
        self.assertIn("De er ikke en opgaveliste", page)
        self.assertIn("Hvorfor vist: selskabsnavn i titel.", page)
        self.assertIn("Vælg denne kilde til Mistral", page)
        self.assertIn(f"/ai-jobs?q={self.unprocessed_id}", page)
        self.assertIn("Vælg kilder ved behov", page)
        self.assertIn("/ai-jobs?q=Novo", page)

        jobs = self.get("/ai-jobs?q=Novo")
        self.assertIn(self.unprocessed_id, jobs)
        self.assertIn("Novo pipeline and future products", jobs)
        self.assertIn(self.historical_id, jobs)
        self.assertIn("Novo historical context", jobs)

        portfolio_path = self.kb.db_path.parent / "portfolio.sqlite"
        self.assertTrue(portfolio_path.is_file())
        with PortfolioStore(portfolio_path) as store:
            entries = store.entries()
            self.assertEqual(1, len(entries))
            self.assertEqual("holding", entries[0]["kind"])
            self.assertEqual("120 aktier", entries[0]["position_note"])

        tables = {
            row[0]
            for row in self.kb.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertNotIn("portfolio_entries", tables)

    def test_duplicate_company_is_rejected(self):
        path = self.root / "standalone-portfolio.sqlite"
        with PortfolioStore(path) as store:
            store.save(
                company_name="Novo Nordisk",
                ticker="NOVO-B",
                kind="watchlist",
                position_note=None,
                time_horizon="long_term",
                note=None,
            )
            with self.assertRaisesRegex(Exception, "findes allerede"):
                store.save(
                    company_name="Novo Nordisk",
                    ticker=None,
                    kind="holding",
                    position_note=None,
                    time_horizon="unspecified",
                    note=None,
                )


if __name__ == "__main__":
    unittest.main()