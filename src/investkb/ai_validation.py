from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .validation import ValidationError


AI_VALIDATION_OUTCOMES = {"passed", "needs_review", "error"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validation_context(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    row = conn.execute(
        """SELECT c.id AS claim_id,
                  cv.id AS claim_version_id,
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


def record_ai_validation(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    outcome: str,
    validator_provider: str,
    validator_model: str,
    validator_version: str,
    note: str | None = None,
    created_at: str | None = None,
) -> str:
    """Persist one AI quality-control event without changing human review state.

    The stored event is bound to the current claim version and current source
    version/hash. It is intentionally separate from claims.review_status.
    """
    if outcome not in AI_VALIDATION_OUTCOMES:
        raise ValidationError(f"Ukendt AI-kontrolresultat: {outcome}")
    for label, value in (
        ("validator_provider", validator_provider),
        ("validator_model", validator_model),
        ("validator_version", validator_version),
    ):
        if not value or not value.strip():
            raise ValidationError(f"{label} skal være udfyldt")

    context = _validation_context(conn, claim_id)
    if not bool(context["source_is_current"]):
        raise ValidationError("AI-kontrol kræver den aktuelle kildeversion")
    if context["source_version_archived_at"] or context["source_archived_at"]:
        raise ValidationError("AI-kontrol kan ikke registreres på en arkiveret kilde")
    if not bool(context["has_evidence"]):
        raise ValidationError("AI-kontrol kræver registreret evidens for den aktuelle claim-version")

    validation_id = f"ai-validation-{uuid.uuid4().hex[:24]}"
    timestamp = created_at or _now_iso()
    with conn:
        conn.execute(
            """INSERT INTO ai_claim_validations
               (id, claim_id, claim_version_id, source_version_id, source_sha256,
                validator_provider, validator_model, validator_version,
                outcome, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                validation_id,
                claim_id,
                context["claim_version_id"],
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


def current_ai_validation(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any] | None:
    """Return the newest validation that still matches current claim/source state."""
    row = conn.execute(
        """SELECT v.*
           FROM ai_claim_validations v
           JOIN claims c ON c.id=v.claim_id
           JOIN claim_versions cv ON cv.id=v.claim_version_id
           JOIN source_versions sv ON sv.id=v.source_version_id
           JOIN sources s ON s.id=sv.logical_source_id
           WHERE v.claim_id=?
             AND cv.claim_id=c.id
             AND cv.is_current=1
             AND c.source_id=v.source_version_id
             AND sv.sha256=v.source_sha256
             AND sv.is_current=1
             AND sv.archived_at IS NULL
             AND s.archived_at IS NULL
           ORDER BY v.created_at DESC, v.rowid DESC
           LIMIT 1""",
        (claim_id,),
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


def ai_validation_history(conn: sqlite3.Connection, claim_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """SELECT * FROM ai_claim_validations
               WHERE claim_id=? ORDER BY created_at DESC, rowid DESC""",
            (claim_id,),
        )
    ]
