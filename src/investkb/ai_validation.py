from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validation import ValidationError


AI_VALIDATION_OUTCOMES = {"passed", "needs_review", "error"}
VALIDATION_SCHEMA_VERSION = 1

_VALIDATION_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_validations (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    claim_version_id TEXT NOT NULL,
    claim_payload_sha256 TEXT NOT NULL,
    source_version_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    validator_provider TEXT NOT NULL,
    validator_model TEXT NOT NULL,
    validator_version TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('passed','needs_review','error')),
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claim_validations_claim
    ON claim_validations(claim_id, created_at);
CREATE INDEX IF NOT EXISTS idx_claim_validations_context
    ON claim_validations(
        claim_version_id,
        claim_payload_sha256,
        source_version_id,
        source_sha256
    );
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_validation_db_path(knowledge_db_path: Path | str) -> Path:
    """Return the local sidecar path beside the knowledgebase database."""
    return Path(knowledge_db_path).with_name("ai_validation.sqlite")


def _validation_context(kb_conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    row = kb_conn.execute(
        """SELECT c.id AS claim_id,
                  c.review_status AS review_status,
                  cv.id AS claim_version_id,
                  cv.payload_sha256 AS claim_payload_sha256,
                  c.source_id AS source_version_id,
                  sv.sha256 AS source_sha256,
                  sv.is_current AS source_is_current,
                  sv.archived_at AS source_version_archived_at,
                  s.archived_at AS source_archived_at,
                  EXISTS(
                      SELECT 1 FROM evidence_locations el
                      WHERE el.claim_version_id=cv.id
                        AND el.source_version_id=sv.id
                        AND COALESCE(TRIM(el.excerpt), '') <> ''
                  ) AS has_evidence
           FROM claims c
           JOIN claim_versions cv ON cv.claim_id=c.id AND cv.is_current=1
           JOIN source_versions sv ON sv.id=c.source_id
           JOIN sources s ON s.id=sv.logical_source_id
           WHERE c.id=?""",
        (claim_id,),
    ).fetchone()
    if row is None:
        raise KeyError(claim_id)
    return row


class AIValidationStore:
    """Local persistence for progressive AI quality-control results.

    This store is deliberately separate from the authoritative knowledgebase
    schema. It records a quality-control layer tied to immutable identifiers
    from the knowledgebase, but it never updates claims.review_status.
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.conn.executescript(_VALIDATION_SCHEMA_SQL)
        row = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
        installed = int(row[0])
        if installed > VALIDATION_SCHEMA_VERSION:
            raise RuntimeError(
                f"AI-kontrolbasen bruger schema {installed}, men programmet understøtter højst "
                f"{VALIDATION_SCHEMA_VERSION}"
            )
        if installed == 0:
            self.conn.execute(
                "INSERT INTO schema_version(version, applied_at) VALUES(?, ?)",
                (VALIDATION_SCHEMA_VERSION, _now_iso()),
            )
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "AIValidationStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def record(
        self,
        kb_conn: sqlite3.Connection,
        claim_id: str,
        *,
        outcome: str,
        validator_provider: str,
        validator_model: str,
        validator_version: str,
        note: str | None = None,
        created_at: str | None = None,
    ) -> str:
        """Persist one AI-control event without writing to the knowledgebase."""
        if outcome not in AI_VALIDATION_OUTCOMES:
            raise ValidationError(f"Ukendt AI-kontrolresultat: {outcome}")
        for label, value in (
            ("validator_provider", validator_provider),
            ("validator_model", validator_model),
            ("validator_version", validator_version),
        ):
            if not value or not value.strip():
                raise ValidationError(f"{label} skal være udfyldt")

        context = _validation_context(kb_conn, claim_id)
        if not bool(context["source_is_current"]):
            raise ValidationError("AI-kontrol kræver den aktuelle kildeversion")
        if context["source_version_archived_at"] or context["source_archived_at"]:
            raise ValidationError("AI-kontrol kan ikke registreres på en arkiveret kilde")
        if not bool(context["has_evidence"]):
            raise ValidationError("AI-kontrol kræver registreret evidens for den aktuelle claim-version")

        validation_id = f"ai-validation-{uuid.uuid4().hex[:24]}"
        timestamp = created_at or _now_iso()
        with self.conn:
            self.conn.execute(
                """INSERT INTO claim_validations
                   (id, claim_id, claim_version_id, claim_payload_sha256,
                    source_version_id, source_sha256,
                    validator_provider, validator_model, validator_version,
                    outcome, note, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    validation_id,
                    claim_id,
                    context["claim_version_id"],
                    context["claim_payload_sha256"],
                    context["source_version_id"],
                    context["source_sha256"],
                    validator_provider.strip(),
                    validator_model.strip(),
                    validator_version.strip(),
                    outcome,
                    note,
                    timestamp,
                ),
            )
        return validation_id

    def current(self, kb_conn: sqlite3.Connection, claim_id: str) -> dict[str, Any] | None:
        """Return newest validation only while claim/source context still matches."""
        try:
            context = _validation_context(kb_conn, claim_id)
        except KeyError:
            return None
        if (
            not bool(context["source_is_current"])
            or context["source_version_archived_at"]
            or context["source_archived_at"]
            or not bool(context["has_evidence"])
        ):
            return None

        row = self.conn.execute(
            """SELECT * FROM claim_validations
               WHERE claim_id=?
                 AND claim_version_id=?
                 AND claim_payload_sha256=?
                 AND source_version_id=?
                 AND source_sha256=?
               ORDER BY created_at DESC, rowid DESC
               LIMIT 1""",
            (
                claim_id,
                context["claim_version_id"],
                context["claim_payload_sha256"],
                context["source_version_id"],
                context["source_sha256"],
            ),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["quality_status"] = {
            "passed": "ai_controlled",
            "needs_review": "requires_control",
            "error": "validation_error",
        }[str(result["outcome"])]
        return result

    def history(self, claim_id: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                """SELECT * FROM claim_validations
                   WHERE claim_id=? ORDER BY created_at DESC, rowid DESC""",
                (claim_id,),
            )
        ]
