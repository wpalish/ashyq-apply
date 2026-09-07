"""Verifying one extracted claim against the page it claims to come from.

Extraction is pattern-matching and will always be able to be talked into a
false positive; this module is the seam where a candidate claim is checked
against the evidence it arrived with before it is allowed to exist:

* the excerpt must actually appear in the page text (``EXCERPT_NOT_VERBATIM``);
* the value must fall inside the published range for its claim type
  (``VALUE_OUT_OF_RANGE``) — an IELTS band of 9.5 does not exist;
* an official-domain source must actually be served from an allowed domain
  (``DOMAIN_NOT_OFFICIAL``) — ``narxoz.kz`` inside a query parameter is not
  the page's host;
* the page class must be one that can answer the claim's question at all
  (``PAGE_TYPE_REJECTED``).

Every check whose context is absent is NOT evaluated: a claim verified
without page text, without a source URL, without allowed domains or without
a page type is never rejected for the missing context. Unknown stays
unknown; the verifier only rejects on positive contradiction.

Pure domain logic: no I/O, no network, and no imports from
``app.adapters.*`` (that direction is forbidden). The page type is therefore
matched by its string value — ``PageType`` members are ``StrEnum`` and
compare (and hash) equal to their values, so plain strings interop in both
directions.

Two deliberate verdicts worth spelling out:

* ``verify_claim`` forgives letter case at the excerpt step (excerpts and
  page text travel through different extraction paths; only content
  contradictions reject there), while ``is_verbatim_excerpt`` itself is the
  strict, case-sensitive predicate for callers that need exact quoting.
* The value table below is deliberately narrower than every number a page
  could publish. It rejects *impossible* values; plausibility tuning (such
  as the tuition floor) lives with the extractor that owns that window.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast
from urllib.parse import urlparse

from app.domain.enums import ClaimType

__all__ = [
    "CLAIM_TYPE_PAGE_TYPES",
    "OFFICIAL_PUBLIC_TLDS",
    "VALUE_RANGE_RULES",
    "RejectReason",
    "Verdict",
    "VerificationInput",
    "is_verbatim_excerpt",
    "normalize_text",
    "page_type_admits",
    "registrable_domain",
    "url_matches_domains",
    "value_in_range",
    "verify_claim",
]


class RejectReason(StrEnum):
    """Why a claim was not allowed to exist."""

    EXCERPT_NOT_VERBATIM = "excerpt_not_verbatim"
    VALUE_OUT_OF_RANGE = "value_out_of_range"
    DOMAIN_NOT_OFFICIAL = "domain_not_official"
    PAGE_TYPE_REJECTED = "page_type_rejected"


@dataclass(frozen=True)
class VerificationInput:
    """A candidate claim plus every piece of context a check might need.

    Absent context is ``None``/empty, and a check whose context is absent is
    skipped — it never rejects.
    """

    claim_type: ClaimType
    value: object
    excerpt: str | None = None
    page_text: str | None = None
    source_url: str | None = None
    page_type: str | None = None
    official_domain: bool = False
    allowed_domains: Sequence[str] = ()
    today: date | None = None


@dataclass(frozen=True)
class Verdict:
    """The outcome of one verification: accept, or one specific reason."""

    accepted: bool
    reason: RejectReason | None = None


# --- text normalisation -----------------------------------------------------


_WHITESPACE_RUN: Final[re.Pattern[str]] = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """NFKC, then collapse every Unicode whitespace run to one space, then strip."""
    return _WHITESPACE_RUN.sub(" ", unicodedata.normalize("NFKC", text)).strip()


def is_verbatim_excerpt(excerpt: str, page_text: str) -> bool:
    """True when the excerpt appears in the page: case-sensitive substring
    after normalising BOTH sides (NFKC, whitespace runs collapsed)."""
    return (
        bool(excerpt) and bool(page_text) and normalize_text(excerpt) in normalize_text(page_text)
    )


# --- the value range table --------------------------------------------------
#
# One rule per claim type, keyed by the claim types the extractors actually
# produce. A claim type without a rule here is never out of range: the
# verifier rejects impossible values, it does not second-guess plausible
# ones. Bands the extractors already narrow (IELTS 4.0-9.0 and friends) are
# recorded at their physical limits; the step is part of the IELTS rule
# because score scales publish half bands only.

_STEP_TOLERANCE: Final = 1e-9

#: Money claims carry {"amount": ..., "currency": ...} from parse_money.
_ISO_DATE: Final[re.Pattern[str]] = re.compile(r"\d{4}-\d{2}-\d{2}")
_BARE_YEAR: Final[re.Pattern[str]] = re.compile(r"\d{4}")


def _band_check(low: float, high: float, step: float | None) -> Callable[[object, date], bool]:
    def check(value: object, today: date) -> bool:
        number = cast("float", value)
        if not low <= number <= high:
            return False
        return step is None or abs(number / step - round(number / step)) <= _STEP_TOLERANCE

    return check


def _money_check(value: object, today: date) -> bool:
    """Any real fee or cost is above zero; zero is a misread, not a price."""
    return cast("dict[str, float]", value)["amount"] > 0


def _deadline_check(value: object, today: date) -> bool:
    """ISO date format only, or a bare year that is not already past."""
    text = cast("str", value)
    if _ISO_DATE.fullmatch(text):
        return True
    if _BARE_YEAR.fullmatch(text):
        return int(text) >= today.year
    return False


VALUE_RANGE_RULES: Final[Mapping[ClaimType, Callable[[object, date], bool]]] = MappingProxyType(
    {
        ClaimType.IELTS_MIN_OVERALL: _band_check(0.0, 9.0, 0.5),
        ClaimType.IELTS_MIN_SUBSCORE: _band_check(0.0, 9.0, 0.5),
        ClaimType.TOEFL_MIN_TOTAL: _band_check(0, 120, None),
        ClaimType.DUOLINGO_MIN: _band_check(0, 160, None),
        ClaimType.SAT_MIN_TOTAL: _band_check(0, 1600, None),
        ClaimType.APPLICATION_FEE: _money_check,
        ClaimType.TUITION: _money_check,
        ClaimType.MANDATORY_FEES: _money_check,
        ClaimType.HOUSING_COST: _money_check,
        ClaimType.MEALS_COST: _money_check,
        ClaimType.HEALTH_INSURANCE_COST: _money_check,
        ClaimType.BOOKS_COST: _money_check,
        ClaimType.TOTAL_COST_OF_ATTENDANCE: _money_check,
        ClaimType.ADMISSION_DEADLINE: _deadline_check,
    }
)


def value_in_range(claim_type: ClaimType, value: object, *, today: date) -> bool:
    """True unless the value contradicts its claim type's published range."""
    rule = VALUE_RANGE_RULES.get(claim_type)
    if rule is None:
        return True
    return rule(value, today)


# --- domain matching --------------------------------------------------------
#
# There is no public-suffix list dependency in this project, so the
# "registrable domain" is computed conservatively: two labels, or three when
# the last two are a known multi-part public suffix. That covers every shape
# this pipeline meets — university hosts, the official-TLD rule below, and
# attacker hosts like narxoz.kz.attacker.example (whose registrable domain
# is attacker.example, whatever the label says).

_MULTIPART_PUBLIC_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        "ac.uk",
        "gov.uk",
        "co.uk",
        "org.uk",
        "edu.au",
        "gov.au",
        "com.au",
        "ac.nz",
        "govt.nz",
        "co.nz",
        "edu.sg",
        "ac.za",
        "edu.hk",
    }
)

#: Public suffixes that on their own mark an official academic or government
#: source. Matching is done on the HOST's registrable domain — a ".edu"
#: anywhere else in the URL string (path, query) proves nothing.
OFFICIAL_PUBLIC_TLDS: Final[tuple[str, ...]] = (
    "edu",
    "ac.uk",
    "edu.au",
    "gov",
    "gov.uk",
    "ac.nz",
    "edu.sg",
)


def registrable_domain(host: str) -> str:
    """The host reduced to its registrable domain (``www.narxoz.kz`` ->
    ``narxoz.kz``; ``narxoz.kz.attacker.example`` -> ``attacker.example``)."""
    labels = [part for part in host.lower().strip().rstrip(".").split(".") if part]
    if len(labels) <= 2:
        return ".".join(labels)
    keep = 3 if ".".join(labels[-2:]) in _MULTIPART_PUBLIC_SUFFIXES else 2
    return ".".join(labels[-keep:])


def url_matches_domains(url: str, allowed_domains: Iterable[str]) -> bool:
    """True when the URL's HOST belongs to one of the allowed domains.

    Only the host decides: the university's name inside a query parameter or
    a path segment is a spoof, not a source.
    """
    host = urlparse(url).hostname or ""
    registrable = registrable_domain(host)
    return any(registrable == registrable_domain(d) for d in allowed_domains if d)


# --- the page-type table ----------------------------------------------------
#
# domain/ cannot import the classifier, so the table is keyed by page-type
# string values; PageType members interop with these directly. The families
# mirror page_classifier.ACCEPTS, and a consistency test in the QA suite
# imports both sides and guards the mirror page by page.

_PROGRAM_PAGES: Final[frozenset[str]] = frozenset({"program_detail", "intake_specific_program"})
_REQUIREMENTS_PAGES: Final[frozenset[str]] = frozenset(
    {
        "program_detail",
        "intake_specific_program",
        "general_admissions",
        "country_credential_requirements",
    }
)
_COSTS_PAGES: Final[frozenset[str]] = frozenset(
    {"costs", "program_detail", "intake_specific_program"}
)
_DOCUMENTS_PAGES: Final[frozenset[str]] = frozenset(
    {
        "documents",
        "program_detail",
        "intake_specific_program",
        "general_admissions",
        "scholarship_award",
    }
)
_SCHOLARSHIP_AWARD_PAGES: Final[frozenset[str]] = frozenset({"scholarship_award"})

CLAIM_TYPE_PAGE_TYPES: Final[Mapping[ClaimType, frozenset[str]]] = MappingProxyType(
    {
        # program_exists family
        ClaimType.PROGRAM_EXISTS: _PROGRAM_PAGES,
        # requirements family
        ClaimType.IELTS_MIN_OVERALL: _REQUIREMENTS_PAGES,
        ClaimType.IELTS_MIN_SUBSCORE: _REQUIREMENTS_PAGES,
        ClaimType.IELTS_ACCEPTED_TYPES: _REQUIREMENTS_PAGES,
        ClaimType.TOEFL_MIN_TOTAL: _REQUIREMENTS_PAGES,
        ClaimType.DUOLINGO_MIN: _REQUIREMENTS_PAGES,
        ClaimType.MIN_GPA: _REQUIREMENTS_PAGES,
        ClaimType.GPA_SCALE: _REQUIREMENTS_PAGES,
        ClaimType.SAT_POLICY: _REQUIREMENTS_PAGES,
        ClaimType.SAT_MIN_TOTAL: _REQUIREMENTS_PAGES,
        ClaimType.SUPERSCORE_POLICY: _REQUIREMENTS_PAGES,
        ClaimType.ADMISSION_DEADLINE: _REQUIREMENTS_PAGES,
        ClaimType.PORTFOLIO_REQUIRED: _REQUIREMENTS_PAGES,
        ClaimType.INTERVIEW_REQUIRED: _REQUIREMENTS_PAGES,
        ClaimType.ENTRANCE_EXAM_REQUIRED: _REQUIREMENTS_PAGES,
        ClaimType.CREDENTIAL_EVALUATION_REQUIRED: _REQUIREMENTS_PAGES,
        ClaimType.APPLICATION_FEE: _REQUIREMENTS_PAGES,
        ClaimType.FEE_WAIVER_AVAILABLE: _REQUIREMENTS_PAGES,
        # intake family
        ClaimType.INTAKE_OPEN: _PROGRAM_PAGES,
        # costs family
        ClaimType.TUITION: _COSTS_PAGES,
        ClaimType.MANDATORY_FEES: _COSTS_PAGES,
        ClaimType.HOUSING_COST: _COSTS_PAGES,
        ClaimType.MEALS_COST: _COSTS_PAGES,
        ClaimType.HEALTH_INSURANCE_COST: _COSTS_PAGES,
        ClaimType.BOOKS_COST: _COSTS_PAGES,
        ClaimType.TOTAL_COST_OF_ATTENDANCE: _COSTS_PAGES,
        # documents family
        ClaimType.REQUIRED_DOCUMENT: _DOCUMENTS_PAGES,
        ClaimType.ESSAY_PROMPT: _DOCUMENTS_PAGES,
        ClaimType.RECOMMENDATION_REQUIREMENT: _DOCUMENTS_PAGES,
        # scholarship_award family
        ClaimType.SCHOLARSHIP_EXISTS: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_AMOUNT: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_COVERAGE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_APPLICATION_MODE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_DEADLINE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_RENEWABLE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_RENEWAL_REQUIREMENT: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_MIN_TEST_SCORE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_STACKABLE: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_COUNT: _SCHOLARSHIP_AWARD_PAGES,
        ClaimType.SCHOLARSHIP_DURATION_YEARS: _SCHOLARSHIP_AWARD_PAGES,
    }
)


def page_type_admits(claim_type: ClaimType, page_type: str) -> bool:
    """True when this class of page can answer this claim type's question.

    Claim types outside the table (no extractor family produces them from a
    classified page) admit nothing.
    """
    return page_type in CLAIM_TYPE_PAGE_TYPES.get(claim_type, frozenset())


# --- the seam ---------------------------------------------------------------


def verify_claim(claim: VerificationInput) -> Verdict:
    """Check one candidate claim: excerpt -> value -> domain -> page_type.

    First failure wins; a fully supported claim is accepted with no reason.
    """
    today = claim.today or date.today()
    if (
        claim.page_text is not None
        and claim.excerpt
        and not is_verbatim_excerpt(claim.excerpt.casefold(), claim.page_text.casefold())
    ):
        return Verdict(False, RejectReason.EXCERPT_NOT_VERBATIM)
    if not value_in_range(claim.claim_type, claim.value, today=today):
        return Verdict(False, RejectReason.VALUE_OUT_OF_RANGE)
    if (
        claim.official_domain
        and claim.allowed_domains
        and claim.source_url
        and not url_matches_domains(claim.source_url, claim.allowed_domains)
    ):
        return Verdict(False, RejectReason.DOMAIN_NOT_OFFICIAL)
    if claim.page_type is not None and not page_type_admits(claim.claim_type, claim.page_type):
        return Verdict(False, RejectReason.PAGE_TYPE_REJECTED)
    return Verdict(True, None)
