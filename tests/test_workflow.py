import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.outputs import write_dashboard, write_export, write_report, write_tasks
from investkb.inbox import scan_inbox
from investkb.repository import KnowledgeBase
from investkb.validation import ValidationError, validate_extraction


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()
        self.source = self.root / "source.txt"
        self.source.write_text("[00:01] En dokumenteret investeringspåstand.", encoding="utf-8")
        self.source_id, created = self.kb.import_source(
            self.source, "podcast_transcript", source_store=self.root / "sources"
        )
        self.assertTrue(created)

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def extraction(self):
        data = json.loads((ROOT / "examples" / "demo_extraction.json").read_text(encoding="utf-8"))
        data["source_id"] = self.source_id
        return data

    def test_end_to_end_and_idempotent_source(self):
        same_id, created = self.kb.import_source(
            self.source, "podcast_transcript", source_store=self.root / "sources"
        )
        self.assertEqual(self.source_id, same_id)
        self.assertFalse(created)
        _, count = self.kb.ingest(self.extraction())
        self.assertEqual(2, count)
        self.assertEqual(2, len(self.kb.claims()))

        tasks = self.root / "tasks.jsonl"
        report = self.root / "report.md"
        dashboard = self.root / "dashboard.html"
        export = self.root / "export.jsonl"
        self.assertEqual(1, write_tasks(self.kb, tasks, all_sources=True))
        self.assertEqual(2, write_report(self.kb, report))
        self.assertEqual(2, write_dashboard(self.kb, dashboard))
        self.assertEqual(2, write_export(self.kb, export))
        self.assertIn("Eksempel Energi", report.read_text(encoding="utf-8"))
        self.assertIn("InvestViden – kontroloversigt", dashboard.read_text(encoding="utf-8"))

        priority_tasks = self.root / "priority-tasks.jsonl"
        write_tasks(
            self.kb,
            priority_tasks,
            all_sources=True,
            preferences={"extraction_priorities": {"events": ["regnskaber"]}},
        )
        task = json.loads(priority_tasks.read_text(encoding="utf-8"))
        self.assertEqual(["regnskaber"], task["priorities"]["events"])

    def test_review_preserved_on_reingest(self):
        self.kb.ingest(self.extraction())
        claim_id = self.kb.claims()[0]["id"]
        self.kb.set_review(claim_id, "approved", "Kontrolleret")
        self.kb.ingest(self.extraction())
        status = {c["id"]: c["review_status"] for c in self.kb.claims()}[claim_id]
        self.assertEqual("approved", status)

    def test_invalid_confidence_is_rejected(self):
        data = self.extraction()
        data["claims"][0]["confidence"] = 1.5
        with self.assertRaises(ValidationError):
            validate_extraction(data)

    def test_status_and_priority_report(self):
        self.kb.ingest(self.extraction())
        stats = self.kb.stats(0.95)
        self.assertEqual(1, stats["low_confidence"])
        report = self.root / "priority.md"
        write_report(
            self.kb,
            report,
            preferences={"portfolio": {"stocks": ["Eksempel Energi"], "watchlist": []}},
        )
        text = report.read_text(encoding="utf-8")
        self.assertIn("Relevans for din portefølje", text)
        self.assertIn("### Eksempel Energi", text)

    def test_remove_source_cascades(self):
        self.kb.ingest(self.extraction())
        self.kb.remove_source(self.source_id)
        self.assertEqual(0, self.kb.stats()["sources"])
        self.assertEqual(0, self.kb.stats()["claims"])

    def test_bulk_review(self):
        self.kb.ingest(self.extraction())
        count = self.kb.set_review_all("approved", "ai_extracted", "Godkendt i samlet kontrol")
        self.assertEqual(2, count)
        self.assertEqual({"approved": 2}, self.kb.stats()["review_counts"])

    def test_scan_inbox_dry_run_import_and_duplicate_location(self):
        inbox = self.root / "inbox"
        correct = inbox / "transskriptioner" / "Macro Mondays"
        wrong = inbox / "transskriptioner" / "Millionærklubben"
        correct.mkdir(parents=True)
        wrong.mkdir(parents=True)
        filename = "2026-07-20 China Macro Mondays.txt"
        (correct / filename).write_text("The same transcript.", encoding="utf-8")
        (wrong / filename).write_text("The same transcript.", encoding="utf-8")
        settings = {
            "inbox": {
                "podcast_publishers": {"Macro Mondays": "Macro Mondays / Real Vision"},
                "podcast_languages": {"Macro Mondays": "en"},
            }
        }

        preview = scan_inbox(
            self.kb, inbox, settings, dry_run=True, source_store=self.root / "stored"
        )
        self.assertEqual(1, preview["new"])
        self.assertEqual(1, len(preview["duplicate_locations"]))
        self.assertEqual(1, self.kb.stats()["sources"])

        imported = scan_inbox(
            self.kb, inbox, settings, source_store=self.root / "stored"
        )
        self.assertEqual(1, imported["new"])
        row = self.kb.conn.execute(
            "SELECT publisher, published_at, language, title FROM sources WHERE title=?",
            ("China Macro Mondays",),
        ).fetchone()
        self.assertEqual("Macro Mondays / Real Vision", row["publisher"])
        self.assertEqual("2026-07-20", row["published_at"])
        self.assertEqual("en", row["language"])

        repeated = scan_inbox(
            self.kb, inbox, settings, source_store=self.root / "stored"
        )
        self.assertEqual(0, repeated["new"])
        self.assertEqual(1, repeated["existing"])

    def test_verified_backup_and_retention(self):
        self.kb.ingest(self.extraction())
        backup_dir = self.root / "backups"
        first = self.kb.backup_database(backup_dir)
        self.assertEqual("ok", first["integrity"])
        with KnowledgeBase(first["path"]) as restored:
            self.assertEqual(2, restored.stats()["claims"])

        second = self.kb.backup_database(backup_dir, keep=1)
        self.assertEqual("ok", second["integrity"])
        self.assertEqual(1, len(list(backup_dir.glob("investviden-*.sqlite"))))
        self.assertEqual(1, len(second["removed"]))


if __name__ == "__main__":
    unittest.main()
