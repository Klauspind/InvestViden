from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

from .repository import KnowledgeBase, file_sha256, slug


RENDERER_VERSION = "investviden-timestamped-transcript/1.0"
DERIVED_FOLDERS = {"chunks", "cleaned", "compressed", "knowledge", "metadata", "quality_reports"}
DATE_PREFIX = re.compile(r"^(20\d{2})[-_](\d{2})[-_](\d{2})")


@dataclass(frozen=True)
class PodcastEpisode:
    json_path: Path
    json_sha256: str
    episode_id: str
    episode_key: str
    podcast: str
    publisher: str
    title: str
    published_at: str
    language: str
    duration_seconds: float | None
    schema_version: str
    processor: str | None
    processing_timestamp: str | None
    transcription_provider: str | None
    transcription_model: str | None
    quality_score: float | None
    quality_grade: str | None
    segments: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SyncItem:
    episode: PodcastEpisode
    target_path: Path
    sidecar_path: Path
    rendered_text: str
    rendered_sha256: str
    status: str
    detail: str | None = None


def _mapped(mapping: dict[str, Any], key: str, fallback: str) -> str:
    folded = key.casefold()
    for configured, value in mapping.items():
        if configured.casefold() == folded:
            return str(value)
    return fallback


def _safe_folder_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", value).strip(" .")
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"Ugyldigt podcastnavn: {value!r}")
    return cleaned


def _published_date(value: Any, filename: str) -> str:
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            return parsedate_to_datetime(raw).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            try:
                return date.fromisoformat(raw[:10]).isoformat()
            except ValueError:
                pass
    match = DATE_PREFIX.match(filename)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
    raise ValueError("Mangler en gyldig udgivelsesdato i source.published og filnavnet")


def _seconds(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Segmentets {field} skal være et tal")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Segmentets {field} skal være et endeligt, ikke-negativt tal")
    return result


def _timestamp(seconds: float, *, round_up: bool = False) -> str:
    total = math.ceil(seconds) if round_up else math.floor(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _clean_segment_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Segmentets text skal være tekst")
    return " ".join(value.split())


def _episode_key(podcast: str, published_at: str, episode_id: str, title: str) -> str:
    identity = episode_id.strip() or slug(title)
    return f"{slug(podcast)}|{published_at}|{identity}"


def discover_episode_jsons(source_root: Path) -> list[Path]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(source_root)
    paths: list[Path] = []
    for folder in sorted(source_root.iterdir(), key=lambda item: item.name.casefold()):
        if not folder.is_dir() or folder.name.casefold() in DERIVED_FOLDERS:
            continue
        paths.extend(sorted(folder.glob("*.json"), key=lambda item: item.name.casefold()))
    return paths


def read_episode(path: Path, settings: dict[str, Any] | None = None) -> PodcastEpisode:
    settings = settings or {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ugyldig JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Episode-JSON skal være et objekt")
    source = data.get("source")
    segments = data.get("segments")
    if not isinstance(source, dict) or not isinstance(segments, list):
        raise ValueError("Episode-JSON mangler source-objekt eller segments-liste")

    podcast = str(source.get("podcast") or path.parent.name).strip()
    if not podcast:
        raise ValueError("Podcastnavnet mangler")
    title = str(source.get("title") or path.stem).strip()
    published_at = _published_date(source.get("published"), path.name)
    language = str(source.get("language") or "da").strip() or "da"
    episode_id = str(data.get("id") or "").strip()
    processing = source.get("processing") if isinstance(source.get("processing"), dict) else {}
    transcription = data.get("transcription") if isinstance(data.get("transcription"), dict) else {}
    quality = data.get("quality") if isinstance(data.get("quality"), dict) else {}
    duration = source.get("duration_seconds")
    if duration is not None:
        duration = _seconds(duration, "source.duration_seconds")

    validated_segments: list[dict[str, Any]] = []
    previous_start = -1.0
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            raise ValueError(f"Segment {index} skal være et objekt")
        start = _seconds(segment.get("start"), "start")
        end = _seconds(segment.get("end"), "end")
        text = _clean_segment_text(segment.get("text"))
        if end < start:
            raise ValueError(f"Segment {index} slutter før det starter")
        if start < previous_start:
            raise ValueError(f"Segment {index} er ikke i kronologisk rækkefølge")
        previous_start = start
        if text:
            validated_segments.append({"start": start, "end": end, "text": text})
    if not validated_segments:
        raise ValueError("Episode-JSON indeholder ingen tekstsegmenter")

    publisher_mapping = settings.get("inbox", {}).get("podcast_publishers", {})
    publisher = _mapped(publisher_mapping, podcast, podcast)
    score = quality.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        score = None

    return PodcastEpisode(
        json_path=path.resolve(),
        json_sha256=file_sha256(path),
        episode_id=episode_id,
        episode_key=_episode_key(podcast, published_at, episode_id, title),
        podcast=podcast,
        publisher=publisher,
        title=title,
        published_at=published_at,
        language=language,
        duration_seconds=float(duration) if duration is not None else None,
        schema_version=str(data.get("schema_version") or "unknown"),
        processor=str(processing.get("processor")) if processing.get("processor") else None,
        processing_timestamp=str(processing.get("timestamp")) if processing.get("timestamp") else None,
        transcription_provider=(
            str(transcription.get("provider")) if transcription.get("provider") else None
        ),
        transcription_model=str(transcription.get("model")) if transcription.get("model") else None,
        quality_score=float(score) if score is not None else None,
        quality_grade=str(quality.get("grade")) if quality.get("grade") else None,
        segments=tuple(validated_segments),
    )


def render_episode(episode: PodcastEpisode) -> str:
    duration = _timestamp(episode.duration_seconds, round_up=True) if episode.duration_seconds is not None else "ukendt"
    quality = "ukendt"
    if episode.quality_score is not None:
        quality = f"{episode.quality_score:g}"
        if episode.quality_grade:
            quality += f" ({episode.quality_grade})"
    lines = [
        episode.title,
        "=" * len(episode.title),
        "",
        f"Podcast: {episode.podcast}",
        f"Udgivet: {episode.published_at}",
        f"Sprog: {episode.language}",
        f"Episode-ID: {episode.episode_id or 'ukendt'}",
        f"Varighed: {duration}",
        f"Kvalitetsscore: {quality}",
        f"Kilde-JSON-SHA256: {episode.json_sha256}",
        f"Kildeformat: {episode.schema_version}",
        f"Transskription: {episode.transcription_provider or 'ukendt'} / {episode.transcription_model or 'ukendt'}",
        f"Efterbehandling: {episode.processor or 'ukendt'} ({episode.processing_timestamp or 'ukendt'})",
        f"InvestViden-renderer: {RENDERER_VERSION}",
        "",
        "FULD, RENSED OG TIDSKODET TRANSKRIPTION",
        "----------------------------------------",
        "",
    ]
    for segment in episode.segments:
        start = _timestamp(float(segment["start"]))
        end = _timestamp(float(segment["end"]), round_up=True)
        lines.append(f"[{start}–{end}] {segment['text']}")
    return "\n".join(lines) + "\n"


def _rendered_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _target_stem(episode: PodcastEpisode) -> str:
    stem = episode.json_path.stem.strip()
    if not DATE_PREFIX.match(stem):
        stem = f"{episode.published_at} {stem}"
    return stem


def _legacy_identity_matches(kb: KnowledgeBase, episode: PodcastEpisode) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    expected_title = slug(episode.title)
    for row in kb.podcast_sources_on_date(episode.published_at):
        if slug(str(row["publisher"] or "")) != slug(episode.publisher):
            continue
        existing_title = slug(str(row["title"] or ""))
        same_title = expected_title == existing_title
        title_contains_other = expected_title in existing_title or existing_title in expected_title
        similar_title = SequenceMatcher(None, expected_title, existing_title).ratio() >= 0.72
        if same_title or title_contains_other or similar_title:
            result.append(dict(row))
    return result


def plan_podcast_sync(
    kb: KnowledgeBase,
    source_root: Path,
    target_root: Path,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or {}
    target_root = target_root.resolve()
    items: list[SyncItem] = []
    errors: list[str] = []
    for path in discover_episode_jsons(source_root):
        try:
            episode = read_episode(path, settings)
            rendered = render_episode(episode)
            rendered_sha = _rendered_sha256(rendered)
            target = target_root / _safe_folder_name(episode.podcast) / f"{_target_stem(episode)}.txt"
            sidecar = target.with_suffix(".source.json")

            registered = kb.source_by_hash(rendered_sha)
            provenance_match = kb.source_by_episode_key(episode.episode_key)
            identity_matches = _legacy_identity_matches(kb, episode)
            if registered:
                status = "registered"
                detail = str(registered["id"])
            elif provenance_match:
                status = "existing_episode"
                detail = f"{provenance_match['id']} har en anden kilde-/tekstversion"
            elif identity_matches:
                status = "existing_episode"
                detail = ", ".join(str(row["id"]) for row in identity_matches)
            elif target.exists():
                if file_sha256(target) == rendered_sha:
                    status = "ready"
                    detail = "tidskodet tekst findes allerede i indbakken"
                else:
                    status = "target_conflict"
                    detail = "målfilen findes med andet indhold"
            else:
                status = "new"
                detail = None
            items.append(SyncItem(episode, target, sidecar, rendered, rendered_sha, status, detail))
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: {exc}")

    counts: dict[str, int] = {}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return {"source_root": str(source_root.resolve()), "target_root": str(target_root), "items": items, "counts": counts, "errors": errors}


def _sidecar(item: SyncItem) -> dict[str, Any]:
    episode = item.episode
    return {
        "schema_version": "1.0",
        "kind": "investviden_podcast_source",
        "episode_key": episode.episode_key,
        "episode": {
            "id": episode.episode_id or None,
            "podcast": episode.podcast,
            "publisher": episode.publisher,
            "title": episode.title,
            "published_at": episode.published_at,
            "language": episode.language,
            "duration_seconds": episode.duration_seconds,
        },
        "upstream": {
            "path": str(episode.json_path),
            "sha256": episode.json_sha256,
            "schema_version": episode.schema_version,
            "processor": episode.processor,
            "processing_timestamp": episode.processing_timestamp,
        },
        "render": {
            "renderer_version": RENDERER_VERSION,
            "sha256": item.rendered_sha256,
            "segment_count": len(episode.segments),
        },
    }


def _write_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if path.exists():
        raise FileExistsError(path)
    temporary.write_text(text, encoding="utf-8", newline="\n")
    try:
        if path.exists():
            raise FileExistsError(path)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def apply_podcast_sync(plan: dict[str, Any]) -> dict[str, Any]:
    written: list[str] = []
    sidecars: list[str] = []
    errors = list(plan.get("errors", []))
    for item in plan["items"]:
        if item.status not in {"new", "ready"}:
            continue
        try:
            if item.status == "new":
                _write_new(item.target_path, item.rendered_text)
                written.append(str(item.target_path))
            sidecar_text = json.dumps(_sidecar(item), ensure_ascii=False, indent=2) + "\n"
            if item.sidecar_path.exists():
                existing = item.sidecar_path.read_text(encoding="utf-8-sig")
                if json.loads(existing) != json.loads(sidecar_text):
                    raise FileExistsError(f"Sidecar findes med andet indhold: {item.sidecar_path}")
            else:
                _write_new(item.sidecar_path, sidecar_text)
                sidecars.append(str(item.sidecar_path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{item.target_path}: {exc}")
    return {"written": written, "sidecars": sidecars, "errors": errors}


def public_sync_items(items: Iterable[SyncItem]) -> list[dict[str, Any]]:
    return [
        {
            "status": item.status,
            "podcast": item.episode.podcast,
            "published_at": item.episode.published_at,
            "title": item.episode.title,
            "target": str(item.target_path),
            "detail": item.detail,
        }
        for item in items
    ]
