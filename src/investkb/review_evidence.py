"""Local evidence checks shared by the review UI and write operations."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


AI_EVIDENCE_PROVIDERS = {"mistral", "openai"}
MAX_LOCAL_EVIDENCE_BYTES = 20 * 1024 * 1024


def _normalized_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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

    dataset = item.get("dataset")
    provider = str(item.get("provider") or "")
    path = Path(str(item.get("stored_path") or ""))
    legacy_aggregate = (
        dataset == "legacy"
        and (
            provider == "legacy-knowledge-base-migration"
            or path.suffix.lower() in {".json", ".jsonl"}
            or "knowledge_base" in str(item.get("source_title") or "").lower()
        )
    )

    if legacy_aggregate:
        blockers.append(
            "Evidensen henviser til en legacy-samlefil, ikke en verificeret originalpassage. "
            "Samlefilens dato er ikke dokumentation for udsagnets dato."
        )
    elif dataset == "legacy" or provider in AI_EVIDENCE_PROVIDERS:
        try:
            if path.stat().st_size > MAX_LOCAL_EVIDENCE_BYTES:
                raise OSError("Kildekopien er for stor til lokal evidenskontrol")
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != item.get("source_sha256"):
                blockers.append("Kildekopiens hash stemmer ikke med den registrerede kildeversion.")
            else:
                excerpt = str(item.get("excerpt") or "").strip()
                decoded = content.decode("utf-8-sig", errors="replace")
                if not excerpt:
                    blockers.append("Udsagnet kan ikke godkendes uden et ordret evidensuddrag.")
                elif dataset == "legacy":
                    if excerpt not in decoded:
                        blockers.append("Et ordret evidenscitat kunne ikke genfindes i kildekopien.")
                elif _normalized_whitespace(excerpt) not in _normalized_whitespace(decoded):
                    blockers.append(
                        "AI-evidensuddraget kunne ikke genfindes ordret i den hash-verificerede kildekopi. "
                        "Ret evidensen eller markér udsagnet som usikkert/afvist før aktiv viden."
                    )
        except OSError:
            blockers.append("Den registrerede kildekopi kunne ikke læses til evidenskontrol.")

    if dataset == "legacy" and issues:
        blockers.append("Datoforskellen skal afklares mod originalkilden før godkendelse.")
    return {"can_approve": not blockers, "issues": issues + blockers}
