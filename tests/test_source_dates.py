import hashlib
import json
import sys
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.mistral_jobs import create_mistral_job
from investkb.operational_navigation import create_operational_server
from investkb.operational_web_app import _source_matches
from investkb.repository import KnowledgeBase
from investkb.source_dates import source_date


class SourceDateTest(unittest.TestCase):
    def test_registered_date_and_unknown_values(self):
        self.assertEqual((date(2026, 10, 9), "Udgivet: 09.10.2026"),
                         source_date({"published_at": "2026-10-09"}))
        self.assertEqual("Udgivet: 09.10.2026",
                         source_date({"published_at": "2026-10-09T23:00:00Z"})[1])
        for value in (None, "", "  ", "2026-02-30", "2026-10", "2026-10-09garbage"):
            with self.subTest(value=value):
                self.assertEqual((None, "Udgivelsesdato ukendt"), source_date({
                    "published_at": value, "imported_at": "2026-10-28"}))

    def test_provenance_fallback_and_registered_date_precedence(self):
        source = {"source_type": "podcast_transcript", "provenance_json": json.dumps({
            "kind": "investviden_podcast_source", "episode": {"published_at": "2024-03-02"},
            "upstream": {"processing_timestamp": "2026-10-28"}})}
        self.assertEqual((date(2024, 3, 2), "Udgivet: 02.03.2024 (registreret provenance)"),
                         source_date(source))
        source["published_at"] = "2025-01-01"
        self.assertEqual("Udgivet: 01.01.2025", source_date(source)[1])
        source["published_at"] = None
        for metadata in ('broken', '[]', '{"episode": []}',
                         '{"kind":"investviden_podcast_source","episode":null}'):
            source["provenance_json"] = metadata
            self.assertEqual((None, "Udgivelsesdato ukendt"), source_date(source))

    def test_filename_hint_is_explicit_and_not_a_sortable_publication_date(self):
        for path in (r"C:\archive\2024-03-02 Episode.txt", "/archive/2024_03_02_Episode.txt"):
            self.assertEqual((None, "Udgivelsesdato ukendt · Dato fra filnavn: 02.03.2024 (ikke verificeret)"),
                             source_date({"source_type": "podcast_transcript", "original_path": path}))
        for path in ("/2024-03-02/EP-1049.txt", "EP-1049.txt", "2024-02-30 Podcast.txt",
                     "2024-03_02 Episode.txt", "2024-03-021 Episode.txt", "Episode 02.03.24.txt"):
            with self.subTest(path=path):
                self.assertEqual((None, "Udgivelsesdato ukendt"), source_date({
                    "source_type": "podcast_transcript", "original_path": path}))


class SourceDateIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kb = KnowledgeBase(self.root / "kb.sqlite")
        self.kb.initialize()

    def tearDown(self):
        self.kb.close()
        self.temp.cleanup()

    def source(self, filename, published=None):
        path = self.root / filename
        path.write_text(f"Synthetic podcast: {filename}", encoding="utf-8")
        return self.kb.import_source(path, "podcast_transcript", title=filename,
                                     published_at=published, source_store=self.root / "sources")[0]

    def provenance(self, source_id, published):
        self.kb.record_source_provenance(source_id, {
            "kind": "investviden_podcast_source", "episode_key": source_id,
            "episode": {"title": "Synthetic", "publisher": "Synthetic", "language": "da",
                        "published_at": published},
            "upstream": {"path": "synthetic.json", "sha256": "0" * 64},
            "render": {"renderer_version": "synthetic"}})
        # Model historical missing metadata without modifying a real database.
        with self.kb.conn:
            self.kb.conn.execute("UPDATE source_versions SET published_at=NULL WHERE id=?", (source_id,))

    def test_selection_sorts_known_dates_before_unknown_before_limit(self):
        old = self.source("old.txt", "2020-01-01")
        newest = self.source("newest.txt", "2026-10-01")
        provenance = self.source("provenance.txt")
        self.provenance(provenance, "2025-03-02")
        unknown = self.source("unknown.txt")
        filename = self.source("2026-10-28 hint.txt")
        blank = self.source("blank.txt", "")
        with self.kb.conn:
            self.kb.conn.execute("UPDATE source_versions SET imported_at='2099-01-01' WHERE id IN (?,?,?)",
                                 (unknown, filename, blank))
        before = self.kb.conn.total_changes
        self.assertEqual([newest, provenance, old],
                         [s["id"] for s in _source_matches(self.kb, "", limit=3)])
        rows = _source_matches(self.kb, "")
        self.assertEqual({unknown, filename, blank}, {s["id"] for s in rows[3:]})
        self.assertEqual(before, self.kb.conn.total_changes)

    def test_existing_fifteen_drafts_show_dates_without_changing_database_or_sending(self):
        ids = [self.source("2023-02-01 hint.txt" if i == 2 else f"draft-{i}.txt",
                           "2026-10-09" if i == 0 else None) for i in range(15)]
        self.provenance(ids[1], "2024-03-02")
        jobs = [create_mistral_job(self.kb, self.root / "incoming", source_ids=[s]) for s in ids]
        # A selectable source must also show its date and policy/selection controls.
        self.source("selectable.txt", "2025-06-01")
        self.source("undated-selectable.txt")
        before = hashlib.sha256(self.kb.db_path.read_bytes()).hexdigest()
        server, app = create_operational_server(self.kb.db_path, 0)
        app.mistral_transport = Mock(side_effect=AssertionError("No external AI expected"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_address[1]}/ai-jobs", timeout=5) as response:
                page = response.read().decode("utf-8")
            selection, history = page.split("<h2>Jobhistorik</h2>")
            self.assertIn("Udgivet: 01.06.2025", selection)
            self.assertIn("Udgivelsesdato ukendt", selection)
            self.assertIn('name="source_id"', selection)
            self.assertIn("AI-politik", selection)
            self.assertIn("Udgivet: 09.10.2026", history)
            self.assertIn("Udgivet: 02.03.2024 (registreret provenance)", history)
            self.assertIn("Dato fra filnavn: 01.02.2023 (ikke verificeret)", history)
            self.assertEqual(13, history.count("Udgivelsesdato ukendt"))
            for job in jobs:
                self.assertIn(job["id"], history)
            self.assertIn("Bekræft kilder og pris", history)
            self.assertIn("Estimat USD", history)
            self.assertEqual("2026-10-09", self.kb.ai_job(jobs[0]["id"])["items"][0]["published_at"])
            self.assertEqual({"draft"}, {job["status"] for job in self.kb.ai_jobs()})
            app.mistral_transport.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(before, hashlib.sha256(self.kb.db_path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
