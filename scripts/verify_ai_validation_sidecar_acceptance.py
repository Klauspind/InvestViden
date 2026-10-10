from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_validation import (  # noqa: E402
    AIValidationStore,
    VALIDATION_SCHEMA_VERSION,
    default_validation_db_path,
)


ACCEPTANCE_VALIDATOR_PROVIDER = "investviden-acceptance"
ACCEPTANCE_VALIDATOR_MODEL = "no-external-ai"
ACCEPTANCE_VALIDATOR_VERSION = "iv019-sidecar-acceptance-v1"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_read_only(database: Path) -> sqlite3.Connection:
    uri = database.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _select_acceptance_claim(conn: sqlite3.Connection, claim_id: str | None) -> sqlite3.Row:
    where = "c.id=?" if claim_id else "c.review_status='ai_extracted'"
    params: tuple[str, ...] = (claim_id,) if claim_id else ()
    row = conn.execute(
        f"""SELECT c.id, c.review_status
            FROM claims c
            JOIN claim_versions cv ON cv.claim_id=c.id AND cv.is_current=1
            JOIN source_versions sv ON sv.id=c.source_id
            JOIN sources s ON s.id=sv.logical_source_id
            WHERE {where}
              AND sv.is_current=1
              AND sv.archived_at IS NULL
              AND s.archived_at IS NULL
              AND EXISTS(
                  SELECT 1 FROM evidence_locations el
                  WHERE el.claim_version_id=cv.id
                    AND el.source_version_id=sv.id
                    AND COALESCE(TRIM(el.excerpt), '') <> ''
              )
            ORDER BY c.updated_at DESC, c.id
            LIMIT 1""",
        params,
    ).fetchone()
    if row is None:
        if claim_id:
            raise RuntimeError(
                "Det valgte claim kan ikke bruges til acceptance: det skal være aktuelt og have registreret evidens."
            )
        raise RuntimeError(
            "Ingen aktuel ai_extracted kandidat med registreret evidens blev fundet til acceptance."
        )
    return row


def _validation_schema(store: AIValidationStore) -> int:
    row = store.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0])


def _validation_count(store: AIValidationStore) -> int:
    return int(store.conn.execute("SELECT COUNT(*) FROM claim_validations").fetchone()[0])


def _cleanup_sidecar(path: Path) -> None:
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if candidate.exists():
            candidate.unlink()


def run_acceptance(
    database: Path,
    *,
    sidecar: Path | None = None,
    claim_id: str | None = None,
) -> dict[str, Any]:
    database = database.expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Knowledgebase findes ikke: {database}")

    sidecar_path = (sidecar or default_validation_db_path(database)).expanduser().resolve()
    _require(sidecar_path != database, "AI-kontrolsidecar må ikke være samme fil som knowledgebasen")
    _require(sidecar_path.parent == database.parent, "Acceptance kræver sidecar i samme runtime-mappe som knowledgebasen")

    database_hash_before = _sha256(database)
    production_sidecar_existed = sidecar_path.exists()

    with _open_read_only(database) as kb_conn:
        schema_version = int(
            kb_conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
        )
        _require(schema_version == 4, f"Acceptance kræver schema 4; databasen bruger schema {schema_version}")
        _require(int(kb_conn.execute("PRAGMA query_only").fetchone()[0]) == 1, "Knowledgebase er ikke query_only")

        claim = _select_acceptance_claim(kb_conn, claim_id)
        selected_claim_id = str(claim["id"])
        review_status_before = str(claim["review_status"])

        with AIValidationStore(sidecar_path) as production_store:
            production_sidecar_schema = _validation_schema(production_store)
            production_validation_count = _validation_count(production_store)
        _require(
            production_sidecar_schema == VALIDATION_SCHEMA_VERSION,
            "Produktions-sidecaren har forkert schema-version",
        )

        acceptance_path = sidecar_path.with_name(
            f"ai_validation.acceptance-{uuid.uuid4().hex[:12]}.sqlite"
        )
        _require(not acceptance_path.exists(), "Midlertidig acceptance-sidecar findes allerede")

        try:
            with AIValidationStore(acceptance_path) as acceptance_store:
                validation_id = acceptance_store.record(
                    kb_conn,
                    selected_claim_id,
                    outcome="passed",
                    validator_provider=ACCEPTANCE_VALIDATOR_PROVIDER,
                    validator_model=ACCEPTANCE_VALIDATOR_MODEL,
                    validator_version=ACCEPTANCE_VALIDATOR_VERSION,
                    note=(
                        "Ephemeral IV-019 workstation acceptance. "
                        "This is not a semantic AI validation and is deleted after the test."
                    ),
                )
                first = acceptance_store.current(kb_conn, selected_claim_id)
                _require(first is not None, "Testkontrolresultatet kunne ikke læses umiddelbart efter skrivning")
                _require(first["quality_status"] == "ai_controlled", "Testresultatet fik forkert quality_status")

            with AIValidationStore(acceptance_path) as reopened_store:
                reopened = reopened_store.current(kb_conn, selected_claim_id)
                _require(reopened is not None, "Testkontrolresultatet overlevede ikke genåbning")
                _require(reopened["id"] == validation_id, "Genåbning fandt et andet kontrolresultat")
                _require(reopened["quality_status"] == "ai_controlled", "Genåbnet resultat har forkert quality_status")
                acceptance_reopen_schema = _validation_schema(reopened_store)

            review_status_after = str(
                kb_conn.execute("SELECT review_status FROM claims WHERE id=?", (selected_claim_id,)).fetchone()[0]
            )
            _require(
                review_status_after == review_status_before,
                "Menneskelig reviewstatus ændrede sig under acceptance",
            )
        finally:
            _cleanup_sidecar(acceptance_path)

    database_hash_after = _sha256(database)
    _require(database_hash_after == database_hash_before, "Knowledgebase-filen ændrede hash under acceptance")

    return {
        "ok": True,
        "knowledgebase_schema": schema_version,
        "knowledgebase_read_only": True,
        "knowledgebase_sha256_unchanged": True,
        "knowledgebase_sha256": database_hash_after,
        "selected_claim_id": selected_claim_id,
        "review_status_before": review_status_before,
        "review_status_after": review_status_after,
        "review_status_unchanged": review_status_after == review_status_before,
        "production_sidecar_path": str(sidecar_path),
        "production_sidecar_existed_before": production_sidecar_existed,
        "production_sidecar_exists_after": sidecar_path.is_file(),
        "production_sidecar_schema": production_sidecar_schema,
        "production_validation_count": production_validation_count,
        "ephemeral_validation_id": validation_id,
        "ephemeral_quality_status": "ai_controlled",
        "ephemeral_reopen_schema": acceptance_reopen_schema,
        "ephemeral_sidecar_deleted": not acceptance_path.exists(),
        "external_ai_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "IV-019 workstation-accept af vedvarende AI-kontrolsidecar. "
            "Knowledgebasen åbnes read-only; ingen ekstern AI kaldes."
        )
    )
    parser.add_argument("--database", required=True, type=Path, help="Eksisterende schema-4 consumer knowledgebase")
    parser.add_argument(
        "--sidecar",
        type=Path,
        default=None,
        help="Valgfri ai_validation.sqlite; standard er ved siden af knowledgebasen",
    )
    parser.add_argument(
        "--claim-id",
        default=None,
        help="Valgfrit aktuelt claim med evidens; ellers vælges en ai_extracted kandidat automatisk",
    )
    args = parser.parse_args()

    result = run_acceptance(args.database, sidecar=args.sidecar, claim_id=args.claim_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
