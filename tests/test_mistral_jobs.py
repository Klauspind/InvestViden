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

from investkb.mistral_jobs import create_mistral_job, execute_mistral_job
from investkb.repository import KnowledgeBase
from investkb.validation import ValidationError
from investkb.web_app import create_server


class MistralJobTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        self.incoming = self.root / "incoming"
        self.audit = self.root / "audit"
        self.schema = ROOT / "schemas" / "extraction-v0.1.schema.json"
        self.source_ids = []
        for index in range(2):
            path = self.root / f"source-{index}.txt"
            path.write_text(f"[00:0{index}] Syntetisk investeringsudsagn {index}.", encoding="utf-8")
            source_id, _ = self.kb.import_source(
                path, "podcast_transcript", source_store=self.root / "sources"
            )
            self.source_ids.append(source_id)

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def response(self, payload, *, response_id="mistral-job-response"):
        source_id = payload["metadata"]["source_id"]
        extraction = json.loads((ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8"))
        extraction["source_id"] = source_id
        extraction["claims"][0]["review_status"] = "approved"
        return {
            "id": response_id + "-" + source_id,
            "model": "mistral-large-2512",
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(extraction, ensure_ascii=False)},
            }],
            "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280},
        }

    def test_draft_has_versioned_estimate_and_requires_confirmation(self):
        calls = []
        job = create_mistral_job(self.kb, self.incoming, limit=1)

        self.assertEqual("draft", job["status"])
        self.assertEqual(1, len(job["items"]))
        self.assertGreater(job["estimated_cost_usd"], 0)
        self.assertLessEqual(job["estimated_cost_usd"], 0.10)
        self.assertEqual("mistral-standard-2026-09-14", job["pricing_version"])
        self.assertEqual(0, job["items"][0]["attempt_count"])
        self.assertFalse(self.incoming.exists())

        with self.assertRaisesRegex(ValidationError, "ikke bekræftet"):
            execute_mistral_job(
                self.kb, job["id"], self.schema, self.incoming, self.audit,
                api_key="not-real", transport=lambda *args: calls.append(args),
            )
        self.assertEqual([], calls)
        self.kb.confirm_ai_job(job["id"])
        self.assertEqual("confirmed", self.kb.ai_job(job["id"])["status"])

    def test_price_limit_and_source_limit_are_hard_guards(self):
        with self.assertRaisesRegex(ValidationError, "overstiger prisloftet"):
            create_mistral_job(self.kb, self.incoming, limit=1, cost_limit_usd=0.001)
        with self.assertRaisesRegex(ValidationError, "mellem 1 og 5"):
            create_mistral_job(self.kb, self.incoming, limit=6)
        self.assertEqual([], self.kb.ai_jobs())

    def test_confirmed_job_runs_to_validated_pending_results_never_approved(self):
        job = create_mistral_job(self.kb, self.incoming, limit=1)
        self.kb.confirm_ai_job(job["id"])
        result = execute_mistral_job(
            self.kb, job["id"], self.schema, self.incoming, self.audit,
            api_key="not-real", transport=lambda payload, key, timeout: self.response(payload),
        )

        self.assertEqual("completed", result["status"])
        self.assertEqual("validated", result["items"][0]["status"])
        self.assertEqual(1, result["items"][0]["attempt_count"])
        self.assertEqual(200, result["items"][0]["prompt_tokens"])
        self.assertEqual(80, result["items"][0]["completion_tokens"])
        self.assertGreater(result["actual_cost_usd"], 0)
        answer = json.loads(next(self.incoming.glob("mistral-*.json")).read_text(encoding="utf-8"))
        self.assertEqual({"ai_extracted"}, {claim["review_status"] for claim in answer["claims"]})
        self.assertEqual(0, len(self.kb.claims()))

    def test_partial_job_retries_only_selected_failed_source(self):
        job = create_mistral_job(self.kb, self.incoming, limit=2)
        self.kb.confirm_ai_job(job["id"])
        failed_source = job["items"][1]["source_version_id"]

        def first_transport(payload, key, timeout):
            if payload["metadata"]["source_id"] == failed_source:
                raise RuntimeError("syntetisk transportfejl")
            return self.response(payload, response_id="first")

        first = execute_mistral_job(
            self.kb, job["id"], self.schema, self.incoming, self.audit,
            api_key="not-real", transport=first_transport,
        )
        self.assertEqual("partial", first["status"])
        statuses = {item["source_version_id"]: item["status"] for item in first["items"]}
        self.assertEqual("failed", statuses[failed_source])

        successful_source = next(source for source, status in statuses.items() if status == "validated")
        with self.assertRaisesRegex(ValidationError, "Kun fejlede"):
            execute_mistral_job(
                self.kb, job["id"], self.schema, self.incoming, self.audit,
                api_key="not-real", transport=lambda p, k, t: self.response(p),
                retry_source_ids=[successful_source],
            )

        final = execute_mistral_job(
            self.kb, job["id"], self.schema, self.incoming, self.audit,
            api_key="not-real", transport=lambda p, k, t: self.response(p, response_id="retry"),
            retry_source_ids=[failed_source],
        )
        self.assertEqual("completed", final["status"])
        attempts = {item["source_version_id"]: item["attempt_count"] for item in final["items"]}
        self.assertEqual(1, attempts[successful_source])
        self.assertEqual(2, attempts[failed_source])

    def test_ask_policy_needs_exact_source_hash_when_job_is_created(self):
        for source_id in self.source_ids:
            self.kb.set_source_permission(source_id, "local_only")
        path = self.root / "ask-source.txt"
        path.write_text("Syntetisk ask-kilde", encoding="utf-8")
        ask_id, _ = self.kb.import_source(
            path, "report", source_store=self.root / "sources", ai_permission="ask"
        )
        ask_hash = next(row["sha256"] for row in self.kb.source_policies() if row["id"] == ask_id)

        with self.assertRaisesRegex(ValidationError, "Ingen kilder"):
            create_mistral_job(self.kb, self.incoming, limit=1)
        job = create_mistral_job(
            self.kb, self.incoming, limit=1, approvals={ask_id: ask_hash}
        )
        self.assertEqual(ask_id, job["items"][0]["source_version_id"])

    def test_http_job_flow_has_separate_create_confirm_and_send_steps(self):
        database_path = self.kb.db_path
        server, app = create_server(database_path, 0)
        app.mistral_api_key = "not-real"
        app.mistral_transport = lambda payload, key, timeout: self.response(payload, response_id="http")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        def post(values):
            payload = urlencode(values, doseq=True).encode("utf-8")
            with urlopen(Request(base_url + "/ai-jobs", data=payload), timeout=10) as response:
                return response.read().decode("utf-8")

        try:
            with urlopen(base_url + "/ai-jobs", timeout=5) as response:
                page = response.read().decode("utf-8")
            self.assertIn("Opret kladde med valgte kilder", page)
            self.assertIn(self.source_ids[0], page)

            page = post({
                "csrf_token": app.csrf_token,
                "action": "create",
                "source_id": self.source_ids[0],
            })
            self.assertIn("Ingen tekst er sendt", page)
            job = self.kb.ai_jobs()[0]
            self.assertEqual("draft", job["status"])
            self.assertFalse(app.ai_incoming.exists())

            page = post({
                "csrf_token": app.csrf_token,
                "action": "confirm",
                "job_id": job["id"],
            })
            self.assertIn("endnu ikke sendt", page)
            self.assertEqual("confirmed", self.kb.ai_job(job["id"])["status"])

            page = post({
                "csrf_token": app.csrf_token,
                "action": "run",
                "job_id": job["id"],
            })
            self.assertIn("status completed", page)
            self.assertEqual("completed", self.kb.ai_job(job["id"])["status"])
            answer = json.loads(next(app.ai_incoming.glob("mistral-*.json")).read_text(encoding="utf-8"))
            self.assertEqual({"ai_extracted"}, {claim["review_status"] for claim in answer["claims"]})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
