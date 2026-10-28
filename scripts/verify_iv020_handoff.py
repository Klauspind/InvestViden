"""Test one selected real package in a NEW isolated workspace, never active state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deliver_transskribinator_episode import ROOT, _inventory, _overlap, deliver
from run_transskribinator_consumer import inspect, run


def verify(app: Path, package: Path, test_root: Path) -> dict:
    app, package = app.resolve(strict=True), package.resolve(strict=True)
    if not test_root.is_absolute() or str(test_root).startswith(("\\\\", "//")):
        raise ValueError("Choose a new absolute local test directory")
    root = test_root.resolve()
    if any(_overlap(root, p) for p in (app, package, ROOT)):
        raise ValueError("Test directory overlaps protected files")
    # Exclusive creation is the boundary: no existing consumer database or
    # settings are opened, copied, adopted or migrated.
    root.mkdir()
    delivery, state = root / "delivery", root / "state"
    before = _inventory(package)
    preview = deliver(app, package, delivery, check=True)
    if preview["outcome"] != "ready" or delivery.exists() or state.exists():
        raise ValueError("Preview unexpectedly wrote delivery/state")
    first_delivery = deliver(app, package, delivery)
    delivered = {p.relative_to(delivery): p.read_bytes() for p in delivery.rglob("*.json")}
    second_delivery = deliver(app, package, delivery)
    check = inspect(delivery, state)
    if (not check["ok"] or state.exists() or check["delivery_episodes"] != 1
            or first_delivery["outcome"] != "delivered" or second_delivery["outcome"] != "skipped"):
        raise ValueError("Delivery/check gate failed")
    first = run(delivery, state)
    second = run(delivery, state)
    if (first["new_imported"], first["draft_jobs_created"], first["backup_integrity"],
            second["new_imported"], second["draft_jobs_created"], second["existing"]) != (1, 1, "ok", 0, 0, 1):
        raise ValueError("Import/idempotence gate failed")
    for result in (first, second):
        if (result["database_schema"] != 4 or result["database_integrity"] != "ok"
                or result["ai_attempts"] != 0 or result["claims"] != 0
                or result["external_ai_calls"] != 0):
            raise ValueError("Consumer integrity/AI gate failed")
    if before != _inventory(package) or any((delivery / p).read_bytes() != data for p, data in delivered.items()):
        raise ValueError("Input package or delivery changed")
    return {"test": "IV-020 Qt package isolated handoff", "result": "PASS",
            "first_delivered": 1, "repeat_skipped": 1, "first_imported": 1,
            "first_drafts": 1, "repeat_imported": 0, "repeat_drafts": 0,
            "repeat_existing": 1, "backup_integrity": "ok", "database_integrity": "ok",
            "package_unchanged": True, "delivery_unchanged": True,
            "external_ai_calls": 0, "active_database_used": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-app", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--test-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.producer_app, args.package, args.test_root)
    except Exception as exc:
        result = {"test": "IV-020 Qt package isolated handoff", "result": "FAIL",
                  "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
