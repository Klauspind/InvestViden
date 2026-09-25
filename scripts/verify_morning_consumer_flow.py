"""Isolated morning consumer acceptance: podcast episode -> intake -> local AI draft.

This script never opens the protected active database and never executes an AI transport.
It is intended for a finished Transskribering episode JSON delivered to InvestViden.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from investkb.intake import InputRegistry, apply_input, plan_input
from investkb.mistral_jobs import DEFAULT_COST_LIMIT_USD, create_mistral_job
from investkb.podcast_sync import read_episode
from investkb.repository import KnowledgeBase, file_sha256


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def find_episode(root: Path) -> Path:
    candidates: list[Path] = []
    for path in root.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("segments"), list):
            candidates.append(path)
    require(len(candidates) == 1, "Expected exactly one episode JSON")
    return candidates[0]


def require_empty_work_dir(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.exists():
        require(resolved.is_dir(), "Work path is not a directory")
        require(not any(resolved.iterdir()), "Work directory must be new or empty")
    else:
        resolved.mkdir(parents=True)
    return resolved


def verify(episode_path: Path, work_dir: Path) -> dict[str, object]:
    work_dir = require_empty_work_dir(work_dir)
    original_hash = file_sha256(episode_path)
    episode = read_episode(episode_path)

    database = work_dir / "schema4.sqlite"
    workspace = work_dir / "workspace"
    incoming = work_dir / "incoming"

    with KnowledgeBase(database) as kb:
        kb.initialize()
        registry = InputRegistry(workspace)
        registered = registry.register(
            str(episode_path.parent),
            "podcast_transcript",
            "allow",
            episode.publisher,
            episode.language,
            "podcast_json",
        )
        plan = plan_input(kb, registered)
        require(not plan["errors"], "Input preview failed")
        selected = [
            index
            for index, item in enumerate(plan["items"])
            if item.path.resolve() == episode_path.resolve()
        ]
        require(len(selected) == 1, "Episode missing from intake preview")
        require(plan["items"][selected[0]].status == "new", "Episode is not a new source")

        imported = apply_input(kb, plan, selected, workspace)
        require(not imported["errors"], "Input apply failed")
        require(len(imported["imported"]) == 1, "Expected exactly one imported source")
        source_id = imported["imported"][0]
        require(imported.get("backup", {}).get("integrity") == "ok", "Intake backup was not verified")

        provenance = kb.conn.execute(
            "SELECT * FROM source_provenance WHERE source_id=?", (source_id,)
        ).fetchone()
        require(provenance is not None, "Missing source provenance")
        upstream = json.loads(provenance["metadata_json"])["upstream"]
        require(upstream["sha256"] == original_hash, "Episode hash was not preserved")
        if episode.derivation is not None:
            require(upstream.get("derivation") == episode.derivation, "Derivation was not preserved")
        if episode.segment_accounting is not None:
            require(
                upstream.get("segment_accounting") == episode.segment_accounting,
                "Segment accounting was not preserved",
            )

        policy = next(row for row in kb.source_policies() if row["id"] == source_id)
        require(policy["ai_permission"] == "allow", "Imported source policy is not allow")
        require(kb.external_ai_allowed(source_id, policy["sha256"]), "AI policy gate rejected allow source")

        job = create_mistral_job(
            kb,
            incoming,
            source_ids=[source_id],
            cost_limit_usd=DEFAULT_COST_LIMIT_USD,
        )
        require(job["status"] == "draft", "AI job did not remain a draft")
        require(len(job["items"]) == 1, "Expected one AI job item")
        require(job["items"][0]["source_version_id"] == source_id, "Draft references wrong source")
        require(job["items"][0]["attempt_count"] == 0, "Draft unexpectedly has an AI attempt")
        require(float(job["estimated_cost_usd"]) <= DEFAULT_COST_LIMIT_USD, "Draft exceeds cost limit")
        require(kb.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0, "Unexpected claims")
        require(not incoming.exists() or not any(incoming.iterdir()), "AI output appeared without transport")

        repeat = plan_input(kb, registered)
        matched = [item for item in repeat["items"] if item.path.resolve() == episode_path.resolve()]
        require(len(matched) == 1 and matched[0].status == "existing", "Repeat intake is not idempotent")
        require(kb.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1, "Duplicate source")

        result = {
            "schema_version": 4,
            "source_imported": True,
            "provenance_preserved": True,
            "intake_backup_integrity": "ok",
            "ai_permission": "allow",
            "ai_job_status": "draft",
            "ai_job_items": 1,
            "ai_attempts": 0,
            "estimated_cost_within_limit": True,
            "repeat_intake_status": "existing",
            "original_source_unchanged": False,
            "external_ai_calls": 0,
            "active_database_used": False,
        }

    result["original_source_unchanged"] = file_sha256(episode_path) == original_hash
    require(result["original_source_unchanged"], "Original episode changed")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(find_episode(args.episode_root), args.work_dir)
    except Exception as exc:
        # Input paths/text may be private; expose only the exception class.
        print("STOP: isolated morning consumer flow not verified (" + type(exc).__name__ + ")")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
