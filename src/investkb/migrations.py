from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


LATEST_SCHEMA_VERSION = 4


def current_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0])


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _claim_payload(conn: sqlite3.Connection, claim: sqlite3.Row) -> dict[str, Any]:
    companies = [
        {"name": row[0], "ticker": row[1], "role": row[2]}
        for row in conn.execute(
            """SELECT co.name, co.ticker, cc.role
               FROM claim_companies cc JOIN companies co ON co.id=cc.company_id
               WHERE cc.claim_id=? ORDER BY co.normalized_name""",
            (claim["id"],),
        )
    ]
    themes = [
        str(row[0])
        for row in conn.execute(
            """SELECT t.name FROM claim_themes ct JOIN themes t ON t.id=ct.theme_id
               WHERE ct.claim_id=? ORDER BY t.normalized_name""",
            (claim["id"],),
        )
    ]
    points: dict[str, list[str]] = {
        "thesis": [],
        "risk": [],
        "catalyst": [],
        "condition": [],
    }
    for row in conn.execute(
        """SELECT point_type, text FROM claim_points
           WHERE claim_id=? ORDER BY point_type, position""",
        (claim["id"],),
    ):
        points[str(row[0])].append(str(row[1]))
    evidence_row = conn.execute(
        "SELECT excerpt, start_ref, end_ref FROM evidence WHERE claim_id=?",
        (claim["id"],),
    ).fetchone()
    evidence = {
        "excerpt": evidence_row[0] if evidence_row else None,
        "start_ref": evidence_row[1] if evidence_row else None,
        "end_ref": evidence_row[2] if evidence_row else None,
    }
    return {
        "claim_type": claim["claim_type"],
        "summary": claim["summary"],
        "speaker": claim["speaker"],
        "sentiment": claim["sentiment"],
        "action": claim["action"],
        "time_horizon": claim["time_horizon"],
        "discussion_depth": claim["discussion_depth"],
        "confidence": claim["confidence"],
        "companies": companies,
        "themes": themes,
        "points": points,
        "evidence": evidence,
    }


def _snapshot_existing_claims(conn: sqlite3.Connection) -> None:
    claims = list(conn.execute("SELECT * FROM claims ORDER BY id"))
    for claim in claims:
        payload = _claim_payload(conn, claim)
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        version_id = f"claim-version-{payload_sha256[:24]}"
        conn.execute(
            """INSERT OR IGNORE INTO claim_versions
               (id, claim_id, version_number, payload_json, payload_sha256,
                created_at, created_by, supersedes_version_id, is_current)
               VALUES (?, ?, 1, ?, ?, ?, 'schema-v3-migration', NULL, 1)""",
            (version_id, claim["id"], payload_json, payload_sha256, claim["created_at"]),
        )
        evidence = payload["evidence"]
        display_ref = "–".join(
            str(value) for value in (evidence["start_ref"], evidence["end_ref"]) if value
        ) or None
        conn.execute(
            """INSERT OR IGNORE INTO evidence_locations
               (claim_version_id, source_version_id, locator_type, excerpt,
                start_value, end_value, page_number, line_start, line_end, display_ref)
               VALUES (?, ?, 'unstructured', ?, NULL, NULL, NULL, NULL, NULL, ?)""",
            (version_id, claim["source_id"], evidence["excerpt"], display_ref),
        )
        event_key = f"schema-v3:{claim['id']}:{claim['review_status']}:{claim['updated_at']}"
        event_id = f"review-{hashlib.sha256(event_key.encode('utf-8')).hexdigest()[:24]}"
        conn.execute(
            """INSERT OR IGNORE INTO review_events
               (id, claim_id, claim_version_id, event_type, previous_status,
                new_status, note, reviewer, created_at)
               VALUES (?, ?, ?, 'migrated_state', NULL, ?, ?, 'owner', ?)""",
            (
                event_id,
                claim["id"],
                version_id,
                claim["review_status"],
                claim["review_note"],
                claim["updated_at"],
            ),
        )


def _migrate_v3(conn: sqlite3.Connection, applied_at: str) -> None:
    if "sha256" not in _table_columns(conn, "sources"):
        raise RuntimeError("Schema v3 forventede den tidligere sources-tabel")

    conn.execute("ALTER TABLE sources RENAME TO source_versions")
    conn.executescript(
        """
        CREATE TABLE sources (
            id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL CHECK (source_type IN
                ('podcast_transcript','newsletter','report','article','note','other')),
            title TEXT NOT NULL,
            publisher TEXT,
            published_at TEXT,
            language TEXT NOT NULL DEFAULT 'da',
            ai_permission TEXT NOT NULL CHECK (ai_permission IN
                ('allow','ask','local_only','blocked')),
            dataset TEXT NOT NULL DEFAULT 'active',
            archived_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        ALTER TABLE source_versions ADD COLUMN logical_source_id TEXT;
        ALTER TABLE source_versions ADD COLUMN version_number INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE source_versions ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE source_versions ADD COLUMN archived_at TEXT;

        CREATE INDEX idx_source_versions_logical ON source_versions(logical_source_id, version_number);
        CREATE UNIQUE INDEX idx_source_versions_current
            ON source_versions(logical_source_id) WHERE is_current=1;

        CREATE TABLE claim_versions (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            supersedes_version_id TEXT REFERENCES claim_versions(id),
            is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)),
            UNIQUE(claim_id, version_number),
            UNIQUE(claim_id, payload_sha256)
        );

        CREATE UNIQUE INDEX idx_claim_versions_current
            ON claim_versions(claim_id) WHERE is_current=1;

        CREATE TABLE review_events (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
            claim_version_id TEXT NOT NULL REFERENCES claim_versions(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            note TEXT,
            reviewer TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX idx_review_events_claim ON review_events(claim_id, created_at);

        CREATE TABLE evidence_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_version_id TEXT NOT NULL REFERENCES claim_versions(id) ON DELETE CASCADE,
            source_version_id TEXT NOT NULL REFERENCES source_versions(id) ON DELETE CASCADE,
            locator_type TEXT NOT NULL CHECK (locator_type IN
                ('timestamp','page','line','unstructured')),
            excerpt TEXT,
            start_value REAL,
            end_value REAL,
            page_number INTEGER,
            line_start INTEGER,
            line_end INTEGER,
            display_ref TEXT,
            UNIQUE(claim_version_id, source_version_id, locator_type, display_ref)
        );

        CREATE TABLE ai_jobs (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            model TEXT,
            status TEXT NOT NULL CHECK (status IN
                ('draft','confirmed','running','completed','partial','failed','cancelled')),
            source_limit INTEGER NOT NULL,
            estimated_cost_usd REAL,
            cost_limit_usd REAL NOT NULL,
            created_at TEXT NOT NULL,
            confirmed_at TEXT,
            completed_at TEXT
        );

        CREATE TABLE ai_job_items (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES ai_jobs(id) ON DELETE CASCADE,
            source_version_id TEXT NOT NULL REFERENCES source_versions(id),
            status TEXT NOT NULL CHECK (status IN
                ('queued','sent','validated','failed','imported','cancelled')),
            attempt_count INTEGER NOT NULL DEFAULT 0,
            response_id TEXT,
            error TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            actual_cost_usd REAL,
            updated_at TEXT NOT NULL,
            UNIQUE(job_id, source_version_id)
        );
        """
    )

    versions = list(conn.execute("SELECT * FROM source_versions ORDER BY id"))
    for version in versions:
        legacy = conn.execute(
            """SELECT 1 FROM extraction_runs
               WHERE source_id=? AND provider='legacy-knowledge-base-migration' LIMIT 1""",
            (version["id"],),
        ).fetchone()
        dataset = "legacy" if legacy else "active"
        permission = (
            "local_only" if legacy
            else "allow" if version["source_type"] == "podcast_transcript"
            else "ask"
        )
        logical_id = f"source-{version['sha256'][:16]}"
        conn.execute(
            """INSERT INTO sources
               (id, source_type, title, publisher, published_at, language,
                ai_permission, dataset, archived_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)""",
            (
                logical_id,
                version["source_type"],
                version["title"],
                version["publisher"],
                version["published_at"],
                version["language"],
                permission,
                dataset,
                version["imported_at"],
                version["imported_at"],
            ),
        )
        conn.execute(
            "UPDATE source_versions SET logical_source_id=? WHERE id=?",
            (logical_id, version["id"]),
        )

    conn.executescript(
        """
        CREATE TRIGGER source_versions_require_logical_source_insert
        BEFORE INSERT ON source_versions
        WHEN NEW.logical_source_id IS NULL
          OR NOT EXISTS (SELECT 1 FROM sources WHERE id=NEW.logical_source_id)
        BEGIN
            SELECT RAISE(ABORT, 'source version requires a logical source');
        END;

        CREATE TRIGGER source_versions_require_logical_source_update
        BEFORE UPDATE OF logical_source_id ON source_versions
        WHEN NEW.logical_source_id IS NULL
          OR NOT EXISTS (SELECT 1 FROM sources WHERE id=NEW.logical_source_id)
        BEGIN
            SELECT RAISE(ABORT, 'source version requires a logical source');
        END;

        CREATE TRIGGER sources_restrict_delete_with_versions
        BEFORE DELETE ON sources
        WHEN EXISTS (SELECT 1 FROM source_versions WHERE logical_source_id=OLD.id)
        BEGIN
            SELECT RAISE(ABORT, 'logical source still has versions');
        END;
        """
    )
    _snapshot_existing_claims(conn)
    conn.execute(
        "INSERT INTO schema_version(version, applied_at) VALUES(3, ?)",
        (applied_at,),
    )


def _migrate_v4(conn: sqlite3.Connection, applied_at: str) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE claims_fts USING fts5(
            claim_id UNINDEXED,
            summary,
            speaker,
            source_title,
            companies,
            themes,
            evidence,
            tokenize='unicode61 remove_diacritics 2'
        );

        INSERT INTO claims_fts(
            claim_id, summary, speaker, source_title, companies, themes, evidence
        )
        SELECT
            c.id,
            c.summary,
            COALESCE(c.speaker, ''),
            sv.title,
            COALESCE((
                SELECT group_concat(co.name, ' ')
                FROM claim_companies cc JOIN companies co ON co.id=cc.company_id
                WHERE cc.claim_id=c.id
            ), ''),
            COALESCE((
                SELECT group_concat(t.name, ' ')
                FROM claim_themes ct JOIN themes t ON t.id=ct.theme_id
                WHERE ct.claim_id=c.id
            ), ''),
            COALESCE((SELECT e.excerpt FROM evidence e WHERE e.claim_id=c.id), '')
        FROM claims c JOIN source_versions sv ON sv.id=c.source_id;
        """
    )
    conn.execute(
        "INSERT INTO schema_version(version, applied_at) VALUES(4, ?)",
        (applied_at,),
    )


def apply_migrations(conn: sqlite3.Connection, applied_at: str) -> None:
    version = current_schema_version(conn)
    if version > LATEST_SCHEMA_VERSION:
        raise RuntimeError(
            f"Databasen bruger schema {version}, men programmet understøtter højst {LATEST_SCHEMA_VERSION}"
        )
    if version < 3:
        with conn:
            _migrate_v3(conn, applied_at)
        version = 3
    if version < 4:
        with conn:
            _migrate_v4(conn, applied_at)
