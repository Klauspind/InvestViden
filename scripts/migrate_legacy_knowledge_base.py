"""Migrér den gamle knowledge_base.json til InvestKB 0.1.

Legacy-filen bevares som én originalkilde. Investeringsudsagn konverteres til
det nuværende extraction-format og markeres som usikre, indtil de er gennemset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.repository import KnowledgeBase  # noqa: E402
from investkb.validation import validate_extraction  # noqa: E402


def text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (text(part) for part in value) if item]


def sentiment(value: Any) -> str:
    normalized = (text(value) or "").lower()
    return {
        "bullish": "positive",
        "bearish": "negative",
        "positive": "positive",
        "negative": "negative",
        "neutral": "neutral",
        "mixed": "mixed",
    }.get(normalized, "unclear")


def horizon(value: Any) -> str:
    normalized = (text(value) or "").lower().replace("-", "_").replace(" ", "_")
    return {
        "short": "short_term",
        "short_term": "short_term",
        "medium": "medium_term",
        "medium_term": "medium_term",
        "long": "long_term",
        "long_term": "long_term",
    }.get(normalized, "unspecified")


def stable_id(section: str, *parts: Any) -> str:
    basis = json.dumps([section, *parts], ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]
    return f"claim-legacy-{digest}"


def speaker(value: Any) -> str | None:
    if isinstance(value, list):
        names = strings(value)
        return ", ".join(names) if names else None
    return text(value)


def reference(*parts: Any) -> str:
    return " | ".join(item for item in (text(part) for part in parts) if item) or "legacy knowledge base"


def unique_companies(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for company in companies:
        name = text(company.get("name"))
        if not name:
            continue
        normalized = " ".join(name.casefold().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(company)
    return result


def claim(
    *,
    claim_id: str,
    claim_type: str,
    summary: Any,
    speaker_name: Any = None,
    sentiment_value: Any = None,
    time_horizon: Any = None,
    confidence: float = 0.6,
    companies: list[dict[str, Any]] | None = None,
    themes: list[str] | None = None,
    thesis: list[str] | None = None,
    risks: list[str] | None = None,
    catalysts: list[str] | None = None,
    conditions: list[str] | None = None,
    evidence_excerpt: Any = None,
    evidence_ref: Any = None,
) -> dict[str, Any] | None:
    summary_text = text(summary)
    if not summary_text:
        return None
    points = (thesis or []) + (risks or []) + (catalysts or []) + (conditions or [])
    depth = "detailed" if len(points) >= 4 or len(summary_text) >= 500 else "moderate" if points else "brief"
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "summary": summary_text,
        "speaker": speaker(speaker_name),
        "sentiment": sentiment(sentiment_value),
        "action": "none",
        "time_horizon": horizon(time_horizon),
        "discussion_depth": depth,
        "confidence": confidence,
        "review_status": "uncertain",
        "companies": unique_companies(companies or []),
        "themes": list(dict.fromkeys(strings(themes or []))),
        "thesis": strings(thesis or []),
        "risks": strings(risks or []),
        "catalysts": strings(catalysts or []),
        "conditions": strings(conditions or []),
        "evidence": {
            "excerpt": text(evidence_excerpt) or summary_text,
            "start_ref": text(evidence_ref) or "legacy knowledge base",
            "end_ref": None,
        },
    }


def company_claims(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for legacy_key, company_data in data.get("companies", {}).items():
        if not isinstance(company_data, dict):
            continue
        name = text(company_data.get("name")) or text(legacy_key)
        if not name:
            continue
        company = {"name": name, "ticker": None, "role": "primary"}
        sector = text(company_data.get("sector"))
        for index, mention in enumerate(company_data.get("mentions", [])):
            if not isinstance(mention, dict):
                continue
            context = text(mention.get("context"))
            item = claim(
                claim_id=stable_id("company", legacy_key, index, mention),
                claim_type="company_view" if context else "mention",
                summary=context or f"{name} er omtalt i legacy-vidensbasen.",
                speaker_name=mention.get("speakers"),
                sentiment_value=mention.get("sentiment"),
                confidence=0.45 if mention.get("_quality") == "low" else 0.62,
                companies=[company],
                themes=[sector] if sector else [],
                thesis=mention.get("key_points", []),
                evidence_excerpt=context,
                evidence_ref=reference(mention.get("date"), mention.get("podcast"), mention.get("source")),
            )
            if item:
                yield item
        consensus = text(company_data.get("consensus_trend"))
        if consensus:
            item = claim(
                claim_id=stable_id("company-consensus", legacy_key, consensus),
                claim_type="company_view",
                summary=consensus,
                confidence=0.5,
                companies=[company],
                themes=[sector] if sector else [],
                evidence_ref="legacy aggregate: consensus_trend",
            )
            if item:
                yield item


def theme_claims(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for legacy_key, theme_data in data.get("themes", {}).items():
        if not isinstance(theme_data, dict):
            continue
        theme_name = text(theme_data.get("name")) or text(legacy_key)
        if not theme_name:
            continue
        evolution = theme_data.get("evolution", [])
        if isinstance(evolution, list) and evolution:
            for index, entry in enumerate(evolution):
                if not isinstance(entry, dict):
                    continue
                related = []
                for company_name in strings(entry.get("related_companies", [])):
                    related.append({"name": company_name, "ticker": None, "role": "discussed"})
                item = claim(
                    claim_id=stable_id("theme", legacy_key, index, entry),
                    claim_type="theme",
                    summary=entry.get("summary"),
                    confidence=0.6,
                    companies=related,
                    themes=[theme_name],
                    evidence_ref=reference(entry.get("date"), "legacy theme evolution"),
                )
                if item:
                    yield item
        else:
            item = claim(
                claim_id=stable_id("theme-description", legacy_key, theme_data.get("description")),
                claim_type="theme",
                summary=theme_data.get("description"),
                confidence=0.55,
                themes=[theme_name],
                evidence_ref=reference(theme_data.get("first_mentioned"), theme_data.get("last_mentioned")),
            )
            if item:
                yield item


def market_claims(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for index, entry in enumerate(data.get("market_conditions", [])):
        if not isinstance(entry, dict):
            continue
        factors = strings(entry.get("key_factors", []))
        macro = strings(entry.get("macro_data", []))
        summary = text(entry.get("summary")) or "; ".join(factors + macro)
        item = claim(
            claim_id=stable_id("market", index, entry),
            claim_type="macroeconomic",
            summary=summary,
            sentiment_value=entry.get("sentiment"),
            confidence=0.35 if entry.get("_quality") == "low" or entry.get("_needs_reprocessing") else 0.6,
            themes=["Markedsforhold"],
            thesis=factors + macro,
            evidence_ref=reference(entry.get("date"), entry.get("source")),
        )
        if item:
            yield item


def prediction_claims(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    confidence_map = {"high": 0.72, "medium": 0.6, "low": 0.45}
    for index, entry in enumerate(data.get("expert_predictions", [])):
        if not isinstance(entry, dict):
            continue
        item = claim(
            claim_id=stable_id("prediction", index, entry),
            claim_type="forecast",
            summary=entry.get("prediction"),
            speaker_name=entry.get("speaker"),
            time_horizon=entry.get("timeframe"),
            confidence=confidence_map.get((text(entry.get("confidence")) or "").lower(), 0.55),
            themes=entry.get("tags", []),
            evidence_ref=reference(entry.get("date"), "legacy expert prediction"),
        )
        if item:
            yield item


def strategy_claims(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for index, entry in enumerate(data.get("investment_strategies", [])):
        if not isinstance(entry, dict):
            continue
        name = text(entry.get("name"))
        summary = text(entry.get("summary"))
        combined = f"{name}: {summary}" if name and summary else name or summary
        item = claim(
            claim_id=stable_id("strategy", index, entry),
            claim_type="theme",
            summary=combined,
            speaker_name=entry.get("described_by"),
            confidence=0.58,
            themes=["Investeringsstrategi"],
            conditions=[entry.get("suitable_for")] if text(entry.get("suitable_for")) else [],
            evidence_ref=reference(entry.get("date"), "legacy investment strategy"),
        )
        if item:
            yield item


def convert(data: dict[str, Any], source_id: str) -> tuple[dict[str, Any], dict[str, int]]:
    groups = {
        "company_mentions": list(company_claims(data)),
        "theme_developments": list(theme_claims(data)),
        "market_conditions": list(market_claims(data)),
        "expert_predictions": list(prediction_claims(data)),
        "investment_strategies": list(strategy_claims(data)),
    }
    unique: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for items in groups.values():
        for item in items:
            key = (item["claim_type"], item["summary"].strip(), item.get("speaker"))
            unique.setdefault(key, item)
    extraction = {
        "schema_version": "0.1",
        "source_id": source_id,
        "provider": "legacy-knowledge-base-migration",
        "model": None,
        "extracted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "claims": list(unique.values()),
    }
    validate_extraction(extraction)
    counts = {name: len(items) for name, items in groups.items()}
    counts["unique_claims"] = len(unique)
    counts["duplicates_skipped"] = sum(len(items) for items in groups.values()) - len(unique)
    return extraction, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_json", type=Path)
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "knowledgebase.sqlite")
    parser.add_argument("--source-store", type=Path, default=ROOT / "data" / "sources")
    parser.add_argument("--output", type=Path, default=ROOT / "extractions" / "legacy-knowledge-base.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.legacy_json.read_text(encoding="utf-8-sig"))
    if args.dry_run:
        extraction, counts = convert(data, "dry-run-source")
        print(json.dumps({**counts, "valid": bool(extraction)}, ensure_ascii=False, indent=2))
        return 0

    with KnowledgeBase(args.db) as kb:
        source_id, source_created = kb.import_source(
            args.legacy_json,
            source_type="other",
            title="Legacy knowledge_base v3.0",
            publisher="Millionærklubben, Nordnet m.fl.",
            published_at=text(data.get("_meta", {}).get("last_updated")),
            source_store=args.source_store,
        )
        extraction, counts = convert(data, source_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run_id, ingested = kb.ingest(extraction)
    result = {
        **counts,
        "source_id": source_id,
        "source_created": source_created,
        "run_id": run_id,
        "ingested": ingested,
        "output": str(args.output.resolve()),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
