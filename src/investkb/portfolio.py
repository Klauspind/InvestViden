from __future__ import annotations

import re
import sqlite3
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from .repository import now_iso
from .validation import ValidationError


PORTFOLIO_KINDS = {
    "holding": "Position",
    "watchlist": "Watchlist",
}

TIME_HORIZONS = {
    "short_term": "Kort sigt",
    "medium_term": "Mellemlang sigt",
    "long_term": "Lang sigt",
    "unspecified": "Ikke angivet",
}


def company_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "company"


class PortfolioStore:
    """Small local SQLite store for personal portfolio/watchlist state.

    The store deliberately lives next to, but outside, the knowledge database so
    IV-012 does not migrate the already accepted consumer knowledgebase.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def __enter__(self) -> "PortfolioStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def initialize(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS portfolio_entries (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                company_key TEXT NOT NULL UNIQUE,
                ticker TEXT,
                kind TEXT NOT NULL CHECK (kind IN ('holding','watchlist')),
                position_note TEXT,
                time_horizon TEXT NOT NULL CHECK (time_horizon IN
                    ('short_term','medium_term','long_term','unspecified')),
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_portfolio_kind_name
                ON portfolio_entries(kind, company_name);
            """
        )
        self.conn.commit()

    def entries(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT * FROM portfolio_entries
               ORDER BY CASE kind WHEN 'holding' THEN 0 ELSE 1 END,
                        lower(company_name), id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def entry(self, entry_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM portfolio_entries WHERE id=?", (entry_id,)
        ).fetchone()
        if not row:
            raise KeyError(entry_id)
        return dict(row)

    def save(
        self,
        *,
        company_name: str,
        ticker: str | None,
        kind: str,
        position_note: str | None,
        time_horizon: str,
        note: str | None,
        entry_id: str | None = None,
    ) -> str:
        company_name = company_name.strip()
        ticker = (ticker or "").strip().upper() or None
        position_note = (position_note or "").strip() or None
        note = (note or "").strip() or None
        if not company_name or len(company_name) > 200:
            raise ValidationError("Virksomhedsnavn skal være 1-200 tegn")
        if ticker and len(ticker) > 30:
            raise ValidationError("Ticker må højst være 30 tegn")
        if kind not in PORTFOLIO_KINDS:
            raise ValidationError("Vælg Position eller Watchlist")
        if time_horizon not in TIME_HORIZONS:
            raise ValidationError("Ukendt tidshorisont")
        if position_note and len(position_note) > 200:
            raise ValidationError("Positionsnotat må højst være 200 tegn")
        if note and len(note) > 2000:
            raise ValidationError("Notat må højst være 2000 tegn")

        key = company_key(company_name)
        duplicate = self.conn.execute(
            "SELECT id FROM portfolio_entries WHERE company_key=?", (key,)
        ).fetchone()
        if duplicate and str(duplicate["id"]) != (entry_id or ""):
            raise ValidationError("Virksomheden findes allerede i portefølje/watchlist")

        timestamp = now_iso()
        if entry_id:
            with self.conn:
                cursor = self.conn.execute(
                    """UPDATE portfolio_entries
                       SET company_name=?, company_key=?, ticker=?, kind=?, position_note=?,
                           time_horizon=?, note=?, updated_at=? WHERE id=?""",
                    (
                        company_name, key, ticker, kind, position_note,
                        time_horizon, note, timestamp, entry_id,
                    ),
                )
                if not cursor.rowcount:
                    raise KeyError(entry_id)
            return entry_id

        entry_id = f"portfolio-{uuid.uuid4().hex[:20]}"
        with self.conn:
            self.conn.execute(
                """INSERT INTO portfolio_entries
                   (id, company_name, company_key, ticker, kind, position_note,
                    time_horizon, note, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry_id, company_name, key, ticker, kind, position_note,
                    time_horizon, note, timestamp, timestamp,
                ),
            )
        return entry_id

    def delete(self, entry_id: str) -> None:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM portfolio_entries WHERE id=?", (entry_id,)
            )
            if not cursor.rowcount:
                raise KeyError(entry_id)
