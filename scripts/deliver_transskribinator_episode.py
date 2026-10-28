"""Explicit one-package handoff using the unchanged Transskribinator adapter.

Run with the producer's Python runtime and --producer-app pointing at its app
directory. No database, download, inference, settings or AI job is opened.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from investkb.podcast_sync import read_episode


def _overlap(left: Path, right: Path) -> bool:
    return left.is_relative_to(right) or right.is_relative_to(left)


def _inventory(package: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in package.iterdir() if p.is_file()}


def _content(path: Path) -> dict:
    # These three fields describe the adapter's temporary execution, rather
    # than episode content. Everything else, including provenance, must match.
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    source = value["source"]
    for key in ("created_at", "original_path"):
        source.pop(key, None)
    source.get("processing", {}).pop("timestamp", None)
    return value


def deliver(producer_app: Path, package: Path, output_root: Path, *, check=False) -> dict:
    app = producer_app.expanduser().resolve(strict=True)
    package = package.expanduser().resolve(strict=True)
    output = output_root.expanduser().resolve()
    if not package.is_dir() or not app.is_dir():
        raise ValueError("Choose a producer app and one complete package directory")
    if any(_overlap(output, protected) for protected in (package, app, ROOT)):
        raise ValueError("Delivery must be separate from package, app and repository")
    # The selected installed app supplies the existing versioned adapter and
    # postprocessor configuration. Do not copy or reinterpret that contract.
    sys.path.insert(0, str(app))
    from tools.podcast_delivery import deliver_one
    from transskribering.batch import batch_lock
    from transskribering.service import verify_package

    with batch_lock():
        canonical = verify_package(package)
        if canonical["transcription"]["profile"] != {"id": "podcast-legacy", "version": "1"}:
            raise ValueError("Only podcast-legacy v1 is supported")
        before = _inventory(package)
        with tempfile.TemporaryDirectory(prefix="iv020-handoff-") as temporary:
            staging = Path(temporary)
            # Stage first: even rejected dates, content or collisions never
            # leave an unusable episode in the selected delivery directory.
            with redirect_stdout(io.StringIO()):
                if deliver_one(package, staging) != "delivered":
                    raise ValueError("Adapter did not deliver the selected podcast")
            candidates = list(staging.rglob("*.json"))
            if len(candidates) != 1:
                raise ValueError("Expected exactly one episode JSON")
            candidate = candidates[0]
            episode = read_episode(candidate)
            if not episode.derivation or not episode.segment_accounting:
                raise ValueError("Missing canonical provenance or segment accounting")
            if before != _inventory(package):
                raise ValueError("Package changed during handoff")
            target = output / candidate.relative_to(staging)
            if not target.resolve().is_relative_to(output) or target.is_symlink():
                raise ValueError("Redirected delivery target")

            def existing():
                if target.is_symlink() or not target.is_file():
                    raise ValueError("Invalid delivery target")
                read_episode(target)
                if _content(target) != _content(candidate):
                    raise ValueError("Existing delivery conflicts; nothing overwritten")
                return "skipped"

            if target.exists():
                outcome = existing()
            elif check:
                outcome = "ready"
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Same-filesystem hardlink publishes atomically without a
                # replace race. Unsupported filesystems fail closed.
                fd, name = tempfile.mkstemp(prefix=".iv020-", suffix=".tmp", dir=target.parent)
                pending = Path(name)
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(candidate.read_bytes())
                        handle.flush()
                        os.fsync(handle.fileno())
                    try:
                        os.link(pending, target)
                        outcome = "delivered"
                    except FileExistsError:
                        outcome = existing()
                finally:
                    pending.unlink(missing_ok=True)
            return {"schema_version": "investviden-podcast-handoff-v1", "ok": True,
                    "mode": "check" if check else "deliver", "outcome": outcome,
                    "episodes": 1, "package_unchanged": True, "external_ai_calls": 0,
                    "database_opened": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-app", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--delivery-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = deliver(args.producer_app, args.package, args.delivery_root, check=args.check)
    except Exception as exc:
        result = {"schema_version": "investviden-podcast-handoff-v1", "ok": False,
                  "error_type": type(exc).__name__, "external_ai_calls": 0, "database_opened": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
