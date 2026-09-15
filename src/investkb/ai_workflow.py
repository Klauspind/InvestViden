from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .repository import KnowledgeBase, file_sha256, read_extractions
from .content_quality import is_promotional_noise
from .validation import ValidationError, validate_extraction


def _archive_target(path: Path, archive_dir: Path) -> Path:
    target = archive_dir / path.name
    if not target.exists():
        return target
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    digest = file_sha256(path)[:8]
    return archive_dir / f"{path.stem}-{stamp}-{digest}{path.suffix.lower()}"


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
            parsed.append((path, extraction))

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
