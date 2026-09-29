"""Persistent local consumer for Transskribinator episode deliveries.

This consumer owns a dedicated schema-4 database outside the repository. It
imports new podcast episode JSONs idempotently and creates local, unconfirmed
Mistral job drafts. It never executes AI transport and must never use the
protected legacy database.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from investkb.intake import apply_input, plan_input
from investkb.migrations import current_schema_version
from investkb.mistral_jobs import (
    DEFAULT_COST_LIMIT_USD,
    create_mistral_job,
    estimate_task_cost,
)
from investkb.openai_api import plan_openai_extractions
from investkb.podcast_sync import read_episode
from investkb.repository import KnowledgeBase, file_sha256
from investkb.validation import ValidationError


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_DATA_ROOT = (ROOT / "data").resolve()
PROTECTED_DB = (PROTECTED_DATA_ROOT / "knowledgebase.sqlite").resolve()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _root_config(delivery_root: Path) -> dict[str, str]:
    return {
        "path": str(delivery_root),
        "format": "podcast_json",
        "source_type": "podcast_transcript",
        "permission": "allow",
        "publisher": "",
        "language": "da",
    }


def _validate_paths(delivery_root: Path, state_root: Path) -> tuple[Path, Path]:
    delivery = delivery_root.expanduser().resolve(strict=True)
    if not delivery.is_dir():
        raise ValidationError("Leveringsmappen findes ikke")
    state = state_root.expanduser().resolve()
    if delivery == state or _inside(delivery, state) or _inside(state, delivery):
        raise ValidationError("Leveringsmappe og consumer-state skal vaere adskilt")
    if _inside(state, PROTECTED_DATA_ROOT):
        raise ValidationError("Consumer-state maa ikke ligge i repositoryets beskyttede data-mappe")
    return delivery, state


def _validate_delivery(delivery_root: Path) -> dict[str, int]:
    json_count = 0
    episode_count = 0
    invalid_count = 0
    for path in sorted(delivery_root.rglob("*.json")):
        if not path.is_file():
            continue
        json_count += 1
        try:
            read_episode(path)
            episode_count += 1
        except (OSError, UnicodeError, ValueError):
            invalid_count += 1
    return {
        "json_files": json_count,
        "episodes": episode_count,
        "invalid": invalid_count,
    }


def _sources_without_job(kb: KnowledgeBase) -> list[str]:
    rows = kb.conn.execute(
        """SELECT sv.id
             FROM source_versions sv
             JOIN sources s ON s.id=sv.logical_source_id
            WHERE sv.is_current=1
              AND sv.archived_at IS NULL
              AND s.archived_at IS NULL
              AND s.ai_permission='allow'
              AND NOT EXISTS (
                    SELECT 1 FROM extraction_runs r WHERE r.source_id=sv.id
              )
              AND NOT EXISTS (
                    SELECT 1 FROM ai_job_items i WHERE i.source_version_id=sv.id
              )
            ORDER BY sv.imported_at, sv.id"""
    ).fetchall()
    return [str(row["id"]) for row in rows]


def _draft_preflight(kb: KnowledgeBase, incoming: Path, source_ids: list[str]) -> None:
    for source_id in source_ids:
        tasks = plan_openai_extractions(kb, incoming, source_ids=[source_id])
        if len(tasks) != 1:
            raise ValidationError("Kilden kan ikke planlaegges som lokal jobkladde")
        if estimate_task_cost(tasks[0]) > DEFAULT_COST_LIMIT_USD:
            raise ValidationError("En kilde overskrider prisloftet for en lokal jobkladde")


def _integrity(kb: KnowledgeBase) -> str:
    return str(kb.conn.execute("PRAGMA integrity_check").fetchone()[0])


def inspect(delivery_root: Path, state_root: Path) -> dict[str, object]:
    delivery, state = _validate_paths(delivery_root, state_root)
    delivery_status = _validate_delivery(delivery)
    state_db = state / "knowledgebase.sqlite"
    result: dict[str, object] = {
        "schema_version": "investviden-transskribinator-consumer-run-v1",
        "mode": "check",
        "ok": delivery_status["episodes"] > 0 and delivery_status["invalid"] == 0,
        "delivery_json_files": delivery_status["json_files"],
        "delivery_episodes": delivery_status["episodes"],
        "invalid_delivery_json": delivery_status["invalid"],
        "state_database_exists": state_db.is_file(),
        "external_ai_calls": 0,
        "active_database_used": False,
    }
    if state_db.is_file():
        if state_db.resolve() == PROTECTED_DB:
            raise ValidationError("Consumeren maa ikke bruge den beskyttede legacy-database")
        uri = "file:" + state_db.resolve().as_posix() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            result["database_schema"] = current_schema_version(conn)
            result["database_integrity"] = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
            result["sources"] = int(conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0])
            result["draft_jobs"] = int(conn.execute("SELECT COUNT(*) FROM ai_jobs WHERE status='draft'").fetchone()[0])
    return result


def run(delivery_root: Path, state_root: Path) -> dict[str, object]:
    delivery, state = _validate_paths(delivery_root, state_root)
    delivery_status = _validate_delivery(delivery)
    if delivery_status["episodes"] == 0:
        raise ValidationError("Ingen episodeleveringer fundet")
    if delivery_status["invalid"]:
        raise ValidationError("Leveringsmappen indeholder ugyldig episode-JSON")

    state.mkdir(parents=True, exist_ok=True)
    database = (state / "knowledgebase.sqlite").resolve()
    if database == PROTECTED_DB or _inside(database, PROTECTED_DATA_ROOT):
        raise ValidationError("Consumeren maa ikke bruge den beskyttede legacy-database")
    workspace = state / "workspace"
    incoming = state / "incoming"

    with KnowledgeBase(database) as kb:
        kb.initialize()
        plan = plan_input(kb, _root_config(delivery))
        if plan["errors"]:
            raise ValidationError("Consumer-preview indeholder fejl")

        counts = {"new": 0, "existing": 0, "duplicate": 0, "conflict": 0}
        for item in plan["items"]:
            counts[item.status] = counts.get(item.status, 0) + 1
        if counts.get("conflict", 0):
            raise ValidationError("Consumer-preview indeholder episodekonflikt")
        if counts.get("duplicate", 0):
            raise ValidationError("Consumer-preview indeholder dubletlevering")

        selected = [index for index, item in enumerate(plan["items"]) if item.status == "new"]
        imported_ids: list[str] = []
        backup_integrity = None
        if selected:
            applied = apply_input(kb, plan, selected, workspace)
            if applied["errors"]:
                raise ValidationError("Consumer-import fejlede")
            imported_ids = [str(value) for value in applied["imported"]]
            if len(imported_ids) != len(selected):
                raise ValidationError("Ikke alle nye leveringer blev importeret")
            backup_integrity = applied.get("backup", {}).get("integrity")
            if backup_integrity != "ok":
                raise ValidationError("Consumer-backup blev ikke verificeret")

        source_ids = _sources_without_job(kb)
        _draft_preflight(kb, incoming, source_ids)

        draft_jobs_created = 0
        for source_id in source_ids:
            job = create_mistral_job(
                kb,
                incoming,
                source_ids=[source_id],
                cost_limit_usd=DEFAULT_COST_LIMIT_USD,
            )
            if job["status"] != "draft" or len(job["items"]) != 1:
                raise ValidationError("Consumeren oprettede ikke den forventede lokale jobkladde")
            if job["items"][0]["attempt_count"] != 0:
                raise ValidationError("Jobkladden har uventet AI-forsoeg")
            draft_jobs_created += 1

        for item in plan["items"]:
            if file_sha256(item.path) != item.original_sha256:
                raise ValidationError("En episodelevering blev aendret under consumer-koerslen")

        total_sources = int(kb.conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0])
        total_jobs = int(kb.conn.execute("SELECT COUNT(*) FROM ai_jobs").fetchone()[0])
        total_job_items = int(kb.conn.execute("SELECT COUNT(*) FROM ai_job_items").fetchone()[0])
        ai_attempts = int(kb.conn.execute("SELECT COALESCE(SUM(attempt_count), 0) FROM ai_job_items").fetchone()[0])
        claims = int(kb.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0])

        return {
            "schema_version": "investviden-transskribinator-consumer-run-v1",
            "mode": "run",
            "ok": True,
            "database_schema": current_schema_version(kb.conn),
            "database_integrity": _integrity(kb),
            "delivery_episodes": delivery_status["episodes"],
            "new_imported": len(imported_ids),
            "existing": counts.get("existing", 0),
            "draft_jobs_created": draft_jobs_created,
            "total_sources": total_sources,
            "total_ai_jobs": total_jobs,
            "total_ai_job_items": total_job_items,
            "ai_attempts": ai_attempts,
            "claims": claims,
            "backup_integrity": backup_integrity,
            "original_sources_unchanged": True,
            "external_ai_calls": 0,
            "active_database_used": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = inspect(args.delivery_root, args.state_root) if args.check else run(
            args.delivery_root, args.state_root
        )
    except Exception as exc:
        print(json.dumps({
            "schema_version": "investviden-transskribinator-consumer-run-v1",
            "ok": False,
            "error_type": type(exc).__name__,
            "external_ai_calls": 0,
            "active_database_used": False,
        }, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
