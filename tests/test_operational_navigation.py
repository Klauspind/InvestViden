import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.operational_navigation import _focus_job_in_html, _job_redirect


class OperationalNavigationTest(unittest.TestCase):
    def test_confirm_redirect_keeps_filter_and_focuses_exact_job(self):
        job_id = "ai-job-6a2082bd564c4005afc5"
        target = _job_redirect(
            "/ai-jobs?message=Job+ai-job-6a2082bd564c4005afc5+er+bekr%C3%A6ftet%2C+men+endnu+ikke+sendt.",
            "http://127.0.0.1:8765/ai-jobs?q=Novo",
        )
        parsed = urlparse(target)
        self.assertEqual("/ai-jobs", parsed.path)
        self.assertEqual("Novo", parse_qs(parsed.query)["q"][0])
        self.assertEqual(job_id, parsed.fragment)

    def test_job_cards_receive_matching_fragment_ids(self):
        job_id = "ai-job-6a2082bd564c4005afc5"
        body = (
            '<h1>Mistral-job</h1><h2>Jobhistorik</h2>'
            f'<article class="card"><h3>{job_id}</h3><p>Status: confirmed</p></article>'
        ).encode("utf-8")
        focused = _focus_job_in_html(body).decode("utf-8")
        self.assertIn(f'<article class="card" id="{job_id}"><h3>{job_id}</h3>', focused)

    def test_non_job_redirect_is_unchanged(self):
        self.assertEqual("/search?q=Novo", _job_redirect("/search?q=Novo", None))


if __name__ == "__main__":
    unittest.main()
