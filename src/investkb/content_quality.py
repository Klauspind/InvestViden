"""High-precision rules for content that must not become investment knowledge."""
from __future__ import annotations

import re


_PROMOTIONAL_MARKERS = (
    "sponsoreret af saxo bank",
    "sponsoreret af saxobank",
    "følge med i millionærklubbens portefølje",
    "følg med i millionærklubbens portefølje",
    "blive inspireret af eksperterne",
    "bliv inspireret af eksperterne",
    "opret din aktiesparekonto gebyrfrit",
    "1,2 millioner kunder",
)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def is_promotional_noise(summary: str) -> bool:
    """Recognize the repeated Millionærklubben/Saxo sponsor boilerplate.

    The rule deliberately requires two independent markers. A normal analytical
    statement about Saxo Bank or an aktiesparekonto therefore remains visible.
    """
    text = _normalized(summary)
    return sum(marker in text for marker in _PROMOTIONAL_MARKERS) >= 2
