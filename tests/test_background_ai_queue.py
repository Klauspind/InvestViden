import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.operational_navigation import create_operational_server
from investkb.repository import KnowledgeBase


class BackgroundAIQueueTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "kb.sqlite"
        self.source_ids = []
        with KnowledgeBase(self.db_path) as kb:
            kb.initialize()
            for index, name in enumerate(("Novo Alpha", "Novo Beta", "Novo Gamma"), start=1):
                path = self.root / f"source-{index}.txt"
                path.write_text(f"{name} reported strong demand in the latest update.", encoding="utf-8")
                source_id, _ = kb.import_source(
                    path,
                    "report",
                    title=name,
                    publisher="Synthetic Research",
                    published_at=f"2026-10-0{index}",
                    source_store=self.root / "sources",
                    ai_permission="ask",
                )
                self.source_ids.append(source_id)

        self.started = threading.Event()
        self.release = threading.Event()
        self.block_transport = False
        self.fail_source_id = None
        self.active_calls = 0
        self.max_active_calls = 0
        self.transport_lock = threading.Lock()

        self.server, self.app = create_operational_server(self.db_path, 0)
        self.app.mistral_api_key = "not-real"
        self.app.mistral_transport = self.response
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.release.set()
        queue = getattr(self.app, "background_ai_queue", None)
        if queue is not None:
            queue.wait_until_idle(5)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def response(self, payload, key, timeout):
        source_id = payload["metadata"]["source_id"]
        with self.transport_lock:
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            self.started.set()
            if self.block_transport:
                self.release.wait(5)
            if source_id == self.fail_source_id:
                raise RuntimeError("syntetisk Mistral-fejl")
            extraction = json.loads((ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8"))
            extraction["source_id"] = source_id
            extraction["claims"] = [extraction["claims"][0]]
            claim = extraction["claims"][0]
            claim["summary"] = f"Research signal for {source_id}."
            claim["speaker"] = None
            claim["review_status"] = "approved"
            claim["companies"] = [{"name": "Novo Nordisk", "ticker": "NOVO-B", "role": "primary"}]
            claim["themes"] = ["demand"]
            with KnowledgeBase(self.db_path) as kb:
                stored = kb.conn.execute(
                    "SELECT stored_path FROM source_versions WHERE id=?", (source_id,)
                ).fetchone()[0]
            source_text = Path(stored).read_text(encoding="utf-8")
            claim["evidence"] = {
                "excerpt": source_text,
                "start_ref": "p1",
                "end_ref": "p1",
            }
            time.sleep(0.03)
            return {
                "id": "iv014-response-" + source_id,
                "model": "mistral-small-2603",
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps(extraction, ensure_ascii=False)},
                }],
                "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280},
            }
        finally:
            with self.transport_lock:
                self.active_calls -= 1

    def get(self, path, timeout=3):
        with urlopen(self.base + path, timeout=timeout) as response:
            return response.read().decode("utf-8")

    def post(self, values, timeout=3):
        payload = urlencode(values, doseq=True).encode("utf-8")
        request = Request(
            self.base + "/ai-jobs",
            data=payload,
            headers={"Referer": self.base + "/ai-jobs?q=Novo"},
        )
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")

    def create_and_confirm(self, source_ids):
        self.post({
            "csrf_token": self.app.csrf_token,
            "action": "create",
            "source_id": source_ids,
        })
        with KnowledgeBase(self.db_path) as kb:
            job_id = kb.ai_jobs()[0]["id"]
        self.post({
            "csrf_token": self.app.csrf_token,
            "action": "confirm",
            "job_id": job_id,
        })
        return job_id

    def test_send_returns_immediately_while_job_continues_in_background(self):
        job_id = self.create_and_confirm([self.source_ids[0]])
        self.block_transport = True

        page = self.post({
            "csrf_token": self.app.csrf_token,
            "action": "run",
            "job_id": job_id,
        }, timeout=2)
        self.assertIn("sat i baggrundskø", page)
        self.assertTrue(self.started.wait(2))

        overview = self.get("/", timeout=2)
        self.assertIn("Din lokale investeringsviden", overview)
        jobs_page = self.get("/ai-jobs?q=Novo", timeout=2)
        self.assertIn("Mistral arbejder i baggrunden", jobs_page)
        self.assertIn("Opdater status", jobs_page)

        self.release.set()
        self.assertTrue(self.app.background_ai_queue.wait_until_idle(5))
        with KnowledgeBase(self.db_path) as kb:
            self.assertEqual("completed", kb.ai_job(job_id)["status"])
            self.assertEqual(1, len(kb.claims()))

    def test_multiple_confirmed_jobs_can_be_queued_and_run_sequentially(self):
        first = self.create_and_confirm([self.source_ids[0]])
        second = self.create_and_confirm([self.source_ids[1]])

        page = self.get("/ai-jobs?q=Novo")
        self.assertIn("Send flere bekræftede jobs", page)
        self.assertIn(first, page)
        self.assertIn(second, page)

        page = self.post({
            "csrf_token": self.app.csrf_token,
            "action": "run_batch",
            "batch_job_id": [first, second],
        })
        self.assertIn("2 bekræftede jobs er sat i baggrundskø", page)
        self.assertTrue(self.app.background_ai_queue.wait_until_idle(5))

        with KnowledgeBase(self.db_path) as kb:
            self.assertEqual("completed", kb.ai_job(first)["status"])
            self.assertEqual("completed", kb.ai_job(second)["status"])
            self.assertEqual(2, len(kb.claims()))
        self.assertEqual(1, self.max_active_calls)

    def test_partial_status_is_explained_and_successful_item_is_kept(self):
        self.fail_source_id = self.source_ids[1]
        job_id = self.create_and_confirm([self.source_ids[0], self.source_ids[1]])
        self.post({
            "csrf_token": self.app.csrf_token,
            "action": "run",
            "job_id": job_id,
        })
        self.assertTrue(self.app.background_ai_queue.wait_until_idle(5))

        with KnowledgeBase(self.db_path) as kb:
            job = kb.ai_job(job_id)
            self.assertEqual("partial", job["status"])
            self.assertEqual({"validated", "failed"}, {item["status"] for item in job["items"]})
            self.assertEqual(1, len(kb.claims()))

        page = self.get("/ai-jobs?q=Novo")
        self.assertIn("partial · delvist færdig", page)
        self.assertIn("De vellykkede resultater er bevaret", page)
        self.assertIn("Genkør valgte", page)


if __name__ == "__main__":
    unittest.main()
