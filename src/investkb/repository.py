from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .schema import SCHEMA_SQL
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

    def initialize(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES(1, ?)",
            (now_iso(),),
        )
        self.conn.commit()

    def import_source(
        self,
        path: Path,
        source_type: str,
        title: str | None = None,
        publisher: str | None = None,
        published_at: str | None = None,
        language: str = "da",
        source_store: Path | str = "data/sources",
    ) -> tuple[str, bool]:
        self.initialize()
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        content_hash = file_sha256(path)
        existing = self.conn.execute("SELECT id FROM sources WHERE sha256 = ?", (content_hash,)).fetchone()
        if existing:
            return str(existing["id"]), False

        source_id = f"src-{content_hash[:16]}"
        store = Path(source_store)
        store.mkdir(parents=True, exist_ok=True)
        stored = store / f"{content_hash[:12]}_{path.name}"
        shutil.copy2(path, stored)
        self.conn.execute(
            """INSERT INTO sources
               (id, source_type, title, publisher, published_at, language,
                original_path, stored_path, sha256, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source_id, source_type, title or path.stem, publisher, published_at, language,
                str(path), str(stored.resolve()), content_hash, now_iso(),
            ),
        )
        self.conn.commit()
        return source_id, True

    def source_by_hash(self, content_hash: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM sources WHERE sha256 = ?", (content_hash,)).fetchone()

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
        source = self.conn.execute("SELECT id FROM sources WHERE id = ?", (data["source_id"],)).fetchone()
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
            for claim in data["claims"]:
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
        return run_id, len(data["claims"])

    def review_rows(self, status: str | None = None) -> list[sqlite3.Row]:
        sql = """SELECT c.id, c.summary, c.confidence, c.review_status, c.sentiment,
                        c.action, s.title AS source_title
                 FROM claims c JOIN sources s ON s.id=c.source_id"""
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
        cursor = self.conn.execute(
            "UPDATE claims SET review_status=?, review_note=?, updated_at=? WHERE id=?",
            (status, note, now_iso(), claim_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(claim_id)
        self.conn.commit()

    def set_review_all(self, status: str, from_status: str, note: str | None = None) -> int:
        if status not in REVIEW_STATUSES or from_status not in REVIEW_STATUSES:
            raise ValidationError("Ugyldig kontrolstatus")
        cursor = self.conn.execute(
            """UPDATE claims SET review_status=?, review_note=?, updated_at=?
               WHERE review_status=?""",
            (status, note, now_iso(), from_status),
        )
        self.conn.commit()
        return cursor.rowcount

    def remove_source(self, source_id: str) -> None:
        cursor = self.conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        if cursor.rowcount != 1:
            raise KeyError(source_id)
        self.conn.commit()

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
        sql = "SELECT * FROM sources s"
        if not all_sources:
            sql += " WHERE NOT EXISTS (SELECT 1 FROM extraction_runs r WHERE r.source_id=s.id)"
        return list(self.conn.execute(sql + " ORDER BY imported_at"))

    def stats(self, low_confidence_threshold: float = 0.8) -> dict[str, Any]:
        source_count = self.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        claim_count = self.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        run_count = self.conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]
        unprocessed = self.conn.execute(
            """SELECT COUNT(*) FROM sources s WHERE NOT EXISTS
               (SELECT 1 FROM extraction_runs r WHERE r.source_id=s.id)"""
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

    def claims(self, include_rejected: bool = False) -> list[dict[str, Any]]:
        where = "" if include_rejected else " WHERE c.review_status != 'rejected'"
        rows = self.conn.execute(
            """SELECT c.*, s.title AS source_title, s.publisher, s.published_at
               FROM claims c JOIN sources s ON s.id=c.source_id""" + where +
            " ORDER BY COALESCE(s.published_at, s.imported_at) DESC, c.id"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
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
