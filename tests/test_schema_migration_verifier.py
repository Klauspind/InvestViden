import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from investkb.schema import SCHEMA_SQL
from scripts.verify_schema_v3_migration import verify


class SchemaMigrationVerifierTest(unittest.TestCase):
    def _make_legacy(self, path: Path, version: int) -> None:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(SCHEMA_SQL)
            if version == 1:
                conn.execute("DROP TABLE source_provenance")
            conn.execute(
                "INSERT INTO schema_version(version, applied_at) VALUES(?, '2026-08-21T12:00:00+00:00')",
                (version,),
            )
            if version == 2:
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES(1, '2026-08-20T12:00:00+00:00')"
                )
            conn.execute(
                """INSERT INTO sources
                   (id, source_type, title, publisher, published_at, language,
                    original_path, stored_path, sha256, imported_at)
                   VALUES ('source-old', 'report', 'Historisk testkilde', NULL, '2026-08-20', 'da',
                           'C:/legacy/source.txt', 'C:/legacy/source.txt', ?, '2026-08-21T12:00:00+00:00')""",
                ("a" * 64,),
            )
            conn.execute(
                """INSERT INTO extraction_runs
                   (id, source_id, provider, model, schema_version, extracted_at, imported_at)
                   VALUES ('run-old', 'source-old', 'legacy-test', NULL, '0.1',
                           '2026-08-21T12:01:00+00:00', '2026-08-21T12:01:00+00:00')"""
            )
            conn.execute(
                """INSERT INTO claims
                   (id, source_id, run_id, fingerprint, claim_type, summary, speaker,
                    sentiment, action, time_horizon, discussion_depth, confidence,
                    review_status, review_note, created_at, updated_at)
                   VALUES ('claim-old', 'source-old', 'run-old', 'fp-old', 'theme',
                           'Historisk udsagn', NULL, 'neutral', 'none', 'unspecified',
                           'brief', 0.7, 'approved', 'Kontrolleret',
                           '2026-08-21T12:02:00+00:00', '2026-08-21T12:02:00+00:00')"""
            )
            conn.execute(
                """INSERT INTO evidence(claim_id, excerpt, start_ref, end_ref)
                   VALUES ('claim-old', 'Historisk udsagn', 'side 1', NULL)"""
            )
            conn.commit()
        finally:
            conn.close()

    def _assert_source_unchanged(self, source: Path, expected_version: int) -> None:
        conn = sqlite3.connect(source)
        try:
            self.assertEqual(
                expected_version,
                int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]),
            )
            self.assertEqual(
                1,
                int(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]),
            )
        finally:
            conn.close()

    def test_schema1_copy_is_migrated_and_source_remains_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "schema1.sqlite"
            output = root / "schema4.sqlite"
            self._make_legacy(source, 1)

            result = verify(source, output)

            self.assertEqual(1, result["source_schema_version"])
            self.assertTrue(all(result["comparisons"].values()))
            self.assertEqual(0, result["before"]["source_provenance"])
            self.assertEqual(0, result["after"]["source_provenance"])
            self._assert_source_unchanged(source, 1)

    def test_schema2_copy_still_migrates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "schema2.sqlite"
            output = root / "schema4.sqlite"
            self._make_legacy(source, 2)

            result = verify(source, output)

            self.assertEqual(2, result["source_schema_version"])
            self.assertTrue(all(result["comparisons"].values()))
            self._assert_source_unchanged(source, 2)


if __name__ == "__main__":
    unittest.main()
