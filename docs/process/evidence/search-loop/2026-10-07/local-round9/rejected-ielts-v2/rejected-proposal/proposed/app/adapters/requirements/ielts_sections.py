"""IELTS prose from its own semantic block; never an admission permission."""

from __future__ import annotations

import re
from collections.abc import Generator, Iterator
from dataclasses import replace

from app.adapters.extraction import ClaimBuilder
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import content_for_reading
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import ClaimScope
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import ClaimType
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim
from bs4 import Tag

_IELTS = re.compile(r"\bIELTS\b|\bInternational English Language Testing System\b", re.I)
_OTHER_TEST = re.compile(
    r"\b(?:TOEFL|CAEL|Duolingo|PTE|Cambridge|ELDA|COPE|IB)\b"
    r"|\bInternational Baccalaureate\b",
    re.I,
)
# Read the entire numeric atom: never 6 from 60 or discard decimal digits.
_NUMBER = r"(?<![\w.,])([-+]?\d+(?:\.\d+)?)(?!\w|[.,]\d)"
_NON_SCORE_UNIT = (
    r"(?!\s*(?:%|\b(?:months?|days?|weeks?|years?|hours?|minutes?|seconds?|credits?|words?)\b))"
)
_OVERALL = re.compile(r"\boverall\b[^\d.\n]{0,35}?" + _NUMBER + _NON_SCORE_UNIT, re.I)
_FLOOR = re.compile(
    r"\bno\s+(?:individual\s+)?(?:sub-?)?(?:score|band|component|section|part)\s+"
    r"(?:below|less\s+than|lower\s+than)\s*" + _NUMBER + _NON_SCORE_UNIT,
    re.I,
)
_NAMED = re.compile(
    r"\b(reading|writing|speaking|listening)\b"
    r"(?:\s+(?:(?:minimum\s+)?(?:band\s+)?score|band|minimum)(?:\s+of)?)?\s*[:=]?\s*"
    + _NUMBER
    + _NON_SCORE_UNIT,
    re.I,
)
_DECLINE_SUBJECT = (
    r"\bIELTS(?:\s*\(?\s*(?P<variant>UKVI\s+Academic|Academic|General\s+Training)\s*\)?)?"
    r"(?:\s+(?:test|module|version))?"
)
_DECLINE = re.compile(
    _DECLINE_SUBJECT
    + r"\s+(?:(?:is|are)\s+)?(?:no\s+longer\s+accepted|not\s+accepted|cannot\s+be\s+accepted)\b",
    re.I,
)
_DECLINE_REVERSE = re.compile(
    r"\b(?:do|does|will)\s+not\s+accept(?:\s+the)?\s+"
    + _DECLINE_SUBJECT
    + r"(?=\s*(?:[.;,:!?]|$))",
    re.I,
)
_IMPLICIT_DECLINE = re.compile(
    r"\b(?:no\s+longer\s+accepted|not\s+accepted|cannot\s+be\s+accepted)\b", re.I
)
_YEAR_RANGE = re.compile(r"\b20\d{2}\s*[/–—-]\s*(?:20\d{2}|\d{2})\b")
_INTAKE_TERM = re.compile(r"\b(?:fall|autumn|spring|summer|winter)\b", re.I)
_REGION = {"main", "article", "section", "details", "dialog", "li", "dd", "aside"}
_REGION_ROLE = {"main", "article", "region", "dialog", "listitem", "complementary"}
_CHROME = {"nav", "header", "footer"}
_CHROME_ROLE = {"navigation", "menu", "menubar", "tablist", "banner", "contentinfo"}
_CHROME_CLASS = re.compile(r"^(?:nav|menu|breadcrumb|social|share)(?:[-_]|$)", re.I)
# Standard accordion/card widgets are semantic sibling regions. A header wrapper
# is not itself a region: its heading still owns the adjacent widget body.
_WIDGET = re.compile(r"(?:^|-)accordion-item$|(?:^|-)collapsible-item$|^card$", re.I)
_TYPES = frozenset(
    {ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE, ClaimType.IELTS_ACCEPTED_TYPES}
)
_WS = re.compile(r"\s+")


def _flat(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _chrome(node: Tag) -> bool:
    return (
        node.name in _CHROME
        or str(node.get("role", "")).lower() in _CHROME_ROLE
        or any(_CHROME_CLASS.search(str(c)) for c in node.get("class", []))
    )


def _region(node: Tag) -> bool:
    return (
        node.name in _REGION
        or str(node.get("role", "")).lower() in _REGION_ROLE
        or any(_WIDGET.search(str(c)) for c in node.get("class", []))
    )


def _blocks(html: str) -> Iterator[tuple[str, list[tuple[int, str, int]], int]]:
    root = content_for_reading(parse_html(html))

    def visit(
        node: Tag, headings: list[tuple[int, str, int]]
    ) -> Generator[tuple[str, list[tuple[int, str, int]], int], None, list[tuple[int, str, int]]]:
        current = list(headings)
        for child in node.children:
            if not isinstance(child, Tag) or _chrome(child):
                continue
            if re.fullmatch(r"h[1-6]", child.name or ""):
                level = int(child.name[1])
                while current and current[-1][0] >= level:
                    current.pop()
                current.append((level, _flat(child.get_text(" ", strip=True)), id(child)))
                continue
            own_region = _region(child)
            # An exam heading outside an explicit region cannot assert that
            # region's purpose. Preserve ancestor context, but close exam owners.
            nested = (
                [
                    (n, t, key)
                    for n, t, key in current
                    if not (_IELTS.search(t) or _OTHER_TEST.search(t))
                ]
                if own_region
                else current
            )
            # An explicit accordion content panel belongs to its same item,
            # even if the site leaves aria-labelledby empty. A generic sibling
            # section has no such relationship and still closes the owner.
            parent_region = next(
                (a for a in child.parents if isinstance(a, Tag) and _region(a)), None
            )
            if (
                own_region
                and child.get("data-accordion-component") == "content"
                and isinstance(parent_region, Tag)
                and (
                    parent_region.get("data-accordion-component") == "item"
                    or any(_WIDGET.search(str(c)) for c in parent_region.get("class", []))
                )
            ):
                nested = list(current)
            labelled = str(child.get("aria-labelledby", "")).split()
            if own_region and labelled:
                for label in labelled:
                    heading = root.find(id=label)
                    if not isinstance(heading, Tag) or not re.fullmatch(
                        r"h[1-6]", heading.name or ""
                    ):
                        continue
                    if any(_chrome(a) for a in heading.parents if isinstance(a, Tag)):
                        continue
                    heading_region = next(
                        (a for a in heading.parents if isinstance(a, Tag) and _region(a)), None
                    )
                    child_region = next(
                        (a for a in child.parents if isinstance(a, Tag) and _region(a)), None
                    )
                    if heading_region is child_region:
                        nested = [
                            *nested,
                            (
                                int(heading.name[1]),
                                _flat(heading.get_text(" ", strip=True)),
                                id(heading),
                            ),
                        ]
            is_block = child.name in {"p", "li", "dd", "dt"} and not child.find(
                ["p", "li", "dd", "dt", "table", "h1", "h2", "h3", "h4", "h5", "h6"]
            )
            if is_block:
                # A list item is its own test statement; its siblings never join.
                yield _flat(child.get_text(" ", strip=True)), list(nested), id(child)
                continue
            if child.name == "table":
                continue  # unchanged structural reader owns tables
            returned = yield from visit(child, list(nested))
            if not own_region:
                current = returned
        return current

    yield from visit(root, [])


def _entries(html: str) -> Iterator[tuple[str, str | None, tuple[str, ...], int]]:
    for text, headings, block_key in _blocks(html):
        if not text:
            continue
        owner, owner_key = next(
            (
                (h, key)
                for _, h, key in reversed(headings)
                if _IELTS.search(h) or _OTHER_TEST.search(h)
            ),
            (None, block_key),
        )
        if owner and _IELTS.search(owner) and not _OTHER_TEST.search(owner):
            if not _OTHER_TEST.search(text):
                yield text, owner, tuple(h for _, h, _ in headings), owner_key
            continue
        # Without a heading owner, the same sentence must name IELTS itself.
        for sentence in re.split(r"(?<=[.!?;])\s+(?=[^\d])", text):
            if _IELTS.search(sentence) and not _OTHER_TEST.search(sentence):
                yield sentence, None, tuple(h for _, h, _ in headings), block_key


def _variant(label: str) -> str | None:
    if re.search(r"\bgeneral\s+training\b", label, re.I):
        return "general_training"
    if re.search(r"\bacademic\b", label, re.I):
        return "ukvi_academic" if re.search(r"\bukvi\b", label, re.I) else "academic"
    return None


def _declined(text: str, owner: str | None) -> bool:
    matches = [*_DECLINE.finditer(text), *_DECLINE_REVERSE.finditer(text)]
    for match in matches:
        variant = _variant(match.group("variant") or "")
        own_variant = _variant(owner or "")
        # A refused test variant does not withdraw another explicitly named
        # variant: Indicator/Online/One Skill phrases do not match this parser.
        if not owner or not variant or not own_variant or variant == own_variant:
            return True
    return bool(owner and not _IELTS.search(text) and _IMPLICIT_DECLINE.search(text)) or bool(
        owner and (_DECLINE.search(owner) or _DECLINE_REVERSE.search(owner))
    )


def _excerpt(text: str, owner: str | None, page_text: str, headings: tuple[str, ...]) -> str | None:
    page = _flat(page_text)
    block = _flat(text)
    if not block or block not in page:
        return None
    start = page.find(block)
    end = start + len(block)
    boundaries = [owner] if owner else []
    # A local qualification/year/intake must remain visible in the same
    # contiguous quote as the exam, not just in the persisted scope object.
    for heading in headings:
        scope = read_scope(heading)
        if scope.qualification or scope.academic_year or scope.intake:
            boundaries.append(heading)
    block_start = start
    for boundary in boundaries:
        position = page.rfind(_flat(boundary), 0, block_start)
        if position < 0:
            return None
        start = min(start, position)
    quote = page[start:end]
    # Never join a heading to a later value by dropping intervening words.
    if len(quote) > MAX_EXCERPT_CHARS or not is_verbatim_excerpt(quote, page_text):
        return None
    return quote


def extract_owned_ielts(html: str, builder: ClaimBuilder, *, skip: set[ClaimType]) -> list[Claim]:
    """Read at most one of each IELTS type, retaining legacy first-answer order."""
    if builder.page_text is None:
        return []  # no contiguous verifier context, no prose claims
    found: list[Claim] = []
    answered = set(skip)
    original_scope = builder.meta.get("scope")
    original_year = builder.meta.get("academic_year")
    original_intake = builder.meta.get("intake")
    title = str(builder.meta.get("page_title") or "")
    title_scope = read_scope(title, title=title)
    entries = list(_entries(html))
    declined_owners = {key for text, owner, _, key in entries if owner and _declined(text, owner)}
    try:
        for text, owner, headings, owner_key in entries:
            if owner_key in declined_owners or _declined(text, owner):
                continue
            if answered >= _TYPES:
                break
            quote = _excerpt(text, owner, builder.page_text, headings)
            if quote is None:
                continue
            scope_text = " ".join([*headings, text])
            local = read_scope(scope_text)
            # Only the local/ancestor words or the page's own stored title can
            # supply year/intake. Global body scope can belong to another exam.
            year = local.academic_year or (
                None if _YEAR_RANGE.search(scope_text) else title_scope.academic_year
            )
            intake = local.intake or (
                None if _INTAKE_TERM.search(scope_text) else title_scope.intake
            )
            if isinstance(original_scope, ClaimScope):
                builder.meta["scope"] = replace(
                    original_scope,
                    qualification=local.qualification,
                    academic_year=year,
                    intake=intake,
                )
            else:
                builder.meta["scope"] = replace(local, academic_year=year, intake=intake)
            # These Claim fields also describe the source, not the request.
            # Restore them after IELTS so other readers remain unchanged.
            builder.meta["academic_year"] = year
            builder.meta["intake"] = intake
            section = owner or "IELTS statement"
            overall = _OVERALL.search(text)
            if overall and ClaimType.IELTS_MIN_OVERALL not in answered:
                value = float(overall.group(1))
                if 4 <= value <= 9:
                    claim = builder.add(ClaimType.IELTS_MIN_OVERALL, value, quote, section=section)
                    if claim:
                        found.append(claim)
                        answered.add(claim.claim_type)
            if ClaimType.IELTS_MIN_SUBSCORE not in answered:
                named = {
                    m.group(1).lower(): float(m.group(2))
                    for m in _NAMED.finditer(text)
                    if 4 <= float(m.group(2)) <= 9
                }
                floor = _FLOOR.search(text)
                subscore = (
                    dict(sorted(named.items()))
                    if named
                    else float(floor.group(1))
                    if floor
                    else None
                )
                if subscore is not None and (isinstance(subscore, dict) or 4 <= subscore <= 9):
                    claim = builder.add(
                        ClaimType.IELTS_MIN_SUBSCORE, subscore, quote, section=section
                    )
                    if claim:
                        found.append(claim)
                        answered.add(claim.claim_type)
            if ClaimType.IELTS_ACCEPTED_TYPES not in answered:
                label = " ".join([owner or "", text])
                types = []
                if re.search(r"\bacademic\b", label, re.I) and not re.search(
                    r"academic\s+(?:is\s+)?not\s+accepted|not\s+accept\w*[^;.]{0,30}academic",
                    label,
                    re.I,
                ):
                    types.append("academic")
                    if re.search(r"\bukvi\b", label, re.I):
                        types.append("ukvi_academic")
                if re.search(r"\bgeneral\s+training\b", label, re.I) and not re.search(
                    r"general\s+training\s+(?:is\s+)?not\s+accepted|not\s+accept\w*[^;.]{0,30}general\s+training",
                    label,
                    re.I,
                ):
                    types.append("general_training")
                minimum_here = bool(overall or _FLOOR.search(text) or _NAMED.search(text))
                accepted_here = bool(
                    re.search(r"\baccept(?:ed|s)?\b", text, re.I)
                ) and not re.search(r"\bnot\b.{0,30}\baccept", text, re.I)
                if types and (minimum_here or accepted_here):
                    claim = builder.add(
                        ClaimType.IELTS_ACCEPTED_TYPES, types, quote, section=section
                    )
                    if claim:
                        found.append(claim)
                        answered.add(claim.claim_type)
    finally:
        builder.meta["scope"] = original_scope
        builder.meta["academic_year"] = original_year
        builder.meta["intake"] = original_intake
    return found
