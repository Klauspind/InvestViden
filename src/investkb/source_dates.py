"""Read-only publication-date labels for source selection and job history."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any


def _publication_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].+)?", raw):
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def source_date(source: dict[str, Any]) -> tuple[date | None, str]:
    """Return a sortable registered date and a label; never use import timestamps.

    Filename hints deliberately remain unsortable as publication dates.
    No original file, sidecar or remote service is opened.
    """
    published = _publication_date(source.get("published_at"))
    if published:
        return published, f"Udgivet: {published:%d.%m.%Y}"
    if source.get("source_type") == "podcast_transcript":
        try:
            metadata = json.loads(source.get("provenance_json") or "{}")
        except (ValueError, TypeError):
            metadata = {}
        if isinstance(metadata, dict) and metadata.get("kind") == "investviden_podcast_source":
            episode = metadata.get("episode")
            published = _publication_date(episode.get("published_at")) if isinstance(episode, dict) else None
            if published:
                return published, f"Udgivet: {published:%d.%m.%Y} (registreret provenance)"
        # Handle both Windows and POSIX paths while running on either platform.
        filename = re.split(r"[/\\]", str(source.get("original_path") or ""))[-1]
        match = re.match(r"^(20\d{2})([-_])(\d{2})\2(\d{2})(?=$|[ ._-])", filename)
        if match:
            hint = _publication_date(f"{match[1]}-{match[3]}-{match[4]}")
            if hint:
                return None, f"Udgivelsesdato ukendt · Dato fra filnavn: {hint:%d.%m.%Y} (ikke verificeret)"
    return None, "Udgivelsesdato ukendt"
