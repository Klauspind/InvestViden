"""Start InvestViden against the persistent Transskribinator consumer database."""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from investkb.operational_navigation import serve_operational  # noqa: E402


def default_database() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_appdata:
        raise RuntimeError("LOCALAPPDATA er ikke sat; consumer-databasen kan ikke findes")
    return Path(local_appdata) / "InvestViden" / "runtime" / "transskribinator-consumer" / "knowledgebase.sqlite"


def check_database(path: Path) -> dict[str, int | str]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(
            f"Consumer-databasen findes ikke: {resolved}. Kør Transskribinator-consumeren først."
        )
    uri = "file:" + resolved.as_posix() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        sources = int(conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0])
    if integrity != "ok":
        raise RuntimeError(f"Databasen fejlede integritetskontrol: {integrity}")
    return {"integrity": integrity, "sources": sources}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Tilsidesæt den normale consumer-database")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="Kontrollér kun at consumer-databasen kan læses")
    args = parser.parse_args(argv)
    try:
        database = (args.db or default_database()).expanduser().resolve()
        status = check_database(database)
        if args.check:
            print(f"Consumer-database: {database}")
            print(f"Integritet: {status['integrity']}")
            print(f"Kilder: {status['sources']}")
            return 0
        if not 0 <= args.port <= 65535:
            raise ValueError("--port skal være mellem 0 og 65535")
        serve_operational(database, args.port, not args.no_browser)
        return 0
    except (FileNotFoundError, RuntimeError, ValueError, sqlite3.Error) as exc:
        print(f"Fejl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
