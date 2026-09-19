from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from .ai_workflow import process_ai_inbox
from .inbox import scan_inbox
from .mistral_api import (
    DEFAULT_MAX_OUTPUT_TOKENS as DEFAULT_MISTRAL_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL as DEFAULT_MISTRAL_MODEL,
    DEFAULT_TEMPERATURE as DEFAULT_MISTRAL_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_MISTRAL_TIMEOUT_SECONDS,
    mistral_status,
    run_mistral_extractions,
    verify_mistral_access,
)
from .mistral_jobs import (
    DEFAULT_COST_LIMIT_USD,
    INPUT_USD_PER_MILLION_TOKENS,
    OUTPUT_USD_PER_MILLION_TOKENS,
    PRICING_VERSION,
    create_mistral_job,
    execute_mistral_job,
)
from .openai_api import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TIMEOUT_SECONDS,
    openai_status,
    plan_openai_extractions,
    run_openai_extractions,
)
from .outputs import write_ai_package, write_dashboard, write_export, write_report, write_tasks
from .podcast_sync import apply_podcast_sync, plan_podcast_sync
from .repository import KnowledgeBase, read_extractions
from .validation import ValidationError
from .web_app import serve
from .weekly_runner import (
    inspect_weekly_recovery,
    require_isolated_schema4_database,
    run_weekly_drafts,
)


SOURCE_TYPES = ["podcast_transcript", "newsletter", "report", "article", "note", "other"]
REVIEW_STATUSES = ["ai_extracted", "approved", "corrected", "uncertain", "rejected"]

def source_approval(value: str) -> tuple[str, str]:
    source_id, separator, digest = value.partition(":")
    if not separator or not source_id or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise argparse.ArgumentTypeError("Brug SOURCE_ID:SHA256 for den konkrete kildeversion")
    return source_id, digest.lower()


def _print_mistral_job(job: dict) -> None:
    print(f"Job: {job['id']} | status: {job['status']} | model: {job['model']}")
    print(f"Estimat: USD {float(job['estimated_cost_usd']):.4f} | loft: USD {float(job['cost_limit_usd']):.2f}")
    for item in job["items"]:
        error = f" | fejl: {item['error']}" if item.get("error") else ""
        print(
            f"  {item['source_version_id']} | {item['status']} | forsøg {item['attempt_count']} | "
            f"{item['title']}{error}"
        )


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
    source.add_argument("--ai-permission", choices=["allow", "ask", "local_only", "blocked"], default="ask")
    sub.add_parser("source-policies", help="Vis kilders AI-tilladelse og SHA-256")
    policy = sub.add_parser("source-policy", help="Sæt AI-tilladelse for en bestemt kilde")
    policy.add_argument("source_id")
    policy.add_argument("--permission", required=True, choices=["allow", "ask", "local_only", "blocked"])
    scan = sub.add_parser("scan-inbox", help="Find og importér nye tekstkilder fra indbakken")
    scan.add_argument("--path", type=Path, default=Path("inbox"))
    scan.add_argument("--config", type=Path, default=Path("config/settings.json"))
    scan.add_argument("--dry-run", action="store_true", help="Vis resultatet uden at importere")
    scan.add_argument("--prepare", action="store_true", help="Generér også udtræksopgaver for ubehandlede kilder")
    scan.add_argument("--tasks-output", type=Path, default=Path("output/extraction-tasks.jsonl"))
    podcast_sync = sub.add_parser(
        "sync-podcasts",
        help="Klargør fulde, tidskodede podcasttekster fra episode-JSON",
    )
    podcast_sync.add_argument("--source", type=Path, help="Rodmappe med efterbehandlede podcast-JSON-filer")
    podcast_sync.add_argument("--target", type=Path, help="Målmappe under den lokale InvestViden-indbakke")
    podcast_sync.add_argument("--config", type=Path, default=Path("config/settings.json"))
    podcast_sync.add_argument(
        "--apply",
        action="store_true",
        help="Skriv nye tidskodede tekster og provenance-sidecars; uden flaget vises kun en plan",
    )
    remove_source = sub.add_parser("remove-source", help="Fjern en kilde og dens udtræk")
    remove_source.add_argument("source_id")
    remove_source.add_argument("--confirm", action="store_true", help="Bekræft den permanente sletning")

    prepare = sub.add_parser("prepare", help="Generér JSONL-opgaver til valgfri AI")
    prepare.add_argument("--output", type=Path, default=Path("output/extraction-tasks.jsonl"))
    prepare.add_argument("--all", action="store_true", help="Medtag også allerede behandlede kilder")
    prepare.add_argument("--config", type=Path, default=Path("config/settings.json"))

    ai_package = sub.add_parser("prepare-ai", help="Lav uploadklare opgavefiler til en valgfri AI")
    ai_package.add_argument("--output-dir", type=Path, default=Path("output/ai-pakke"))
    ai_package.add_argument("--all", action="store_true", help="Medtag også allerede behandlede kilder")
    ai_package.add_argument("--config", type=Path, default=Path("config/settings.json"))

    api_status = sub.add_parser("openai-status", help="Vis sikker API-status uden at vise nøglen")
    api_status.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    api_status.add_argument("--config", type=Path, default=Path("config/settings.json"))

    mistral_api_status = sub.add_parser("mistral-status", help="Vis sikker Mistral API-status uden at vise nøglen")
    mistral_api_status.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    mistral_api_status.add_argument("--config", type=Path, default=Path("config/settings.json"))
    mistral_api_status.add_argument(
        "--verify",
        action="store_true",
        help="Kontrollér nøgle og model mod Mistral uden at sende en kilde",
    )

    run_mistral = sub.add_parser("run-mistral", help="Forhåndsvis eller send nye kilder til Mistral API")
    run_mistral.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    run_mistral.add_argument("--audit-dir", type=Path, default=Path("output/mistral-audit"))
    run_mistral.add_argument("--config", type=Path, default=Path("config/settings.json"))
    run_mistral.add_argument("--model", help="Tilsidesæt den konfigurerede Mistral-model")
    run_mistral.add_argument("--max-output-tokens", type=int)
    run_mistral.add_argument("--timeout-seconds", type=int)
    run_mistral.add_argument("--temperature", type=float)
    run_mistral.add_argument("--limit", type=int, default=1, help="Maksimalt antal kilder; standard er én")
    run_mistral.add_argument(
        "--apply",
        action="store_true",
        help="Send de viste kilder; uden flaget bruges ingen API og ingen penge",
    )

    mistral_jobs = sub.add_parser("mistral-jobs", help="Vis de seneste persistente Mistral-job")
    mistral_jobs.add_argument("--limit", type=int, default=20)
    job_create = sub.add_parser("mistral-job-create", help="Opret en Mistral-jobkladde uden API-kald")
    job_create.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    job_create.add_argument("--config", type=Path, default=Path("config/settings.json"))
    job_create.add_argument("--limit", type=int, default=1, help="Maksimalt 1-5 kilder")
    job_create.add_argument("--cost-limit", type=float, default=DEFAULT_COST_LIMIT_USD)
    job_create.add_argument("--approve-source", action="append", type=source_approval, default=[],
                            metavar="SOURCE_ID:SHA256")
    job_confirm = sub.add_parser("mistral-job-confirm", help="Bekræft pris og kilder for en jobkladde")
    job_confirm.add_argument("job_id")
    job_run = sub.add_parser("mistral-job-run", help="Kør et særskilt bekræftet Mistral-job")
    job_run.add_argument("job_id")
    job_run.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    job_run.add_argument("--audit-dir", type=Path, default=Path("output/mistral-audit"))
    job_run.add_argument("--config", type=Path, default=Path("config/settings.json"))
    job_run.add_argument("--retry-source", action="append", default=[], metavar="SOURCE_ID",
                         help="Genkør kun denne fejlede kilde; kan gentages")
    job_run.add_argument("--apply", action="store_true",
                         help="Påkrævet for afsendelse; uden flaget vises kun jobbet")

    run_ai = sub.add_parser("run-ai", help="Forhåndsvis eller send nye kilder til OpenAI API")
    run_ai.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    run_ai.add_argument("--audit-dir", type=Path, default=Path("output/openai-audit"))
    run_ai.add_argument("--config", type=Path, default=Path("config/settings.json"))
    run_ai.add_argument("--model", help="Tilsidesæt den konfigurerede OpenAI-model")
    run_ai.add_argument("--reasoning-effort", choices=["none", "low", "medium", "high", "xhigh", "max"])
    run_ai.add_argument("--max-output-tokens", type=int)
    run_ai.add_argument("--timeout-seconds", type=int)
    run_ai.add_argument("--limit", type=int, default=1, help="Maksimalt antal kilder; standard er én")
    run_ai.add_argument(
        "--apply",
        action="store_true",
        help="Send de viste kilder; uden flaget bruges ingen API og ingen penge",
    )
    for command in (run_mistral, run_ai, prepare, ai_package):
        command.add_argument("--approve-source", action="append", type=source_approval, default=[],
                             metavar="SOURCE_ID:SHA256", help="Godkend en ask-kilde til denne kørsel; kan gentages")

    process_ai = sub.add_parser("process-ai", help="Validér og indlæs alle AI-svar fra incoming-mappen")
    process_ai.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    process_ai.add_argument("--archive", type=Path, default=Path("extractions/processed"))
    process_ai.add_argument("--config", type=Path, default=Path("config/settings.json"))
    process_ai.add_argument("--dry-run", action="store_true", help="Validér uden at indlæse eller flytte filer")

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
    report.add_argument(
        "--status",
        action="append",
        choices=REVIEW_STATUSES,
        help="Medtag kun denne kontrolstatus; kan gentages",
    )
    report.add_argument("--config", type=Path, default=Path("config/settings.json"))
    dashboard = sub.add_parser("dashboard", help="Generér lokal HTML-kontroloversigt")
    dashboard.add_argument("--output", type=Path, default=Path("output/kontroloversigt.html"))
    export = sub.add_parser("export", help="Eksportér normaliserede udsagn som JSONL")
    export.add_argument("--output", type=Path, default=Path("output/knowledgebase.jsonl"))
    sub.add_parser("demo", help="Kør et reproducerbart ende-til-ende-demo-flow")
    ui = sub.add_parser("ui", help="Start den lokale InvestViden-brugerflade")
    ui.add_argument("--port", type=int, default=8765, help="Lokal port; standard 8765")
    ui.add_argument("--no-browser", action="store_true", help="Åbn ikke browseren automatisk")
    weekly = sub.add_parser(
        "weekly-drafts",
        help="Forhåndsvis eller opret ugentlige, ubekræftede Mistral-jobkladder",
    )
    weekly.add_argument("--database", type=Path, required=True,
                        help="Eksisterende, isoleret schema-4-database; ingen standardsti")
    weekly.add_argument("--incoming", type=Path, default=Path("extractions/incoming"))
    weekly.add_argument("--state-dir", type=Path, default=Path("output/weekly-runner/state"))
    weekly.add_argument("--backup-dir", type=Path, default=Path("backups/weekly-runner"))
    weekly.add_argument("--max-jobs", type=int, default=5)
    weekly.add_argument(
        "--apply", action="store_true",
        help="Opret kun ubekræftede kladder; uden flaget er kommandoen read-only preview",
    )
    recovery = sub.add_parser(
        "weekly-recovery",
        help="Afstem ugejournal og jobdatabase skrivebeskyttet",
    )
    recovery.add_argument("--database", type=Path, required=True,
                          help="Eksisterende, isoleret schema-4-database; ingen standardsti")
    recovery.add_argument("--state-dir", type=Path, default=Path("output/weekly-runner/state"))
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
    if args.command in {"weekly-drafts", "weekly-recovery"}:
        database = args.database.resolve()
        if not database.is_file():
            raise FileNotFoundError(
                f"Den valgte database findes ikke: {database}. "
                "Runneren opretter eller migrerer ikke en database."
            )
        with KnowledgeBase(database) as kb:
            require_isolated_schema4_database(kb)
            if args.command == "weekly-recovery":
                result = inspect_weekly_recovery(kb, args.state_dir)
            else:
                result = run_weekly_drafts(
                    kb, args.incoming, args.state_dir, args.backup_dir,
                    max_jobs=args.max_jobs, apply=args.apply,
                )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "ui":
        if not 0 <= args.port <= 65535:
            raise ValidationError("--port skal være mellem 0 og 65535")
        serve(args.db, args.port, not args.no_browser)
        return 0
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
                args.path, args.type, args.title, args.publisher, args.published_at, args.language,
                ai_permission=args.ai_permission,
            )
            print(f"{'Importeret' if created else 'Allerede importeret'}: {source_id}")
        elif args.command == "source-policies":
            for source in kb.source_policies():
                print(f"{source['id']} | {source['ai_permission']} | {source['title']} | {source['sha256']}")
        elif args.command == "source-policy":
            kb.set_source_permission(args.source_id, args.permission)
            print("Kildepolitikken er gemt. Ingen tekst er sendt til AI.")
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
        elif args.command == "sync-podcasts":
            settings = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            sync_settings = settings.get("podcast_import", {})
            source_value = args.source or sync_settings.get("source_root")
            target_value = args.target or sync_settings.get("target_root", "inbox/transskriptioner")
            if not source_value:
                raise ValidationError(
                    "Angiv --source eller podcast_import.source_root i config/settings.json"
                )
            plan = plan_podcast_sync(kb, Path(source_value), Path(target_value), settings)
            label = "ANVEND – " if args.apply else "FORHÅNDSVISNING – "
            counts = plan["counts"]
            print(f"{label}podcastimport fra komplet episode-JSON")
            print(f"Fundet og valideret: {len(plan['items'])}")
            print(f"Nye: {counts.get('new', 0)}")
            print(f"Allerede klargjort: {counts.get('ready', 0)}")
            print(f"Allerede registreret: {counts.get('registered', 0)}")
            print(f"Eksisterende episode/anden version: {counts.get('existing_episode', 0)}")
            print(f"Målkonflikter: {counts.get('target_conflict', 0)}")
            print(f"Læse-/formatfejl: {len(plan['errors'])}")
            status_labels = {
                "new": "NY",
                "ready": "KLAR",
                "registered": "REGISTRERET",
                "existing_episode": "KRÆVER BESLUTNING",
                "target_conflict": "KONFLIKT",
            }
            for item in plan["items"]:
                suffix = f" – {item.detail}" if item.detail else ""
                print(
                    f"  {status_labels[item.status]}: {item.episode.podcast} | "
                    f"{item.episode.published_at} | {item.episode.title}{suffix}"
                )
            for error in plan["errors"]:
                print(f"  FEJL: {error}")
            if args.apply:
                result = apply_podcast_sync(plan)
                print(f"Skrev {len(result['written'])} ny(e) tidskodet tekstfil(er)")
                print(f"Skrev {len(result['sidecars'])} provenance-sidecar(s)")
                if result["errors"]:
                    print(f"Skrivefejl: {len(result['errors'])}")
                    for error in result["errors"]:
                        print(f"  FEJL: {error}")
                    return 2
                print("OneDrive-kilderne blev kun læst og er ikke ændret.")
                print("Næste kontrol: .\\run.cmd scan-inbox --dry-run")
            else:
                print("Ingen podcast- eller indbakkefiler blev ændret. Tilføj --apply for at klargøre nye episoder.")
        elif args.command == "remove-source":
            if not args.confirm:
                raise ValidationError("Tilføj --confirm for at fjerne kilden og dens udtræk")
            kb.remove_source(args.source_id)
            print(f"Fjernede kilde og tilknyttede udtræk: {args.source_id}")
        elif args.command == "prepare":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            count = write_tasks(kb, args.output, args.all, preferences, dict(args.approve_source))
            print(f"Skrev {count} opgave(r) til {args.output}")
        elif args.command == "prepare-ai":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            root = Path(__file__).resolve().parents[2]
            written = write_ai_package(
                kb, args.output_dir, root / "schemas" / "extraction-v0.1.schema.json",
                args.all, preferences, dict(args.approve_source),
            )
            print(f"AI-pakke klar med {len(written)} opgave(r): {args.output_dir.resolve()}")
            print(f"Start her: {(args.output_dir / 'START-HER.md').resolve()}")
        elif args.command == "openai-status":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            api_settings = preferences.get("openai", {})
            model = str(api_settings.get("model", DEFAULT_MODEL))
            api = openai_status(kb, args.incoming)
            print("OpenAI API-status")
            print(f"Model: {model}")
            if api["key_configured"]:
                print(f"API-nøgle: konfigureret ({api['key_origin']}); selve nøglen vises aldrig")
            else:
                print("API-nøgle: mangler")
            print(f"Ubehandlede kilder: {api['unprocessed']}")
            print(f"Allerede i AI-indlæsningskø: {api['pending']}")
            print(f"Klar til API: {api['ready']}")
            print(f"Afventer kildepolitik eller engangsgodkendelse: {api['policy_waiting']}")
        elif args.command == "mistral-status":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            api_settings = preferences.get("mistral", {})
            model = str(api_settings.get("model", DEFAULT_MISTRAL_MODEL))
            api = mistral_status(kb, args.incoming)
            print("Mistral API-status")
            print(f"Model: {model}")
            if api["key_configured"]:
                print(f"API-nøgle: konfigureret ({api['key_origin']}); selve nøglen vises aldrig")
            else:
                print("API-nøgle: mangler")
            print(f"Ubehandlede kilder: {api['unprocessed']}")
            print(f"Allerede i AI-indlæsningskø: {api['pending']}")
            print(f"Klar til API: {api['ready']}")
            print(f"Afventer kildepolitik eller engangsgodkendelse: {api['policy_waiting']}")
            if args.verify:
                verification = verify_mistral_access(model)
                print(f"API-forbindelse: godkendt; {verification['models']} model-ID'er tilgængelige")
                if verification["model_available"]:
                    print(f"Standardmodel: tilgængelig ({model})")
                else:
                    print(f"Standardmodel: ikke fundet for denne nøgle ({model})")
                    return 2
        elif args.command == "mistral-jobs":
            jobs = kb.ai_jobs(args.limit)
            if not jobs:
                print("Ingen Mistral-job endnu.")
            for job in jobs:
                _print_mistral_job(job)
        elif args.command == "mistral-job-create":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            model = str(preferences.get("mistral", {}).get("model", DEFAULT_MISTRAL_MODEL))
            job = create_mistral_job(
                kb, args.incoming, limit=args.limit, model=model,
                cost_limit_usd=args.cost_limit, approvals=dict(args.approve_source),
            )
            print("Mistral-jobkladde oprettet. Ingen tekst er sendt.")
            print(
                f"Prissats {PRICING_VERSION}: input USD {INPUT_USD_PER_MILLION_TOKENS:.2f}/M, "
                f"output USD {OUTPUT_USD_PER_MILLION_TOKENS:.2f}/M"
            )
            _print_mistral_job(job)
            print(f"Kontrollér kilder og beløb, og bekræft særskilt med: .\\run.cmd mistral-job-confirm {job['id']}")
        elif args.command == "mistral-job-confirm":
            job = kb.ai_job(args.job_id)
            _print_mistral_job(job)
            kb.confirm_ai_job(args.job_id)
            print("Jobbet er bekræftet, men endnu ikke sendt.")
            print(f"Kør med: .\\run.cmd mistral-job-run {args.job_id} --apply")
        elif args.command == "mistral-job-run":
            job = kb.ai_job(args.job_id)
            _print_mistral_job(job)
            if not args.apply:
                print("Ingen tekst blev sendt. Tilføj --apply for at køre det bekræftede job.")
            else:
                preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
                root = Path(__file__).resolve().parents[2]
                result = execute_mistral_job(
                    kb, args.job_id, root / "schemas" / "extraction-v0.1.schema.json",
                    args.incoming, args.audit_dir, preferences=preferences,
                    retry_source_ids=args.retry_source or None,
                )
                _print_mistral_job(result)
                print("Validerede svar ligger i indlæsningskøen og er ikke menneskeligt godkendt.")
        elif args.command == "run-mistral":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            api_settings = preferences.get("mistral", {})
            model = str(args.model or api_settings.get("model", DEFAULT_MISTRAL_MODEL))
            max_output_tokens = (
                args.max_output_tokens
                if args.max_output_tokens is not None
                else api_settings.get("max_output_tokens", DEFAULT_MISTRAL_MAX_OUTPUT_TOKENS)
            )
            timeout_seconds = (
                args.timeout_seconds
                if args.timeout_seconds is not None
                else api_settings.get("timeout_seconds", DEFAULT_MISTRAL_TIMEOUT_SECONDS)
            )
            temperature = (
                args.temperature
                if args.temperature is not None
                else api_settings.get("temperature", DEFAULT_MISTRAL_TEMPERATURE)
            )
            tasks = plan_openai_extractions(kb, args.incoming, args.limit, dict(args.approve_source))
            print("ANVEND – Mistral API" if args.apply else "FORHÅNDSVISNING – Mistral API")
            print(f"Model: {model}")
            print(f"Maksimalt antal kilder: {args.limit}")
            print(f"Klar i denne kørsel: {len(tasks)}")
            for task in tasks:
                print(
                    f"  KLAR: {task.source_id} | {task.title} | "
                    f"ca. {task.estimated_input_tokens:,} input-tokens"
                )
            if not args.apply:
                print("Ingen kildetekst blev sendt, og der blev ikke brugt API-kredit.")
                print("Tilføj --apply for at sende de viste kilder.")
            else:
                root = Path(__file__).resolve().parents[2]
                result = run_mistral_extractions(
                    kb,
                    root / "schemas" / "extraction-v0.1.schema.json",
                    args.incoming,
                    args.audit_dir,
                    preferences,
                    model,
                    max_output_tokens,
                    timeout_seconds,
                    temperature,
                    args.limit,
                    approvals=dict(args.approve_source),
                )
                print(f"Sendte og validerede: {result['sent']} af {result['planned']}")
                for path in result["files"]:
                    print(f"  AI-SVAR: {path}")
                if result["usage"]:
                    usage = ", ".join(f"{name}={value}" for name, value in sorted(result["usage"].items()))
                    print(f"API-forbrug rapporteret af Mistral: {usage}")
                for error in result["errors"]:
                    print(f"  FEJL {error['source_id']}: {error['error']}")
                if result["errors"]:
                    return 2
                if result["sent"]:
                    print("Svarene er kun lagt i indlæsningskøen og er ikke godkendt.")
                    print("Næste kontrol: .\\run.cmd process-ai --dry-run")
        elif args.command == "run-ai":
            preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
            api_settings = preferences.get("openai", {})
            model = str(args.model or api_settings.get("model", DEFAULT_MODEL))
            reasoning_effort = str(
                args.reasoning_effort
                or api_settings.get("reasoning_effort", DEFAULT_REASONING_EFFORT)
            )
            max_output_tokens = (
                args.max_output_tokens
                if args.max_output_tokens is not None
                else api_settings.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)
            )
            timeout_seconds = (
                args.timeout_seconds
                if args.timeout_seconds is not None
                else api_settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
            )
            tasks = plan_openai_extractions(kb, args.incoming, args.limit, dict(args.approve_source))
            print("ANVEND – OpenAI API" if args.apply else "FORHÅNDSVISNING – OpenAI API")
            print(f"Model: {model}")
            print(f"Maksimalt antal kilder: {args.limit}")
            print(f"Klar i denne kørsel: {len(tasks)}")
            for task in tasks:
                print(
                    f"  KLAR: {task.source_id} | {task.title} | "
                    f"ca. {task.estimated_input_tokens:,} input-tokens"
                )
            if not args.apply:
                print("Ingen kildetekst blev sendt, og der blev ikke brugt API-kredit.")
                print("Tilføj --apply for at sende de viste kilder.")
            else:
                root = Path(__file__).resolve().parents[2]
                result = run_openai_extractions(
                    kb,
                    root / "schemas" / "extraction-v0.1.schema.json",
                    args.incoming,
                    args.audit_dir,
                    preferences,
                    model,
                    reasoning_effort,
                    max_output_tokens,
                    timeout_seconds,
                    args.limit,
                    approvals=dict(args.approve_source),
                )
                print(f"Sendte og validerede: {result['sent']} af {result['planned']}")
                for path in result["files"]:
                    print(f"  AI-SVAR: {path}")
                if result["usage"]:
                    usage = ", ".join(f"{name}={value}" for name, value in sorted(result["usage"].items()))
                    print(f"API-forbrug rapporteret af OpenAI: {usage}")
                for error in result["errors"]:
                    print(f"  FEJL {error['source_id']}: {error['error']}")
                if result["errors"]:
                    return 2
                if result["sent"]:
                    print("Svarene er kun lagt i indlæsningskøen og er ikke godkendt.")
                    print("Næste kontrol: .\\run.cmd process-ai --dry-run")
        elif args.command == "process-ai":
            result = process_ai_inbox(kb, args.incoming, args.archive, args.dry_run)
            label = "Validerede" if args.dry_run else "Indlæste"
            print(f"{label} {result['claims']} udsagn fra {result['runs']} udtræk i {result['files']} fil(er)")
            if result["promotional_filtered"]:
                print(f"Frasorterede {result['promotional_filtered']} genkendelige reklame-/sponsorudsagn")
            if not args.dry_run and result["files"]:
                preferences = json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config.exists() else {}
                write_report(kb, Path("output/rapport.md"), True, preferences)
                write_report(kb, Path("output/godkendt-rapport.md"), False, preferences)
                write_dashboard(kb, Path("output/kontroloversigt.html"))
                write_export(kb, Path("output/knowledgebase.jsonl"))
                backup_result = kb.backup_database(Path("backups"))
                print(f"Arkiverede {len(result['archived'])} svarfil(er) i {args.archive}")
                print("Rapport, kontroloverblik og vidensbase er opdateret")
                print(f"Verificeret backup: {backup_result['path']}")
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
            if args.approved_only and args.status:
                raise ValidationError("Brug enten --approved-only eller --status, ikke begge")
            include_pending = preferences.get("report", {}).get("include_pending", True)
            if args.approved_only:
                include_pending = False
            statuses = set(args.status) if args.status else None
            count = write_report(kb, args.output, bool(include_pending), preferences, statuses)
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
    except (ValidationError, FileNotFoundError, KeyError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"Fejl: {exc}", file=sys.stderr)
        return 2
