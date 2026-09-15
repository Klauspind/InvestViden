from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .migrations import LATEST_SCHEMA_VERSION, apply_migrations, current_schema_version
from .schema import SCHEMA_SQL
from .review_evidence import assess_evidence
from .content_quality import is_promotional_noise
from .validation import REVIEW_STATUSES, ValidationError, validate_extraction


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "item"


def _digest_text(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KnowledgeBase:
    def __init__(self, db_path: Path | str = "data/knowledgebase.sqlite") -> None:
        self.db_path = Path(db_path)
        self._database_was_new = not self.db_path.exists()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KnowledgeBase":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def initialize(self, allow_migration: bool = False) -> None:
        installed = self.conn.execute("SELECT 1 FROM sqlite_master WHERE name='schema_version'").fetchone()
        if installed and current_schema_version(self.conn) < LATEST_SCHEMA_VERSION and not (allow_migration or self._database_was_new):
            raise RuntimeError("Den eksisterende database kræver en udtrykkeligt godkendt migration på en kopi. Intet er ændret.")
        self.conn.executescript(SCHEMA_SQL)
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES(1, ?)",
            (now_iso(),),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES(2, ?)",
            (now_iso(),),
        )
        self.conn.commit()
        version = current_schema_version(self.conn)
        if version < LATEST_SCHEMA_VERSION and not (allow_migration or self._database_was_new):
            raise RuntimeError(
                f"Databasen bruger schema {version}. Den aktive database migreres ikke automatisk; "
                "brug først den kontrollerede migrationsverifier på en kopi."
            )
        apply_migrations(self.conn, now_iso())

    def import_source(
        self,
        path: Path,
        source_type: str,
        title: str | None = None,
        publisher: str | None = None,
        published_at: str | None = None,
        language: str = "da",
        source_store: Path | str = "data/sources",
        *,
        ai_permission: str | None = None,
    ) -> tuple[str, bool]:
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return self.import_source_bytes(
            path.read_bytes(), path, source_type, title, publisher, published_at,
            language, source_store, ai_permission=ai_permission,
        )

    def import_source_bytes(
        self, content: bytes, original_path: Path, source_type: str,
        title: str | None = None, publisher: str | None = None,
        published_at: str | None = None, language: str = "da",
        source_store: Path | str = "data/sources", *, ai_permission: str | None = None,
    ) -> tuple[str, bool]:
        """Import the exact approved snapshot, preserving its original location."""
        self.initialize()
        permission = ai_permission if ai_permission is not None else (
            "allow" if source_type == "podcast_transcript" else "ask"
        )
        if permission not in {"allow", "ask", "local_only", "blocked"}:
            raise ValidationError("Ukendt AI-tilladelse")
        if source_type not in {"podcast_transcript", "newsletter", "report", "article", "note", "other"}:
            raise ValidationError("Ukendt kildetype")
        path = original_path.resolve()
        content_hash = hashlib.sha256(content).hexdigest()
        existing = self.conn.execute("SELECT id FROM source_versions WHERE sha256 = ?", (content_hash,)).fetchone()
        if existing:
            return str(existing["id"]), False

        source_id = f"src-{content_hash[:16]}"
        logical_source_id = f"source-{content_hash[:16]}"
        store = Path(source_store)
        store.mkdir(parents=True, exist_ok=True)
        stored = store / f"{content_hash[:12]}_{path.name}"
        if stored.exists():
            if file_sha256(stored) != content_hash:
                raise ValidationError(f"Kildekopien findes med andet indhold: {stored}")
        else:
            with stored.open("xb") as handle:
                handle.write(content)
        timestamp = now_iso()
        self.conn.execute(
            """INSERT INTO sources
               (id, source_type, title, publisher, published_at, language,
                ai_permission, dataset, archived_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', NULL, ?, ?)""",
            (
                logical_source_id, source_type, title or path.stem, publisher,
                published_at, language, permission, timestamp, timestamp,
            ),
        )
        self.conn.execute(
            """INSERT INTO source_versions
               (id, source_type, title, publisher, published_at, language,
                original_path, stored_path, sha256, imported_at,
                logical_source_id, version_number, is_current, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, NULL)""",
            (
                source_id, source_type, title or path.stem, publisher, published_at, language,
                str(path), str(stored.resolve()), content_hash, timestamp, logical_source_id,
            ),
        )
        self.conn.commit()
        return source_id, True

    def set_source_permission(self, source_id: str, permission: str) -> None:
        if permission not in {"allow", "ask", "local_only", "blocked"}:
            raise ValidationError("Ukendt AI-tilladelse")
        with self.conn:
            cursor = self.conn.execute(
                """UPDATE sources SET ai_permission=?, updated_at=?
                   WHERE id=(SELECT logical_source_id FROM source_versions WHERE id=?)""",
                (permission, now_iso(), source_id),
            )
            if not cursor.rowcount:
                raise KeyError(source_id)

    def external_ai_allowed(self, source_id: str, sha256: str, approvals: dict[str, str] | None = None) -> bool:
        row = self.conn.execute(
            """SELECT s.ai_permission, sv.sha256 FROM source_versions sv
               JOIN sources s ON s.id=sv.logical_source_id WHERE sv.id=?
               AND sv.is_current=1 AND sv.archived_at IS NULL AND s.archived_at IS NULL""",
            (source_id,),
        ).fetchone()
        return bool(row and row["sha256"] == sha256 and (
            row["ai_permission"] == "allow" or (
                row["ai_permission"] == "ask" and (approvals or {}).get(source_id) == sha256
            )
        ))

    def require_external_ai(self, source_id: str, sha256: str, approvals: dict[str, str] | None = None) -> None:
        if not self.external_ai_allowed(source_id, sha256, approvals):
            raise ValidationError(f"Kildepolitikken tillader ikke ekstern AI for {source_id}")

    def source_policies(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(
            """SELECT sv.id, sv.title, sv.sha256, s.ai_permission, s.dataset,
                      sv.published_at FROM source_versions sv
               JOIN sources s ON s.id=sv.logical_source_id WHERE sv.is_current=1
               ORDER BY sv.imported_at DESC, sv.id"""
        )]

    def create_ai_job(
        self, provider: str, model: str, source_ids: list[str],
        estimated_cost_usd: float, cost_limit_usd: float,
    ) -> str:
        if provider != "mistral":
            raise ValidationError("Kun Mistral-job understøttes i denne jobkø")
        if not 1 <= len(source_ids) <= 5 or len(source_ids) != len(set(source_ids)):
            raise ValidationError("Et AI-job skal indeholde 1-5 unikke kilder")
        if cost_limit_usd <= 0 or cost_limit_usd > 0.10:
            raise ValidationError("Prisloftet skal være over USD 0 og højst USD 0,10")
        if estimated_cost_usd < 0 or estimated_cost_usd > cost_limit_usd:
            raise ValidationError("Det estimerede beløb overstiger prisloftet")
        placeholders = ",".join("?" for _ in source_ids)
        rows = list(self.conn.execute(
            f"""SELECT id FROM source_versions WHERE id IN ({placeholders})
                 AND is_current=1 AND archived_at IS NULL""", source_ids
        ))
        if {str(row["id"]) for row in rows} != set(source_ids):
            raise ValidationError("Jobbet indeholder en ukendt eller arkiveret kildeversion")
        job_id = f"ai-job-{uuid.uuid4().hex[:20]}"
        timestamp = now_iso()
        with self.conn:
            self.conn.execute(
                """INSERT INTO ai_jobs
                   (id, provider, model, status, source_limit, estimated_cost_usd,
                    cost_limit_usd, created_at)
                   VALUES (?, ?, ?, 'draft', ?, ?, ?, ?)""",
                (job_id, provider, model, len(source_ids), estimated_cost_usd,
                 cost_limit_usd, timestamp),
            )
            for source_id in source_ids:
                self.conn.execute(
                    """INSERT INTO ai_job_items
                       (id, job_id, source_version_id, status, attempt_count, updated_at)
                       VALUES (?, ?, ?, 'queued', 0, ?)""",
                    (f"ai-item-{uuid.uuid4().hex[:20]}", job_id, source_id, timestamp),
                )
        return job_id

    def ai_job(self, job_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM ai_jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        result = dict(row)
        result["items"] = [dict(item) for item in self.conn.execute(
            """SELECT i.*, sv.title, sv.sha256, s.ai_permission
               FROM ai_job_items i
               JOIN source_versions sv ON sv.id=i.source_version_id
               JOIN sources s ON s.id=sv.logical_source_id
               WHERE i.job_id=? ORDER BY i.rowid""", (job_id,)
        )]
        result["actual_cost_usd"] = sum(float(item["actual_cost_usd"] or 0) for item in result["items"])
        return result

    def ai_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValidationError("Joblisten skal vise mellem 1 og 100 job")
        ids = [str(row["id"]) for row in self.conn.execute(
            "SELECT id FROM ai_jobs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
        )]
        return [self.ai_job(job_id) for job_id in ids]

    def confirm_ai_job(self, job_id: str) -> None:
        with self.conn:
            cursor = self.conn.execute(
                """UPDATE ai_jobs SET status='confirmed', confirmed_at=?
                   WHERE id=? AND status='draft' AND estimated_cost_usd <= cost_limit_usd""",
                (now_iso(), job_id),
            )
            if not cursor.rowcount:
                raise ValidationError("Kun en gyldig jobkladde kan bekræftes")

    def start_ai_job(self, job_id: str, retry_source_ids: list[str] | None = None) -> list[dict[str, Any]]:
        job = self.ai_job(job_id)
        retry_source_ids = retry_source_ids or []
        if job["status"] == "confirmed":
            if retry_source_ids:
                raise ValidationError("Første kørsel bruger alle kilder i det bekræftede job")
            selected = [item for item in job["items"] if item["status"] == "queued"]
        elif job["status"] in {"partial", "failed"}:
            if not retry_source_ids or len(retry_source_ids) != len(set(retry_source_ids)):
                raise ValidationError("Vælg mindst én unik fejlet kilde til genkørsel")
            failed = {str(item["source_version_id"]): item for item in job["items"] if item["status"] == "failed"}
            if not set(retry_source_ids).issubset(failed):
                raise ValidationError("Kun fejlede kilder fra jobbet kan genkøres")
            selected = [failed[source_id] for source_id in retry_source_ids]
        else:
            raise ValidationError("Jobbet er ikke bekræftet eller klar til genkørsel")
        if not selected:
            raise ValidationError("Jobbet har ingen kilder klar til kørsel")
        timestamp = now_iso()
        with self.conn:
            self.conn.execute("UPDATE ai_jobs SET status='running', completed_at=NULL WHERE id=?", (job_id,))
            for item in selected:
                self.conn.execute(
                    """UPDATE ai_job_items SET status='sent', attempt_count=attempt_count+1,
                       error=NULL, updated_at=? WHERE id=?""",
                    (timestamp, item["id"]),
                )
        return [dict(item) for item in selected]

    def finish_ai_job_item(
        self, item_id: str, *, success: bool, response_id: str | None = None,
        error: str | None = None, prompt_tokens: int | None = None,
        completion_tokens: int | None = None, actual_cost_usd: float | None = None,
    ) -> None:
        with self.conn:
            cursor = self.conn.execute(
                """UPDATE ai_job_items SET status=?, response_id=?, error=?, prompt_tokens=?,
                   completion_tokens=?, actual_cost_usd=?, updated_at=? WHERE id=?""",
                ("validated" if success else "failed", response_id, error,
                 prompt_tokens, completion_tokens, actual_cost_usd, now_iso(), item_id),
            )
            if not cursor.rowcount:
                raise KeyError(item_id)

    def finish_ai_job(self, job_id: str) -> str:
        job = self.ai_job(job_id)
        statuses = [item["status"] for item in job["items"]]
        if any(status == "sent" for status in statuses):
            raise ValidationError("Alle kilder skal afsluttes, før jobbet kan lukkes")
        final = "completed" if all(status == "validated" for status in statuses) else (
            "partial" if any(status == "validated" for status in statuses) else "failed"
        )
        with self.conn:
            self.conn.execute(
                "UPDATE ai_jobs SET status=?, completed_at=? WHERE id=?",
                (final, now_iso(), job_id),
            )
        return final

    def source_by_hash(self, content_hash: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM source_versions WHERE sha256 = ?", (content_hash,)).fetchone()

    def source_by_episode_key(self, episode_key: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """SELECT s.* FROM source_provenance p
               JOIN source_versions s ON s.id=p.source_id WHERE p.episode_key=?""",
            (episode_key,),
        ).fetchone()

    def podcast_sources_on_date(self, published_at: str) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            """SELECT * FROM source_versions
               WHERE source_type='podcast_transcript' AND published_at=?
               ORDER BY id""",
            (published_at,),
        ))

    def record_source_provenance(self, source_id: str, metadata: dict[str, Any]) -> None:
        if metadata.get("kind") != "investviden_podcast_source":
            raise ValueError("Ukendt provenance-kind")
        upstream = metadata.get("upstream")
        render = metadata.get("render")
        episode = metadata.get("episode")
        if not all(isinstance(value, dict) for value in (upstream, render, episode)):
            raise ValueError("Ufuldstændig podcast-provenance")
        required = {
            "episode_key": metadata.get("episode_key"),
            "upstream_path": upstream.get("path"),
            "upstream_sha256": upstream.get("sha256"),
            "renderer_version": render.get("renderer_version"),
        }
        missing = [name for name, value in required.items() if not isinstance(value, str) or not value]
        if missing:
            raise ValueError(f"Podcast-provenance mangler: {', '.join(missing)}")
        source_metadata = {
            "title": episode.get("title"),
            "publisher": episode.get("publisher"),
            "published_at": episode.get("published_at"),
            "language": episode.get("language"),
        }
        invalid_metadata = [
            name for name, value in source_metadata.items()
            if not isinstance(value, str) or not value.strip()
        ]
        if invalid_metadata:
            raise ValueError(f"Podcast-provenance mangler kildemetadata: {', '.join(invalid_metadata)}")
        existing = self.conn.execute(
            "SELECT * FROM source_provenance WHERE source_id=?", (source_id,)
        ).fetchone()
        if existing:
            identity = (
                existing["episode_key"],
                existing["upstream_sha256"],
                existing["renderer_version"],
            )
            incoming = (
                required["episode_key"],
                required["upstream_sha256"],
                required["renderer_version"],
            )
            if identity != incoming:
                raise ValueError(f"Kilden {source_id} har allerede en anden, uforanderlig provenance")
        with self.conn:
            if not existing:
                self.conn.execute(
                    """INSERT INTO source_provenance
                       (source_id, episode_key, upstream_path, upstream_sha256,
                        upstream_episode_id, upstream_schema_version, renderer_version,
                        metadata_json, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        source_id,
                        required["episode_key"],
                        required["upstream_path"],
                        required["upstream_sha256"],
                        episode.get("id"),
                        upstream.get("schema_version"),
                        required["renderer_version"],
                        json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                        now_iso(),
                    ),
                )
            self.conn.execute(
                """UPDATE source_versions SET title=?, publisher=?, published_at=?, language=?
                   WHERE id=?""",
                (
                    source_metadata["title"].strip(),
                    source_metadata["publisher"].strip(),
                    source_metadata["published_at"].strip(),
                    source_metadata["language"].strip(),
                    source_id,
                ),
            )
            self.conn.execute(
                """UPDATE sources SET title=?, publisher=?, published_at=?, language=?, updated_at=?
                   WHERE id=(SELECT logical_source_id FROM source_versions WHERE id=?)""",
                (
                    source_metadata["title"].strip(),
                    source_metadata["publisher"].strip(),
                    source_metadata["published_at"].strip(),
                    source_metadata["language"].strip(),
                    now_iso(),
                    source_id,
                ),
            )

    def _upsert_company(self, company: dict[str, Any]) -> str:
        normalized = slug(company["name"])
        existing = self.conn.execute(
            "SELECT id, ticker FROM companies WHERE normalized_name = ?", (normalized,)
        ).fetchone()
        if existing:
            if not existing["ticker"] and company.get("ticker"):
                self.conn.execute("UPDATE companies SET ticker = ? WHERE id = ?", (company["ticker"], existing["id"]))
            return str(existing["id"])
        company_id = f"company-{normalized}-{_digest_text(company['name'], 6)}"
        self.conn.execute(
            "INSERT INTO companies(id, name, ticker, normalized_name) VALUES(?, ?, ?, ?)",
            (company_id, company["name"].strip(), company.get("ticker"), normalized),
        )
        return company_id

    def _upsert_theme(self, name: str) -> str:
        normalized = slug(name)
        existing = self.conn.execute("SELECT id FROM themes WHERE normalized_name = ?", (normalized,)).fetchone()
        if existing:
            return str(existing["id"])
        theme_id = f"theme-{normalized}-{_digest_text(name, 6)}"
        self.conn.execute(
            "INSERT INTO themes(id, name, normalized_name) VALUES(?, ?, ?)",
            (theme_id, name.strip(), normalized),
        )
        return theme_id

    def ingest(self, data: dict[str, Any]) -> tuple[str, int]:
        self.initialize()
        validate_extraction(data)
        source = self.conn.execute(
            "SELECT id FROM source_versions WHERE id = ?", (data["source_id"],)
        ).fetchone()
        if not source:
            raise ValidationError(f"Ukendt source_id: {data['source_id']}")

        run_id = f"run-{uuid.uuid4().hex[:16]}"
        imported_at = now_iso()
        with self.conn:
            self.conn.execute(
                """INSERT INTO extraction_runs
                   (id, source_id, provider, model, schema_version, extracted_at, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, data["source_id"], data["provider"], data.get("model"),
                 data["schema_version"], data["extracted_at"], imported_at),
            )
            accepted_claims = [
                claim for claim in data["claims"]
                if not is_promotional_noise(claim["summary"])
            ]
            for claim in accepted_claims:
                fingerprint_basis = json.dumps(
                    [claim["claim_type"], claim["summary"].strip(), claim.get("speaker")],
                    ensure_ascii=False, sort_keys=True,
                )
                fingerprint = _digest_text(fingerprint_basis, 32)
                claim_id = claim.get("claim_id") or f"claim-{_digest_text(data['source_id'] + fingerprint, 20)}"
                timestamp = now_iso()
                existing = self.conn.execute(
                    "SELECT id, review_status FROM claims WHERE source_id = ? AND fingerprint = ?",
                    (data["source_id"], fingerprint),
                ).fetchone()
                if existing:
                    claim_id = str(existing["id"])
                    review_status = existing["review_status"] if existing["review_status"] in {"approved", "corrected"} else claim["review_status"]
                    self.conn.execute(
                        """UPDATE claims SET run_id=?, claim_type=?, summary=?, speaker=?, sentiment=?,
                           action=?, time_horizon=?, discussion_depth=?, confidence=?, review_status=?, updated_at=?
                           WHERE id=?""",
                        (run_id, claim["claim_type"], claim["summary"].strip(), claim.get("speaker"),
                         claim["sentiment"], claim["action"], claim["time_horizon"], claim["discussion_depth"],
                         claim["confidence"], review_status, timestamp, claim_id),
                    )
                    for table in ("claim_companies", "claim_themes", "claim_points", "evidence"):
                        self.conn.execute(f"DELETE FROM {table} WHERE claim_id = ?", (claim_id,))
                else:
                    self.conn.execute(
                        """INSERT INTO claims
                           (id, source_id, run_id, fingerprint, claim_type, summary, speaker, sentiment,
                            action, time_horizon, discussion_depth, confidence, review_status, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (claim_id, data["source_id"], run_id, fingerprint, claim["claim_type"],
                         claim["summary"].strip(), claim.get("speaker"), claim["sentiment"], claim["action"],
                         claim["time_horizon"], claim["discussion_depth"], claim["confidence"],
                         claim["review_status"], timestamp, timestamp),
                    )

                for company in claim.get("companies", []):
                    company_id = self._upsert_company(company)
                    self.conn.execute(
                        "INSERT INTO claim_companies(claim_id, company_id, role) VALUES(?, ?, ?)",
                        (claim_id, company_id, company["role"]),
                    )
                for theme in claim.get("themes", []):
                    theme_id = self._upsert_theme(theme)
                    self.conn.execute("INSERT INTO claim_themes(claim_id, theme_id) VALUES(?, ?)", (claim_id, theme_id))
                for point_type, key in (("thesis", "thesis"), ("risk", "risks"), ("catalyst", "catalysts"), ("condition", "conditions")):
                    for position, point in enumerate(claim.get(key, [])):
                        self.conn.execute(
                            "INSERT INTO claim_points(claim_id, point_type, position, text) VALUES(?, ?, ?, ?)",
                            (claim_id, point_type, position, point.strip()),
                        )
                evidence = claim["evidence"]
                self.conn.execute(
                    "INSERT INTO evidence(claim_id, excerpt, start_ref, end_ref) VALUES(?, ?, ?, ?)",
                    (claim_id, evidence.get("excerpt"), evidence.get("start_ref"), evidence.get("end_ref")),
                )
                self._record_claim_version(claim_id, str(data["provider"]), timestamp)
                self._refresh_claim_search(claim_id)
        return run_id, len(accepted_claims)

    def _refresh_claim_search(self, claim_id: str) -> None:
        self.conn.execute("DELETE FROM claims_fts WHERE claim_id=?", (claim_id,))
        self.conn.execute(
            """INSERT INTO claims_fts(
                   claim_id, summary, speaker, source_title, companies, themes, evidence
               )
               SELECT c.id, c.summary, COALESCE(c.speaker, ''), sv.title,
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
               FROM claims c JOIN source_versions sv ON sv.id=c.source_id
               WHERE c.id=?""",
            (claim_id,),
        )

    def _claim_version_payload(self, claim_id: str) -> dict[str, Any]:
        claim = self.conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
        if not claim:
            raise KeyError(claim_id)
        companies = [
            dict(row)
            for row in self.conn.execute(
                """SELECT co.name, co.ticker, cc.role FROM claim_companies cc
                   JOIN companies co ON co.id=cc.company_id
                   WHERE cc.claim_id=? ORDER BY co.normalized_name""",
                (claim_id,),
            )
        ]
        themes = [
            str(row["name"])
            for row in self.conn.execute(
                """SELECT t.name FROM claim_themes ct JOIN themes t ON t.id=ct.theme_id
                   WHERE ct.claim_id=? ORDER BY t.normalized_name""",
                (claim_id,),
            )
        ]
        points: dict[str, list[str]] = {
            "thesis": [],
            "risk": [],
            "catalyst": [],
            "condition": [],
        }
        for row in self.conn.execute(
            """SELECT point_type, text FROM claim_points
               WHERE claim_id=? ORDER BY point_type, position""",
            (claim_id,),
        ):
            points[str(row["point_type"])].append(str(row["text"]))
        evidence_row = self.conn.execute(
            "SELECT excerpt, start_ref, end_ref FROM evidence WHERE claim_id=?", (claim_id,)
        ).fetchone()
        evidence = dict(evidence_row) if evidence_row else {
            "excerpt": None,
            "start_ref": None,
            "end_ref": None,
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

    def _record_claim_version(self, claim_id: str, created_by: str, created_at: str) -> str:
        payload = self._claim_version_payload(claim_id)
        payload_json = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        duplicate = self.conn.execute(
            "SELECT id FROM claim_versions WHERE claim_id=? AND payload_sha256=?",
            (claim_id, payload_sha256),
        ).fetchone()
        if duplicate:
            current = self.conn.execute(
                "SELECT is_current FROM claim_versions WHERE id=?", (duplicate["id"],)
            ).fetchone()
            if not current["is_current"]:
                raise ValidationError("Rettelsen matcher en tidligere version. Præcisér rettelsen før godkendelse.")
            return str(duplicate["id"])
        previous = self.conn.execute(
            """SELECT id, version_number FROM claim_versions
               WHERE claim_id=? AND is_current=1""",
            (claim_id,),
        ).fetchone()
        version_number = int(previous["version_number"]) + 1 if previous else 1
        if previous:
            self.conn.execute(
                "UPDATE claim_versions SET is_current=0 WHERE id=?", (previous["id"],)
            )
        version_id = f"claim-version-{uuid.uuid4().hex[:24]}"
        self.conn.execute(
            """INSERT INTO claim_versions
               (id, claim_id, version_number, payload_json, payload_sha256,
                created_at, created_by, supersedes_version_id, is_current)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                version_id,
                claim_id,
                version_number,
                payload_json,
                payload_sha256,
                created_at,
                created_by,
                previous["id"] if previous else None,
            ),
        )
        claim = self.conn.execute(
            "SELECT source_id FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        evidence = payload["evidence"]
        display_ref = "–".join(
            str(value)
            for value in (evidence.get("start_ref"), evidence.get("end_ref"))
            if value
        ) or None
        self.conn.execute(
            """INSERT INTO evidence_locations
               (claim_version_id, source_version_id, locator_type, excerpt,
                start_value, end_value, page_number, line_start, line_end, display_ref)
               VALUES (?, ?, 'unstructured', ?, NULL, NULL, NULL, NULL, NULL, ?)""",
            (version_id, claim["source_id"], evidence.get("excerpt"), display_ref),
        )
        return version_id

    def _append_review_event(
        self,
        claim_id: str,
        previous_status: str | None,
        new_status: str,
        note: str | None,
        created_at: str,
        event_type: str = "status_changed",
    ) -> None:
        version = self.conn.execute(
            "SELECT id FROM claim_versions WHERE claim_id=? AND is_current=1",
            (claim_id,),
        ).fetchone()
        if not version:
            version_id = self._record_claim_version(claim_id, "system", created_at)
        else:
            version_id = str(version["id"])
        self.conn.execute(
            """INSERT INTO review_events
               (id, claim_id, claim_version_id, event_type, previous_status,
                new_status, note, reviewer, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'owner', ?)""",
            (
                f"review-{uuid.uuid4().hex[:24]}",
                claim_id,
                version_id,
                event_type,
                previous_status,
                new_status,
                note,
                created_at,
            ),
        )

    def review_rows(self, status: str | None = None) -> list[sqlite3.Row]:
        sql = """SELECT c.id, c.summary, c.confidence, c.review_status, c.sentiment,
                        c.action, s.title AS source_title
                 FROM claims c JOIN source_versions s ON s.id=c.source_id"""
        params: tuple[Any, ...] = ()
        if status:
            sql += " WHERE c.review_status = ?"
            params = (status,)
        else:
            sql += " WHERE c.review_status IN ('ai_extracted','uncertain')"
        sql += " ORDER BY c.confidence ASC, c.updated_at DESC"
        return list(self.conn.execute(sql, params))

    def set_review(self, claim_id: str, status: str, note: str | None = None) -> None:
        if status not in REVIEW_STATUSES:
            raise ValidationError(f"Ugyldig review status: {status}")
        if status in {"approved", "corrected"}:
            self._require_approval_evidence(claim_id)
        current = self.conn.execute(
            "SELECT review_status FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        if not current:
            raise KeyError(claim_id)
        timestamp = now_iso()
        with self.conn:
            self.conn.execute(
                "UPDATE claims SET review_status=?, review_note=?, updated_at=? WHERE id=?",
                (status, note, timestamp, claim_id),
            )
            self._append_review_event(
                claim_id, str(current["review_status"]), status, note, timestamp
            )

    def _require_approval_evidence(self, claim_id: str) -> None:
        assessment = self.claim_detail(claim_id)["evidence_assessment"]
        if not assessment["can_approve"]:
            raise ValidationError(" ".join(assessment["issues"]) + " Vælg Kræver originalkilde for legacyudsagn.")

    def clarify_legacy(self, claim_id: str, requires_source: bool, note: str | None = None) -> None:
        """Append a decision; the latest event determines the clarification list."""
        item = self.claim_detail(claim_id)
        if item["dataset"] != "legacy":
            raise ValidationError("Denne handling gælder kun legacyudsagn")
        note = (note or "").strip()
        if requires_source and not note:
            raise ValidationError("Beskriv hvilken originalkilde eller afklaring der mangler")
        if not note:
            note = "Lades uafklaret til senere individuel gennemgang."
        timestamp = now_iso()
        with self.conn:
            self.conn.execute(
                "UPDATE claims SET review_status='uncertain', review_note=?, updated_at=? WHERE id=?",
                (note, timestamp, claim_id),
            )
            self._append_review_event(
                claim_id, item["review_status"], "uncertain", note, timestamp,
                "original_source_required" if requires_source else "left_unresolved",
            )

    def correct_claim(self, claim_id: str, summary: str, note: str) -> None:
        summary = summary.strip()
        note = note.strip()
        if not summary:
            raise ValidationError("Det rettede udsagn må ikke være tomt")
        if not note:
            raise ValidationError("Beskriv kort, hvorfor udsagnet blev rettet")
        current = self.conn.execute(
            "SELECT review_status FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        if not current:
            raise KeyError(claim_id)
        self._require_approval_evidence(claim_id)
        if summary == self.claim_detail(claim_id)["summary"]:
            raise ValidationError("Ret udsagnsteksten, eller vælg Godkend uden rettelse")
        timestamp = now_iso()
        with self.conn:
            self.conn.execute(
                """UPDATE claims SET summary=?, review_status='corrected', review_note=?,
                   updated_at=? WHERE id=?""",
                (summary, note, timestamp, claim_id),
            )
            self._record_claim_version(claim_id, "owner", timestamp)
            self._refresh_claim_search(claim_id)
            self._append_review_event(
                claim_id,
                str(current["review_status"]),
                "corrected",
                note,
                timestamp,
                "claim_corrected",
            )

    def set_review_all(self, status: str, from_status: str, note: str | None = None) -> int:
        if status not in REVIEW_STATUSES or from_status not in REVIEW_STATUSES:
            raise ValidationError("Ugyldig kontrolstatus")
        if status in {"approved", "corrected"}:
            raise ValidationError(
                "Massegodkendelse er deaktiveret; hvert udsagn skal gennemgås med sin evidens"
            )
        rows = list(
            self.conn.execute("SELECT id FROM claims WHERE review_status=?", (from_status,))
        )
        timestamp = now_iso()
        with self.conn:
            for row in rows:
                claim_id = str(row["id"])
                self.conn.execute(
                    """UPDATE claims SET review_status=?, review_note=?, updated_at=?
                       WHERE id=?""",
                    (status, note, timestamp, claim_id),
                )
                self._append_review_event(
                    claim_id, from_status, status, note, timestamp, "bulk_status_changed"
                )
        return len(rows)

    def remove_source(self, source_id: str) -> None:
        version = self.conn.execute(
            "SELECT logical_source_id FROM source_versions WHERE id=?", (source_id,)
        ).fetchone()
        if not version:
            raise KeyError(source_id)
        logical_source_id = str(version["logical_source_id"])
        with self.conn:
            claim_ids = [
                str(row["id"])
                for row in self.conn.execute("SELECT id FROM claims WHERE source_id=?", (source_id,))
            ]
            for claim_id in claim_ids:
                self.conn.execute("DELETE FROM claims_fts WHERE claim_id=?", (claim_id,))
            self.conn.execute("DELETE FROM source_versions WHERE id=?", (source_id,))
            remaining = self.conn.execute(
                "SELECT 1 FROM source_versions WHERE logical_source_id=? LIMIT 1",
                (logical_source_id,),
            ).fetchone()
            if not remaining:
                self.conn.execute("DELETE FROM sources WHERE id=?", (logical_source_id,))

    def backup_database(self, output_dir: Path, keep: int | None = None) -> dict[str, Any]:
        if keep is not None and keep < 1:
            raise ValidationError("--keep skal være mindst 1")
        self.initialize()
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
        backup_path = output_dir / f"investviden-{timestamp}.sqlite"
        temporary_path = backup_path.with_suffix(".sqlite.tmp")
        destination = sqlite3.connect(temporary_path)
        try:
            self.conn.backup(destination)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
        except Exception:
            destination.close()
            temporary_path.unlink(missing_ok=True)
            raise
        finally:
            try:
                destination.close()
            except sqlite3.Error:
                pass
        if integrity != "ok":
            temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Backup fejlede integritetskontrol: {integrity}")
        temporary_path.replace(backup_path)

        removed: list[str] = []
        if keep is not None:
            backups = sorted(
                output_dir.glob("investviden-*.sqlite"),
                key=lambda item: item.stat().st_mtime_ns,
                reverse=True,
            )
            for old_backup in backups[keep:]:
                old_backup.unlink()
                removed.append(str(old_backup.resolve()))
        return {
            "path": str(backup_path.resolve()),
            "size": backup_path.stat().st_size,
            "sha256": file_sha256(backup_path),
            "integrity": integrity,
            "removed": removed,
        }

    def sources_for_extraction(self, all_sources: bool = False) -> list[sqlite3.Row]:
        sql = """SELECT sv.*, s.ai_permission, s.dataset
                 FROM source_versions sv JOIN sources s ON s.id=sv.logical_source_id
                 WHERE sv.is_current=1 AND sv.archived_at IS NULL AND s.archived_at IS NULL"""
        if not all_sources:
            sql += " AND NOT EXISTS (SELECT 1 FROM extraction_runs r WHERE r.source_id=sv.id)"
        return list(self.conn.execute(sql + " ORDER BY sv.imported_at"))

    def stats(self, low_confidence_threshold: float = 0.8) -> dict[str, Any]:
        source_count = self.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        claim_count = self.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        run_count = self.conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]
        unprocessed = self.conn.execute(
            """SELECT COUNT(*) FROM source_versions sv JOIN sources s
               ON s.id=sv.logical_source_id
               WHERE sv.is_current=1 AND sv.archived_at IS NULL AND s.archived_at IS NULL
               AND NOT EXISTS (SELECT 1 FROM extraction_runs r WHERE r.source_id=sv.id)"""
        ).fetchone()[0]
        review_counts = {
            row["review_status"]: row["count"]
            for row in self.conn.execute(
                "SELECT review_status, COUNT(*) AS count FROM claims GROUP BY review_status"
            )
        }
        low_confidence = self.conn.execute(
            "SELECT COUNT(*) FROM claims WHERE confidence < ? AND review_status != 'rejected'",
            (low_confidence_threshold,),
        ).fetchone()[0]
        return {
            "sources": source_count,
            "claims": claim_count,
            "runs": run_count,
            "unprocessed_sources": unprocessed,
            "review_counts": review_counts,
            "low_confidence": low_confidence,
            "low_confidence_threshold": low_confidence_threshold,
        }

    def review_details(self, status: str = "ai_extracted") -> list[dict[str, Any]]:
        if status not in REVIEW_STATUSES:
            raise ValidationError(f"Ugyldig kontrolstatus: {status}")
        rows = self.conn.execute(
            """SELECT c.id, c.summary, c.speaker, c.claim_type, c.sentiment,
                      c.action, c.time_horizon, c.confidence, c.review_status,
                      c.review_note, sv.title AS source_title, sv.publisher,
                      sv.published_at, sv.stored_path, s.dataset,
                      r.provider, r.model, e.excerpt, e.start_ref, e.end_ref,
                      COALESCE((
                          SELECT group_concat(co.name, ', ')
                          FROM claim_companies cc JOIN companies co ON co.id=cc.company_id
                          WHERE cc.claim_id=c.id
                      ), '') AS companies,
                      COALESCE((
                          SELECT group_concat(t.name, ', ')
                          FROM claim_themes ct JOIN themes t ON t.id=ct.theme_id
                          WHERE ct.claim_id=c.id
                      ), '') AS themes
               FROM claims c
               JOIN source_versions sv ON sv.id=c.source_id
               JOIN sources s ON s.id=sv.logical_source_id
               LEFT JOIN extraction_runs r ON r.id=c.run_id
               LEFT JOIN evidence e ON e.claim_id=c.id
               WHERE c.review_status=? AND s.dataset != 'legacy'
               ORDER BY COALESCE(sv.published_at, sv.imported_at) DESC,
                        c.confidence ASC, c.id""",
            (status,),
        ).fetchall()
        return [dict(row) for row in rows]

    def claim_detail(self, claim_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """SELECT c.*, sv.title AS source_title, sv.publisher, sv.published_at,
                      sv.stored_path, sv.sha256 AS source_sha256, sv.source_type,
                      s.archived_at AS source_archived_at, sv.archived_at AS version_archived_at,
                      sv.is_current AS source_is_current, s.dataset, r.provider, r.model,
                      e.excerpt, e.start_ref, e.end_ref
               FROM claims c
               JOIN source_versions sv ON sv.id=c.source_id
               JOIN sources s ON s.id=sv.logical_source_id
               LEFT JOIN extraction_runs r ON r.id=c.run_id
               LEFT JOIN evidence e ON e.claim_id=c.id
               WHERE c.id=?""",
            (claim_id,),
        ).fetchone()
        if not row:
            raise KeyError(claim_id)
        item = dict(row)
        item["companies"] = [dict(company) for company in self.conn.execute(
            """SELECT co.name, co.ticker, cc.role FROM claim_companies cc
               JOIN companies co ON co.id=cc.company_id
               WHERE cc.claim_id=? ORDER BY cc.role, co.name""",
            (claim_id,),
        )]
        item["themes"] = [str(theme["name"]) for theme in self.conn.execute(
            """SELECT t.name FROM claim_themes ct JOIN themes t ON t.id=ct.theme_id
               WHERE ct.claim_id=? ORDER BY t.name""",
            (claim_id,),
        )]
        item["history"] = [dict(event) for event in self.conn.execute(
            """SELECT re.id, re.claim_version_id, re.event_type, re.previous_status,
                      re.new_status, re.note, re.reviewer, re.created_at, cv.version_number
               FROM review_events re JOIN claim_versions cv ON cv.id=re.claim_version_id
               WHERE re.claim_id=? ORDER BY re.rowid DESC""",
            (claim_id,),
        )]
        item["versions"] = [dict(version) for version in self.conn.execute(
            """SELECT id, version_number, payload_json, created_at, created_by, is_current
               FROM claim_versions WHERE claim_id=? ORDER BY version_number DESC""", (claim_id,)
        )]
        item["requires_original_source"] = bool(
            item["history"] and item["review_status"] == "uncertain"
            and item["history"][0]["event_type"] == "original_source_required"
        )
        item["evidence_assessment"] = assess_evidence(item)
        return item

    def search_claims(self, query: str, lane: str = "active", limit: int = 100) -> list[dict[str, Any]]:
        current_source = "s.archived_at IS NULL AND sv.archived_at IS NULL AND sv.is_current=1"
        lanes = {
            "active": f"({current_source}) AND c.review_status IN ('approved','corrected')",
            "signals": f"({current_source}) AND s.dataset != 'legacy' AND c.review_status IN ('ai_extracted','uncertain')",
            "archive": f"(NOT ({current_source}) OR c.review_status='rejected' OR (s.dataset='legacy' AND c.review_status NOT IN ('approved','corrected')))",
            "clarification": """s.dataset='legacy' AND c.review_status='uncertain' AND
                (SELECT re.event_type FROM review_events re WHERE re.claim_id=c.id
                 ORDER BY re.rowid DESC LIMIT 1)='original_source_required'""",
            "noise": "s.dataset='legacy'",
            "all": "1=1",
        }
        if lane not in lanes:
            raise ValidationError("Ukendt søgeområde")
        tokens = re.findall(r"\w+", query, flags=re.UNICODE)
        if not tokens and query.strip():
            return []
        match_query = " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)
        match_filter = "claims_fts MATCH ? AND " if tokens else ""
        rank = "bm25(claims_fts)" if tokens else "0"
        snippet = "snippet(claims_fts, 6, '', '', ' … ', 18)" if tokens else "substr(claims_fts.evidence, 1, 240)"
        candidate_limit = max(limit * 5, 500) if lane in {"archive", "clarification", "noise", "all"} else limit
        rows = self.conn.execute(
            f"""SELECT c.id, c.summary, c.speaker, c.confidence, c.review_status,
                       sv.title AS source_title, sv.published_at, s.dataset,
                       c.review_note, {snippet} AS match_excerpt,
                       {rank} AS rank
                FROM claims_fts
                JOIN claims c ON c.id=claims_fts.claim_id
                JOIN source_versions sv ON sv.id=c.source_id
                JOIN sources s ON s.id=sv.logical_source_id
                WHERE {match_filter} {lanes[lane]}
                ORDER BY rank, COALESCE(sv.published_at, sv.imported_at) DESC, c.id
                LIMIT ?""",
            (match_query, candidate_limit) if tokens else (candidate_limit,),
        ).fetchall()
        result = [dict(row) for row in rows]
        if lane == "noise":
            result = [row for row in result if is_promotional_noise(row["summary"])]
        else:
            result = [row for row in result if not is_promotional_noise(row["summary"])]
        return result[:limit]

    def claims(self, include_rejected: bool = False, include_promotional: bool = False) -> list[dict[str, Any]]:
        where = "" if include_rejected else " WHERE c.review_status != 'rejected'"
        rows = self.conn.execute(
            """SELECT c.*, s.title AS source_title, s.publisher, s.published_at
               FROM claims c JOIN source_versions s ON s.id=c.source_id""" + where +
            " ORDER BY COALESCE(s.published_at, s.imported_at) DESC, c.id"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            if not include_promotional and is_promotional_noise(item["summary"]):
                continue
            item["companies"] = [dict(x) for x in self.conn.execute(
                """SELECT co.name, co.ticker, cc.role FROM claim_companies cc
                   JOIN companies co ON co.id=cc.company_id WHERE cc.claim_id=? ORDER BY cc.role, co.name""",
                (row["id"],),
            )]
            item["themes"] = [x["name"] for x in self.conn.execute(
                "SELECT t.name FROM claim_themes ct JOIN themes t ON t.id=ct.theme_id WHERE ct.claim_id=? ORDER BY t.name",
                (row["id"],),
            )]
            points: dict[str, list[str]] = {"thesis": [], "risk": [], "catalyst": [], "condition": []}
            for point in self.conn.execute(
                "SELECT point_type, text FROM claim_points WHERE claim_id=? ORDER BY point_type, position", (row["id"],)
            ):
                points[point["point_type"]].append(point["text"])
            item["points"] = points
            evidence = self.conn.execute("SELECT excerpt, start_ref, end_ref FROM evidence WHERE claim_id=?", (row["id"],)).fetchone()
            item["evidence"] = dict(evidence) if evidence else {}
            result.append(item)
        return result


def read_extractions(path: Path) -> Iterable[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValidationError(f"Ugyldig JSON på linje {line_number}: {exc}") from exc
    else:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            yield from data
        else:
            yield data
