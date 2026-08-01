from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .inbox import scan_inbox
from .outputs import write_dashboard, write_export, write_report, write_tasks
from .repository import KnowledgeBase, read_extractions
from .validation import ValidationError


SOURCE_TYPES = ["podcast_transcript", "newsletter", "report", "article", "note", "other"]
REVIEW_STATUSES = ["ai_extracted", "approved", "corrected", "uncertain", "rejected"]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="investviden", description="InvestViden – kildebaseret investeringsviden")
    result.add_argument("--db", default="data/knowledgebase.sqlite", help="Sti til SQLite-database")
    sub = result.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialisér databasen")
    backup = sub.add_parser("backup", help="Opret og verificér en sikker SQLite-backup")
    backup.add_argument("--output-dir", type=Path, default=Path("backups"))
    backup.add_argument("--keep", type=int, help="Behold kun de seneste N backups")
    status = sub.add_parser("status", help="Vis kilder, udtræk og kontrolbehov")
    status.add_argument("--threshold", type=float, help="Override grænsen for lav sikkerhed")
    status.add_argument("--config", type=Path, default=Path("config/settings.json"))
    source = sub.add_parser("import-source", help="Importér og hash en originalkilde")
    source.add_argument("path", type=Path)
    source.add_argument("--type", required=True, choices=SOURCE_TYPES)
    source.add_argument("--title")
    source.add_argument("--publisher")
    source.add_argument("--published-at")
    source.add_argument("--language", default="da")
    scan = sub.add_parser("scan-inbox", help="Find og importér nye tekstkilder fra indbakken")
    scan.add_argument("--path", type=Path, default=Path("inbox"))
    scan.add_argument("--config", type=Path, default=Path("config/settings.json"))
    scan.add_argument("--dry-run", action="store_true", help="Vis resultatet uden at importere")
    scan.add_argument("--prepare", action="store_true", help="Generér også udtræksopgaver for ubehandlede kilder")
    scan.add_argument("--tasks-output", type=Path, default=Path("output/extraction-tasks.jsonl"))
    remove_source = sub.add_parser("remove-source", help="Fjern en kilde og dens udtræk")
    remove_source.add_argument("source_id")
    remove_source.add_argument("--confirm", action="store_true", help="Bekræft den permanente sletning")

    prepare = sub.add_parser("prepare", help="Generér JSONL-opgaver til valgfri AI")
    prepare.add_argument("--output", type=Path, default=Path("output/extraction-tasks.jsonl"))
    prepare.add_argument("--all", action="store_true", help="Medtag også allerede behandlede kilder")
    prepare.add_argument("--config", type=Path, default=Path("config/settings.json"))

    ingest = sub.add_parser("ingest", help="Validér og indlæs JSON eller JSONL")
    ingest.add_argument("path", type=Path)

    review_list = sub.add_parser("review-list", help="Vis kontrolkø")
    review_list.add_argument("--status", choices=REVIEW_STATUSES)
    review_set = sub.add_parser("review-set", help="Opdatér kontrolstatus")
    review_set.add_argument("claim_id")
    review_set.add_argument("--status", required=True, choices=REVIEW_STATUSES)
    review_set.add_argument("--note")
    review_all = sub.add_parser("review-all", help="Opdatér alle udsagn med en bestemt kontrolstatus")
    review_all.add_argument("--from-status", default="ai_extracted", choices=REVIEW_STATUSES)
    review_all.add_argument("--status", required=True, choices=REVIEW_STATUSES)
    review_all.add_argument("--note")

    report = sub.add_parser("report", help="Generér Markdown-rapport")
    report.add_argument("--output", type=Path, default=Path("output/rapport.md"))
    report.add_argument("--approved-only", action="store_true")
    report.add_argument("--config", type=Path, default=Path("config/settings.json"))
    dashboard = sub.add_parser("dashboard", help="Generér lokal HTML-kontroloversigt")
    dashboard.add_argument("--output", type=Path, default=Path("output/kontroloversigt.html"))
    export = sub.add_parser("export", help="Eksportér normaliserede udsagn som JSONL")
    export.add_argument("--output", type=Path, default=Path("output/knowledgebase.jsonl"))
    sub.add_parser("demo", help="Kør et reproducerbart ende-til-ende-demo-flow")
    return result


def _demo(kb: KnowledgeBase) -> None:
    root = Path(__file__).resolve().parents[2]
    source_file = root / "examples" / "demo_transcript.txt"
    extraction_file = root / "examples" / "demo_extraction.json"
    source_id, _ = kb.import_source(
        source_file, "podcast_transcript", "Demoepisode om investeringstemaer",
        "Demo Podcast", "2026-07-31",
    )
    extraction = json.loads(extraction_file.read_text(encoding="utf-8"))
    extraction["source_id"] = source_id
    kb.ingest(extraction)
    output = Path("output")
    write_tasks(kb, output / "extraction-tasks.jsonl", all_sources=True)
    write_report(kb, output / "demo-rapport.md")
    write_dashboard(kb, output / "kontroloversigt.html")
    write_export(kb, output / "knowledgebase.jsonl")
    print(f"Demo klar: {kb.db_path} og {output.resolve()}")


def run(args: argparse.Namespace) -> int:
    with KnowledgeBase(args.db) as kb:
        kb.initialize()
        if args.command == "init":
            print(f"Database klar: {kb.db_path.resolve()}")
        elif args.command == "backup":
            result = kb.backup_database(args.output_dir, args.keep)
            print(f"Backup klar: {result['path']}")
            print(f"Størrelse: {result['size']} bytes")
            print(f"SHA-256: {result['sha256']}")
            print(f"Integritetskontrol: {result['integrity']}")
            if result["removed"]:
                print(f"Fjernede {len(result['removed'])} ældre backup(s) pga. --keep")
        elif args.command == "status":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            threshold = args.threshold
            if threshold is None:
                threshold = preferences.get("report", {}).get("low_confidence_threshold", 0.8)
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
                raise ValidationError("--threshold skal være mellem 0 og 1")
            stats = kb.stats(float(threshold))
            print(f"Kilder: {stats['sources']} ({stats['unprocessed_sources']} ubehandlede)")
            print(f"Udtrækskørsler: {stats['runs']}")
            print(f"Udsagn: {stats['claims']}")
            print(f"Lav sikkerhed (<{stats['low_confidence_threshold']:.0%}): {stats['low_confidence']}")
            if stats["review_counts"]:
                print("Kontrolstatus:")
                for name, count in sorted(stats["review_counts"].items()):
                    print(f"  {name}: {count}")
        elif args.command == "import-source":
            source_id, created = kb.import_source(
                args.path, args.type, args.title, args.publisher, args.published_at, args.language
            )
            print(f"{'Importeret' if created else 'Allerede importeret'}: {source_id}")
        elif args.command == "scan-inbox":
            settings = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            result = scan_inbox(kb, args.path, settings, args.dry_run)
            prefix = "DRY RUN – " if args.dry_run else ""
            print(f"{prefix}InvestViden indbakkescanning")
            print(f"Fundet: {result['candidates']} tekstfil(er), {result['unique']} unikke")
            print(f"Nye: {result['new']}")
            print(f"Allerede registreret: {result['existing']}")
            print(f"Dubletplaceringer: {len(result['duplicate_locations'])}")
            for duplicate in result["duplicate_locations"]:
                print(f"  DUBLET: {duplicate['duplicate']}")
                print(f"  BEHOLDT: {duplicate['kept']}")
            for imported in result["imports"]:
                label = imported["source_id"] or "ville blive importeret"
                print(f"  NY: {imported['title']} [{label}]")
            print(f"Fejl: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"  FEJL: {error}")
            if args.prepare and not args.dry_run:
                count = write_tasks(kb, args.tasks_output, False, settings)
                print(f"Klargjorde {count} udtræksopgave(r) i {args.tasks_output}")
        elif args.command == "remove-source":
            if not args.confirm:
                raise ValidationError("Tilføj --confirm for at fjerne kilden og dens udtræk")
            kb.remove_source(args.source_id)
            print(f"Fjernede kilde og tilknyttede udtræk: {args.source_id}")
        elif args.command == "prepare":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            count = write_tasks(kb, args.output, args.all, preferences)
            print(f"Skrev {count} opgave(r) til {args.output}")
        elif args.command == "ingest":
            runs = claims = 0
            for extraction in read_extractions(args.path):
                _, count = kb.ingest(extraction)
                runs += 1
                claims += count
            print(f"Indlæste {claims} udsagn fra {runs} udtræk")
        elif args.command == "review-list":
            rows = kb.review_rows(args.status)
            if not rows:
                print("Kontrolkøen er tom.")
            for row in rows:
                print(f"{row['id']} | {row['confidence']:.0%} | {row['review_status']} | {row['source_title']} | {row['summary']}")
        elif args.command == "review-set":
            kb.set_review(args.claim_id, args.status, args.note)
            print(f"Opdaterede {args.claim_id} til {args.status}")
        elif args.command == "review-all":
            count = kb.set_review_all(args.status, args.from_status, args.note)
            print(f"Opdaterede {count} udsagn fra {args.from_status} til {args.status}")
        elif args.command == "report":
            preferences = {}
            if args.config.exists():
                preferences = json.loads(args.config.read_text(encoding="utf-8-sig"))
            include_pending = preferences.get("report", {}).get("include_pending", True)
            if args.approved_only:
                include_pending = False
            count = write_report(kb, args.output, bool(include_pending), preferences)
            print(f"Skrev {count} udsagn til {args.output}")
        elif args.command == "dashboard":
            count = write_dashboard(kb, args.output)
            print(f"Skrev {count} udsagn til {args.output}")
        elif args.command == "export":
            count = write_export(kb, args.output)
            print(f"Eksporterede {count} udsagn til {args.output}")
        elif args.command == "demo":
            _demo(kb)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "demo" and args.db == "data/knowledgebase.sqlite":
        args.db = "data/demo.sqlite"
    try:
        return run(args)
    except (ValidationError, FileNotFoundError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Fejl: {exc}", file=sys.stderr)
        return 2
