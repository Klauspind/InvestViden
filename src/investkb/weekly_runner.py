"""Conservative weekly Mistral *draft* runner (no external calls or approvals).

Run only against an explicitly chosen schema-4 database. Scheduling and job
execution are deliberately outside this module; drafts still require an owner
confirmation through the existing Mistral workflow.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .mistral_jobs import DEFAULT_COST_LIMIT_USD, create_mistral_job, estimate_task_cost
from .migrations import LATEST_SCHEMA_VERSION, current_schema_version
from .openai_api import _pending_source_ids, plan_openai_extractions
from .repository import KnowledgeBase, file_sha256
from .validation import ValidationError


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _week(value: date) -> str:
    year, number, _ = value.isocalendar()
    return f'{year}-W{number:02d}'


def _require_isolated_schema4_database(kb: KnowledgeBase) -> None:
    """Refuse writes unless the caller supplied a non-active schema-4 copy.

    The weekly runner is intentionally not a migration mechanism.  In
    particular, its normal repository default (`data/knowledgebase.sqlite`) is
    the protected schema-2 production database on the owner's machine.
    """
    database_path = Path(kb.db_path).resolve()
    active_path = (Path.cwd() / "data" / "knowledgebase.sqlite").resolve()
    if database_path == active_path:
        raise RuntimeError(
            "Den aktive data/knowledgebase.sqlite må ikke bruges af den ugentlige runner. "
            "Vælg en udtrykkeligt isoleret schema-4-kopi."
        )
    try:
        version = current_schema_version(kb.conn)
    except Exception as exc:
        raise RuntimeError("Runneren kræver en eksisterende, isoleret schema-4-database") from exc
    if version != LATEST_SCHEMA_VERSION:
        raise RuntimeError(
            f"Runneren kræver schema {LATEST_SCHEMA_VERSION}; databasen bruger schema {version}. "
            "Migration må kun ske på en kontrolleret kopi."
        )


def _batches(kb: KnowledgeBase, incoming_dir: Path, max_jobs: int) -> tuple[list[list[str]], int]:
    pending = _pending_source_ids(incoming_dir)
    reserved = {
        str(row[0]) for row in kb.conn.execute('SELECT DISTINCT source_version_id FROM ai_job_items')
    }
    batches: list[list[str]] = []
    skipped = 0
    current: list[str] = []
    cost = 0.0
    for source in kb.sources_for_extraction(False):
        source_id = str(source['id'])
        if source_id in pending or source_id in reserved or source['ai_permission'] != 'allow':
            skipped += 1
            continue
        if not kb.external_ai_allowed(source_id, str(source['sha256'])):
            skipped += 1
            continue
        # Reuse the existing planner's hash verification and cost safeguards.
        task = plan_openai_extractions(kb, incoming_dir, source_ids=[source_id])[0]
        estimated = estimate_task_cost(task)
        if estimated > DEFAULT_COST_LIMIT_USD:
            skipped += 1
            continue
        if current and (len(current) == 5 or cost + estimated > DEFAULT_COST_LIMIT_USD):
            batches.append(current)
            current, cost = [], 0.0
            if len(batches) >= max_jobs:
                break
        current.append(source_id)
        cost += estimated
    if current and len(batches) < max_jobs:
        batches.append(current)
    return batches, skipped


def _verified_backup(kb: KnowledgeBase, backup_dir: Path, keep: int = 30) -> dict[str, Any]:
    """Verify backup bytes again before deleting old, locally owned backups."""
    info = kb.backup_database(backup_dir, keep=None)
    path = Path(info['path'])
    if info['integrity'] != 'ok' or not path.is_file() or file_sha256(path) != info['sha256']:
        raise RuntimeError('Backup hash/integrity mismatch; no retention performed')
    import sqlite3
    uri = path.resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as check:
        if check.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup read-only integrity check failed; no retention performed')
    backups = sorted(backup_dir.glob('investviden-*.sqlite'),
                     key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    removed = []
    for old in backups[keep:]:
        if old.resolve() == path.resolve():
            continue
        old.unlink()
        removed.append(old.name)
    return {'name': path.name, 'sha256': info['sha256'], 'integrity': 'ok', 'removed': len(removed)}


def run_weekly_drafts(kb: KnowledgeBase, incoming_dir: Path, state_dir: Path,
                      backup_dir: Path, *, today: date | None = None,
                      max_jobs: int = 5, apply: bool = False) -> dict[str, Any]:
    """Preview by default; apply only creates *unconfirmed* drafts.

    A persistent local week marker and exclusive lock fail closed after crashes.
    A failed/incomplete week requires explicit operator reconciliation rather
    than risking duplicated jobs. No AI transport is called by this module.
    """
    if not 1 <= max_jobs <= 20:
        raise ValidationError('max_jobs must be 1..20')
    if apply:
        _require_isolated_schema4_database(kb)
    week = _week(today or datetime.now(timezone.utc).date())
    state_dir = Path(state_dir)
    marker = state_dir / f'weekly-{week}.json'
    if marker.exists():
        existing = json.loads(marker.read_text(encoding='utf-8'))
        return {'week': week, 'status': 'already_completed' if existing.get('status') == 'completed' else 'manual_recovery_required',
                'jobs': len(existing.get('jobs', []))}
    batches, skipped = _batches(kb, incoming_dir, max_jobs)
    if not apply:
        return {'week': week, 'status': 'preview', 'jobs': len(batches),
                'eligible_sources': sum(map(len, batches)), 'skipped_sources': skipped}
    if not batches:
        return {'week': week, 'status': 'nothing_to_do', 'jobs': 0, 'skipped_sources': skipped}
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / 'weekly.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError('A weekly run is locked; operator reconciliation required') from exc
    os.close(descriptor)
    try:
        # Recheck while holding the lock, before any database writes.
        if marker.exists():
            return {'week': week, 'status': 'manual_recovery_required', 'jobs': 0}
        state: dict[str, Any] = {'week': week, 'status': 'started', 'jobs': []}
        _atomic_json(marker, state)
        try:
            for ids in batches:
                # Existing create_mistral_job rechecks hashes, policy and cost.
                job = create_mistral_job(kb, incoming_dir, source_ids=ids,
                                        cost_limit_usd=DEFAULT_COST_LIMIT_USD)
                state['jobs'].append(job['id'])
                _atomic_json(marker, state)
            state['backup'] = _verified_backup(kb, backup_dir)
            state['status'] = 'completed'
            _atomic_json(marker, state)
        except Exception:
            state['status'] = 'manual_recovery_required'
            # Best-effort backup of drafts already written; never auto-retry jobs.
            if state['jobs'] and 'backup' not in state:
                try:
                    state['backup'] = _verified_backup(kb, backup_dir)
                except Exception:
                    pass
            _atomic_json(marker, state)
            raise
        return {'week': week, 'status': 'completed', 'jobs': len(state['jobs']),
                'eligible_sources': sum(map(len, batches)), 'skipped_sources': skipped,
                'backup_integrity': state['backup']['integrity']}
    finally:
        lock.unlink(missing_ok=True)
