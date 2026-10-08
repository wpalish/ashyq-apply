"""Strict in-memory routing proof; never Claim/applicant/intake coverage."""
from __future__ import annotations
import re, unicodedata
from urllib.parse import urlparse
from bs4 import Tag
from app.adapters import page_classifier as _route_pc
from app.adapters.page_classifier import PageClassification,PageType
from app.adapters.fetching import FetchResult
from app.adapters.html_parse import parse_html
from app.adapters.search.ontology import canonical_field

def _route_normalize(label: str) -> str:
    text = unicodedata.normalize("NFKC", label).casefold().replace("&", " and ")
    return " ".join(re.findall(r"[^\W_]+", text))


def _route_primary(label: str) -> str:
    return re.split(r"\s+[-–—]\s+|\|", label, maxsplit=1)[0].strip()


def _required_field_routes(fields: list[str]) -> frozenset[str] | None:
    if not fields or any(not isinstance(value, str) or not value.strip() for value in fields):
        return None
    keys = [canonical_field(value) for value in fields]
    return frozenset(keys) if all(keys) else None


def _whole_route_key(label: str) -> str | None:
    # Preserve ordering and conjunctions: a joint/related title is not one own field.
    words = _route_normalize(_route_primary(label)).split()
    suffix = {"major", "honours", "honors", "hons", "degree", "programme", "program"}
    while words and words[-1] in suffix:
        words.pop()
    degree_prefix = {
        "bachelor", "bachelors", "undergraduate", "bsc", "bs", "beng", "ba",
        "master", "masters", "postgraduate", "msc", "ms", "meng", "ma",
        "phd", "doctoral", "doctorate", "foundation",
    }
    wrappers = degree_prefix | {"of", "in", "science", "engineering", "arts", "degree", "programme", "program"}
    for start in range(len(words)):
        if start and (words[0] not in degree_prefix or not set(words[:start]) <= wrappers):
            break
        term = " ".join(words[start:])
        # These broad single-word aliases remain conservative in this new permission.
        if term in {"computing", "informatics"}:
            continue
        key = canonical_field(term)
        if key is not None:
            return key
    return None


def _route_chrome(node: Tag) -> bool:
    return _route_pc._academic_chrome(node) or bool(
        _route_pc._CHROME_HINT.search(" ".join([*node.get("class", []), str(node.get("id", ""))]))
    )


def _local_route_degree(h1: Tag, requested: str) -> bool:
    label = h1.get_text(" ", strip=True)
    own_levels = {
        level for pattern, level in _route_pc._DEGREE_WORDS if re.search(pattern, label, re.I)
    }
    if own_levels:
        return own_levels == {requested}
    # A degree-only metadata sibling is local. URL/title/body degree mentions are not.
    metadata_words = {
        "bachelor", "bachelors", "undergraduate", "bsc", "bs", "beng", "ba",
        "master", "masters", "postgraduate", "msc", "ms", "meng", "ma",
        "phd", "doctoral", "doctorate", "foundation", "year", "degree",
        "full", "part", "time", "programme", "program",
    }
    seen_levels = set()
    for direction in ("previous_sibling", "next_sibling"):
        sibling = getattr(h1, direction)
        while sibling is not None and not str(sibling).strip():
            sibling = getattr(sibling, direction)
        if not isinstance(sibling, Tag) or _route_chrome(sibling):
            continue
        text = sibling.get_text(" ", strip=True)
        words = set(_route_normalize(text).split())
        if len(text) > 100 or not words <= metadata_words:
            continue
        seen_levels.update(
            level for pattern, level in _route_pc._DEGREE_WORDS if re.search(pattern, text, re.I)
        )
    return seen_levels == {requested}


def own_field_route(result: FetchResult, page: PageClassification, degree: str) -> str | None:
    if page.page_type not in {PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}:
        return None
    if page.degree_level != degree:
        return None
    root = _route_pc.main_content(parse_html(result.text))
    headings = [
        node for node in root.find_all(True)
        if (node.name == "h1" or (str(node.get("role", "")).lower() == "heading" and str(node.get("aria-level", "")) == "1"))
        and not _route_chrome(node)
        and not any(_route_chrome(parent) for parent in node.parents if isinstance(parent, Tag))
    ]
    if len(headings) != 1:
        return None
    heading = headings[0]
    identity = heading.get_text(" ", strip=True)
    key = _whole_route_key(identity)
    if key is None or _whole_route_key(page.title) != key or not _local_route_degree(heading, degree):
        return None
    own_text = root.get_text(" ", strip=True)
    if re.search(
        r"\bnon[- ]degree\b|\b(?:does?|do) not (?:offer|award)\b[^.]{0,60}\bdegree\b"
        r"|\bno degree\b[^.]{0,40}\b(?:awarded|offered)\b",
        own_text, re.I,
    ):
        return None
    # Reuse existing scoped academic-purpose proof without a whole-page fallback.
    if not _route_pc._programme_content_identity(
        identity, page.title, urlparse(result.final_url or result.url).path,
        root.get_text(" ", strip=True), root,
    ):
        return None
    return key

