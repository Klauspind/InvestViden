import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from investkb.operational_web_app import create_operational_server
from investkb.repository import KnowledgeBase
from start_consumer_ui import check_database, default_database


class OperationalFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()

        novo = self.root / "novo.txt"
        novo.write_text(
            "Novo Nordisk reported strong demand in the latest update.",
            encoding="utf-8",
        )
        self.novo_id, _ = self.kb.import_source(
            novo,
            "report",
            title="Novo Nordisk update",
            publisher="Synthetic Research",
            published_at="2026-10-06",
            source_store=self.root / "sources",
            ai_permission="ask",
        )
        other = self.root / "other.txt"
        other.write_text("Another company update.", encoding="utf-8")
        self.other_id, _ = self.kb.import_source(
            other,
            "report",
            title="Other company update",
            publisher="Synthetic Research",
            published_at="2026-10-05",
            source_store=self.root / "sources",
            ai_permission="ask",
        )

        self.server, self.app = create_operational_server(self.kb.db_path, 0)
        self.app.mistral_api_key = "not-real"
        self.app.mistral_transport = self.response
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.kb.close()
        self.temp.cleanup()

    def response(self, payload, key, timeout):
        source_id = payload["metadata"]["source_id"]
        extraction = json.loads((ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8"))
        extraction["source_id"] = source_id
        extraction["claims"] = [extraction["claims"][0]]
        claim = extraction["claims"][0]
        claim["summary"] = "Novo Nordisk reported strong demand."
        claim["speaker"] = None
        claim["review_status"] = "approved"
        claim["companies"] = [{"name": "Novo Nordisk", "ticker": "NOVO-B", "role": "primary"}]
        claim["themes"] = ["demand"]
        claim["evidence"] = {
            "excerpt": "Novo Nordisk reported strong demand in the latest update.",
            "start_ref": "p1",
            "end_ref": "p1",
        }
        return {
            "id": "iv011-response-" + source_id,
            "model": "mistral-small-2603",
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(extraction, ensure_ascii=False)},
            }],
            "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280},
        }

    def get(self, path):
        with urlopen(self.base + path, timeout=5) as response:
            return response.read().decode("utf-8")

    def post(self, values):
        payload = urlencode(values, doseq=True).encode("utf-8")
        with urlopen(Request(self.base + "/ai-jobs", data=payload), timeout=10) as response:
            return response.read().decode("utf-8")

    def test_source_discovery_and_confirmed_job_end_in_research_without_manual_process_ai(self):
        overview = self.get("/")
        self.assertIn("AI-behandlede kilder", overview)
        self.assertIn("Ubehandlede kilder", overview)

        search = self.get("/search?q=Novo")
        self.assertIn("0 udsagnsresultater", search)
        self.assertIn("Ubehandlede kilder, der matcher · 1", search)
        self.assertIn("Novo Nordisk update", search)
        self.assertIn("/ai-jobs?q=Novo", search)

        jobs = self.get("/ai-jobs?q=Novo")
        self.assertIn(self.novo_id, jobs)
        self.assertNotIn(self.other_id, jobs)

        page = self.post({
            "csrf_token": self.app.csrf_token,
            "action": "create",
            "source_id": self.novo_id,
        })
        self.assertIn("Ingen tekst er sendt", page)
        job = self.kb.ai_jobs()[0]
        self.assertEqual("draft", job["status"])
        self.assertFalse(self.app.ai_incoming.exists())

        page = self.post({
            "csrf_token": self.app.csrf_token,
            "action": "confirm",
            "job_id": job["id"],
        })
        self.assertIn("endnu ikke sendt", page)
        self.assertEqual("confirmed", self.kb.ai_job(job["id"])["status"])

        page = self.post({
            "csrf_token": self.app.csrf_token,
            "action": "run",
            "job_id": job["id"],
        })
        self.assertIn("AI-kandidater er indlæst i Research", page)
        self.assertEqual("completed", self.kb.ai_job(job["id"])["status"])
        self.assertEqual([], list(self.app.ai_incoming.glob("*.json")))
        self.assertEqual(1, len(list(self.app.ai_processed.glob("*.json"))))
        claims = self.kb.claims()
        self.assertEqual(1, len(claims))
        self.assertEqual("ai_extracted", claims[0]["review_status"])

        research = self.get("/search?q=Novo")
        self.assertIn("Novo Nordisk reported strong demand.", research)
        self.assertIn("Kildeunderbygget · ikke menneskeligt verificeret", research)
        self.assertNotIn("Ubehandlede kilder, der matcher · 1", research)

    def test_consumer_launcher_path_and_read_only_check(self):
        old_localappdata = os.environ.get("LOCALAPPDATA")
        try:
            os.environ["LOCALAPPDATA"] = str(self.root / "localappdata")
            expected = (
                Path(os.environ["LOCALAPPDATA"])
                / "InvestViden"
                / "runtime"
                / "transskribinator-consumer"
                / "knowledgebase.sqlite"
            )
            self.assertEqual(expected, default_database())
            status = check_database(self.kb.db_path)
            self.assertEqual("ok", status["integrity"])
            self.assertEqual(2, status["sources"])
        finally:
            if old_localappdata is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = old_localappdata


if __name__ == "__main__":
    unittest.main()
