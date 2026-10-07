from __future__ import annotations

import re
import unicodedata
from typing import Any


_GENERIC_COMPANY_TOKENS = {
    "aktieselskab",
    "company",
    "corp",
    "corporation",
    "group",
    "holding",
    "holdings",
    "inc",
    "limited",
    "ltd",
    "plc",
}


def _normalized_words(value: str | None) -> list[str]:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode().casefold()
    return re.findall(r"[a-z0-9]+", text)


def _contains_phrase(words: list[str], phrase: list[str]) -> bool:
    if not words or not phrase or len(phrase) > len(words):
        return False
    width = len(phrase)
    return any(words[index:index + width] == phrase for index in range(len(words) - width + 1))


def source_relevance(entry: dict[str, Any], source: dict[str, Any]) -> tuple[int, str]:
    """Return a deterministic metadata relevance score and human-readable reason.

    IV-015 deliberately stays local and schema-free. Matching is whole-word based so
    a portfolio token such as ``Novo`` does not match unrelated substrings such as
    ``Novonesis``. The score is only a prioritisation aid; it never changes review
    status or AI permissions.
    """

    company_words = _normalized_words(str(entry.get("company_name") or ""))
    ticker_words = _normalized_words(str(entry.get("ticker") or ""))
    title_words = _normalized_words(str(source.get("title") or ""))
    publisher_words = _normalized_words(str(source.get("publisher") or ""))

    meaningful_company_words = [
        word for word in company_words
        if len(word) >= 4 and word not in _GENERIC_COMPANY_TOKENS
    ]

    if company_words and _contains_phrase(title_words, company_words):
        return 400, "selskabsnavn i titel"
    if ticker_words and _contains_phrase(title_words, ticker_words):
        return 390, "ticker i titel"

    matched_title_words = [word for word in meaningful_company_words if word in title_words]
    if len(matched_title_words) >= 2:
        return 330, "flere selskabsord i titel"
    if matched_title_words:
        return 260, f"selskabsord i titel: {matched_title_words[0]}"

    if company_words and _contains_phrase(publisher_words, company_words):
        return 230, "selskabet er registreret som udgiver"
    if ticker_words and _contains_phrase(publisher_words, ticker_words):
        return 220, "ticker hos udgiver"

    return 0, ""


def prioritize_sources(entry: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter peripheral metadata hits and rank relevant sources newest-first.

    Recency is the primary ordering because IV-015 is meant to keep old historical
    material from crowding out current research. Relevance score breaks ties and is
    shown in the UI as an explanation, not as an investment score.
    """

    prioritized: list[dict[str, Any]] = []
    for row in rows:
        score, reason = source_relevance(entry, row)
        if score <= 0:
            continue
        enriched = dict(row)
        enriched["relevance_score"] = score
        enriched["relevance_reason"] = reason
        enriched["relevance_label"] = "Høj relevans" if score >= 330 else "Sandsynlig relevans"
        prioritized.append(enriched)

    prioritized.sort(
        key=lambda row: (
            str(row.get("published_at") or row.get("imported_at") or ""),
            int(row.get("relevance_score") or 0),
            str(row.get("id") or ""),
        ),
        reverse=True,
    )
    return prioritized
