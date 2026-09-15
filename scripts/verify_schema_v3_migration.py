from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase  # noqa: E402


TRACKED_TABLES = (
    "extraction_runs",
    "claims",
    "companies",
    "claim_companies",
    "themes",
    "claim_themes",
    "claim_points",
    "evidence",
    "source_provenance",
)


def _counts(conn: sqlite3.Connection, tables: tuple[str, ...]) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in tables
    }


def _status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT review_status, COUNT(*) FROM claims GROUP BY review_status ORDER BY review_status"
        )
    }


def verify(source: Path, output: Path) -> dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("Outputkopien må ikke være den aktive database")
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        raise FileExistsError(f"Output findes allerede og overskrives ikke: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    source_uri = f"file:{source.as_posix()}?mode=ro"
    original = sqlite3.connect(source_uri, uri=True)
    original.row_factory = sqlite3.Row
    try:
        version = int(original.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        if version != 2:
            raise RuntimeError(f"Verifieren forventer schema 2, men fandt schema {version}")
        before = _counts(original, ("sources",) + TRACKED_TABLES)
        before_status = _status_counts(original)
        before_hashes = {
            str(row[0]) for row in original.execute("SELECT sha256 FROM sources ORDER BY sha256")
        }
        copied = sqlite3.connect(output)
        try:
            original.backup(copied)
        finally:
            copied.close()
    finally:
        original.close()

    with KnowledgeBase(output) as migrated:
        migrated.initialize(allow_migration=True)
        after = _counts(migrated.conn, ("sources", "source_versions") + TRACKED_TABLES)
        after_status = _status_counts(migrated.conn)
        after_hashes = {
            str(row[0])
            for row in migrated.conn.execute("SELECT sha256 FROM source_versions ORDER BY sha256")
        }
        integrity = str(migrated.conn.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_errors = [tuple(row) for row in migrated.conn.execute("PRAGMA foreign_key_check")]
        schema_version = int(
            migrated.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        )
        versioned_claims = int(
            migrated.conn.execute("SELECT COUNT(*) FROM claim_versions").fetchone()[0]
        )
        review_events = int(
            migrated.conn.execute("SELECT COUNT(*) FROM review_events").fetchone()[0]
        )
        legacy_sources = int(
            migrated.conn.execute("SELECT COUNT(*) FROM sources WHERE dataset='legacy'").fetchone()[0]
        )
        indexed_claims = int(
            migrated.conn.execute("SELECT COUNT(*) FROM claims_fts").fetchone()[0]
        )

    comparisons = {
        "source_versions_preserved": before["sources"] == after["source_versions"],
        "logical_sources_created": before["sources"] == after["sources"],
        "source_hashes_preserved": before_hashes == after_hashes,
        "tracked_rows_preserved": all(before[name] == after[name] for name in TRACKED_TABLES),
        "review_statuses_preserved": before_status == after_status,
        "one_initial_version_per_claim": versioned_claims == before["claims"],
        "one_initial_review_event_per_claim": review_events == before["claims"],
        "all_claims_searchable": indexed_claims == before["claims"],
        "integrity_ok": integrity == "ok",
        "foreign_keys_ok": not foreign_key_errors,
        "schema_version_4": schema_version == 4,
    }
    if not all(comparisons.values()):
        failed = [name for name, passed in comparisons.items() if not passed]
        raise RuntimeError(f"Migrationskontrol fejlede: {', '.join(failed)}")

    return {
        "source": str(source),
        "migrated_copy": str(output),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "before": before,
        "after": after,
        "review_statuses": after_status,
        "claim_versions": versioned_claims,
        "review_events": review_events,
        "legacy_sources": legacy_sources,
        "indexed_claims": indexed_claims,
        "integrity": integrity,
        "foreign_key_errors": foreign_key_errors,
        "comparisons": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrér en konsistent kopi til seneste schema og bevis, at indholdet er bevaret"
    )
    parser.add_argument("source", type=Path, help="Aktiv schema-v2-database; åbnes skrivebeskyttet")
    parser.add_argument("output", type=Path, help="Ny migrationskopi; må ikke eksistere")
    args = parser.parse_args()
    report = verify(args.source, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
