"""Conditional Benefits-section evidence without funding or entitlement projections."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.adapters.extraction import _MONEY, parse_money, readable_text
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import main_content
from app.domain.enums import ClaimType
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim


@dataclass(frozen=True)
class PolicyEvidence:
    value: dict[str, Any]
    quote: str


_BENEFITS_HEADING = re.compile(
    r"^(?:benefits(?: of(?: the)? award)?|(?:award|scholarship) benefits"
    r"|what (?:the )?(?:award|scholarship) covers)$",
    re.I,
)
_NON_BINDING = re.compile(
    r"\b(?:optional|voluntary|illustrative|may|might|could|approximately)\b"
    r"|\b(?:as|an?)\s+examples?\b|^examples?\b"
    r"|\b(?:not|never)\s+(?:covered|required|available|provided)\b"
    r"|\bsubject to change\b",
    re.I,
)
_SHARED_CONDITION = re.compile(
    r"^(?:the )?(?:scholarship|award) covers (?:up to )?(?:the )?"
    r"(?:normal|standard) (?:programme|program|course) duration "
    r"on condition that [^.]+\.$",
    re.I,
)
_LABEL = re.compile(
    r"^(?:full coverage|(?:living|maintenance|subsistence) (?:allowance|stipend)"
    r"|(?:accommodation|housing) allowance|travel grant)\b",
    re.I,
)
_TUITION = re.compile(
    r"^full coverage of subsidi[sz]ed tuition fees\s*"
    r"\(after (?P<grant>[^()]+)\)\.$",
    re.I,
)
_LIVING = re.compile(
    r"^(?:living|maintenance|subsistence) (?:allowance|stipend) of (?P<money>.+?) "
    r"per (?P<period>academic year|year|month)\.$",
    re.I,
)
_HOUSING = re.compile(
    r"^(?:accommodation|housing) allowance of up to (?P<money>.+?) "
    r"per (?P<period>academic year|year|month)\.\s*"
    r"\(applicable to (?P<condition>.+?)\.\)$",
    re.I,
)
_TRAVEL = re.compile(
    r"^travel grant of up to (?P<money>.+?) for (?P<purpose>an? overseas programme) "
    r"subject to terms and conditions in the (?P<form>.+? form) "
    r"\(for new cohorts from (?P<cohort>AY\s*20\d{2})\)\.$",
    re.I,
)
_TAIL_QUALIFIER = re.compile(
    r"\b(?:these|those|above|aforementioned|benefits|allowances|coverage|if|unless"
    r"|provided|subject|condition|eligible|only|except)\b",
    re.I,
)
_COMPUTER = re.compile(r"^(?:computer|equipment) allowance of (?P<money>.+?) \(one-off\)\.$", re.I)
_BOND = re.compile(
    r"^no bond is attached to (?P<award>[^.]+?) apart from the "
    r"(?:\d+|[a-z]+)-year bond applicable to (?P<population>[^.]+?) "
    r"under the (?P<scheme>[^.]+? scheme)\.$",
    re.I,
)
_COLLEGE = re.compile(
    r"^enrolment into (?P<college>[^.]+? college)\s*[-–—]\s*"
    r"(?P<name>[^.]+? college)\s*\.$",
    re.I,
)
_HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
_CONTAINERS = ["section", "article", "table", "div", "main", "body"]
_BACKWARD_HEADING = re.compile(r"\b(?:these|those|above|benefits?|allowances?|coverage)\b", re.I)


def _flat(text: str) -> str:
    return " ".join(text.split())


def _pattern(text: str) -> re.Pattern[str]:
    return re.compile(r"\s+".join(re.escape(word) for word in text.split()))


def _money(text: str) -> tuple[int | float, str] | None:
    """One complete existing-lexer money token, with an unambiguous currency."""
    match = _MONEY.fullmatch(text)
    if match is None or match.group(1) == "$":
        return None
    value = parse_money(text)
    if value is None or value[0] <= 0:
        return None
    amount, currency = value
    return int(amount) if amount.is_integer() else amount, currency


def _item(text: str) -> tuple[str, dict[str, object]] | None:
    if _NON_BINDING.search(text):
        return None
    tuition = _TUITION.fullmatch(text)
    if tuition:
        grant = re.sub(r"[^a-z0-9]+", "_", tuition.group("grant").casefold()).strip("_")
        return "tuition", {"fraction": 1.0, "basis": "subsidised_after_" + grant}
    for pattern, category, amount_key in [
        (_LIVING, "living", "fixed_amount"),
        (_HOUSING, "housing", "maximum"),
        (_TRAVEL, "travel", "maximum"),
    ]:
        match = pattern.fullmatch(text)
        if match is None:
            continue
        money = _money(match.group("money"))
        if money is None:
            return None
        amount, currency = money
        value: dict[str, object] = {"currency": currency, amount_key: amount}
        if category in {"living", "housing"}:
            value["period"] = match.group("period").casefold().replace(" ", "_")
        if category == "housing":
            value["requires"] = match.group("condition")
        elif category == "travel":
            value["requires"] = match.group("purpose")
            value["terms"] = match.group("form")
            value["cohorts_from"] = re.sub(r"\s+", "", match.group("cohort")).upper()
        return category, value
    return None


def _independent_tail(text: str) -> bool:
    """Only fully parsed distinct subjects; never drop an unknown tail condition."""
    if _NON_BINDING.search(text) or _TAIL_QUALIFIER.search(text):
        return False
    computer = _COMPUTER.fullmatch(text)
    if computer is not None:
        return _money(computer.group("money")) is not None
    return bool(_BOND.fullmatch(text) or _COLLEGE.fullmatch(text))


def _owned_benefits_heading(ul: Tag) -> Tag | None:
    """Never borrow a heading from a completed sibling section/container."""
    container = ul.find_parent(_CONTAINERS)
    if container is None:
        return None
    heading = ul.find_previous(_HEADINGS)
    if (
        heading is not None
        and heading.find_parent(_CONTAINERS) is container
        and _BENEFITS_HEADING.fullmatch(_flat(heading.get_text(" ", strip=True)))
    ):
        return heading
    return None


def _policy_candidate(ul: Tag) -> bool:
    return _owned_benefits_heading(ul) is not None and any(
        _LABEL.search(_flat(li.get_text(" ", strip=True)))
        for li in ul.find_all("li", recursive=False)
    )


def _following_scope_clear(ul: Tag) -> bool:
    """An unparsed note before the next local heading may qualify every benefit."""
    container = ul.find_parent(_CONTAINERS)
    heading = _owned_benefits_heading(ul)
    if container is None or heading is None:
        return False
    after = False
    for tag in container.find_all(True):
        if tag is ul:
            after = True
            continue
        if not after or any(parent is ul for parent in tag.parents):
            continue
        if tag.name in _HEADINGS:
            title = _flat(tag.get_text(" ", strip=True))
            separate_boundary = (
                tag.find_parent(_CONTAINERS) is container
                and int(tag.name[1]) <= int(heading.name[1])
                and (not _BACKWARD_HEADING.search(title) or _BENEFITS_HEADING.fullmatch(title))
            )
            if separate_boundary:
                break
            return False
        if tag.name == "p":
            text = _flat(tag.get_text(" ", strip=True))
            if not text:
                continue
            anchor = tag.find("a", recursive=False)
            local_navigation = (
                isinstance(anchor, Tag)
                and str(anchor.get("href", "")).startswith("#")
                and _flat(anchor.get_text(" ", strip=True)) == text
                and not _NON_BINDING.search(text)
                and not _TAIL_QUALIFIER.search(text)
            )
            if not local_navigation:
                return False
    return True


def _from_list(ul: Tag, page_text: str) -> PolicyEvidence | None:
    if _owned_benefits_heading(ul) is None or not _following_scope_clear(ul):
        return None
    sibling = ul.find_previous_sibling()
    if not isinstance(sibling, Tag) or sibling.name != "p":
        return None
    prefix = _flat(sibling.get_text(" ", strip=True))
    if not _SHARED_CONDITION.fullmatch(prefix) or _NON_BINDING.search(prefix):
        return None
    items = list(ul.find_all("li", recursive=False))
    found: dict[str, dict[str, object]] = {}
    first: int | None = None
    last: int | None = None
    for index, li in enumerate(items):
        text = _flat(li.get_text(" ", strip=True))
        parsed = _item(text)
        if parsed is None:
            if set(found) == {
                "tuition",
                "living",
                "housing",
                "travel",
            } and _independent_tail(text):
                continue
            return None  # refuse unparsed scope, polarity, limits, or uncertain benefits
        category, value = parsed
        if category in found:
            if found[category] != value:
                return None
            continue
        found[category] = value
        first = index if first is None else first
        last = index
    if set(found) != {"tuition", "living", "housing", "travel"} or first != 0 or last is None:
        return None
    list_text = readable_text(str(ul))
    beginning = _pattern(_flat(items[first].get_text(" ", strip=True))).search(list_text)
    ending = _pattern(_flat(items[last].get_text(" ", strip=True))).search(list_text)
    if beginning is None or ending is None or beginning.start() > ending.end():
        return None
    span = list_text[beginning.start() : ending.end()]
    expected = prefix + " " + span
    exact = _pattern(expected).search(page_text)
    if exact is None or len(exact.group()) > MAX_EXCERPT_CHARS:
        return None
    policy: dict[str, Any] = {"conditions": [prefix]}
    for category in ["tuition", "living", "housing", "travel"]:
        policy[category] = found[category]
    return PolicyEvidence(policy, exact.group())


def read_conditional_policy(
    html: str, existing_claims: Iterable[Claim] = ()
) -> PolicyEvidence | None:
    """A single coherent policy; no monetary or CoverageBreakdown projections."""
    if any(claim.claim_type is ClaimType.SCHOLARSHIP_COVERAGE for claim in existing_claims):
        return None
    content: BeautifulSoup = main_content(parse_html(html))
    page_text = readable_text(html)
    policies: list[PolicyEvidence] = []
    for ul in content.find_all("ul"):
        if not _policy_candidate(ul):
            continue
        policy = _from_list(ul, page_text)
        if policy is None:
            return None
        if not policies:
            policies.append(policy)
        elif policy.value != policies[0].value:
            return None
    return policies[0] if policies else None
