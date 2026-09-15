"""Local evidence checks shared by the review UI and write operations."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def assess_evidence(item: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    blockers: list[str] = []
    if not any(str(item.get(key) or "").strip() for key in ("excerpt", "start_ref", "end_ref")):
        blockers.append("Udsagnet kan ikke godkendes uden registreret kildeevidens.")
    if item.get("source_archived_at") or item.get("version_archived_at") or not item.get("source_is_current", 1):
        blockers.append("Kildeversionen er arkiveret eller erstattet og kan ikke give aktiv viden.")

    published = str(item.get("published_at") or "")[:10]
    dates = sorted(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", " ".join(
        str(item.get(key) or "") for key in ("start_ref", "end_ref")
    ))))
    if published and dates and any(date != published for date in dates):
        issues.append(
            f"Datouoverensstemmelse: Den registrerede kildedato er {published}, "
            f"mens evidensreferencen angiver {', '.join(dates)}. "
            "Datoerne er ikke automatisk den samme hændelse eller udsagnsdato."
        )

    if item.get("dataset") == "legacy":
        path = Path(str(item.get("stored_path") or ""))
        aggregate = (
            item.get("provider") == "legacy-knowledge-base-migration"
            or path.suffix.lower() in {".json", ".jsonl"}
            or "knowledge_base" in str(item.get("source_title") or "").lower()
        )
        if aggregate:
            blockers.append(
                "Evidensen henviser til en legacy-samlefil, ikke en verificeret originalpassage. "
                "Samlefilens dato er ikke dokumentation for udsagnets dato."
            )
        else:
            try:
                if path.stat().st_size > 20 * 1024 * 1024:
                    raise OSError("Kildekopien er for stor til lokal evidenskontrol")
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != item.get("source_sha256"):
                    blockers.append("Kildekopiens hash stemmer ikke med den registrerede kildeversion.")
                excerpt = str(item.get("excerpt") or "").strip()
                if not excerpt or excerpt not in content.decode("utf-8-sig", errors="replace"):
                    blockers.append("Et ordret evidenscitat kunne ikke genfindes i kildekopien.")
            except OSError:
                blockers.append("Den registrerede kildekopi kunne ikke læses til evidenskontrol.")
        if issues:
            blockers.append("Datoforskellen skal afklares mod originalkilden før godkendelse.")
    return {"can_approve": not blockers, "issues": issues + blockers}
