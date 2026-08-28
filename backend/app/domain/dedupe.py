"""Deduplicating universities, programmes and scholarships.

Sources spell the same institution several ways ("Univ. of X", "X University").
Normalising to a stable key keeps one row per real thing without a fuzzy
matcher whose mistakes would be invisible.
"""

from __future__ import annotations

import re
import unicodedata

_NOISE = {
    "university", "universiteit", "universitat", "universite", "universidad", "universita",
    "the", "of", "at", "for", "and", "college", "institute", "school",
    "hochschule", "politecnico", "polytechnic", "univ",
}
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _PUNCT.sub(" ", text.lower())
    return _WS.sub(" ", text).strip()


def university_key(name: str, country: str = "") -> str:
    tokens = [t for t in normalize(name).split() if t not in _NOISE]
    if not tokens:
        tokens = normalize(name).split()
    return f"{normalize(country)}::{'-'.join(sorted(set(tokens)))}"


def program_key(university: str, program: str, degree: str, intake: str, country: str = "") -> str:
    prog_tokens = [t for t in normalize(program).split() if t not in {"bsc", "msc", "ba", "ma", "in", "the"}]
    return f"{university_key(university, country)}|{'-'.join(prog_tokens)}|{normalize(degree)}|{normalize(intake)}"


def scholarship_key(university: str, name: str, country: str = "") -> str:
    tokens = [t for t in normalize(name).split() if t not in {"scholarship", "award", "grant", "the", "programme", "program"}]
    if not tokens:
        tokens = normalize(name).split()
    return f"{university_key(university, country)}|{'-'.join(tokens)}"


def dedupe_by(items: list, key_fn) -> list:
    """Keep the first occurrence of each key, preserving order."""
    seen: set[str] = set()
    out = []
    for item in items:
        k = key_fn(item)
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out
