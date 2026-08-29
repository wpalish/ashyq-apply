"""Sitemap-first live discovery.

Every test here is deterministic and offline: sitemaps and pages are served
from a stub, so the suite never depends on a university's site being up or
unchanged. The live behaviour is measured separately by
``scripts/canary_discovery.py``, whose findings are in
``docs/LIVE_DISCOVERY_REPORT.md``.

The rule these tests exist to protect: discovery says *where to look*, never
*what is true*. A manual seed, a sitemap entry and a navigation link are all
leads; only a fetched and classified page is evidence.
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from typing import ClassVar

import pytest

from app.adapters.discovery.live_discovery import (
    MAX_PAGES_PER_CATEGORY,
    MAX_PROGRAM_CANDIDATES_CHECKED,
    MAX_SITEMAP_DOCUMENTS,
    REGISTRY_PATH,
    LiveDiscoveryAdapter,
    PageCategory,
    SitemapReader,
    canonical_url,
    catalogue_shows_subject,
    categorise_url,
    decode_sitemap,
    looks_like_catalogue,
    matches_degree,
    matches_field,
    parse_sitemap,
    parse_sitemap_directives,
    registrable_domain,
    same_institution,
)
from app.adapters.fetching import Fetcher, FetchResult
from app.domain.enums import FetchOutcome

# --- stub transport -------------------------------------------------------


class StubSite:
    """Serves fixed bodies for fixed URLs through the real Fetcher interface."""

    def __init__(self, pages: dict[str, bytes | str], missing_outcome=FetchOutcome.HTTP_ERROR):
        self.pages = pages
        self.missing_outcome = missing_outcome
        self.requested: list[str] = []

    def install(self, fetcher: Fetcher) -> Fetcher:
        async def fake_get(url: str, *, use_cache: bool = True) -> FetchResult:
            self.requested.append(url)
            body = self.pages.get(url)
            if body is None:
                return FetchResult(
                    url=url, outcome=self.missing_outcome, status_code=404,
                    error="not in this test's page set", final_url=url,
                )
            raw = body.encode() if isinstance(body, str) else body
            return FetchResult(
                url=url, outcome=FetchOutcome.OK, status_code=200, content=raw,
                text=raw.decode("utf-8", errors="replace"),
                content_type="application/xml", fetched_at=datetime.now(UTC), final_url=url,
            )

        fetcher.get = fake_get  # type: ignore[method-assign]
        return fetcher


def sitemap_xml(*locations: str) -> str:
    entries = "".join(f"<url><loc>{loc}</loc></url>" for loc in locations)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</urlset>"
    )


def program_html(name: str = "BSc Computer Science") -> str:
    """A page the classifier recognises as one programme.

    Discovery confirms its programme candidates by reading them, so a stub that
    serves nothing for a candidate URL is a site where that page does not
    exist — and the correct answer there is that no programme was found.
    """
    return (
        f"<html><head><title>{name} - University</title></head><body>"
        "<header><nav><a href='/'>Home</a></nav></header><main>"
        f"<h1>{name}</h1>"
        "<p>This three-year bachelor's degree programme is taught in English. "
        "Entry requirements include IELTS 6.5 overall. Applications close on 1 May.</p>"
        "<h2>Entry requirements</h2><p>A secondary school diploma and IELTS 6.5.</p>"
        "<h2>Tuition fees</h2><p>The tuition fee is EUR 15,000 per year.</p>"
        "</main></body></html>"
    )


def sitemap_index_xml(*locations: str) -> str:
    entries = "".join(f"<sitemap><loc>{loc}</loc></sitemap>" for loc in locations)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</sitemapindex>"
    )


@pytest.fixture
def profile_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


# --- domain and URL handling ---------------------------------------------


class TestRegistrableDomain:
    @pytest.mark.parametrize("host,expected", [
        ("www.rug.nl", "rug.nl"),
        ("rug.nl", "rug.nl"),
        ("studieren.univie.ac.at", "univie.ac.at"),
        ("admissions.hku.hk", "hku.hk"),
        ("www.ntu.edu.sg", "ntu.edu.sg"),
        ("admission.kaist.ac.kr", "kaist.ac.kr"),
        ("you.ubc.ca", "ubc.ca"),
        ("en.uw.edu.pl", "uw.edu.pl"),
    ])
    def test_multipart_suffixes_are_handled(self, host, expected):
        """Taking the last two labels would make every ac.uk site one domain."""
        assert registrable_domain(host) == expected

    @pytest.mark.parametrize("url,domain,same", [
        ("https://www.rug.nl/education", "www.rug.nl", True),
        ("https://rug.nl/education", "www.rug.nl", True),
        ("https://studieren.univie.ac.at/x", "www.univie.ac.at", True),
        ("https://evil.example.com/rug.nl", "www.rug.nl", False),
        ("https://www.tudelft.nl/x", "www.rug.nl", False),
        ("https://other.ac.at/x", "www.univie.ac.at", False),
    ])
    def test_off_domain_urls_are_recognised(self, url, domain, same):
        assert same_institution(url, domain) is same


class TestCanonicalUrl:
    @pytest.mark.parametrize("raw,expected", [
        ("https://WWW.RUG.NL/Education/", "https://www.rug.nl/Education"),
        ("https://www.rug.nl/education#section", "https://www.rug.nl/education"),
        ("https://www.rug.nl/education?utm_source=x", "https://www.rug.nl/education"),
        ("https://www.rug.nl/education?fbclid=abc", "https://www.rug.nl/education"),
        ("https://www.rug.nl:443/education", "https://www.rug.nl/education"),
        ("https://www.rug.nl//education//cs", "https://www.rug.nl/education/cs"),
        ("https://www.rug.nl/", "https://www.rug.nl/"),
    ])
    def test_equivalent_urls_normalise_to_one_form(self, raw, expected):
        assert canonical_url(raw) == expected

    def test_meaningful_query_parameters_are_kept(self):
        """Dropping them would merge genuinely different pages."""
        assert "id=42" in canonical_url("https://uni.edu/p?id=42")

    def test_query_order_does_not_create_a_second_url(self):
        assert canonical_url("https://uni.edu/p?b=2&a=1") == canonical_url(
            "https://uni.edu/p?a=1&b=2"
        )


class TestUrlCategorisation:
    @pytest.mark.parametrize("url,category", [
        ("https://uni.edu/en/education/programmes/bachelors/computer-science", PageCategory.PROGRAM_PAGE),
        # Hyphenated compound, as Vienna publishes it.
        ("https://uni.edu/en/bachelordiploma-programmes/computer-science-bachelor",
         PageCategory.PROGRAM_PAGE),
        ("https://uni.edu/bsc-computer-science", PageCategory.PROGRAM_PAGE),
        ("https://uni.edu/en/education/programmes/bachelors", PageCategory.PROGRAM_CATALOG),
        # Hyphenated compounds: how most universities actually name the page.
        ("https://uni.edu/en/degree-programmes", PageCategory.PROGRAM_CATALOG),
        ("https://uni.edu/education/degree-programmes-1st-2nd-and-long-cycle-programmes",
         PageCategory.PROGRAM_CATALOG),
        ("https://uni.edu/admission-and-application", PageCategory.ADMISSIONS),
        ("https://uni.edu/entry_requirements", PageCategory.ADMISSIONS),
        ("https://uni.edu/tuition-fees", PageCategory.COSTS),
        ("https://uni.edu/cost-of-attendance", PageCategory.COSTS),
        ("https://uni.edu/scholarships", PageCategory.SCHOLARSHIPS),
        ("https://uni.edu/financial_aid", PageCategory.SCHOLARSHIPS),
        ("https://uni.edu/required-documents", PageCategory.DOCUMENTS),
    ])
    def test_urls_are_filed_under_the_right_category(self, url, category):
        assert categorise_url(url)[0] == category

    @pytest.mark.parametrize("url", [
        "https://uni.edu/news/2026/something",
        "https://uni.edu/events/open-day",
        "https://uni.edu/vacancies/professor",
        "https://uni.edu/alumni/donate",
        "https://uni.edu/privacy",
        "https://uni.edu/assets/style.css",
        "https://uni.edu/brochure.pdf.zip",
        "https://uni.edu/library/search",
        # Near-misses for the catalogue pattern: the segment has to end with
        # the listing word, not merely contain it.
        "https://uni.edu/about/degree-ceremony-photos",
        "https://uni.edu/programme-news",
        # Events and newsletters *inside* a programme path — every one of these
        # was returned as a programme page by a live run.
        "https://uni.edu/education/bachelor/bachelor-open-day",
        "https://uni.edu/education/bachelor/onlinebachelorweek",
        "https://uni.edu/education/bachelor/student-for-a-day",
        "https://uni.edu/education/bachelor/campus-tour",
        "https://uni.edu/education/bachelor/online-university-tour",
        "https://uni.edu/education/bachelor/webklassen",
        # A research group's project page is not a degree, whatever its slug.
        "https://uni.edu/research/zernike/a-group/bsc-msc-project-guidelines",
        "https://uni.edu/research/institutes/group/msc-and-bsc-projects",
        "https://uni.edu/en/programmes/elec-student-newsletters",
        "https://uni.edu/sv/program/elec-nyhetsbrev-for-studerande",
        "https://uni.edu/programmes/bachelors/cs-information-session",
    ])
    def test_irrelevant_urls_score_nothing(self, url):
        assert categorise_url(url)[0] is None

    @pytest.mark.parametrize("url,is_catalogue", [
        ("https://uni.edu/en/degree-programmes", True),
        # Scores higher as admissions, but is still worth walking for programmes.
        ("https://uni.edu/applying-ubc/how-to-apply/degrees-programs/", True),
        ("https://uni.edu/studies/programmes", True),
        ("https://uni.edu/about/degree-ceremony-photos", False),
        ("https://uni.edu/programme-news", False),
        ("https://uni.edu/news/2026/new-programme-launched", False),
        ("https://uni.edu/en/education/programmes/bachelors/computer-science", False),
    ])
    def test_whether_a_page_lists_programmes_is_asked_separately(self, url, is_catalogue):
        assert looks_like_catalogue(url) is is_catalogue

    @pytest.mark.parametrize("url", [
        "https://uni.edu/admissions/undergraduate/scholarships/detail/sci-award",
        "https://uni.edu/en/education/programmes/bachelors/funding/award",
        "https://uni.edu/study/financial-aid/undergraduate-grants",
    ])
    def test_a_funding_page_is_never_a_programme(self, url):
        """NTU offered a scholarship page as the applicant's programme page.

        "undergraduate" in the path outscored "scholarships" beside it. Which
        funding category such a URL lands in does not matter; that it is never
        a programme does.
        """
        category = categorise_url(url)[0]
        assert category not in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG)

    def test_the_applicants_subject_outranks_an_unrelated_programme(self):
        """Delft answered a computer science applicant with aerospace.

        Both URLs are structurally identical programme pages, so only the
        subject can separate them, and it has to separate them decisively.
        """
        fields = ["computer science"]
        cs = "https://uni.edu/en/education/programmes/bachelors/bsc-computer-science"
        aero = "https://uni.edu/en/education/programmes/bachelors/ae/bsc-aerospace-engineering"
        cs_total = categorise_url(cs)[1] + matches_field(cs, fields)
        aero_total = categorise_url(aero)[1] + matches_field(aero, fields)
        assert cs_total > aero_total

    def test_a_programme_at_the_wrong_level_is_penalised(self):
        """An MSc page is not a lead for a bachelor applicant."""
        assert matches_degree("https://uni.edu/programmes/masters/cs", "bachelor") < 0
        assert matches_degree("https://uni.edu/programmes/bachelors/cs", "bachelor") > 0


# --- sitemap parsing ------------------------------------------------------


class TestSitemapParsing:
    def test_robots_sitemap_directives_are_read(self):
        robots = (
            "User-agent: *\nDisallow: /private\n"
            "Sitemap: https://uni.edu/sitemap.xml\n"
            "sitemap: https://uni.edu/sitemap-2.xml.gz\n"
        )
        assert parse_sitemap_directives(robots) == [
            "https://uni.edu/sitemap.xml",
            "https://uni.edu/sitemap-2.xml.gz",
        ]

    def test_robots_without_a_sitemap_yields_none(self):
        assert parse_sitemap_directives("User-agent: *\nDisallow: /\n") == []

    def test_a_urlset_yields_pages(self):
        children, pages = parse_sitemap(sitemap_xml("https://uni.edu/a", "https://uni.edu/b"))
        assert children == []
        assert pages == ["https://uni.edu/a", "https://uni.edu/b"]

    def test_a_sitemap_index_yields_children(self):
        children, pages = parse_sitemap(
            sitemap_index_xml("https://uni.edu/s1.xml", "https://uni.edu/s2.xml")
        )
        assert children == ["https://uni.edu/s1.xml", "https://uni.edu/s2.xml"]
        assert pages == []

    def test_malformed_xml_does_not_raise(self):
        assert parse_sitemap("<urlset><loc>broken") == ([], [])

    def test_a_plain_text_sitemap_is_accepted(self):
        """Some sites serve a newline-separated list rather than XML."""
        _, pages = parse_sitemap("https://uni.edu/a\nhttps://uni.edu/b\n")
        assert pages == ["https://uni.edu/a", "https://uni.edu/b"]

    def test_a_gzipped_sitemap_is_decompressed(self):
        raw = gzip.compress(sitemap_xml("https://uni.edu/a").encode())
        text = decode_sitemap(raw, "https://uni.edu/sitemap.xml.gz")
        assert "https://uni.edu/a" in text

    def test_a_corrupt_gzip_yields_empty_text_rather_than_raising(self):
        assert decode_sitemap(b"\x1f\x8bnot-really-gzip", "https://uni.edu/s.xml.gz") == ""


# --- the reader -----------------------------------------------------------


class TestSitemapReader:
    @pytest.mark.asyncio
    async def test_it_follows_a_sitemap_index_into_its_children(self, tmp_path):
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/sitemap_index.xml\n",
            "https://uni.edu/sitemap_index.xml": sitemap_index_xml(
                "https://uni.edu/s-programmes.xml", "https://uni.edu/s-admissions.xml"
            ),
            "https://uni.edu/s-programmes.xml": sitemap_xml(
                "https://uni.edu/programmes/bachelors/computer-science"
            ),
            "https://uni.edu/s-admissions.xml": sitemap_xml("https://uni.edu/admission"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            trace = _trace()
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", trace)

        assert "https://uni.edu/programmes/bachelors/computer-science" in pages
        assert "https://uni.edu/admission" in pages
        assert len(trace.sitemaps_read) == 3

    @pytest.mark.asyncio
    async def test_nested_indexes_are_followed_but_bounded(self, tmp_path):
        """A sitemap index pointing at itself must not loop forever."""
        pages = {
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s0.xml\n",
            "https://uni.edu/s0.xml": sitemap_index_xml("https://uni.edu/s1.xml"),
            "https://uni.edu/s1.xml": sitemap_index_xml("https://uni.edu/s2.xml"),
            "https://uni.edu/s2.xml": sitemap_index_xml("https://uni.edu/s3.xml"),
            "https://uni.edu/s3.xml": sitemap_index_xml("https://uni.edu/s4.xml"),
            "https://uni.edu/s4.xml": sitemap_xml("https://uni.edu/too-deep"),
        }
        site = StubSite(pages)
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            trace = _trace()
            found = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", trace)

        assert "https://uni.edu/too-deep" not in found, "depth bound was not applied"
        assert len(trace.sitemaps_read) <= MAX_SITEMAP_DOCUMENTS

    @pytest.mark.asyncio
    async def test_a_self_referencing_index_terminates(self, tmp_path):
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_index_xml("https://uni.edu/s.xml"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", _trace())
        assert site.requested.count("https://uni.edu/s.xml") == 1

    @pytest.mark.asyncio
    async def test_off_domain_urls_in_a_sitemap_are_dropped(self, tmp_path):
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/programmes/bachelors/cs",
                "https://evil.example.com/programmes/bachelors/cs",
                "https://partner.other.edu/admission",
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            trace = _trace()
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", trace)

        assert pages == ["https://uni.edu/programmes/bachelors/cs"]
        assert any("off the institution's domain" in reason for _u, reason in trace.rejected)

    @pytest.mark.asyncio
    async def test_duplicate_and_equivalent_urls_are_deduplicated(self, tmp_path):
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/programmes/bachelors/cs",
                "https://uni.edu/programmes/bachelors/cs/",
                "https://uni.edu/programmes/bachelors/cs#overview",
                "https://UNI.edu/programmes/bachelors/cs?utm_source=x",
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", _trace())
        assert len(pages) == 1

    @pytest.mark.asyncio
    async def test_conventional_locations_are_tried_when_robots_names_none(self, tmp_path):
        site = StubSite({
            "https://uni.edu/robots.txt": "User-agent: *\nDisallow:\n",
            "https://uni.edu/sitemap.xml": sitemap_xml("https://uni.edu/admission"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", _trace())
        assert pages == ["https://uni.edu/admission"]

    @pytest.mark.asyncio
    async def test_no_sitemap_at_all_is_recorded_not_raised(self, tmp_path):
        site = StubSite({"https://uni.edu/robots.txt": "User-agent: *\n"})
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            trace = _trace()
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", trace)
        assert pages == []
        assert trace.errors

    @pytest.mark.asyncio
    async def test_a_robots_refusal_is_recorded_and_not_worked_around(self, tmp_path):
        """A blocked robots.txt means no sitemap discovery, not a fallback crawl."""
        site = StubSite({}, missing_outcome=FetchOutcome.ROBOTS_DISALLOWED)
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            trace = _trace()
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", trace)
        assert pages == []
        assert any("robots" in e or "robots_disallowed" in e for e in trace.errors)


# --- the adapter ----------------------------------------------------------


class TestAdapter:
    @staticmethod
    def registry_file(tmp_path, entry: dict):
        path = tmp_path / "registry.json"
        path.write_text(json.dumps([entry]))
        return path

    @pytest.mark.asyncio
    async def test_manual_seeds_are_used_and_recorded_with_provenance(
        self, tmp_path, profile_bachelor
    ):
        entry = {
            "name": "Seeded University", "country": "Netherlands", "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {
                "admissions": "https://uni.edu/verified/admission",
                "costs": "https://uni.edu/verified/tuition-fees",
            },
        }
        site = StubSite({"https://uni.edu/robots.txt": "User-agent: *\n"})
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidates = await adapter.discover(profile_bachelor)

        assert candidates[0].admissions_url == "https://uni.edu/verified/admission"
        assert candidates[0].costs_url == "https://uni.edu/verified/tuition-fees"
        trace = adapter.traces[0]
        assert trace.manual_seeds["admissions"] == "https://uni.edu/verified/admission"

    @pytest.mark.asyncio
    async def test_a_manual_seed_is_not_itself_evidence(self, tmp_path, profile_bachelor):
        """A seed says where to look. It confirms nothing about the page.

        Nothing in discovery may set a claim, a requirement or an eligibility
        verdict. Everything it produces is a URL for the classifier to judge.
        """
        entry = {
            "name": "Seeded University", "country": "Netherlands", "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"admissions": "https://uni.edu/verified/admission"},
        }
        site = StubSite({"https://uni.edu/robots.txt": "User-agent: *\n"})
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        # A Candidate carries URLs and attributes only — no claims, no verdicts.
        assert not hasattr(candidate, "claims")
        assert candidate.programs == [], "a seed must not fabricate a programme"
        # And the seeded page was never even fetched by discovery.
        assert "https://uni.edu/verified/admission" not in site.requested

    @pytest.mark.asyncio
    async def test_an_off_domain_manual_seed_is_rejected(self, tmp_path, profile_bachelor):
        entry = {
            "name": "Seeded University", "country": "Netherlands", "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"admissions": "https://evil.example.com/admission"},
        }
        site = StubSite({"https://uni.edu/robots.txt": "User-agent: *\n"})
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.admissions_url is None
        assert any("off the institution's domain" in r for _u, r in adapter.traces[0].rejected)

    @pytest.mark.asyncio
    async def test_a_manual_seed_wins_over_a_discovered_page(self, tmp_path, profile_bachelor):
        """A human-verified URL is a better answer than a scored guess."""
        entry = {
            "name": "Seeded University", "country": "Netherlands", "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"admissions": "https://uni.edu/verified/admission"},
        }
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/discovered/admission-and-application"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.admissions_url == "https://uni.edu/verified/admission"
        # The discovered one is kept as a second lead, not discarded.
        assert "https://uni.edu/discovered/admission-and-application" in \
            adapter.traces[0].selected[PageCategory.ADMISSIONS]

    @pytest.mark.asyncio
    async def test_sitemap_discovery_finds_a_programme_page(self, tmp_path, profile_bachelor):
        entry = {"name": "Sitemapped University", "country": "Netherlands", "city": "X",
                 "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/news/2026/open-day",
                "https://uni.edu/en/education/programmes/bachelors/computer-science",
                "https://uni.edu/en/education/programmes/masters/computer-science",
                "https://uni.edu/tuition-fees",
                "https://uni.edu/scholarships",
            ),
            "https://uni.edu/en/education/programmes/bachelors/computer-science":
                program_html(),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs, "the bachelor programme page was not found"
        assert "bachelors/computer-science" in candidate.programs[0].url
        assert candidate.costs_url == "https://uni.edu/tuition-fees"
        assert candidate.scholarships_url == "https://uni.edu/scholarships"

    @pytest.mark.asyncio
    async def test_the_wrong_degree_level_is_not_offered_first(
        self, tmp_path, profile_bachelor
    ):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/en/education/programmes/masters/computer-science",
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == [], "an MSc page is not a bachelor lead"

    @pytest.mark.asyncio
    async def test_a_candidate_that_reads_as_an_event_is_dropped(
        self, tmp_path, profile_bachelor
    ):
        """Live runs offered open days and campus tours as programme pages.

        They sit under the same path as the real programmes, so no URL rule
        separates them. Reading the page does.
        """
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            # A URL no rule can fault: the right path, the right subject, the
            # right level. Only the page itself reveals it is a visit day.
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/education/bachelor/computer-science-meet-us",
            ),
            "https://uni.edu/education/bachelor/computer-science-meet-us": (
                "<html><head><title>Meet us | Bachelors</title></head><body><main>"
                "<h1>Meet us</h1><p>Come and visit us on campus. "
                "Book a place on a guided tour with a student.</p>"
                "</main></body></html>"
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert any("not a programme page" in reason for _u, reason in adapter.traces[0].rejected)

    @pytest.mark.asyncio
    async def test_a_rejected_candidate_lets_the_next_one_through(
        self, tmp_path, profile_bachelor
    ):
        """Rejecting the top candidate must not mean finding nothing."""
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/programmes/bachelors/computer-science-open-day-2027",
                "https://uni.edu/programmes/bachelors/computer-science",
            ),
            "https://uni.edu/programmes/bachelors/computer-science-open-day-2027": (
                "<html><head><title>Open Day</title></head><body><main><h1>Open Day</h1>"
                "<p>Visit us in March.</p></main></body></html>"
            ),
            "https://uni.edu/programmes/bachelors/computer-science": program_html(),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert [p.url for p in candidate.programs] == [
            "https://uni.edu/programmes/bachelors/computer-science"
        ]

    @pytest.mark.asyncio
    async def test_an_unreadable_candidate_is_reported_not_promoted(
        self, tmp_path, profile_bachelor
    ):
        """A page we could not read is not a confirmed programme."""
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/programmes/bachelors/computer-science",
            ),
            # The programme URL itself is served by nothing.
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert any("could not be read" in reason for _u, reason in adapter.traces[0].rejected)

    @pytest.mark.asyncio
    async def test_a_catalogue_alone_does_not_become_a_programme(
        self, tmp_path, profile_bachelor
    ):
        """The FP-1 rule, enforced at discovery as well as at classification."""
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/education/programmes/bachelors"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert any("cannot confirm a programme" in e for e in adapter.traces[0].errors)

    @pytest.mark.asyncio
    async def test_the_number_of_pages_per_category_is_bounded(
        self, tmp_path, profile_bachelor
    ):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        many = [f"https://uni.edu/scholarships/award-{i}" for i in range(40)]
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(*many),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            await adapter.discover(profile_bachelor)

        selected = adapter.traces[0].selected[PageCategory.SCHOLARSHIPS]
        assert len(selected) <= MAX_PAGES_PER_CATEGORY

    @pytest.mark.asyncio
    async def test_navigation_is_used_only_when_sitemaps_yield_nothing(
        self, tmp_path, profile_bachelor
    ):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "User-agent: *\n",
            "https://uni.edu/": (
                '<html><body><nav>'
                '<a href="/en/education/programmes/bachelors/computer-science">CS</a>'
                '<a href="/tuition-fees">Fees</a>'
                '<a href="https://elsewhere.example.com/scholarships">Off-site</a>'
                '</nav></body></html>'
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        trace = adapter.traces[0]
        assert trace.used_navigation_fallback
        assert candidate.costs_url == "https://uni.edu/tuition-fees"
        assert candidate.scholarships_url is None, "an off-domain link must not be followed"

    @pytest.mark.asyncio
    async def test_navigation_is_not_used_when_the_subject_was_found(
        self, tmp_path, profile_bachelor
    ):
        """Discovery stops widening once the applicant's own subject is
        confirmed — and "confirmed" means the page was read, so the stub has to
        serve it."""
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/en/education/programmes/bachelors/computer-science",
                "https://uni.edu/tuition-fees",
            ),
            "https://uni.edu/en/education/programmes/bachelors/computer-science":
                program_html(),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            await adapter.discover(profile_bachelor)

        assert not adapter.traces[0].used_navigation_fallback
        assert "https://uni.edu/" not in site.requested

    @pytest.mark.asyncio
    async def test_unrelated_programmes_do_not_stop_the_search(
        self, tmp_path, profile_bachelor
    ):
        """The TU Delft defect.

        Delft's sitemap yields aerospace engineering, applied mathematics and
        applied physics. All three are genuine bachelor programme pages, so
        discovery declared success and never walked the catalogue that lists
        the computer science degree the applicant actually asked for. Finding
        three programmes nobody asked about is not a reason to stop looking.
        """
        entry = {
            "name": "U", "country": "Netherlands", "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"program_catalog": "https://uni.edu/en/education/programmes/bachelors"},
        }
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/en/programmes/bachelors/bsc-aerospace-engineering",
                "https://uni.edu/en/programmes/bachelors/bsc-applied-mathematics",
            ),
            "https://uni.edu/en/programmes/bachelors/bsc-aerospace-engineering":
                program_html("BSc Aerospace Engineering"),
            "https://uni.edu/en/programmes/bachelors/bsc-applied-mathematics":
                program_html("BSc Applied Mathematics"),
            "https://uni.edu/en/education/programmes/bachelors": (
                "<html><head><title>Bachelors</title></head><body><main>"
                "<h1>Bachelors</h1>"
                "<a href='/en/programmes/bachelors/bsc-computer-science'>Computer Science</a>"
                "</main></body></html>"
            ),
            "https://uni.edu/en/programmes/bachelors/bsc-computer-science":
                program_html("BSc Computer Science"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        urls = [p.url for p in candidate.programs]
        assert any("computer-science" in u for u in urls), (
            f"the applicant's own subject was never reached; found {urls}"
        )
        assert adapter.traces[0].used_navigation_fallback

    @pytest.mark.asyncio
    async def test_a_profile_naming_no_subject_does_not_walk_the_catalogue(
        self, tmp_path, profile_bachelor
    ):
        """Widening is driven by an unmet subject. With no subject stated, any
        programme satisfies it and the crawler stops."""
        profile_bachelor.context.intended_fields = []
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                "https://uni.edu/en/programmes/bachelors/bsc-aerospace-engineering",
            ),
            "https://uni.edu/en/programmes/bachelors/bsc-aerospace-engineering":
                program_html("BSc Aerospace Engineering"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs
        assert not adapter.traces[0].used_navigation_fallback

    @pytest.mark.asyncio
    async def test_the_number_of_pages_read_to_confirm_is_bounded(
        self, tmp_path, profile_bachelor
    ):
        """A site with many plausible candidates must not become a crawl."""
        many = [f"https://uni.edu/en/programmes/bachelors/bsc-subject-{i}" for i in range(40)]
        pages = {
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(*many),
        }
        for url in many:  # every one reads as a catalogue, so none is confirmed
            pages[url] = "<html><head><title>Bachelors</title></head><body><main>" \
                         "<h1>Bachelors</h1><p>Our programmes.</p></main></body></html>"
        site = StubSite(pages)
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        read = [u for u in site.requested if "bsc-subject-" in u]
        assert len(read) <= MAX_PROGRAM_CANDIDATES_CHECKED * 2, (
            f"read {len(read)} candidate pages; the budget is per confirmation pass"
        )
        assert any("left unchecked rather than guessed at" in e
                   for e in adapter.traces[0].errors)

    @pytest.mark.asyncio
    async def test_navigation_runs_when_only_a_catalogue_was_found(
        self, tmp_path, profile_bachelor
    ):
        """The defect the live canary found: seeds suppressed the fallback.

        Six of ten institutions had a seeded admissions or fee page, which made
        "something was found" true and stopped the fallback from ever running,
        so the run finished with no programme page at all. The fallback now
        depends on the programme page specifically, and it starts from the
        catalogue rather than the global menu.
        """
        entry = {
            "name": "U", "country": "Netherlands", "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"admissions": "https://uni.edu/verified/admission"},
        }
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/education/programmes/bachelors"),
            "https://uni.edu/en/education/programmes/bachelors": (
                '<html><body><main>'
                '<a href="/en/education/programmes/bachelors/computer-science">CS</a>'
                '<a href="/en/education/programmes/bachelors/history">History</a>'
                '</main></body></html>'
            ),
            "https://uni.edu/en/education/programmes/bachelors/computer-science":
                program_html(),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert adapter.traces[0].used_navigation_fallback
        assert candidate.programs, "the catalogue was not walked for programme pages"
        assert "computer-science" in candidate.programs[0].url
        # The catalogue was the starting point, so the homepage was never needed.
        assert "https://uni.edu/" not in site.requested

    @pytest.mark.asyncio
    async def test_a_catalogue_link_is_followed_by_its_wording(
        self, tmp_path, profile_bachelor
    ):
        """Toronto's case: the URL says nothing, the link text says everything.

        ``/data-computer-science`` matches no "programmes" path pattern, but the
        catalogue links to it as "Data & Computer Science".
        """
        entry = {"name": "U", "country": "Canada", "city": "X",
                 "homepage": "https://uni.edu/",
                 "seeds": {"program_catalog": "https://uni.edu/undergraduate-programs"}}
        site = StubSite({
            "https://uni.edu/robots.txt": "User-agent: *\n",
            "https://uni.edu/undergraduate-programs": (
                '<html><body><main>'
                '<a href="/data-computer-science">Data &amp; Computer Science</a>'
                '<a href="/rotman-commerce">Rotman Commerce</a>'
                '<a href="/connect">Sign-up to receive more information</a>'
                '</main></body></html>'
            ),
            # The catalogue links with a short label; the page names itself in full.
            "https://uni.edu/data-computer-science": program_html("BSc Data and Computer Science"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs, "the link text was not used"
        assert candidate.programs[0].url == "https://uni.edu/data-computer-science"
        assert adapter.traces[0].kept_by_link_text
        # The unrelated programme and the sign-up link stay out.
        urls = [p.url for p in candidate.programs]
        assert "https://uni.edu/rotman-commerce" not in urls
        assert "https://uni.edu/connect" not in urls

    @pytest.mark.asyncio
    async def test_link_text_matching_needs_the_whole_subject(
        self, tmp_path, profile_bachelor
    ):
        """"Computer" alone is not "computer science".

        A partial match would drag in computing services, computer labs and
        every news item about a computer.
        """
        entry = {"name": "U", "country": "Canada", "city": "X",
                 "homepage": "https://uni.edu/",
                 "seeds": {"program_catalog": "https://uni.edu/undergraduate-programs"}}
        site = StubSite({
            "https://uni.edu/robots.txt": "User-agent: *\n",
            "https://uni.edu/undergraduate-programs": (
                '<html><body><main>'
                '<a href="/computer-services">Computer Services</a>'
                '<a href="/science-outreach">Science Outreach</a>'
                '</main></body></html>'
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []

    @pytest.mark.asyncio
    async def test_link_text_matching_only_applies_on_a_catalogue(
        self, tmp_path, profile_bachelor
    ):
        """On the homepage the same wording is a news headline as often as a
        programme, so the rule stays where the structure justifies it."""
        entry = {"name": "U", "country": "Canada", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "User-agent: *\n",
            "https://uni.edu/": (
                '<html><body><main>'
                '<a href="/spotlight">Computer Science at U</a>'
                '</main></body></html>'
            ),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert not adapter.traces[0].kept_by_link_text

    @pytest.mark.asyncio
    async def test_a_large_sitemap_does_not_crowd_out_the_programmes(
        self, tmp_path, profile_bachelor
    ):
        """The rug.nl defect: 20,000 news URLs exhausted the budget first.

        Relevance has to be decided as each URL is read. Collecting a prefix of
        the sitemap and filtering afterwards means the bound falls wherever the
        site happened to list its news.
        """
        noise = [f"https://uni.edu/research/news/2022/item-{i}" for i in range(5000)]
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml(
                *noise, "https://uni.edu/en/education/programmes/bachelors/computer-science"
            ),
            "https://uni.edu/en/education/programmes/bachelors/computer-science":
                program_html(),
        })
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs, "the programme page was crowded out by news pages"
        trace = adapter.traces[0]
        assert trace.sitemap_urls_seen == 5001
        assert trace.sitemap_urls_kept == 1, "irrelevant URLs must not be retained"

    @pytest.mark.asyncio
    async def test_an_unreachable_site_is_reported_not_raised(
        self, tmp_path, profile_bachelor
    ):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://gone.edu/"}
        site = StubSite({}, missing_outcome=FetchOutcome.NETWORK_UNAVAILABLE)
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.admissions_url is None
        assert candidate.programs == []
        assert adapter.traces[0].errors

    @pytest.mark.asyncio
    async def test_excluded_countries_are_not_proposed(self, tmp_path, profile_bachelor):
        profile_bachelor.preferences.excluded_countries = ["Netherlands"]
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            StubSite({}).install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            assert await adapter.discover(profile_bachelor) == []

    @pytest.mark.asyncio
    async def test_the_trace_serialises_for_the_canary_report(
        self, tmp_path, profile_bachelor
    ):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite({
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
            "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/tuition-fees"),
        })
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            await adapter.discover(profile_bachelor)

        payload = adapter.traces[0].as_dict()
        assert json.dumps(payload)  # must be machine-readable
        assert payload["sitemaps_read"] == ["https://uni.edu/s.xml"]
        assert payload["selected"][PageCategory.COSTS] == ["https://uni.edu/tuition-fees"]


class TestShippedRegistry:
    """The registry that ships must stay coherent.

    These are the only tests that read the real file. They check its shape, not
    that any particular URL is still live — that is what the canary measures.
    """

    @staticmethod
    def entries() -> list[dict]:
        return json.loads(REGISTRY_PATH.read_text())

    def test_it_covers_at_least_ten_institutions_in_several_countries(self):
        entries = self.entries()
        assert len(entries) >= 10
        assert len({e["country"] for e in entries}) >= 5

    def test_every_seed_is_on_its_own_institutions_domain(self):
        for entry in self.entries():
            for category, url in (entry.get("seeds") or {}).items():
                assert same_institution(url, entry["homepage"]), (
                    f"{entry['name']} seed {category} points off-domain: {url}"
                )

    def test_every_seed_category_is_one_discovery_understands(self):
        for entry in self.entries():
            for category in entry.get("seeds") or {}:
                assert category in PageCategory.ALL, (
                    f"{entry['name']}: unknown seed category {category!r}"
                )

    def test_every_seed_is_an_absolute_https_url(self):
        for entry in self.entries():
            for category, url in (entry.get("seeds") or {}).items():
                assert url.startswith("https://"), f"{entry['name']} {category}: {url}"


def _trace():
    from app.adapters.discovery.live_discovery import DiscoveryTrace

    return DiscoveryTrace(institution="test", domain="uni.edu")


class TestRenderDecision:
    """When is a catalogue worth re-reading through the browser?

    The question is whether the applicant's subject is reachable from what was
    served — not whether the page carries programme links at all. Groningen's
    bachelor catalogue carries fourteen programme-shaped links and not one of
    them is a programme, let alone a computing one, so a rule that only counted
    them never escalated and never found the subject.
    """

    FIELDS: ClassVar[list[str]] = ["computer science"]

    def test_a_catalogue_naming_the_subject_needs_no_render(self):
        links = [("https://uni.edu/programmes/bsc-computer-science", "Computer Science")]
        assert catalogue_shows_subject(links, self.FIELDS, "bachelor")

    def test_a_catalogue_with_links_but_not_the_subject_is_rendered(self):
        links = [
            ("https://uni.edu/education/bachelor/brochures", "Brochures"),
            ("https://uni.edu/education/bachelor/open-days", "Open days"),
            ("https://uni.edu/programmes/bsc-history", "History"),
        ]
        assert not catalogue_shows_subject(links, self.FIELDS, "bachelor")

    def test_the_subject_in_link_text_alone_is_enough(self):
        links = [("https://uni.edu/x/12345", "Computer Science and Engineering")]
        assert catalogue_shows_subject(links, self.FIELDS, "bachelor")

    def test_the_subject_at_the_wrong_level_does_not_count(self):
        links = [("https://uni.edu/programmes/masters/computer-science", "Computer Science")]
        assert not catalogue_shows_subject(links, self.FIELDS, "bachelor")

    def test_with_no_subject_stated_any_programme_link_suffices(self):
        links = [("https://uni.edu/en/programmes/bachelors/history", "History")]
        assert catalogue_shows_subject(links, [], "bachelor")
