"""Verify a real podcast import in a disposable database, with no AI calls."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from investkb.intake import InputRegistry, apply_input, plan_input
from investkb.podcast_sync import read_episode
from investkb.repository import KnowledgeBase, file_sha256


def require(condition, message):
    if not condition:
        raise ValueError(message)


def find_episode(root: Path) -> Path:
    candidates = []
    for path in root.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and "segments" in data and "derivation" in data:
            candidates.append(path)
    require(len(candidates) == 1, "Expected exactly one derived episode")
    return candidates[0]


def verify(episode_path: Path, expected_segments=1371, expected_canonical=1373):
    original_hash = file_sha256(episode_path)
    episode = read_episode(episode_path)
    require(len(episode.segments) == expected_segments, "Unexpected segment count")
    require(episode.derivation is not None and episode.segment_accounting is not None,
            "Missing derivation or segment accounting")
    require(episode.derivation["canonical_segment_count"] == expected_canonical,
            "Unexpected canonical count")
    require(episode.json_sha256 == original_hash, "Input changed while reading")

    # No database argument exists: the active user database cannot be selected.
    with tempfile.TemporaryDirectory(prefix="investviden-derivation-accept-",
                                     dir=os.environ.get("LOCALAPPDATA")) as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        kb = KnowledgeBase(root / "fresh.sqlite")
        try:
            kb.initialize()
            registry = InputRegistry(workspace)
            registered = registry.register(str(episode_path.parent), "podcast_transcript",
                                           "local_only", "", "da", "podcast_json")
            plan = plan_input(kb, registered)
            require(not plan["errors"], "Input preview failed")
            selected = [i for i, item in enumerate(plan["items"])
                        if item.path.resolve() == episode_path.resolve()]
            require(len(selected) == 1, "Episode missing from preview")
            result = apply_input(kb, plan, selected, workspace)
            require(not result["errors"] and len(result["imported"]) == 1, "Import failed")
            row = kb.conn.execute("SELECT * FROM source_provenance").fetchone()
            require(row is not None, "Missing database provenance")
            stored = json.loads(row["metadata_json"])["upstream"]
            require(stored["sha256"] == original_hash == row["upstream_sha256"],
                    "Episode hash mismatch")
            require(stored.get("derivation") == episode.derivation,
                    "Derivation was not preserved")
            require(stored.get("segment_accounting") == episode.segment_accounting,
                    "Segment accounting was not preserved")
            again = plan_input(kb, registered)
            require(not again["errors"], "Repeat preview failed")
            matched = [item for item in again["items"]
                       if item.path.resolve() == episode_path.resolve()]
            require(len(matched) == 1 and matched[0].status == "existing",
                    "Repeat preview did not recognize the source")
            require(kb.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1,
                    "Duplicate source")
            require(kb.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0,
                    "Unexpected claims")
        finally:
            kb.close()
    require(file_sha256(episode_path) == original_hash, "Original episode changed")
    return {"input": episode.segment_accounting["input"],
            "kept": episode.segment_accounting["kept"],
            "removed": episode.segment_accounting["removed"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-root", type=Path, required=True)
    parser.add_argument("--expected-segments", type=int, default=1371)
    parser.add_argument("--expected-canonical", type=int, default=1373)
    args = parser.parse_args()
    try:
        result = verify(find_episode(args.episode_root), args.expected_segments, args.expected_canonical)
    except Exception as exc:
        # Exception text can contain private input; print only its class.
        print("STOP: isolated import not verified (" + type(exc).__name__ + ")")
        return 1
    print("PASS: one source imported into a fresh temporary database")
    print("PASS: derivation, segment accounting and episode hash stored in SQLite")
    print("PASS: repeat scan recognized the source; original episode unchanged")
    print("Segment accounting:", result)
    print("No active database, AI call or scheduled task used")
    print("Upstream hashes preserved as supplied; original media/canonical not rehashed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
