"""Deliver complete podcasts from an explicit data root; import only on request."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deliver_transskribinator_episode import ROOT, _overlap, deliver
import run_transskribinator_consumer as consumer
from investkb.intake import _linked, plan_input
from investkb.migrations import current_schema_version
from investkb.repository import KnowledgeBase


def _packages(data: Path):
    def failed(error):
        raise error

    for parent, directories, files in os.walk(data, followlinks=False, onerror=failed):
        directories[:] = sorted(name for name in directories
                                if not name.startswith(".") and not _linked(Path(parent) / name))
        if "COMPLETE.json" in files:
            directories[:] = []
            yield Path(parent), True
        elif "manifest.json" in files or "transcript.json" in files:
            yield Path(parent), False


def _import_deliveries(delivery: Path, state: Path) -> dict:
    consumer._validate_paths(delivery, state)
    database = state / "knowledgebase.sqlite"
    # Adopt only an existing schema-4 consumer, never create a replacement for
    # a mistyped path or migrate an older database.
    if not database.is_file() or database.resolve().parent != state or _linked(database):
        raise ValueError("Existing consumer database required")
    with KnowledgeBase(database) as kb:
        if current_schema_version(kb.conn) != 4 or consumer._integrity(kb) != "ok":
            raise ValueError("Consumer database must be intact schema 4; no migration performed")
        plan = plan_input(kb, consumer._root_config(delivery))
        selected, selection = consumer.select_new_inputs(plan)
        if plan["errors"]:
            return {"ok": False, "new_imported": 0, **selection,
                    "errors": plan["errors"], "external_ai_calls": 0}
        backup = None
        if selected or consumer._sources_without_job(kb.conn):
            backup = kb.backup_database(state / "backups")
            if backup["integrity"] != "ok":
                raise ValueError("Pre-import backup failed")
    result = consumer.run(delivery, state, skip_conflicts=True)
    result["preimport_backup"] = backup or "not_needed"
    return result


def import_only(delivery_root: Path, state_root: Path) -> dict:
    """Consume existing deliveries without loading/scanning the producer."""
    delivery = delivery_root.expanduser().resolve(strict=True)
    state = state_root.expanduser().resolve()
    if _overlap(delivery, ROOT) or _overlap(state, ROOT):
        raise ValueError("Delivery and state must be outside the repository")
    result = _import_deliveries(delivery, state)
    return {"schema_version": "investviden-podcast-sync-v1", "mode": "import_only",
            "ok": result["ok"], "consumer": result, "external_ai_calls": 0}


def sync(producer_app: Path, data_root: Path, delivery_root: Path,
         state_root: Path | None = None, *, import_requested: bool = False) -> dict:
    app = producer_app.expanduser().resolve(strict=True)
    data = data_root.expanduser().resolve(strict=True)
    delivery = delivery_root.expanduser().resolve()
    if not app.is_dir() or not data.is_dir():
        raise ValueError("Choose an existing producer app and data directory")
    if any(_overlap(delivery, protected) for protected in (data, app, ROOT)):
        raise ValueError("Delivery must be separate from producer data, app and repository")
    state = state_root.expanduser().resolve() if state_root is not None else None
    if state and any(_overlap(state, protected) for protected in (data, delivery, app, ROOT)):
        raise ValueError("Consumer state must be separate from data, delivery, app and repository")
    if import_requested and state is None:
        raise ValueError("Consumer state is required for import")
    sys.path.insert(0, str(app))
    from transskribering.service import verify_package

    result = {"schema_version": "investviden-podcast-sync-v1", "ok": True,
              "new_deliveries": 0, "existing_deliveries": 0,
              "incomplete_packages": 0, "non_podcast_packages": 0,
              "rejected_packages": [], "import_requested": import_requested,
              "consumer": None, "external_ai_calls": 0}
    for package, complete in _packages(data):
        if not complete:
            result["incomplete_packages"] += 1
            continue
        try:
            canonical = verify_package(package)
            if canonical["transcription"]["profile"] != {"id": "podcast-legacy", "version": "1"}:
                result["non_podcast_packages"] += 1
                continue
            outcome = deliver(app, package, delivery)["outcome"]
            result["existing_deliveries" if outcome == "skipped" else "new_deliveries"] += 1
        except Exception as exc:
            result["rejected_packages"].append({"package": str(package.relative_to(data)),
                                                 "error": str(exc), "error_type": type(exc).__name__})
    result["ok"] = not result["rejected_packages"]
    # Valid packages may already be delivered when another package fails.
    # Nothing is overwritten; retry skips successes. Never import a failed sync.
    if import_requested and result["ok"] and delivery.is_dir() and any(delivery.rglob("*.json")):
        try:
            result["consumer"] = _import_deliveries(delivery, state)
            result["ok"] = result["consumer"]["ok"]
        except Exception as exc:
            result.update(ok=False, import_error=str(exc), error_type=type(exc).__name__)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-app", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--delivery-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--import", dest="import_requested", action="store_true")
    parser.add_argument("--import-only", action="store_true")
    args = parser.parse_args(argv)
    if args.import_only and args.state_root is None:
        parser.error("--import-only requires --state-root")
    if not args.import_only and (args.producer_app is None or args.data_root is None):
        parser.error("Delivery requires --producer-app and --data-root")
    try:
        result = import_only(args.delivery_root, args.state_root) if args.import_only else sync(
            args.producer_app, args.data_root, args.delivery_root,
            args.state_root, import_requested=args.import_requested)
    except Exception as exc:
        result = {"schema_version": "investviden-podcast-sync-v1", "ok": False,
                  "error": str(exc), "error_type": type(exc).__name__, "external_ai_calls": 0}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
