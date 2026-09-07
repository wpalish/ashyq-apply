"""Contract tests for ``app.domain.claim_verifier`` (T27).

RED at baseline 28d729c via ImportError: the frozen module does not exist
yet. That is the accepted new-module RED pattern and no shim is added to fake
it green. Once the module lands, every assertion below must pass UNCHANGED —
this file pins the frozen API from planner.md (c2-t27-a1):

- ``RejectReason`` (StrEnum): EXCERPT_NOT_VERBATIM / VALUE_OUT_OF_RANGE /
  DOMAIN_NOT_OFFICIAL / PAGE_TYPE_REJECTED
- ``VerificationInput``: claim_type, value, excerpt, page_text, source_url,
  page_type, official_domain, allowed_domains, today: date. Absent context is
  None/empty, and a check whose context is absent is NOT evaluated — it never
  rejects.
- ``Verdict``: accepted, reason (None when accepted)
- ``verify_claim(VerificationInput) -> Verdict``, first-fail order
  excerpt -> value -> domain -> page_type
- ``normalize_text(text)``: NFKC + Unicode-whitespace-run collapse + strip
- ``is_verbatim_excerpt(excerpt, page_text)``: case-sensitive substring after
  normalisation of BOTH sides
- ``value_in_range(claim_type, value, *, today)``: DATA table — IELTS 0-9 in
  steps of 0.5, TOEFL 0-120, Duolingo 0-160, SAT 0-1600, money amount > 0,
  ADMISSION_DEADLINE ISO date (format-only) or bare year >= today.year
- ``url_matches_domains(url, allowed_domains)``: host suffix-match on the
  registrable domain; occurrences in the query string or path NEVER match
- ``registrable_domain(host)``: registrable domain of a host
- ``page_type_admits(claim_type, page_type)``: the CLAIM_TYPE_PAGE_TYPES
  table, mirroring the page_classifier ACCEPTS families (guarded below by a
  test that imports both sides)

domain/ must not import app.adapters.*, so page_type is matched by its string
value; PageType members are StrEnum and compare (and hash) equal to their
values, which the tests below rely on in both directions.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.adapters.page_classifier import ACCEPTS, PageType
from app.domain.claim_verifier import (
    RejectReason,
    Verdict,
    VerificationInput,
    is_verbatim_excerpt,
    normalize_text,
    page_type_admits,
    registrable_domain,
    url_matches_domains,
    value_in_range,
    verify_claim,
)
from app.domain.enums import ClaimType

TODAY = date(2026, 9, 7)


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_unicode_spaces_collapse_to_plain_spaces(self):
        text = "Fee\u00a0waivers\u2003are\u2009not\u000bavailable"
        assert normalize_text(text) == "Fee waivers are not available"

    def test_whitespace_runs_collapse_to_one_space(self):
        assert normalize_text("a  b \t c\nd\r\ne") == "a b c d e"

    def test_nfkc_folds_compatibility_forms(self):
        assert normalize_text("\uff29\uff25\uff2c\uff34\uff33 \ufb01ne") == "IELTS fine"

    def test_ends_are_stripped(self):
        assert normalize_text("  quoted evidence  ") == "quoted evidence"


# ---------------------------------------------------------------------------
# is_verbatim_excerpt
# ---------------------------------------------------------------------------


class TestIsVerbatimExcerpt:
    PAGE = "Applicants must document an overall band of 6.5 in IELTS\u00a0Academic."

    def test_a_real_substring_is_verbatim(self):
        assert is_verbatim_excerpt("an overall band of 6.5", self.PAGE) is True

    def test_normalisation_applies_to_both_sides(self):
        assert is_verbatim_excerpt("an overall band  of 6.5 in IELTS Academic", self.PAGE) is True

    def test_an_excerpt_is_still_verbatim_when_the_page_wraps_lines(self):
        assert is_verbatim_excerpt("band of\n6.5", "an overall band of 6.5") is True

    def test_a_paraphrase_is_not_verbatim(self):
        assert is_verbatim_excerpt("an overall band of about 6.5", self.PAGE) is False

    def test_a_near_miss_is_not_verbatim(self):
        assert is_verbatim_excerpt("an overall band of 6.50", self.PAGE) is False

    def test_matching_is_case_sensitive(self):
        assert is_verbatim_excerpt("An Overall Band of 6.5", self.PAGE) is False


# ---------------------------------------------------------------------------
# value_in_range — the DATA table, with today injected
# ---------------------------------------------------------------------------


class TestValueInRange:
    @pytest.mark.parametrize(
        ("claim_type", "value", "expected"),
        [
            # IELTS 0-9 in steps of 0.5: the step is part of the rule.
            (ClaimType.IELTS_MIN_OVERALL, 0.0, True),
            (ClaimType.IELTS_MIN_OVERALL, 4.0, True),
            (ClaimType.IELTS_MIN_OVERALL, 6.5, True),
            (ClaimType.IELTS_MIN_OVERALL, 9.0, True),
            (ClaimType.IELTS_MIN_OVERALL, 9.5, False),
            (ClaimType.IELTS_MIN_OVERALL, 6.25, False),
            (ClaimType.IELTS_MIN_OVERALL, -1.0, False),
            (ClaimType.IELTS_MIN_SUBSCORE, 6.0, True),
            (ClaimType.IELTS_MIN_SUBSCORE, 6.25, False),
            (ClaimType.TOEFL_MIN_TOTAL, 0, True),
            (ClaimType.TOEFL_MIN_TOTAL, 90, True),
            (ClaimType.TOEFL_MIN_TOTAL, 120, True),
            (ClaimType.TOEFL_MIN_TOTAL, 121, False),
            (ClaimType.DUOLINGO_MIN, 60, True),
            (ClaimType.DUOLINGO_MIN, 160, True),
            (ClaimType.DUOLINGO_MIN, 161, False),
            (ClaimType.SAT_MIN_TOTAL, 400, True),
            (ClaimType.SAT_MIN_TOTAL, 1600, True),
            (ClaimType.SAT_MIN_TOTAL, 1601, False),
            # Money: amount > 0. The tuition floor is an extract_costs
            # constant, not the verifier's band — a $50 application fee is a
            # perfectly valid APPLICATION_FEE.
            (ClaimType.APPLICATION_FEE, {"amount": 50.0, "currency": "USD"}, True),
            (ClaimType.TUITION, {"amount": 4500.0, "currency": "USD"}, True),
            (ClaimType.TUITION, {"amount": 0.0, "currency": "USD"}, False),
            (ClaimType.HOUSING_COST, {"amount": -5.0, "currency": "USD"}, False),
            # Deadline: ISO format only; a bare year must not be in the past.
            (ClaimType.ADMISSION_DEADLINE, "2027-01-15", True),
            (ClaimType.ADMISSION_DEADLINE, "15 January 2027", False),
            (ClaimType.ADMISSION_DEADLINE, "2026", True),
            (ClaimType.ADMISSION_DEADLINE, "2027", True),
            (ClaimType.ADMISSION_DEADLINE, "2024", False),
        ],
    )
    def test_the_range_table(self, claim_type: ClaimType, value: object, expected: bool):
        assert value_in_range(claim_type, value, today=TODAY) is expected

    def test_the_bare_year_boundary_is_today_year(self):
        assert value_in_range(ClaimType.ADMISSION_DEADLINE, "2026", today=TODAY) is True
        assert value_in_range(ClaimType.ADMISSION_DEADLINE, "2025", today=TODAY) is False
        assert value_in_range(ClaimType.ADMISSION_DEADLINE, "2027", today=date(2027, 1, 1)) is True
        assert value_in_range(ClaimType.ADMISSION_DEADLINE, "2026", today=date(2027, 1, 1)) is False

    def test_claim_types_without_a_rule_are_never_out_of_range(self):
        assert value_in_range(ClaimType.FEE_WAIVER_AVAILABLE, True, today=TODAY) is True
        assert value_in_range(ClaimType.INTAKE_OPEN, False, today=TODAY) is True
        assert value_in_range(ClaimType.SAT_POLICY, "test-optional", today=TODAY) is True


# ---------------------------------------------------------------------------
# url_matches_domains / registrable_domain
# ---------------------------------------------------------------------------


class TestUrlMatchesDomains:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://narxoz.kz/admissions", True),
            ("https://www.narxoz.kz/admissions", True),
            ("https://admissions.narxoz.kz/page", True),
            ("https://NARXOZ.KZ/page", True),
            ("fixture://narxoz.kz/admissions", True),
            ("https://narxoz.kz.attacker.example/", False),
            ("https://narxoz.kz.example.com/", False),
            ("https://attacker.example/?u=narxoz.kz", False),
            ("https://attacker.example/narxoz.kz", False),
            ("https://other-university.example/", False),
        ],
    )
    def test_host_suffix_match(self, url: str, expected: bool):
        assert url_matches_domains(url, ["narxoz.kz"]) is expected, (
            f"{url} vs narxoz.kz: only the host's registrable domain decides"
        )

    def test_no_allowed_domains_never_matches(self):
        assert url_matches_domains("https://narxoz.kz/", []) is False

    def test_several_allowed_domains(self):
        assert url_matches_domains("https://www.tudelft.nl/en", ["tudelft.nl", "rug.nl"]) is True
        assert url_matches_domains("https://rug.nl/p", ["tudelft.nl", "rug.nl"]) is True


class TestRegistrableDomain:
    @pytest.mark.parametrize(
        ("host", "expected"),
        [
            ("narxoz.kz", "narxoz.kz"),
            ("www.narxoz.kz", "narxoz.kz"),
            ("admissions.narxoz.kz", "narxoz.kz"),
            ("attacker.example", "attacker.example"),
            ("narxoz.kz.attacker.example", "attacker.example"),
            ("www.tudelft.nl", "tudelft.nl"),
        ],
    )
    def test_the_registrable_domain_of_a_host(self, host: str, expected: str):
        assert registrable_domain(host) == expected


# ---------------------------------------------------------------------------
# page_type_admits — the CLAIM_TYPE_PAGE_TYPES table
# ---------------------------------------------------------------------------


#: Every claim type the codebase actually produces, keyed by the ACCEPTS
#: extractor family whose page classes may answer its question. POST_STUDY_WORK
#: (government adapter) and RANKING_POSITION (fixture ranking) have no ACCEPTS
#: family and stay outside this table.
FAMILY_CLAIM_TYPES: dict[str, set[ClaimType]] = {
    "program_exists": {ClaimType.PROGRAM_EXISTS},
    "requirements": {
        ClaimType.IELTS_MIN_OVERALL,
        ClaimType.IELTS_MIN_SUBSCORE,
        ClaimType.IELTS_ACCEPTED_TYPES,
        ClaimType.TOEFL_MIN_TOTAL,
        ClaimType.DUOLINGO_MIN,
        ClaimType.MIN_GPA,
        ClaimType.GPA_SCALE,
        ClaimType.SAT_POLICY,
        ClaimType.SAT_MIN_TOTAL,
        ClaimType.SUPERSCORE_POLICY,
        ClaimType.ADMISSION_DEADLINE,
        ClaimType.PORTFOLIO_REQUIRED,
        ClaimType.INTERVIEW_REQUIRED,
        ClaimType.ENTRANCE_EXAM_REQUIRED,
        ClaimType.CREDENTIAL_EVALUATION_REQUIRED,
        ClaimType.APPLICATION_FEE,
        ClaimType.FEE_WAIVER_AVAILABLE,
    },
    "intake": {ClaimType.INTAKE_OPEN},
    "costs": {
        ClaimType.TUITION,
        ClaimType.MANDATORY_FEES,
        ClaimType.HOUSING_COST,
        ClaimType.MEALS_COST,
        ClaimType.HEALTH_INSURANCE_COST,
        ClaimType.BOOKS_COST,
        ClaimType.TOTAL_COST_OF_ATTENDANCE,
    },
    "documents": {
        ClaimType.REQUIRED_DOCUMENT,
        ClaimType.ESSAY_PROMPT,
        ClaimType.RECOMMENDATION_REQUIREMENT,
    },
    "scholarship_award": {
        ClaimType.SCHOLARSHIP_EXISTS,
        ClaimType.SCHOLARSHIP_AMOUNT,
        ClaimType.SCHOLARSHIP_COVERAGE,
        ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE,
        ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION,
        ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION,
        ClaimType.SCHOLARSHIP_APPLICATION_MODE,
        ClaimType.SCHOLARSHIP_DEADLINE,
        ClaimType.SCHOLARSHIP_RENEWABLE,
        ClaimType.SCHOLARSHIP_RENEWAL_REQUIREMENT,
        ClaimType.SCHOLARSHIP_MIN_TEST_SCORE,
        ClaimType.SCHOLARSHIP_STACKABLE,
        ClaimType.SCHOLARSHIP_COUNT,
        ClaimType.SCHOLARSHIP_DURATION_YEARS,
    },
}


class TestPageTypeAdmits:
    @pytest.mark.parametrize(
        ("claim_type", "page_type", "expected"),
        [
            (ClaimType.TUITION, PageType.COSTS, True),
            (ClaimType.TUITION, PageType.GENERAL_ADMISSIONS, False),
            (ClaimType.IELTS_MIN_OVERALL, PageType.GENERAL_ADMISSIONS, True),
            (ClaimType.IELTS_MIN_OVERALL, PageType.COSTS, False),
            (ClaimType.PROGRAM_EXISTS, PageType.PROGRAM_DETAIL, True),
            (ClaimType.PROGRAM_EXISTS, PageType.GENERAL_ADMISSIONS, False),
            (ClaimType.INTAKE_OPEN, PageType.INTAKE_SPECIFIC_PROGRAM, True),
            (ClaimType.INTAKE_OPEN, PageType.COSTS, False),
            (ClaimType.APPLICATION_FEE, PageType.PROGRAM_DETAIL, True),
            (ClaimType.FEE_WAIVER_AVAILABLE, PageType.NEWS, False),
            (ClaimType.SCHOLARSHIP_AMOUNT, PageType.SCHOLARSHIP_AWARD, True),
            (ClaimType.SCHOLARSHIP_AMOUNT, PageType.PROGRAM_DETAIL, False),
            (ClaimType.REQUIRED_DOCUMENT, PageType.DOCUMENTS, True),
            (ClaimType.TUITION, PageType.UNKNOWN, False),
        ],
    )
    def test_the_matrix(self, claim_type: ClaimType, page_type: PageType, expected: bool) -> None:
        assert page_type_admits(claim_type, page_type) is expected

    def test_page_type_is_matched_by_its_string_value(self):
        """domain/ cannot import the classifier: plain strings must interop."""
        assert page_type_admits(ClaimType.TUITION, "costs") is True
        assert page_type_admits(ClaimType.TUITION, "general_admissions") is False

    def test_the_table_mirrors_the_classifier_accepts_families(self):
        """Consistency guard, both sides imported: for every claim type, the
        verifier's answer must agree with ACCEPTS for its family page by page
        — the verifier must never accept a page class the extractor itself
        would have skipped, nor reject one the extractor runs on."""
        for family, claim_types in FAMILY_CLAIM_TYPES.items():
            for claim_type in claim_types:
                for page_type in PageType:
                    expected = page_type in ACCEPTS[family]
                    assert page_type_admits(claim_type, page_type) is expected, (
                        f"{claim_type} vs {page_type}: page_type_admits disagrees "
                        f"with ACCEPTS['{family}']"
                    )


# ---------------------------------------------------------------------------
# verify_claim — the seam, with first-fail ordering
# ---------------------------------------------------------------------------


def _input(**overrides: object) -> VerificationInput:
    fields: dict[str, object] = {
        "claim_type": ClaimType.IELTS_MIN_OVERALL,
        "value": 6.5,
        "excerpt": "an overall band of 6.5",
        "page_text": "Applicants must document an overall band of 6.5 in IELTS Academic.",
        "source_url": "https://www.narxoz.kz/admissions",
        "page_type": "general_admissions",
        "official_domain": True,
        "allowed_domains": ("narxoz.kz",),
        "today": TODAY,
    }
    fields.update(overrides)
    return VerificationInput(**fields)  # type: ignore[arg-type]


class TestVerifyClaim:
    def test_a_fully_supported_claim_is_accepted(self):
        verdict = verify_claim(_input())
        assert isinstance(verdict, Verdict)
        assert verdict.accepted is True
        assert verdict.reason is None

    # --- first-fail order: excerpt -> value -> domain -> page_type --------

    def test_the_excerpt_is_checked_first(self):
        verdict = verify_claim(
            _input(
                excerpt="an overall band of 7.5",
                value=9.5,
                source_url="https://attacker.example/?u=narxoz.kz",
                page_type="costs",
            )
        )
        assert verdict.accepted is False
        assert verdict.reason is RejectReason.EXCERPT_NOT_VERBATIM

    def test_the_value_is_checked_second(self):
        verdict = verify_claim(
            _input(
                value=9.5,
                source_url="https://attacker.example/?u=narxoz.kz",
                page_type="costs",
            )
        )
        assert verdict.accepted is False
        assert verdict.reason is RejectReason.VALUE_OUT_OF_RANGE

    def test_the_domain_is_checked_third(self):
        verdict = verify_claim(
            _input(source_url="https://attacker.example/?u=narxoz.kz", page_type="costs")
        )
        assert verdict.accepted is False
        assert verdict.reason is RejectReason.DOMAIN_NOT_OFFICIAL

    def test_the_page_type_is_checked_last(self):
        verdict = verify_claim(_input(page_type="costs"))
        assert verdict.accepted is False
        assert verdict.reason is RejectReason.PAGE_TYPE_REJECTED

    # --- absent context is not evaluated and never rejects -----------------

    def test_no_page_text_skips_the_excerpt_check(self):
        assert verify_claim(_input(page_text=None, excerpt="whatever")).accepted is True

    def test_an_unofficial_source_skips_the_domain_check(self):
        verdict = verify_claim(
            _input(
                official_domain=False,
                source_url="https://attacker.example/?u=narxoz.kz",
            )
        )
        assert verdict.accepted is True

    def test_empty_allowed_domains_skip_the_domain_check(self):
        assert verify_claim(_input(allowed_domains=())).accepted is True

    def test_no_page_type_skips_the_page_type_check(self):
        assert verify_claim(_input(page_type=None)).accepted is True

    # --- the range rules bite through verify_claim too ---------------------

    def test_an_out_of_range_value_is_rejected(self):
        verdict = verify_claim(_input(value=9.5))
        assert verdict.accepted is False
        assert verdict.reason is RejectReason.VALUE_OUT_OF_RANGE

    def test_a_zero_money_amount_is_rejected(self):
        verdict = verify_claim(
            _input(
                claim_type=ClaimType.TUITION,
                value={"amount": 0.0, "currency": "USD"},
                excerpt="tuition is $0 per year",
                page_text="Tuition is $0 per year for the first cohort.",
            )
        )
        assert (verdict.accepted, verdict.reason) == (False, RejectReason.VALUE_OUT_OF_RANGE)

    def test_the_bare_year_rule_uses_the_injected_today(self):
        current = verify_claim(
            _input(
                claim_type=ClaimType.ADMISSION_DEADLINE,
                value="2026",
                excerpt="2026",
                page_text="The intake year 2026 opens in autumn.",
            )
        )
        assert current.accepted is True

        boundary = verify_claim(
            _input(
                claim_type=ClaimType.ADMISSION_DEADLINE,
                value="2027",
                excerpt="2027",
                page_text="The intake year 2027 opens in autumn.",
                today=date(2027, 1, 1),
            )
        )
        assert boundary.accepted is True

        past = verify_claim(
            _input(
                claim_type=ClaimType.ADMISSION_DEADLINE,
                value="2024",
                excerpt="2024",
                page_text="The intake year 2024 has closed.",
            )
        )
        assert (past.accepted, past.reason) == (False, RejectReason.VALUE_OUT_OF_RANGE)


# ---------------------------------------------------------------------------
# multi-part public suffix agreement (T27 A2 — reviewer blocking F1)
# ---------------------------------------------------------------------------


class TestMultiPartPublicSuffixAgreement:
    """``claim_verifier._MULTIPART_PUBLIC_SUFFIXES`` and the discovery layer's
    ``live_discovery.MULTIPART_SUFFIXES`` must agree. For a host under a
    multi-part suffix the verifier does not list, ``registrable_domain``
    returns the public suffix itself, so two different universities under the
    same suffix collapse into one "registrable domain":

    registrable_domain("uw.edu.pl") -> "edu.pl" == registrable_domain("pw.edu.pl")
    -> url_matches_domains True -> is_official_domain True -> VERIFIED_CURRENT
    claims published from a DIFFERENT institution's page. For *.edu.kz (the
    home market) the official-domain check is entirely vacuous.
    """

    def test_a_sibling_university_under_edu_pl_is_not_the_allowed_domain(self):
        assert url_matches_domains("https://pw.edu.pl/admissions", ["uw.edu.pl"]) is False, (
            "pw.edu.pl and uw.edu.pl are different institutions; sharing the "
            "edu.pl public suffix must not make one official for the other"
        )

    def test_a_sibling_university_under_edu_kz_is_not_the_allowed_domain(self):
        assert url_matches_domains("https://iab.edu.kz/", ["kbtu.edu.kz"]) is False, (
            "iab.edu.kz and kbtu.edu.kz are different institutions; the *.edu.kz "
            "suffix must not make the domain check vacuous on the home market"
        )

    def test_the_registrable_domain_of_an_edu_pl_host_is_not_the_public_suffix(self):
        assert registrable_domain("uw.edu.pl") == "uw.edu.pl"

    def test_the_registrable_domain_of_an_edu_kz_host_is_not_the_public_suffix(self):
        assert registrable_domain("iab.edu.kz") == "iab.edu.kz"

    def test_a_listed_suffix_still_resolves_to_the_registrable_domain(self):
        """Positive pin: suffixes already in the verifier's table keep their
        behaviour — the fix must widen the table, not rewire resolution."""
        assert registrable_domain("www.ox.ac.uk") == "ox.ac.uk"
        assert url_matches_domains("https://www.ox.ac.uk/x", ["ox.ac.uk"]) is True

    def test_the_verifier_suffix_table_covers_the_discovery_table(self):
        """Structural guard against future divergence, both sides imported:
        every multi-part suffix the discovery layer knows must also be known
        to the verifier. domain/ may not import app.adapters.*, so the test
        holds the two tables next to each other (the same pattern as the
        page-type mirror guard above)."""
        from app.adapters.discovery.live_discovery import MULTIPART_SUFFIXES
        from app.domain import claim_verifier

        missing = sorted(set(MULTIPART_SUFFIXES) - set(claim_verifier._MULTIPART_PUBLIC_SUFFIXES))
        assert not missing, (
            "claim_verifier._MULTIPART_PUBLIC_SUFFIXES is missing multi-part "
            f"public suffixes known to live_discovery.MULTIPART_SUFFIXES: {missing}"
        )

    @pytest.mark.asyncio
    async def test_a_sibling_university_page_is_never_verified_current(self, tmp_path, monkeypatch):
        """End to end, through the requirements adapter (harness pattern of
        test_live_regressions.TestSpoofedOfficialDomain): a page with readable
        IELTS requirements served from pw.edu.pl must not publish
        VERIFIED_CURRENT claims for a candidate whose domain is uw.edu.pl."""
        from datetime import UTC, datetime

        from app.adapters.base import Candidate, CandidateProgram
        from app.adapters.fetching import Fetcher, FetchResult
        from app.adapters.requirements.web_requirements import WebRequirementsAdapter
        from app.domain.enums import ClaimStatus, DegreeLevel, FetchOutcome

        url = "https://pw.edu.pl/admissions/requirements"
        html = (
            '<!doctype html><html lang="en"><head><title>Admission requirements '
            "| pw.edu.pl admissions</title></head><body><main><h1>Admission "
            "requirements</h1><p>An IELTS Academic score with an overall band of "
            "6.5 is required for programmes taught in English.</p></main></body></html>"
        )

        async def fake_get(fetched_url: str, *, use_cache: bool = True) -> FetchResult:
            return FetchResult(
                url=fetched_url,
                outcome=FetchOutcome.OK,
                status_code=200,
                content=html.encode(),
                text=html,
                content_type="text/html; charset=utf-8",
                fetched_at=datetime.now(UTC),
                final_url=fetched_url,
            )

        async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
            monkeypatch.setattr(fetcher, "get", fake_get)
            candidate = Candidate(
                name="University of Warsaw", country="Poland", city="Warsaw", domain="uw.edu.pl"
            )
            program = CandidateProgram(
                name="computer science (bachelor)",
                field="computer science",
                degree=DegreeLevel.BACHELOR,
                url=url,
            )
            result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
                candidate, program, "fall 2027"
            )

        assert result.claims, (
            "the pw.edu.pl page does carry readable requirements; what must "
            "change is their status, not their existence"
        )
        verified = [c for c in result.claims if c.status is ClaimStatus.VERIFIED_CURRENT]
        assert not verified, (
            "a page served from pw.edu.pl must not publish VERIFIED_CURRENT "
            "claims for candidate uw.edu.pl: "
            f"{[(c.claim_type, c.normalized_value) for c in verified]}"
        )
