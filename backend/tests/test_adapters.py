"""Extraction, fetching politeness and the privacy guard."""

from __future__ import annotations

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.discovery.fixture_discovery import FixtureDiscoveryAdapter
from app.adapters.extraction import (
    ClaimBuilder,
    extract_costs,
    extract_requirements,
    html_to_text,
    is_official_domain,
    parse_date_string,
    parse_money,
    parse_timezone,
    pdf_to_text,
)
from app.adapters.fetching import Fetcher, PIILeakError, assert_no_pii
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship.web_scholarships import (
    WebScholarshipAdapter,
    _award_links,
)
from app.domain.enums import ClaimType, FetchOutcome
from app.domain.funding import classify


def builder(**kwargs) -> ClaimBuilder:
    kwargs.setdefault("source_url", "https://uni.edu/programme")
    kwargs.setdefault("specificity", "program_intake")
    kwargs.setdefault("official_domain", True)
    return ClaimBuilder(**kwargs)


class TestParsing:
    @pytest.mark.parametrize("text,expected", [
        ("EUR 450 per year", (450.0, "EUR")),
        ("$42,500", (42500.0, "USD")),
        ("USD 100 applies", (100.0, "USD")),
        ("JPY 535,800", (535800.0, "JPY")),
        ("CHF 1,580", (1580.0, "CHF")),
        ("16 500 EUR", (16500.0, "EUR")),
    ])
    def test_money_is_parsed_with_its_currency(self, text, expected):
        assert parse_money(text) == expected

    @pytest.mark.parametrize("text", ["overall band of 6.5", "in 2027", "no figures here"])
    def test_bare_numbers_are_never_read_as_money(self, text):
        assert parse_money(text) is None

    @pytest.mark.parametrize("raw,iso", [
        ("15 January 2027", "2027-01-15"),
        ("January 15, 2027", "2027-01-15"),
        ("2027-01-15", "2027-01-15"),
        ("5 September 2027", "2027-09-05"),
    ])
    def test_dates_are_parsed_in_the_formats_universities_publish(self, raw, iso):
        assert parse_date_string(raw).isoformat() == iso

    def test_an_unparseable_date_returns_none_rather_than_a_guess(self):
        assert parse_date_string("rolling admission") is None

    def test_a_timezone_is_captured_when_published(self):
        assert parse_timezone("closes 23:59 CET") == "CET"

    def test_official_domains_are_recognised(self):
        assert is_official_domain("https://www.asu.edu/x")
        assert is_official_domain("https://www.ox.ac.uk/y")
        assert not is_official_domain("https://rankings.example.com/z")
        assert is_official_domain("https://rug.nl/p", ["rug.nl"])


class TestRequirementExtraction:
    TEXT = """English language requirements: applicants must have an IELTS Academic score
with an overall band of 6.5, with no individual component below 6.0. TOEFL iBT 90 is accepted.
A minimum GPA of 3.0 out of 4.0 scale is required. We are test-optional for 2027 entry.
The application deadline is 15 January 2027 at 23:59 CET. A portfolio is required."""

    def test_a_requirement_split_across_a_line_break_is_still_found(self):
        """Real pages wrap mid-clause; the extractor must not lose the value."""
        claims = extract_requirements(self.TEXT, builder())
        by_type = {c.claim_type: c.normalized_value for c in claims}
        assert by_type[ClaimType.IELTS_MIN_OVERALL] == 6.5

    def test_every_published_requirement_in_the_sample_is_extracted(self):
        by_type = {c.claim_type: c.normalized_value for c in extract_requirements(self.TEXT, builder())}
        assert by_type[ClaimType.IELTS_MIN_SUBSCORE] == 6.0
        assert by_type[ClaimType.TOEFL_MIN_TOTAL] == 90
        assert by_type[ClaimType.MIN_GPA] == 3.0
        assert by_type[ClaimType.GPA_SCALE] == 4.0
        assert by_type[ClaimType.ADMISSION_DEADLINE] == "2027-01-15"
        assert by_type[ClaimType.PORTFOLIO_REQUIRED] is True

    def test_every_claim_keeps_the_text_it_came_from(self):
        for claim in extract_requirements(self.TEXT, builder()):
            assert claim.original_text_excerpt, f"{claim.claim_type} has no excerpt"

    def test_a_deadline_records_its_timezone(self):
        deadline = next(c for c in extract_requirements(self.TEXT, builder())
                        if c.claim_type is ClaimType.ADMISSION_DEADLINE)
        assert "CET" in deadline.notes

    def test_a_page_with_no_requirements_yields_nothing_rather_than_defaults(self):
        assert extract_requirements("Welcome to our university. We have a nice campus.", builder()) == []

    def test_an_unofficial_page_cannot_produce_a_verified_claim(self):
        claims = extract_requirements(
            self.TEXT, builder(official_domain=False, specificity="aggregator")
        )
        assert all(c.status.value == "UNVERIFIED" for c in claims)


class TestCostExtraction:
    def test_labelled_costs_are_extracted_with_their_currency(self):
        text = ("Tuition fee for international students: USD 42,500 per year. "
                "Housing costs approximately $11,200. Meal plan: $6,400.")
        by_type = {c.claim_type: c.normalized_value for c in extract_costs(text, builder())}
        assert by_type[ClaimType.TUITION] == {"amount": 42500.0, "currency": "USD"}
        assert by_type[ClaimType.HOUSING_COST]["amount"] == 11200.0


class TestPrivacyGuard:
    @pytest.mark.parametrize("url", [
        "https://x.com/search?q=someone@example.com",
        "https://x.com/lookup?id=123456789012",
        "https://x.com/a?password=hunter2",
        "https://x.com/a?api_key=abc",
        "https://x.com/a?token=xyz",
    ])
    def test_applicant_data_is_never_placed_in_an_outbound_url(self, url):
        with pytest.raises(PIILeakError):
            assert_no_pii(url)

    @pytest.mark.parametrize("url", [
        "https://www.rug.nl/education/bachelor/computing-science",
        # A numeric CMS node id in a path is not a passport number. Treating it
        # as one made the guard fire on ordinary university URLs.
        "https://www.aalto.fi/en/node/1008496",
        "https://uni.edu/programmes/2026202720282029",
    ])
    def test_an_ordinary_university_url_is_allowed(self, url):
        assert_no_pii(url)

    def test_the_guard_still_catches_an_id_in_a_query_string(self):
        with pytest.raises(PIILeakError):
            assert_no_pii("https://uni.edu/status?applicant=1008496123")

    @pytest.mark.asyncio
    async def test_a_refused_url_skips_that_page_instead_of_ending_the_run(self, tmp_path):
        """One bad link harvested from a page must not abort the research."""
        async with Fetcher(tmp_path / "cache", offline=True) as f:
            result = await f.get("https://uni.edu/x?applicant=1008496123")
        assert result.outcome is FetchOutcome.REFUSED_PRIVACY
        assert "not fetched" in result.error
        assert result.text == ""


class TestFetching:
    @pytest.mark.asyncio
    async def test_offline_mode_reports_unavailability_rather_than_inventing_content(self, tmp_path):
        async with Fetcher(tmp_path / "cache", offline=True) as f:
            result = await f.get("https://example.org/page")
        assert result.outcome is FetchOutcome.NETWORK_UNAVAILABLE
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_a_fixture_url_is_served_from_the_bundled_corpus(self, tmp_path, corpus_dir):
        async with Fetcher(tmp_path / "cache", offline=True, corpus_dir=corpus_dir) as f:
            result = await f.get("fixture://u-groningen/program-0.html")
        assert result.ok
        assert "Computing Science" in result.text

    @pytest.mark.asyncio
    async def test_a_missing_fixture_is_a_404_not_an_empty_page(self, tmp_path, corpus_dir):
        async with Fetcher(tmp_path / "cache", offline=True, corpus_dir=corpus_dir) as f:
            result = await f.get("fixture://nope/missing.html")
        assert not result.ok
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_path_traversal_out_of_the_corpus_is_refused(self, tmp_path, corpus_dir):
        async with Fetcher(tmp_path / "cache", offline=True, corpus_dir=corpus_dir) as f:
            result = await f.get("fixture://../../../etc/passwd")
        assert not result.ok
        assert "traversal" in result.error


class TestPdf:
    def test_the_bundled_pdf_fee_schedule_parses(self, corpus_dir):
        pdf = corpus_dir / "u-groningen" / "fees.pdf"
        text = pdf_to_text(pdf.read_bytes())
        assert "Tuition fee" in text
        assert parse_money(text.splitlines()[3]) is not None

    def test_a_corrupt_pdf_returns_empty_text_rather_than_raising(self):
        assert pdf_to_text(b"not a pdf at all") == ""


class TestHtmlToText:
    def test_scripts_and_styles_are_dropped(self):
        html = "<html><body><script>var x=1</script><style>p{}</style><p>Real content</p></body></html>"
        text = html_to_text(html)
        assert "Real content" in text
        assert "var x" not in text


class TestAdaptersAgainstTheCorpus:
    @pytest.mark.asyncio
    async def test_discovery_returns_the_configured_number_of_candidates(self, settings, profile, corpus_dir):
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            candidates = await FixtureDiscoveryAdapter(f).discover(profile, 40)
        assert 30 <= len(candidates) <= 50
        assert any(c.verifiable for c in candidates)
        assert any(not c.verifiable for c in candidates), "unverifiable leads must be kept, not dropped"

    @pytest.mark.asyncio
    async def test_excluded_countries_are_never_proposed(self, settings, profile, corpus_dir):
        profile.preferences.excluded_countries = ["Netherlands"]
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            candidates = await FixtureDiscoveryAdapter(f).discover(profile, 40)
        assert all(c.country != "Netherlands" for c in candidates)

    @pytest.mark.asyncio
    async def test_the_requirements_adapter_reads_two_sources_and_finds_the_disagreement(
        self, settings, corpus_dir
    ):
        candidate = Candidate(
            name="Delft University of Technology", country="Netherlands", city="Delft",
            domain="tudelft.nl", admissions_url="fixture://tu-delft/admissions.html",
        )
        program = CandidateProgram(name="BSc CSE", field="cs", degree="bachelor",
                                   url="fixture://tu-delft/program-0.html")
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            result = await WebRequirementsAdapter(f, "2026/27").verify(candidate, program, "fall 2027")

        overalls = [c.normalized_value for c in result.claims
                    if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
        assert sorted(overalls) == [6.0, 6.5]
        assert result.pages_checked == 2

    @pytest.mark.asyncio
    async def test_an_unreachable_programme_is_reported_not_skipped(self, settings, corpus_dir):
        candidate = Candidate(name="Gone University", country="X", city="Y",
                              admissions_url="fixture://u-oslo/admissions.html")
        program = CandidateProgram(name="P", field="cs", degree="bachelor", url=None)
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            result = await WebRequirementsAdapter(f, "2026/27").verify(candidate, program, "fall 2027")
        assert result.pages_failed == 1
        assert result.errors

    @pytest.mark.asyncio
    async def test_costs_are_extracted_and_currency_is_preserved(self, settings, corpus_dir):
        candidate = Candidate(name="EPFL", country="Switzerland", city="Lausanne",
                              costs_url="fixture://epfl/costs.html")
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            breakdown, _ = await WebCostAdapter(f, "2026/27").fetch(candidate)
        assert breakdown.items["tuition"].currency == "CHF"
        assert breakdown.academic_year == "2026/27"

    @pytest.mark.asyncio
    async def test_a_missing_scholarship_page_is_an_error_not_an_empty_list(self, settings, corpus_dir):
        candidate = Candidate(name="University of Vienna", country="Austria", city="Vienna",
                              scholarships_url=None)
        program = CandidateProgram(name="P", field="cs", degree="bachelor")
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            awards, result = await WebScholarshipAdapter(f, "2026/27").find(candidate, program, None)
        assert awards == []
        assert "rather than assumed absent" in result.errors[0]

    @pytest.mark.asyncio
    async def test_the_coverage_table_drives_classification_end_to_end(self, settings, corpus_dir):
        """ASU's page says 'a full ride'; its table says tuition and fees only."""
        candidate = Candidate(name="Arizona State University", country="United States", city="Tempe",
                              scholarships_url="fixture://arizona-state/scholarships.html")
        program = CandidateProgram(name="BS CS", field="cs", degree="bachelor")
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            awards, _ = await WebScholarshipAdapter(f, "2026/27").find(candidate, program, None)
        assert len(awards) == 1
        verdict = classify(awards[0], page_text="full ride")
        assert verdict.classification.value == "FULL_TUITION"
        assert verdict.marketing_language_detected

    @pytest.mark.asyncio
    async def test_a_citizenship_restriction_is_read_off_the_page(self, settings, corpus_dir):
        candidate = Candidate(name="KU Leuven", country="Belgium", city="Leuven",
                              scholarships_url="fixture://ku-leuven/scholarships.html")
        program = CandidateProgram(name="BSc Informatics", field="cs", degree="bachelor")
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as f:
            awards, _ = await WebScholarshipAdapter(f, "2026/27").find(candidate, program, None)
        flemish = next(a for a in awards if "Flemish" in a.name)
        assert flemish.international_eligible == "no"
        assert "European Economic Area" in flemish.citizenship_restrictions


class TestAwardLinkFollowing:
    """Regressions from a live run against real university sites.

    Real funding index pages are mostly site furniture. Following every anchor
    turned navigation into scholarships and fabricated 404s from mis-joined
    relative paths.
    """

    def test_a_relative_link_is_resolved_against_the_page_not_appended_to_it(self):
        html = '<a href="/en/scholarships/merit">Merit Scholarship</a>'
        links = _award_links(html, "https://www.aalto.fi/en/admission-services")
        assert links == ["https://www.aalto.fi/en/scholarships/merit"]

    def test_a_dot_relative_link_resolves_against_the_directory(self):
        html = '<a href="merit-award.html">Merit Award</a>'
        links = _award_links(html, "https://uni.edu/funding/index.html")
        assert links == ["https://uni.edu/funding/merit-award.html"]

    def test_fragment_links_are_not_treated_as_separate_awards(self):
        html = """
          <a href="#main-content">Scholarship information</a>
          <a href="/funding/x#navigation">Excellence Scholarship</a>
          <a href="/funding/x#search">Excellence Scholarship</a>
        """
        assert _award_links(html, "https://uni.edu/funding") == ["https://uni.edu/funding/x"]

    def test_navigation_furniture_is_not_followed(self):
        html = """
          <a href="/a">Skip to main content</a>
          <a href="/b">Menu główne</a>
          <a href="/c">Search</a>
          <a href="/d">Privacy policy</a>
        """
        assert _award_links(html, "https://uni.edu/funding") == []

    def test_only_links_that_look_like_an_award_are_followed(self):
        html = """
          <a href="/campus-life">Campus life</a>
          <a href="/news/2026">Latest news</a>
          <a href="/talent-grant">Groningen Talent Grant</a>
        """
        assert _award_links(html, "https://uni.edu/funding") == ["https://uni.edu/talent-grant"]

    def test_an_award_is_recognised_from_its_path_when_the_text_is_generic(self):
        html = '<a href="/international-scholarships/pearson">Read more</a>'
        assert _award_links(html, "https://uni.edu/funding") == [
            "https://uni.edu/international-scholarships/pearson"
        ]

    def test_fixture_urls_still_resolve(self):
        html = '<a href="fixture://u-groningen/scholarship-0.html">Groningen Talent Grant</a>'
        assert _award_links(html, "fixture://u-groningen/scholarships.html") == [
            "fixture://u-groningen/scholarship-0.html"
        ]

    def test_a_share_button_pointing_off_domain_is_not_followed(self):
        """Share links carry the page URL in a query string, so they match hints."""
        html = (
            '<a href="https://www.facebook.com/sharer/sharer.php'
            '?u=https%3A//uni.edu/scholarships">Share</a>'
            '<a href="https://uni.edu/scholarships/merit">Merit Scholarship</a>'
        )
        assert _award_links(html, "https://uni.edu/scholarships") == [
            "https://uni.edu/scholarships/merit"
        ]

    def test_mail_and_script_links_are_ignored(self):
        html = """
          <a href="mailto:scholarships@uni.edu">Scholarship enquiries</a>
          <a href="javascript:void(0)">Scholarship filter</a>
        """
        assert _award_links(html, "https://uni.edu/funding") == []


class TestVerificationCompleteness:
    """Completeness must describe the questions a user needs answered."""

    def test_one_incidental_verified_claim_does_not_read_as_fully_verified(self):
        from app.pipeline.runner import _completeness
        from tests.conftest import make_claim

        claims = [make_claim("scholarship_international_eligible", True)]
        assert _completeness(claims) < 0.25

    def test_answering_every_core_question_reads_as_complete(self):
        from app.pipeline.runner import _completeness
        from tests.conftest import make_claim

        claims = [
            make_claim("ielts_min_overall", 6.5),
            make_claim("min_gpa", 3.0),
            make_claim("admission_deadline", "2027-01-15"),
            make_claim("tuition", {"amount": 20000, "currency": "EUR"}),
            make_claim("scholarship_exists", "Talent Grant"),
            make_claim("scholarship_international_eligible", True),
        ]
        assert _completeness(claims) == 1.0

    def test_nothing_verified_reads_as_nothing(self):
        from app.pipeline.runner import _completeness

        assert _completeness([]) == 0.0

    def test_an_unverified_claim_does_not_count_towards_completeness(self):
        from app.pipeline.runner import _completeness
        from tests.conftest import make_claim

        claims = [make_claim("ielts_min_overall", 6.5, status="UNVERIFIED")]
        assert _completeness(claims) == 0.0


class TestClaimHonesty:
    """A value we could not read must not become a claim."""

    @pytest.mark.asyncio
    async def test_an_unreadable_application_fee_produces_no_claim(self, settings, corpus_dir, tmp_path):
        from app.adapters.requirements.web_requirements import _fee

        # A page that mentions the fee without publishing an amount.
        assert _fee("There is an application fee. Details follow in your offer letter.") is None

    def test_a_readable_application_fee_is_captured_with_its_currency(self):
        from app.adapters.requirements.web_requirements import _fee

        assert _fee("An application fee of USD 100 applies.") == {
            "amount": 100.0,
            "currency": "USD",
        }


class TestTimezoneParsing:
    """A timezone must be read, never inferred from any three-letter word."""

    @pytest.mark.parametrize("text,expected", [
        ("Applications close 15 January 2027 at 23:59 CET", "CET"),
        ("The deadline is 5pm PST", "PST"),
        ("by 17:00 JST", "JST"),
        ("closes 23:59 AEDT", "AEDT"),
    ])
    def test_a_published_timezone_is_captured(self, text, expected):
        from app.adapters.extraction import parse_timezone

        assert parse_timezone(text) == expected

    @pytest.mark.parametrize("text", [
        "We are test-optional; the SAT is not required.",
        "Submit the SAT and ACT if taken.",
        "Applications close 1 May 2027.",
    ])
    def test_an_ordinary_acronym_is_not_read_as_a_timezone(self, text):
        from app.adapters.extraction import parse_timezone

        assert parse_timezone(text) is None
