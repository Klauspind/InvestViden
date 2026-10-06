from __future__ import annotations

import copy
import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .repository import KnowledgeBase, file_sha256, read_extractions
from .content_quality import is_promotional_noise
from .validation import ValidationError, validate_extraction


TIMESTAMP_LINE = re.compile(
    r"^\[(?P<start>\d{2}:\d{2}:\d{2})[–-](?P<end>\d{2}:\d{2}:\d{2})\]\s?.*$"
)
LOCAL_EVIDENCE_PROVIDERS = {"mistral", "openai"}


def _archive_target(path: Path, archive_dir: Path) -> Path:
    target = archive_dir / path.name
    if not target.exists():
        return target
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    digest = file_sha256(path)[:8]
    return archive_dir / f"{path.stem}-{stamp}-{digest}{path.suffix.lower()}"


def _timestamp_seconds(value: str) -> int | None:
    match = re.fullmatch(r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})", value.strip())
    if not match:
        return None
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second"))
    if minute > 59 or second > 59:
        return None
    return hour * 3600 + minute * 60 + second


def _local_timestamp_excerpt(text: str, start_ref: str | None, end_ref: str | None) -> str | None:
    if not start_ref or not end_ref:
        return None
    start = _timestamp_seconds(str(start_ref))
    end = _timestamp_seconds(str(end_ref))
    if start is None or end is None or end < start:
        return None

    selected: list[str] = []
    for line in text.splitlines():
        match = TIMESTAMP_LINE.match(line.strip())
        if not match:
            continue
        line_start = _timestamp_seconds(match.group("start"))
        line_end = _timestamp_seconds(match.group("end"))
        if line_start is None or line_end is None:
            continue
        if line_end >= start and line_start <= end:
            selected.append(line)
    excerpt = "\n".join(selected).strip()
    return excerpt or None


def _prepare_local_evidence(kb: KnowledgeBase, extraction: dict) -> tuple[dict, int, int]:
    """Replace AI podcast excerpts with deterministic local transcript passages.

    The incoming AI response is never rewritten on disk. The returned copy is used
    only for database ingestion, so the archived response preserves the model's raw
    output while active review uses source-derived evidence.
    """
    prepared = copy.deepcopy(extraction)
    if str(prepared.get("provider") or "") not in LOCAL_EVIDENCE_PROVIDERS:
        return prepared, 0, 0

    source = kb.conn.execute(
        "SELECT source_type, stored_path, sha256 FROM source_versions WHERE id=?",
        (prepared["source_id"],),
    ).fetchone()
    if not source or source["source_type"] != "podcast_transcript":
        return prepared, 0, 0

    path = Path(str(source["stored_path"]))
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"Kildekopien kunne ikke læses til lokal evidens: {prepared['source_id']}") from exc
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValidationError(f"Kildekopiens SHA-256 er ændret: {prepared['source_id']}")
    text = raw.decode("utf-8-sig", errors="replace")

    derived = 0
    missing = 0
    for claim in prepared.get("claims", []):
        evidence = claim.get("evidence") if isinstance(claim, dict) else None
        if not isinstance(evidence, dict):
            missing += 1
            continue
        excerpt = _local_timestamp_excerpt(text, evidence.get("start_ref"), evidence.get("end_ref"))
        if excerpt:
            evidence["excerpt"] = excerpt
            derived += 1
        else:
            missing += 1
    return prepared, derived, missing


def process_ai_inbox(
    kb: KnowledgeBase,
    incoming_dir: Path,
    archive_dir: Path,
    dry_run: bool = False,
) -> dict:
    incoming_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path for path in incoming_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
    )
    parsed: list[tuple[Path, dict]] = []
    local_evidence_derived = 0
    local_evidence_missing = 0
    for path in files:
        extractions = list(read_extractions(path))
        if not extractions:
            raise ValidationError(f"Tom AI-svarfil: {path}")
        for extraction in extractions:
            validate_extraction(extraction)
            source_id = extraction["source_id"]
            known = kb.conn.execute(
                "SELECT 1 FROM source_versions WHERE id=?", (source_id,)
            ).fetchone()
            if not known:
                raise ValidationError(f"Ukendt source_id i {path.name}: {source_id}")
            prepared, derived, missing = _prepare_local_evidence(kb, extraction)
            validate_extraction(prepared)
            local_evidence_derived += derived
            local_evidence_missing += missing
            parsed.append((path, prepared))

    promotional_filtered = sum(
        is_promotional_noise(claim["summary"])
        for _, extraction in parsed
        for claim in extraction["claims"]
    )
    result = {
        "files": len(files),
        "runs": len(parsed),
        "claims": sum(len(extraction["claims"]) for _, extraction in parsed) - promotional_filtered,
        "promotional_filtered": promotional_filtered,
        "local_evidence_derived": local_evidence_derived,
        "local_evidence_missing": local_evidence_missing,
        "archived": [],
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    imported_claims = 0
    for _, extraction in parsed:
        _, count = kb.ingest(extraction)
        imported_claims += count
    result["claims"] = imported_claims
    for path in files:
        target = _archive_target(path, archive_dir)
        shutil.move(str(path), str(target))
        result["archived"].append(target)
    return result
