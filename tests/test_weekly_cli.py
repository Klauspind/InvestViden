import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from investkb.cli import main
from investkb.repository import KnowledgeBase


class WeeklyCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'isolated-schema4.sqlite'
        self.source = self.root / 'source.txt'
        self.source.write_text('Syntetisk og ufølsom testkilde.', encoding='utf-8')
        with KnowledgeBase(self.database) as kb:
            kb.initialize()
            kb.import_source(
                self.source, 'podcast_transcript',
                source_store=self.root / 'source-store',
            )

    def _main(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_preview_is_default_and_creates_no_runtime_directories(self):
        state = self.root / 'state'
        backups = self.root / 'backups'
        code, output, error = self._main([
            'weekly-drafts', '--database', str(self.database),
            '--state-dir', str(state), '--backup-dir', str(backups),
        ])
        self.assertEqual((code, error), (0, ''))
        report = json.loads(output)
        self.assertEqual(report['status'], 'preview')
        self.assertFalse(state.exists())
        self.assertFalse(backups.exists())

    def test_recovery_is_read_only_when_no_marker_exists(self):
        state = self.root / 'state'
        code, output, error = self._main([
            'weekly-recovery', '--database', str(self.database),
            '--state-dir', str(state),
        ])
        self.assertEqual((code, error), (0, ''))
        report = json.loads(output)
        self.assertEqual(report['status'], 'no_marker')
        self.assertFalse(state.exists())

    def test_missing_database_is_rejected_without_creation(self):
        missing = self.root / 'missing.sqlite'
        code, output, error = self._main([
            'weekly-drafts', '--database', str(missing),
        ])
        self.assertEqual(code, 2)
        self.assertEqual(output, '')
        self.assertIn('opretter eller migrerer ikke', error)
        self.assertFalse(missing.exists())

    def test_apply_creates_only_draft_marker_and_verified_backup(self):
        state = self.root / 'state'
        backups = self.root / 'backups'
        code, output, error = self._main([
            'weekly-drafts', '--database', str(self.database), '--apply',
            '--incoming', str(self.root / 'incoming'),
            '--state-dir', str(state), '--backup-dir', str(backups),
        ])
        self.assertEqual((code, error), (0, ''))
        report = json.loads(output)
        self.assertEqual(report['status'], 'completed')
        with KnowledgeBase(self.database) as kb:
            jobs = kb.ai_jobs()
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['status'], 'draft')
        self.assertEqual(len(list(backups.glob('investviden-*.sqlite'))), 1)

    def test_windows_launchers_preserve_explicit_database_and_safe_defaults(self):
        root = Path(__file__).resolve().parents[1]
        cmd = (root / 'START_UGENTLIG_INVESTVIDEN.cmd').read_text(encoding='utf-8')
        powershell = (root / 'VERIFICER_UGENTLIG_RUNNER.ps1').read_text(encoding='utf-8')
        self.assertIn('set "DATABASE=%~1"', cmd)
        self.assertIn('set "MODE=preview"', cmd)
        self.assertIn('Skriv OPRET KLADDER', cmd)
        self.assertIn('weekly-recovery', cmd)
        self.assertIn('weekly-drafts', cmd)
        self.assertIn("data\\knowledgebase.sqlite", powershell)
        self.assertNotIn('--apply', powershell)


if __name__ == '__main__':
    unittest.main()
