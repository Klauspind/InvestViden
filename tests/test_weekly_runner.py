"""Offline regression tests; synthetic SQLite, no model transport or live database."""
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from investkb import weekly_runner as weekly
from investkb.repository import KnowledgeBase


class FakeKB:
    def __init__(self, root):
        self.path = root / 'isolated.sqlite'
        self.conn = sqlite3.connect(self.path)
        self.db_path = self.path
        self.conn.execute('CREATE TABLE schema_version(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
        self.conn.execute("INSERT INTO schema_version VALUES (4, '2026-09-19T00:00:00Z')")
        self.conn.execute('CREATE TABLE ai_jobs(id TEXT PRIMARY KEY)')
        self.conn.execute('CREATE TABLE ai_job_items(job_id TEXT, source_version_id TEXT)')
        self.conn.execute('CREATE TABLE synthetic(value TEXT)')
        self.conn.commit()
        self.rows = []
        self.job_count = 0

    def sources_for_extraction(self, all_sources=False):
        return list(self.rows)

    def external_ai_allowed(self, source_id, sha256, approvals=None):
        return any(row['id'] == source_id and row['sha256'] == sha256 and
                   row['ai_permission'] == 'allow' for row in self.rows)

    def backup_database(self, output_dir, keep=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f'investviden-{self.job_count:04d}.sqlite'
        with sqlite3.connect(path) as dest:
            self.conn.backup(dest)
        return {'path': str(path), 'sha256': weekly.file_sha256(path),
                'integrity': 'ok'}


class WeeklyRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kb = FakeKB(self.root)
        self.addCleanup(self.kb.conn.close)
        self.incoming = self.root / 'incoming'
        self.state = self.root / 'state'
        self.backups = self.root / 'backups'
        self.kb.rows = [
            {'id': 'allow-1', 'sha256': 'abc', 'ai_permission': 'allow'},
            {'id': 'ask-1', 'sha256': 'def', 'ai_permission': 'ask'},
            {'id': 'blocked-1', 'sha256': 'ghi', 'ai_permission': 'blocked'},
        ]

    def _plan(self, kb, incoming, source_ids=None, **kwargs):
        return [SimpleNamespace(source_id=source_ids[0])]

    def _create(self, kb, incoming, source_ids=None, **kwargs):
        kb.job_count += 1
        job_id = f'draft-{kb.job_count}'
        with kb.conn:
            kb.conn.execute('INSERT INTO ai_jobs VALUES (?)', (job_id,))
            for source_id in source_ids:
                kb.conn.execute('INSERT INTO ai_job_items VALUES (?, ?)', (job_id, source_id))
        return {'id': job_id, 'status': 'draft'}

    def _runner(self, **kwargs):
        return weekly.run_weekly_drafts(self.kb, self.incoming, self.state,
                                        self.backups, today=date(2026, 9, 19), **kwargs)

    def test_preview_read_only_and_policy_exclusion(self):
        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.03), \
             patch.object(weekly, 'create_mistral_job') as create:
            report = self._runner()
        self.assertEqual((report['status'], report['eligible_sources'], report['skipped_sources']),
                         ('preview', 1, 2))
        create.assert_not_called()
        self.assertFalse(self.state.exists())
        self.assertFalse(self.backups.exists())

    def test_draft_week_is_idempotent_and_backup_is_valid(self):
        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.03), \
             patch.object(weekly, 'create_mistral_job', side_effect=self._create) as create:
            first = self._runner(apply=True)
            second = self._runner(apply=True)
        self.assertEqual(first['status'], 'completed')
        self.assertEqual(first['backup_integrity'], 'ok')
        self.assertEqual(second['status'], 'already_completed')
        self.assertEqual(create.call_count, 1)
        self.assertEqual(self.kb.conn.execute('SELECT count(*) FROM ai_job_items').fetchone()[0], 1)
        self.assertEqual(len(list(self.backups.glob('*.sqlite'))), 1)

    def test_existing_job_not_queued_again(self):
        self.kb.conn.execute('INSERT INTO ai_job_items VALUES (?, ?)', ('existing-job', 'allow-1'))
        self.kb.conn.commit()
        with patch.object(weekly, '_pending_source_ids', return_value=set()):
            result = self._runner()
        self.assertEqual(result['eligible_sources'], 0)

    def test_interrupted_marker_requires_reconciliation(self):
        self.state.mkdir()
        (self.state / 'weekly-2026-W38.json').write_text(
            json.dumps({'week': '2026-W38', 'status': 'started', 'jobs': ['draft-1']}), encoding='utf-8')
        self.assertEqual(self._runner(apply=True)['status'], 'manual_recovery_required')
        self.assertEqual(self.kb.job_count, 0)

    def test_retention_only_our_backups_and_integrity(self):
        self.backups.mkdir()
        for index in range(32):
            (self.backups / f'investviden-old-{index:03d}.sqlite').write_text('old')
        unrelated = self.backups / 'other.sqlite'
        unrelated.write_text('keep')
        self.kb.job_count = 99
        info = weekly._verified_backup(self.kb, self.backups, keep=30)
        self.assertEqual(info['removed'], 3)
        self.assertEqual(len(list(self.backups.glob('investviden-*.sqlite'))), 30)
        self.assertTrue(unrelated.exists())
        self.assertEqual(info['integrity'], 'ok')

    def test_backup_mismatch_never_prunes(self):
        self.backups.mkdir()
        for i in range(31):
            (self.backups / f'investviden-old-{i:03d}.sqlite').write_text('old')
        def corrupt_backup(output_dir, keep=None):
            path = output_dir / 'investviden-new.sqlite'
            path.write_text('not-a-db')
            return {'path': str(path), 'sha256': 'bad', 'integrity': 'ok'}
        self.kb.backup_database = corrupt_backup
        with self.assertRaises(RuntimeError):
            weekly._verified_backup(self.kb, self.backups)
        self.assertEqual(len(list(self.backups.glob('investviden-*.sqlite'))), 32)

    def test_apply_rejects_the_protected_default_database_before_writes(self):
        protected_path = Path.cwd() / 'data' / 'knowledgebase.sqlite'
        original_path = self.kb.db_path
        self.kb.db_path = protected_path
        with self.assertRaisesRegex(RuntimeError, 'aktive data/knowledgebase'):
            self._runner(apply=True)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.backups.exists())
        self.kb.db_path = original_path

    def test_apply_rejects_an_isolated_database_below_schema_4_before_writes(self):
        self.kb.conn.execute('DELETE FROM schema_version')
        self.kb.conn.execute("INSERT INTO schema_version VALUES (3, '2026-09-19T00:00:00Z')")
        self.kb.conn.commit()
        with self.assertRaisesRegex(RuntimeError, 'kræver schema 4'):
            self._runner(apply=True)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.backups.exists())

    def test_isolated_schema4_integration_creates_only_unconfirmed_draft(self):
        database_path = self.root / 'preview' / 'schema4.sqlite'
        source = self.root / 'input.txt'
        source.write_text('En kort, isoleret testkilde.', encoding='utf-8')
        with KnowledgeBase(database_path) as kb:
            kb.initialize()
            source_id, created = kb.import_source(
                source, 'podcast_transcript', source_store=self.root / 'source-store',
            )
            self.assertTrue(created)
            with patch.object(weekly, 'estimate_task_cost', return_value=.03):
                result = weekly.run_weekly_drafts(
                    kb, self.incoming, self.state, self.backups,
                    today=date(2026, 9, 19), apply=True,
                )
            self.assertEqual(result['status'], 'completed')
            jobs = kb.ai_jobs()
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['status'], 'draft')
            self.assertEqual(jobs[0]['items'][0]['source_version_id'], source_id)
        with sqlite3.connect(database_path) as check:
            self.assertEqual(check.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_six_sources_are_split_into_jobs_of_at_most_five(self):
        self.kb.rows = [
            {'id': f'allow-{index}', 'sha256': f'hash-{index}', 'ai_permission': 'allow'}
            for index in range(6)
        ]
        created_batches = []

        def create(kb, incoming, source_ids=None, **kwargs):
            created_batches.append(list(source_ids))
            return self._create(kb, incoming, source_ids=source_ids, **kwargs)

        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.015), \
             patch.object(weekly, 'create_mistral_job', side_effect=create):
            result = self._runner(apply=True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(list(map(len, created_batches)), [5, 1])
        self.assertTrue(all(len(batch) <= 5 for batch in created_batches))

    def test_aggregate_cost_splits_batches_and_individual_over_limit_is_skipped(self):
        self.kb.rows = [
            {'id': f'allow-{index}', 'sha256': f'hash-{index}', 'ai_permission': 'allow'}
            for index in range(4)
        ]
        costs = {'allow-0': .06, 'allow-1': .04, 'allow-2': .01, 'allow-3': .101}

        def estimate(task):
            return costs[task.source_id]

        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', side_effect=estimate):
            batches, skipped = weekly._batches(self.kb, self.incoming, max_jobs=5)
        self.assertEqual(batches, [['allow-0', 'allow-1'], ['allow-2']])
        self.assertEqual(skipped, 1)
        self.assertTrue(all(sum(costs[source_id] for source_id in batch) <= .10 for batch in batches))

    def test_crash_after_database_commit_is_reconciled_without_retry(self):
        def commit_then_crash(kb, incoming, source_ids=None, **kwargs):
            self._create(kb, incoming, source_ids=source_ids, **kwargs)
            raise RuntimeError('synthetic crash after commit')

        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.03), \
             patch.object(weekly, 'create_mistral_job', side_effect=commit_then_crash):
            with self.assertRaisesRegex(RuntimeError, 'synthetic crash'):
                self._runner(apply=True)
        report = weekly.inspect_weekly_recovery(
            self.kb, self.state, today=date(2026, 9, 19),
        )
        self.assertEqual(report['status'], 'manual_recovery_required')
        self.assertEqual(report['planned_sources'], 1)
        self.assertEqual(report['reserved_sources'], 1)
        self.assertEqual(report['missing_sources'], [])
        self.assertEqual(len(report['database_jobs']), 1)
        self.assertEqual(self._runner(apply=True)['status'], 'manual_recovery_required')
        self.assertEqual(self.kb.job_count, 1)

    def test_backup_failure_preserves_draft_and_fail_closed_marker(self):
        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.03), \
             patch.object(weekly, 'create_mistral_job', side_effect=self._create), \
             patch.object(weekly, '_verified_backup', side_effect=RuntimeError('backup failed')):
            with self.assertRaisesRegex(RuntimeError, 'backup failed'):
                self._runner(apply=True)
        marker = json.loads((self.state / 'weekly-2026-W38.json').read_text(encoding='utf-8'))
        self.assertEqual(marker['status'], 'manual_recovery_required')
        self.assertEqual(len(marker['jobs']), 1)
        self.assertEqual(self.kb.conn.execute('SELECT count(*) FROM ai_job_items').fetchone()[0], 1)
        self.assertFalse((self.state / 'weekly.lock').exists())

    def test_stale_lock_is_reported_and_never_cleared_automatically(self):
        self.state.mkdir()
        lock = self.state / 'weekly.lock'
        lock.write_text('', encoding='utf-8')
        report = weekly.inspect_weekly_recovery(
            self.kb, self.state, today=date(2026, 9, 19),
        )
        self.assertEqual(report['status'], 'no_marker')
        self.assertTrue(report['lock_present'])
        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.03):
            with self.assertRaisesRegex(RuntimeError, 'locked'):
                self._runner(apply=True)
        self.assertTrue(lock.exists())

    def test_new_source_version_remains_eligible_when_old_version_is_reserved(self):
        self.kb.rows = [
            {'id': 'source-old', 'sha256': 'old-hash', 'ai_permission': 'allow'},
            {'id': 'source-new', 'sha256': 'new-hash', 'ai_permission': 'allow'},
        ]
        self.kb.conn.execute('INSERT INTO ai_job_items VALUES (?, ?)', ('existing-job', 'source-old'))
        self.kb.conn.commit()
        with patch.object(weekly, '_pending_source_ids', return_value=set()), \
             patch.object(weekly, 'plan_openai_extractions', side_effect=self._plan), \
             patch.object(weekly, 'estimate_task_cost', return_value=.03):
            batches, skipped = weekly._batches(self.kb, self.incoming, max_jobs=5)
        self.assertEqual(batches, [['source-new']])
        self.assertEqual(skipped, 1)


if __name__ == '__main__':
    unittest.main()
