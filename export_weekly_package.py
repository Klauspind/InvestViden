"""Create a read-only weekly InvestViden package for manual AI analysis."""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from investkb.weekly_package import write_weekly_ai_package  # noqa: E402


def default_database() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_appdata:
        raise RuntimeError("LOCALAPPDATA er ikke sat; consumer-databasen kan ikke findes")
    return Path(local_appdata) / "InvestViden" / "runtime" / "transskribinator-consumer" / "knowledgebase.sqlite"


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Brug datoformat YYYY-MM-DD") from exc


def source_approval(value: str) -> tuple[str, str]:
    source_id, separator, digest = value.partition(":")
    if not separator or not source_id or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise argparse.ArgumentTypeError("Brug SOURCE_ID:SHA256 for den konkrete kildeversion")
    return source_id, digest.lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Tilsidesæt den normale consumer-database")
    parser.add_argument("--days", type=int, default=7, help="Antal kalenderdage inkl. slutdato; standard 7")
    parser.add_argument("--through", type=parse_date, help="Slutdato YYYY-MM-DD; standard er i dag")
    parser.add_argument("--output", type=Path, help="Markdown-fil; standard output/ugepakke-YYYY-MM-DD.md")
    parser.add_argument(
        "--approve-source",
        action="append",
        type=source_approval,
        default=[],
        metavar="SOURCE_ID:SHA256",
        help="Medtag en ask-kilde i netop denne pakke; kan gentages",
    )
    args = parser.parse_args(argv)
    period_end = args.through or date.today()
    output = args.output or (ROOT / "output" / f"ugepakke-{period_end.isoformat()}.md")
    try:
        result = write_weekly_ai_package(
            args.db or default_database(),
            output,
            through=period_end,
            days=args.days,
            approvals=dict(args.approve_source),
        )
        print("InvestViden ugepakke klar")
        print(f"Periode: {result['period_start']} - {result['period_end']}")
        print(f"Kilder i perioden: {result['sources_in_period']}")
        print(f"Medtaget efter AI-politik: {result['sources_included']}")
        print(f"Udeladt af AI-politik: {result['sources_policy_excluded']}")
        print(f"Med AI-udtræk: {result['sources_processed']}")
        print(f"Uden AI-udtræk: {result['sources_unprocessed']}")
        print(f"Udsagn: {result['claims']}")
        print(f"Fil: {result['output']}")
        print("Ingen data er sendt til en AI, og databasen er kun åbnet read-only.")
        if result["sources_policy_excluded"]:
            print("Nogle kilder er udeladt af AI-politik. Ask-kilder kræver eksplicit SOURCE_ID:SHA256-godkendelse.")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError, sqlite3.Error, OSError) as exc:
        print(f"Fejl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
