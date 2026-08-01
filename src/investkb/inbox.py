from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .repository import KnowledgeBase, file_sha256, slug


SOURCE_FOLDERS = {
    "transskriptioner": "podcast_transcript",
    "rapporter": "report",
    "nyhedsbreve": "newsletter",
    "andre_kilder": "other",
}
SUPPORTED_SUFFIXES = {".txt", ".md"}
DATE_PREFIX = re.compile(r"^(?P<year>20\d{2})[-_](?P<month>\d{2})[-_](?P<day>\d{2})(?:[ _-]+)?")


@dataclass(frozen=True)
class Candidate:
    path: Path
    sha256: str
    source_type: str
    title: str
    publisher: str | None
    published_at: str | None
    language: str
    folder_label: str | None


def _mapped(mapping: dict[str, Any], key: str, fallback: str) -> str:
    folded = key.casefold()
    for configured, value in mapping.items():
        if configured.casefold() == folded:
            return str(value)
    return fallback


def _date_and_title(path: Path) -> tuple[str | None, str]:
    match = DATE_PREFIX.match(path.stem)
    if not match:
        return None, path.stem.strip()
    raw = f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
    try:
        published_at = date.fromisoformat(raw).isoformat()
    except ValueError:
        return None, path.stem.strip()
    title = path.stem[match.end():].strip(" _-") or path.stem
    return published_at, title


def _candidate(path: Path, inbox_root: Path, settings: dict[str, Any]) -> Candidate | None:
    relative = path.relative_to(inbox_root)
    if len(relative.parts) < 2:
        return None
    source_type = SOURCE_FOLDERS.get(relative.parts[0].casefold())
    if not source_type:
        return None
    published_at, title = _date_and_title(path)
    folder_label = relative.parts[1] if source_type == "podcast_transcript" and len(relative.parts) >= 3 else None
    inbox_settings = settings.get("inbox", {})
    if folder_label:
        publisher = _mapped(inbox_settings.get("podcast_publishers", {}), folder_label, folder_label)
        language = _mapped(inbox_settings.get("podcast_languages", {}), folder_label, "da")
    else:
        publisher = None
        language = "da"
    return Candidate(
        path=path,
        sha256=file_sha256(path),
        source_type=source_type,
        title=title,
        publisher=publisher,
        published_at=published_at,
        language=language,
        folder_label=folder_label,
    )


def _canonical(candidates: list[Candidate]) -> Candidate:
    def score(item: Candidate) -> tuple[int, int, str]:
        folder_in_title = bool(item.folder_label and slug(item.folder_label) in slug(item.path.stem))
        return (-int(folder_in_title), len(item.path.parts), str(item.path).casefold())

    return sorted(candidates, key=score)[0]


def scan_inbox(
    kb: KnowledgeBase,
    inbox_root: Path,
    settings: dict[str, Any] | None = None,
    dry_run: bool = False,
    source_store: Path | str = "data/sources",
) -> dict[str, Any]:
    inbox_root = inbox_root.resolve()
    if not inbox_root.is_dir():
        raise FileNotFoundError(inbox_root)
    settings = settings or {}
    candidates: list[Candidate] = []
    errors: list[str] = []
    for path in sorted(inbox_root.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep" or path.suffix.casefold() not in SUPPORTED_SUFFIXES:
            continue
        try:
            item = _candidate(path, inbox_root, settings)
            if item:
                candidates.append(item)
        except OSError as exc:
            errors.append(f"{path}: {exc}")

    by_hash: dict[str, list[Candidate]] = {}
    for item in candidates:
        by_hash.setdefault(item.sha256, []).append(item)

    report: dict[str, Any] = {
        "candidates": len(candidates),
        "unique": len(by_hash),
        "new": 0,
        "existing": 0,
        "duplicate_locations": [],
        "imports": [],
        "errors": errors,
        "dry_run": dry_run,
    }
    for content_hash, same_content in sorted(by_hash.items()):
        chosen = _canonical(same_content)
        for duplicate in same_content:
            if duplicate.path != chosen.path:
                report["duplicate_locations"].append({
                    "sha256": content_hash,
                    "kept": str(chosen.path),
                    "duplicate": str(duplicate.path),
                })
        existing = kb.source_by_hash(content_hash)
        if existing:
            report["existing"] += 1
            continue
        report["new"] += 1
        if dry_run:
            report["imports"].append({"path": str(chosen.path), "source_id": None, "title": chosen.title})
            continue
        try:
            source_id, _ = kb.import_source(
                chosen.path,
                chosen.source_type,
                chosen.title,
                chosen.publisher,
                chosen.published_at,
                chosen.language,
                source_store,
            )
            report["imports"].append({"path": str(chosen.path), "source_id": source_id, "title": chosen.title})
        except (OSError, ValueError) as exc:
            report["errors"].append(f"{chosen.path}: {exc}")
    return report

