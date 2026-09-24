import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase
from investkb.web_app import create_server


PROMO = (
    "Hos Saxo Bank kan du også følge med i Millionærklubbens portefølje og blive "
    "inspireret af eksperterne; opret din aktiesparekonto gebyrfrit og bliv en af "
    "de 1,2 millioner kunder, der allerede investerer hos Saxo Bank."
)
LEGITIMATE = (
    "Forslaget om et højere loft på aktiesparekontoen vurderes positivt for "
    "langsigtede private investeringer."
)


class FreeUIAcceptanceTest(unittest.TestCase):
    """IV-003: samlet gratis UI-flow uden ekstern AI-transport."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "iv003-schema4.sqlite")
        self.kb.initialize()

        legacy_source = self.root / "legacy-source.txt"
        legacy_source.write_text(PROMO + "\n" + LEGITIMATE, encoding="utf-8")
        legacy_id, _ = self.kb.import_source(
            legacy_source,
            "podcast_transcript",
            title="Syntetisk legacy-kilde",
            source_store=self.root / "sources",
            ai_permission="local_only",
        )
        extraction = json.loads(
            (ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8")
        )
        extraction["source_id"] = legacy_id
        extraction["claims"] = extraction["claims"][:2]
        extraction["claims"][0]["summary"] = PROMO
        extraction["claims"][0]["evidence"]["excerpt"] = PROMO
        extraction["claims"][1]["summary"] = LEGITIMATE
        extraction["claims"][1]["evidence"]["excerpt"] = LEGITIMATE
        with patch("investkb.repository.is_promotional_noise", return_value=False):
            self.kb.ingest(extraction)
        with self.kb.conn:
            self.kb.conn.execute(
                "UPDATE sources SET dataset='legacy' WHERE id=?",
                (legacy_id,),
            )

        ai_source = self.root / "free-ai-source.txt"
        ai_source.write_text(
            "[00:01] Syntetisk og ufølsomt udsagn til gratis UI-accepttest.",
            encoding="utf-8",
        )
        self.ai_source_id, _ = self.kb.import_source(
            ai_source,
            "report",
            title="Gratis UI-testkilde",
            source_store=self.root / "sources",
            ai_permission="allow",
        )

        self.server, self.app = create_server(self.kb.db_path, 0)
        self.transport_calls = []

        def forbidden_transport(*args, **kwargs):
            self.transport_calls.append((args, kwargs))
            raise AssertionError("Gratis IV-003-flow må ikke kalde AI-transport")

        self.app.mistral_transport = forbidden_transport
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

    def post_ai_job(self, **values):
        payload = urlencode(
            {"csrf_token": self.app.csrf_token, **values},
            doseq=True,
        ).encode("utf-8")
        with urlopen(
            Request(self.base + "/ai-jobs", data=payload),
            timeout=10,
        ) as response:
            return response.read().decode("utf-8")

    def test_free_ui_flow_filters_noise_and_stops_after_confirmation(self):
        archive = self.get("/search?lane=archive&q=Saxo")
        self.assertNotIn(PROMO, archive)

        noise = self.get("/search?lane=noise&q=Saxo")
        self.assertIn(PROMO, noise)

        legitimate = self.get("/search?lane=archive&q=aktiesparekonto")
        self.assertIn(LEGITIMATE, legitimate)
        self.assertNotIn(PROMO, legitimate)

        jobs_page = self.get("/ai-jobs")
        self.assertIn("Opret kladde med valgte kilder", jobs_page)
        self.assertIn(self.ai_source_id, jobs_page)
        self.assertIn("Gratis UI-testkilde", jobs_page)

        draft_page = self.post_ai_job(
            action="create",
            source_id=self.ai_source_id,
        )
        self.assertIn("Ingen tekst er sendt", draft_page)
        jobs = self.kb.ai_jobs()
        self.assertEqual(1, len(jobs))
        job_id = jobs[0]["id"]
        self.assertEqual("draft", jobs[0]["status"])
        self.assertEqual([], self.transport_calls)
        self.assertFalse(self.app.ai_incoming.exists())

        confirmed_page = self.post_ai_job(
            action="confirm",
            job_id=job_id,
        )
        self.assertIn("endnu ikke sendt", confirmed_page)
        self.assertIn("Send bekræftet job nu", confirmed_page)
        self.assertEqual("confirmed", self.kb.ai_job(job_id)["status"])
        self.assertEqual([], self.transport_calls)
        self.assertFalse(self.app.ai_incoming.exists())


if __name__ == "__main__":
    unittest.main()
