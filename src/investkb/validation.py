from __future__ import annotations

from typing import Any


CLAIM_TYPES = {"company_view", "theme", "macroeconomic", "forecast", "risk", "mention"}
SENTIMENTS = {"positive", "neutral", "negative", "mixed", "unclear"}
ACTIONS = {"owns", "buying", "hold", "reduce", "sold", "watch", "avoid", "none", "unclear"}
HORIZONS = {"short_term", "medium_term", "long_term", "unspecified"}
DEPTHS = {"brief", "moderate", "detailed"}
REVIEW_STATUSES = {"ai_extracted", "approved", "corrected", "uncertain", "rejected"}
COMPANY_ROLES = {"primary", "discussed", "comparison", "mention"}


class ValidationError(ValueError):
    pass


def _required_text(obj: dict[str, Any], key: str, where: str) -> None:
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        raise ValidationError(f"{where}.{key} skal være en ikke-tom tekst")


def _enum(obj: dict[str, Any], key: str, values: set[str], where: str) -> None:
    if obj.get(key) not in values:
        allowed = ", ".join(sorted(values))
        raise ValidationError(f"{where}.{key} har ugyldig værdi; tilladt: {allowed}")


def validate_extraction(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValidationError("Udtrækket skal være et JSON-objekt")
    _required_text(data, "schema_version", "root")
    if data["schema_version"] != "0.1":
        raise ValidationError("Kun schema_version 0.1 understøttes")
    _required_text(data, "source_id", "root")
    _required_text(data, "provider", "root")
    _required_text(data, "extracted_at", "root")
    claims = data.get("claims")
    if not isinstance(claims, list):
        raise ValidationError("root.claims skal være en liste")

    for index, claim in enumerate(claims):
        where = f"claims[{index}]"
        if not isinstance(claim, dict):
            raise ValidationError(f"{where} skal være et objekt")
        _enum(claim, "claim_type", CLAIM_TYPES, where)
        _required_text(claim, "summary", where)
        _enum(claim, "sentiment", SENTIMENTS, where)
        _enum(claim, "action", ACTIONS, where)
        _enum(claim, "time_horizon", HORIZONS, where)
        _enum(claim, "discussion_depth", DEPTHS, where)
        _enum(claim, "review_status", REVIEW_STATUSES, where)
        confidence = claim.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValidationError(f"{where}.confidence skal være et tal mellem 0 og 1")
        speaker = claim.get("speaker")
        if speaker is not None and not isinstance(speaker, str):
            raise ValidationError(f"{where}.speaker skal være tekst eller null")

        for key in ("themes", "thesis", "risks", "catalysts", "conditions"):
            value = claim.get(key, [])
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                raise ValidationError(f"{where}.{key} skal være en liste af ikke-tomme tekster")

        companies = claim.get("companies", [])
        if not isinstance(companies, list):
            raise ValidationError(f"{where}.companies skal være en liste")
        for company_index, company in enumerate(companies):
            company_where = f"{where}.companies[{company_index}]"
            if not isinstance(company, dict):
                raise ValidationError(f"{company_where} skal være et objekt")
            _required_text(company, "name", company_where)
            _enum(company, "role", COMPANY_ROLES, company_where)
            if company.get("ticker") is not None and not isinstance(company["ticker"], str):
                raise ValidationError(f"{company_where}.ticker skal være tekst eller null")

        evidence = claim.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValidationError(f"{where}.evidence skal være et objekt")
        if not any(evidence.get(key) for key in ("excerpt", "start_ref", "end_ref")):
            raise ValidationError(f"{where}.evidence skal have excerpt eller en kildehenvisning")
    return data

