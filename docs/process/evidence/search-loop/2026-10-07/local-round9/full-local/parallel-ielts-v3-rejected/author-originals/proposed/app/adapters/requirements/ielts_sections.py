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
_NUMBER = r"(?<![\w.,+\-−])([-+]?\d+(?:\.\d+)?)(?!\w|[.,]\d|[-−+–—]\s*\d)"
_NON_SCORE_UNIT = r"(?!\s*(?:%|\b(?:months?|days?|weeks?|years?|hours?|minutes?|seconds?|credits?|words?|GPA|USD|EUR|GBP|CAD|dollars?)\b))"
# Only an explicit score role may bind the number. Arbitrary words between
# "overall" and a fee/GPA number never supply an IELTS band.
_EXAM_LABEL = (
    r"(?:\bIELTS\b|\bInternational English Language Testing System\b)"
    r"(?:\s+(?:UKVI\s+Academic|Academic|General\s+Training)"
    r"|\s*\((?:UKVI\s+Academic|Academic|General\s+Training)"
    r"(?:\s+(?:test|module|version))?\))?"
    r"(?:\s+(?:test|module|version))?"
)
_COMPONENT_TAIL = (
    r"(?!\s+(?:(?:in|for)\s+)?(?:each|every)\s+(?:individual\s+)?(?:component|band|section|part)\b)"
)
_OVERALL = re.compile(
    r"\boverall(?:\s+(?:band(?:\s+score)?|score))?(?:\s+of)?"
    r"(?:\s+is)?(?:\s+(?:at\s+least|minimum))?\s*[:=]?\s*"
    + _NUMBER
    + _NON_SCORE_UNIT
    + _COMPONENT_TAIL,
    re.I,
)
_POSTFIX_OVERALL = re.compile(r"(?:^|" + _EXAM_LABEL + r"\s+)" + _NUMBER + r"\s+overall\b", re.I)
_NON_BAND_TAIL = re.compile(
    r"^\s+(?:overall\s+)?(?:GPA|grade(?:[- ]point)?|processing\s+fee|fee|cost|price|payment)\b",
    re.I,
)
_DIRECT_SCORE = re.compile(
    r"(?:^|" + _EXAM_LABEL + r"\s+)"
    r"(?:minimum(?:\s+(?:band(?:\s+score)?|score))?|(?:band\s+)?score)"
    r"(?:\s+of)?(?:\s+(?:is|at\s+least))?\s*[:=]?\s*" + _NUMBER + _NON_SCORE_UNIT + _COMPONENT_TAIL,
    re.I,
)
_EXAM_BAND = re.compile(
    _EXAM_LABEL + r"\s*[:=]?\s+" + _NUMBER + _NON_SCORE_UNIT + _COMPONENT_TAIL,
    re.I,
)
_EACH_COMPONENT = re.compile(
    r"\b(?:minimum(?:\s+(?:band(?:\s+score)?|score))?|(?:band\s+)?score)"
    r"(?:\s+of)?\s*[:=]?\s*" + _NUMBER + r"\s+(?:(?:in|for)\s+)?(?:each|every)\s+(?:individual\s+)?"
    r"(?:component|band|section|part)\b",
    re.I,
)
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
    r"(?:\bIELTS\b|\bInternational English Language Testing System\b)"
    r"(?:\s*\(?\s*(?P<variant>UKVI\s+Academic|Academic|General\s+Training)\s*\)?)?"
    r"(?:\s+(?:test|module|version))?"
)
_REFUSED = (
    r"(?:no\s+longer(?:\s+be)?\s+accepted|not(?:\s+currently)?\s+accepted"
    r"|(?:will|would|shall|can|could)\s+(?:not|no\s+longer)\s+be\s+accepted"
    r"|cannot\s+be\s+accepted)"
)
_DECLINE = re.compile(
    _DECLINE_SUBJECT + r"(?:\s+(?:(?:minimum|score(?:\s+of)?)\s+)?"
    r"(?P<refused_number>[-+]?\d+(?:\.\d+)?))?"
    r"\s+(?:(?:is|are)\s+)?" + _REFUSED + r"\b",
    re.I,
)
_DECLINE_REVERSE = re.compile(
    r"\b(?:do|does|will)\s+not\s+accept(?:\s+the)?\s+"
    + _DECLINE_SUBJECT
    + r"(?=\s*(?:[.;,:!?]|$))",
    re.I,
)
_IMPLICIT_DECLINE = re.compile(r"\b" + _REFUSED + r"\b", re.I)
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
                and child.name not in {"li", "dd"}
                and str(child.get("role", "")).lower() != "listitem"
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
            is_block = child.name in {"p", "li", "dd", "dt", "div"} and not child.find(
                [
                    "p",
                    "li",
                    "dd",
                    "dt",
                    "div",
                    "section",
                    "article",
                    "main",
                    "aside",
                    "nav",
                    "header",
                    "footer",
                    "table",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                ]
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


def _band(match: re.Match[str] | None, *, group: int = 1) -> float | None:
    if match is None:
        return None
    value = float(match.group(group))
    # Keep full numeric atoms; the authoritative ClaimBuilder verifier remains
    # in place. Invalid/negative/fractional atoms grant no accepted-type proof.
    return value if 4 <= value <= 9 and (value * 2).is_integer() else None


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
            # A numeric requirement explicitly attached to a refused variant
            # cannot become another variant's band through its heading owner.
            # Keep the block intact and abstain; do not splice clauses/quotes.
            if any(m.group("refused_number") is not None for m in _DECLINE.finditer(text)):
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
            # Opt-in IELTS prose uses observed year/intake in flat metadata too.
            # Legacy readers/OFF keep their existing request/routing context;
            # restore those fields immediately after the IELTS-only read.
            builder.meta["academic_year"] = year
            builder.meta["intake"] = intake
            section = owner or "IELTS statement"
            # Choose the first explicitly bound overall role, never the first
            # unlabelled number in the exam section. A per-component role is
            # disjoint and cannot silently become an overall requirement.
            overall_matches = sorted(
                (
                    m
                    for pattern in (_OVERALL, _POSTFIX_OVERALL, _DIRECT_SCORE, _EXAM_BAND)
                    for m in pattern.finditer(text)
                    if not _NON_BAND_TAIL.search(text[m.end() :])
                ),
                key=lambda m: m.start(),
            )
            overall = overall_matches[0] if overall_matches else None
            overall_value = _band(overall)
            if overall_value is not None and ClaimType.IELTS_MIN_OVERALL not in answered:
                value = overall_value
                if 4 <= value <= 9:
                    claim = builder.add(ClaimType.IELTS_MIN_OVERALL, value, quote, section=section)
                    if claim:
                        found.append(claim)
                        answered.add(claim.claim_type)
            if ClaimType.IELTS_MIN_SUBSCORE not in answered:
                named = {
                    m.group(1).lower(): float(m.group(2))
                    for m in _NAMED.finditer(text)
                    if _band(m, group=2) is not None
                }
                floor = _FLOOR.search(text) or _EACH_COMPONENT.search(text)
                subscore = dict(sorted(named.items())) if named else _band(floor) if floor else None
                if subscore is not None and (isinstance(subscore, dict) or 4 <= subscore <= 9):
                    claim = builder.add(
                        ClaimType.IELTS_MIN_SUBSCORE, subscore, quote, section=section
                    )
                    if claim:
                        found.append(claim)
                        answered.add(claim.claim_type)
            if ClaimType.IELTS_ACCEPTED_TYPES not in answered:
                label = " ".join([owner or "", text])
                refused_variants = {
                    _variant(m.group("variant") or "")
                    for pattern in (_DECLINE, _DECLINE_REVERSE)
                    for m in pattern.finditer(label)
                }
                types = []
                if (
                    "academic" not in refused_variants
                    and re.search(r"\bacademic\b", label, re.I)
                    and not re.search(
                        r"academic\s+(?:is\s+)?not\s+accepted|not\s+accept\w*[^;.]{0,30}academic",
                        label,
                        re.I,
                    )
                ):
                    types.append("academic")
                    if "ukvi_academic" not in refused_variants and re.search(
                        r"\bukvi\b", label, re.I
                    ):
                        types.append("ukvi_academic")
                if (
                    "general_training" not in refused_variants
                    and re.search(r"\bgeneral\s+training\b", label, re.I)
                    and not re.search(
                        r"general\s+training\s+(?:is\s+)?not\s+accepted|not\s+accept\w*[^;.]{0,30}general\s+training",
                        label,
                        re.I,
                    )
                ):
                    types.append("general_training")
                minimum_here = overall_value is not None or any(
                    _band(m, group=group) is not None
                    for pattern, group in ((_FLOOR, 1), (_EACH_COMPONENT, 1), (_NAMED, 2))
                    for m in pattern.finditer(text)
                )
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
