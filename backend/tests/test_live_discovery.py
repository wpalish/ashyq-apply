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

import asyncio
import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.discovery.live_discovery import (
    MAX_PAGES_PER_CATEGORY,
    MAX_SITEMAP_DOCUMENTS,
    REGISTRY_PATH,
    LiveDiscoveryAdapter,
    PageCategory,
    SitemapReader,
    canonical_url,
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
        async def fake_get(
            url: str,
            *,
            use_cache: bool = True,
            etag: str | None = None,
            if_modified_since: str | None = None,
        ) -> FetchResult:
            self.requested.append(url)
            body = self.pages.get(url)
            if body is None:
                return FetchResult(
                    url=url,
                    outcome=self.missing_outcome,
                    status_code=404,
                    error="not in this test's page set",
                    final_url=url,
                )
            raw = body.encode() if isinstance(body, str) else body
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                content=raw,
                text=raw.decode("utf-8", errors="replace"),
                content_type="application/xml",
                fetched_at=datetime.now(UTC),
                final_url=url,
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
    @pytest.mark.parametrize(
        "host,expected",
        [
            ("www.rug.nl", "rug.nl"),
            ("rug.nl", "rug.nl"),
            ("studieren.univie.ac.at", "univie.ac.at"),
            ("admissions.hku.hk", "hku.hk"),
            ("admissions.nu.edu.kz", "nu.edu.kz"),
            ("www.ntu.edu.sg", "ntu.edu.sg"),
            ("admission.kaist.ac.kr", "kaist.ac.kr"),
            ("you.ubc.ca", "ubc.ca"),
            ("en.uw.edu.pl", "uw.edu.pl"),
        ],
    )
    def test_multipart_suffixes_are_handled(self, host, expected):
        """Taking the last two labels would make every ac.uk site one domain."""
        assert registrable_domain(host) == expected

    @pytest.mark.parametrize(
        "url,domain,same",
        [
            ("https://www.rug.nl/education", "www.rug.nl", True),
            ("https://rug.nl/education", "www.rug.nl", True),
            ("https://studieren.univie.ac.at/x", "www.univie.ac.at", True),
            ("https://evil.example.com/rug.nl", "www.rug.nl", False),
            ("https://www.tudelft.nl/x", "www.rug.nl", False),
            ("https://other.ac.at/x", "www.univie.ac.at", False),
        ],
    )
    def test_off_domain_urls_are_recognised(self, url, domain, same):
        assert same_institution(url, domain) is same


class TestCanonicalUrl:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://WWW.RUG.NL/Education/", "https://www.rug.nl/Education"),
            ("https://www.rug.nl/education#section", "https://www.rug.nl/education"),
            ("https://www.rug.nl/education?utm_source=x", "https://www.rug.nl/education"),
            ("https://www.rug.nl/education?fbclid=abc", "https://www.rug.nl/education"),
            ("https://www.rug.nl:443/education", "https://www.rug.nl/education"),
            ("https://www.rug.nl//education//cs", "https://www.rug.nl/education/cs"),
            ("https://www.rug.nl/", "https://www.rug.nl/"),
        ],
    )
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
    @pytest.mark.parametrize(
        "url,category",
        [
            (
                "https://uni.edu/en/education/programmes/bachelors/computer-science",
                PageCategory.PROGRAM_PAGE,
            ),
            # Hyphenated compound, as Vienna publishes it.
            (
                "https://uni.edu/en/bachelordiploma-programmes/computer-science-bachelor",
                PageCategory.PROGRAM_PAGE,
            ),
            ("https://uni.edu/bsc-computer-science", PageCategory.PROGRAM_PAGE),
            ("https://uni.edu/en/education/programmes/bachelors", PageCategory.PROGRAM_CATALOG),
            # Hyphenated compounds: how most universities actually name the page.
            ("https://uni.edu/en/degree-programmes", PageCategory.PROGRAM_CATALOG),
            (
                "https://uni.edu/education/degree-programmes-1st-2nd-and-long-cycle-programmes",
                PageCategory.PROGRAM_CATALOG,
            ),
            ("https://uni.edu/admission-and-application", PageCategory.ADMISSIONS),
            ("https://uni.edu/entry_requirements", PageCategory.ADMISSIONS),
            ("https://uni.edu/tuition-fees", PageCategory.COSTS),
            ("https://uni.edu/cost-of-attendance", PageCategory.COSTS),
            ("https://uni.edu/scholarships", PageCategory.SCHOLARSHIPS),
            ("https://uni.edu/financial_aid", PageCategory.SCHOLARSHIPS),
            ("https://uni.edu/required-documents", PageCategory.DOCUMENTS),
        ],
    )
    def test_urls_are_filed_under_the_right_category(self, url, category):
        assert categorise_url(url)[0] == category

    @pytest.mark.parametrize(
        "url",
        [
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
        ],
    )
    def test_irrelevant_urls_score_nothing(self, url):
        assert categorise_url(url)[0] is None

    @pytest.mark.parametrize(
        "url,is_catalogue",
        [
            ("https://uni.edu/en/degree-programmes", True),
            # Scores higher as admissions, but is still worth walking for programmes.
            ("https://uni.edu/applying-ubc/how-to-apply/degrees-programs/", True),
            ("https://uni.edu/studies/programmes", True),
            ("https://uni.edu/about/degree-ceremony-photos", False),
            ("https://uni.edu/programme-news", False),
            ("https://uni.edu/news/2026/new-programme-launched", False),
            ("https://uni.edu/en/education/programmes/bachelors/computer-science", False),
        ],
    )
    def test_whether_a_page_lists_programmes_is_asked_separately(self, url, is_catalogue):
        assert looks_like_catalogue(url) is is_catalogue

    @pytest.mark.parametrize(
        "url",
        [
            "https://uni.edu/admissions/undergraduate/scholarships/detail/sci-award",
            "https://uni.edu/en/education/programmes/bachelors/funding/award",
            "https://uni.edu/study/financial-aid/undergraduate-grants",
        ],
    )
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
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/sitemap_index.xml\n",
                "https://uni.edu/sitemap_index.xml": sitemap_index_xml(
                    "https://uni.edu/s-programmes.xml", "https://uni.edu/s-admissions.xml"
                ),
                "https://uni.edu/s-programmes.xml": sitemap_xml(
                    "https://uni.edu/programmes/bachelors/computer-science"
                ),
                "https://uni.edu/s-admissions.xml": sitemap_xml("https://uni.edu/admission"),
            }
        )
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
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_index_xml("https://uni.edu/s.xml"),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", _trace())
        assert site.requested.count("https://uni.edu/s.xml") == 1

    @pytest.mark.asyncio
    async def test_off_domain_urls_in_a_sitemap_are_dropped(self, tmp_path):
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/programmes/bachelors/cs",
                    "https://evil.example.com/programmes/bachelors/cs",
                    "https://partner.other.edu/admission",
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            trace = _trace()
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", trace)

        assert pages == ["https://uni.edu/programmes/bachelors/cs"]
        assert any("off the institution's domain" in reason for _u, reason in trace.rejected)

    @pytest.mark.asyncio
    async def test_duplicate_and_equivalent_urls_are_deduplicated(self, tmp_path):
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/programmes/bachelors/cs",
                    "https://uni.edu/programmes/bachelors/cs/",
                    "https://uni.edu/programmes/bachelors/cs#overview",
                    "https://UNI.edu/programmes/bachelors/cs?utm_source=x",
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            pages = await SitemapReader(fetcher).collect("https://uni.edu/", "uni.edu", _trace())
        assert len(pages) == 1

    @pytest.mark.asyncio
    async def test_conventional_locations_are_tried_when_robots_names_none(self, tmp_path):
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\nDisallow:\n",
                "https://uni.edu/sitemap.xml": sitemap_xml("https://uni.edu/admission"),
            }
        )
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
            "name": "Seeded University",
            "country": "Netherlands",
            "city": "X",
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
            "name": "Seeded University",
            "country": "Netherlands",
            "city": "X",
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
            "name": "Seeded University",
            "country": "Netherlands",
            "city": "X",
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
            "name": "Seeded University",
            "country": "Netherlands",
            "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"admissions": "https://uni.edu/verified/admission"},
        }
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/discovered/admission-and-application"
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.admissions_url == "https://uni.edu/verified/admission"
        # The discovered one is kept as a second lead, not discarded.
        assert (
            "https://uni.edu/discovered/admission-and-application"
            in adapter.traces[0].selected[PageCategory.ADMISSIONS]
        )

    @pytest.mark.asyncio
    async def test_sitemap_discovery_finds_a_programme_page(self, tmp_path, profile_bachelor):
        entry = {
            "name": "Sitemapped University",
            "country": "Netherlands",
            "city": "X",
            "homepage": "https://uni.edu/",
        }
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/news/2026/open-day",
                    "https://uni.edu/en/education/programmes/bachelors/computer-science",
                    "https://uni.edu/en/education/programmes/masters/computer-science",
                    "https://uni.edu/tuition-fees",
                    "https://uni.edu/scholarships",
                ),
                "https://uni.edu/en/education/programmes/bachelors/computer-science": program_html(),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs, "the bachelor programme page was not found"
        assert "bachelors/computer-science" in candidate.programs[0].url
        assert candidate.costs_url == "https://uni.edu/tuition-fees"
        assert candidate.scholarships_url == "https://uni.edu/scholarships"

    @pytest.mark.asyncio
    async def test_the_wrong_degree_level_is_not_offered_first(self, tmp_path, profile_bachelor):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/en/education/programmes/masters/computer-science",
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == [], "an MSc page is not a bachelor lead"

    @pytest.mark.asyncio
    async def test_fetched_programmes_must_match_requested_level_and_subject(
        self, tmp_path, profile_bachelor
    ):
        """Opaque URLs must not let an MSc or unrelated BSc consume a verify slot."""
        entry = {"name": "U", "country": "Kazakhstan", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/programmes/computer-science-ece",
                    "https://uni.edu/programmes/math",
                    "https://uni.edu/programmes/computer-science",
                ),
                "https://uni.edu/programmes/computer-science-ece": program_html(
                    "MSc Electrical and Computer Engineering"
                ),
                "https://uni.edu/programmes/math": program_html("BSc Mathematics"),
                "https://uni.edu/programmes/computer-science": program_html("BSc Computer Science"),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert [program.url for program in candidate.programs] == [
            "https://uni.edu/programmes/computer-science"
        ]

    @pytest.mark.asyncio
    async def test_a_candidate_that_reads_as_an_event_is_dropped(self, tmp_path, profile_bachelor):
        """Live runs offered open days and campus tours as programme pages.

        They sit under the same path as the real programmes, so no URL rule
        separates them. Reading the page does.
        """
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
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
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert any("not a programme page" in reason for _u, reason in adapter.traces[0].rejected)

    @pytest.mark.asyncio
    async def test_a_rejected_candidate_lets_the_next_one_through(self, tmp_path, profile_bachelor):
        """Rejecting the top candidate must not mean finding nothing."""
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
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
            }
        )
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
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/programmes/bachelors/computer-science",
                ),
                # The programme URL itself is served by nothing.
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert any("could not be read" in reason for _u, reason in adapter.traces[0].rejected)

    @pytest.mark.asyncio
    async def test_a_catalogue_alone_does_not_become_a_programme(self, tmp_path, profile_bachelor):
        """The FP-1 rule, enforced at discovery as well as at classification."""
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/en/education/programmes/bachelors"
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []
        assert any("cannot confirm a programme" in e for e in adapter.traces[0].errors)

    @pytest.mark.asyncio
    async def test_the_number_of_pages_per_category_is_bounded(self, tmp_path, profile_bachelor):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        many = [f"https://uni.edu/scholarships/award-{i}" for i in range(40)]
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(*many),
            }
        )
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
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\n",
                "https://uni.edu/": (
                    "<html><body><nav>"
                    '<a href="/en/education/programmes/bachelors/computer-science">CS</a>'
                    '<a href="/tuition-fees">Fees</a>'
                    '<a href="https://elsewhere.example.com/scholarships">Off-site</a>'
                    "</nav></body></html>"
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        trace = adapter.traces[0]
        assert trace.used_navigation_fallback
        assert candidate.costs_url == "https://uni.edu/tuition-fees"
        assert candidate.scholarships_url is None, "an off-domain link must not be followed"

    @pytest.mark.asyncio
    async def test_navigation_is_not_used_when_a_programme_page_was_found(
        self, tmp_path, profile_bachelor
    ):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/en/education/programmes/bachelors/computer-science",
                    "https://uni.edu/tuition-fees",
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            await adapter.discover(profile_bachelor)

        assert not adapter.traces[0].used_navigation_fallback
        assert "https://uni.edu/" not in site.requested

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
            "name": "U",
            "country": "Netherlands",
            "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"admissions": "https://uni.edu/verified/admission"},
        }
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    "https://uni.edu/en/education/programmes/bachelors"
                ),
                "https://uni.edu/en/education/programmes/bachelors": (
                    "<html><body><main>"
                    '<a href="/en/education/programmes/bachelors/computer-science">CS</a>'
                    '<a href="/en/education/programmes/bachelors/history">History</a>'
                    "</main></body></html>"
                ),
                "https://uni.edu/en/education/programmes/bachelors/computer-science": program_html(),
            }
        )
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
    async def test_a_catalogue_link_is_followed_by_its_wording(self, tmp_path, profile_bachelor):
        """Toronto's case: the URL says nothing, the link text says everything.

        ``/data-computer-science`` matches no "programmes" path pattern, but the
        catalogue links to it as "Data & Computer Science".
        """
        entry = {
            "name": "U",
            "country": "Canada",
            "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"program_catalog": "https://uni.edu/undergraduate-programs"},
        }
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\n",
                "https://uni.edu/undergraduate-programs": (
                    "<html><body><main>"
                    '<a href="/data-computer-science">Data &amp; Computer Science</a>'
                    '<a href="/rotman-commerce">Rotman Commerce</a>'
                    '<a href="/connect">Sign-up to receive more information</a>'
                    "</main></body></html>"
                ),
                # The catalogue links with a short label; the page names itself in full.
                "https://uni.edu/data-computer-science": program_html(
                    "BSc Data and Computer Science"
                ),
            }
        )
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
    async def test_link_text_matching_needs_the_whole_subject(self, tmp_path, profile_bachelor):
        """ "Computer" alone is not "computer science".

        A partial match would drag in computing services, computer labs and
        every news item about a computer.
        """
        entry = {
            "name": "U",
            "country": "Canada",
            "city": "X",
            "homepage": "https://uni.edu/",
            "seeds": {"program_catalog": "https://uni.edu/undergraduate-programs"},
        }
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\n",
                "https://uni.edu/undergraduate-programs": (
                    "<html><body><main>"
                    '<a href="/computer-services">Computer Services</a>'
                    '<a href="/science-outreach">Science Outreach</a>'
                    "</main></body></html>"
                ),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, entry))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert candidate.programs == []

    @pytest.mark.asyncio
    async def test_link_text_matching_only_applies_on_a_catalogue(self, tmp_path, profile_bachelor):
        """On the homepage the same wording is a news headline as often as a
        programme, so the rule stays where the structure justifies it."""
        entry = {"name": "U", "country": "Canada", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\n",
                "https://uni.edu/": (
                    "<html><body><main>"
                    '<a href="/spotlight">Computer Science at U</a>'
                    "</main></body></html>"
                ),
            }
        )
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
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(
                    *noise, "https://uni.edu/en/education/programmes/bachelors/computer-science"
                ),
                "https://uni.edu/en/education/programmes/bachelors/computer-science": program_html(),
            }
        )
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
    async def test_an_unreachable_site_is_reported_not_raised(self, tmp_path, profile_bachelor):
        entry = {
            "name": "U",
            "country": "Netherlands",
            "city": "X",
            "homepage": "https://gone.edu/",
        }
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
    async def test_the_trace_serialises_for_the_canary_report(self, tmp_path, profile_bachelor):
        entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/tuition-fees"),
            }
        )
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


# --- T29 A1: the catalog walker (RED-first on baseline 2ed4f51e) -----------
#
# Scenarios R1-R10 from the frozen T29 planner contract, authored RED-first.
# On this baseline ``app.adapters.discovery.catalog_walker`` does not exist,
# ``DiscoveryTrace`` carries no ``walker`` field, ``as_dict()`` has no
# ``walker`` key, ``LiveDiscoveryAdapter`` has no ``walker_outcomes`` attribute
# and accepts no ``page_recorder`` keyword. Every scenario here drives the
# safe behaviour the walker must implement; on the baseline they fail as:
#
#   R1-R4, R9, R10   ImportError (new module) / KeyError "walker" (new trace
#                    key) / AttributeError walker_outcomes — the accepted
#                    new-module pattern (see test_source_pages.py).
#   R5-R7            the contract's predicted mode is "no interception
#                    happened" (empty programme list). Constructing the
#                    contract's CatalogRenderer is a precondition of these
#                    scenarios, so on the baseline the lazy import fails
#                    first; R6 additionally pins the baseline behaviour that
#                    already holds (the HTML links confirm without a walker)
#                    as a justified-GREEN sub-assertion.
#   R8               TypeError: ``page_recorder`` is a new keyword.
#
# Justified-GREEN pins (behaviour that already holds on the baseline and must
# survive the walker) are marked ``justified-GREEN`` in their docstrings.
#
# The browser doubles below are file-local copies of the FakeBrowser/FakePage
# PATTERN from test_browser_network.py — deliberately not imported from it.

LIVE_SHAPES = Path(__file__).parent / "fixtures" / "live_shapes"


def _shape(name: str) -> str:
    """One of the frozen live_shapes fixtures, as text."""
    return (LIVE_SHAPES / name).read_text()


def _json_shape(name: str) -> str:
    """The JSON fixtures re-serialised, so the wire body matches the file."""
    return json.dumps(json.loads(_shape(name)))


class FakeJsResponse:
    """A network response the rendered page received.

    Exposes the surface a response listener plausibly reads: url, status,
    content type (attribute and headers) and the body as text or bytes.
    """

    def __init__(self, url: str, content_type: str, body: str, status: int = 200) -> None:
        self.url = url
        self.status = status
        self.content_type = content_type
        self.headers = {"content-type": content_type}
        self._body = body
        self.request = type("Req", (), {"url": url, "headers": dict(self.headers)})()

    async def text(self) -> str:
        return self._body

    async def body(self) -> bytes:
        return self._body.encode("utf-8")

    async def json(self):
        return json.loads(self._body)


class WalkerFakePage:
    """A rendered page that fires its recorded network responses on goto."""

    def __init__(self, content: str, responses=(), status: int = 200) -> None:
        self.content_html = content
        self.goto_result = FakePlaywrightResult(status)
        self.responses = list(responses)
        self.handlers: list[tuple[str, object]] = []

    def on(self, event, handler) -> None:
        self.handlers.append((event, handler))

    async def goto(self, url, wait_until=None, timeout=None):
        for event, handler in self.handlers:
            if event != "response":
                continue
            for response in self.responses:
                outcome = handler(response)
                if asyncio.iscoroutine(outcome):
                    await outcome
        return self.goto_result

    async def wait_for_timeout(self, ms) -> None:
        return None

    async def content(self) -> str:
        return self.content_html


class FakePlaywrightResult:
    """Just the attribute browser.py reads off a navigation response."""

    def __init__(self, status: int) -> None:
        self.status = status


class WalkerFakeContext:
    def __init__(self, page: WalkerFakePage) -> None:
        self.page = page
        self.routes: list[tuple[str, object]] = []
        self.closed = False

    async def route(self, pattern, handler) -> None:
        self.routes.append((pattern, handler))

    async def new_page(self) -> WalkerFakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class WalkerFakeBrowser:
    """Stands in for the Chromium handle browser.py drives."""

    def __init__(self, page: WalkerFakePage) -> None:
        self.page = page
        self.contexts: list[WalkerFakeContext] = []

    async def new_context(self, **kwargs) -> WalkerFakeContext:
        context = WalkerFakeContext(self.page)
        self.contexts.append(context)
        return context


def _js_catalog_renderer(tmp_path, page: WalkerFakePage):
    """The contract's CatalogRenderer over the fake browser seam.

    The renderer is attached to a Fetcher that is never entered as a context
    manager (so ``_client`` stays None and no network happens) and whose
    transport is the StubSite — the same shape test_browser_network.py uses.
    """
    from app.adapters.discovery.catalog_walker import CatalogRenderer

    fetcher = Fetcher(tmp_path / "walker-cache", delay_seconds=0.0, respect_robots=False)
    renderer = CatalogRenderer(fetcher)
    renderer._browser = WalkerFakeBrowser(page)  # type: ignore[assignment]
    fetcher.attach_renderer(renderer)
    return fetcher, renderer


def _catalogue_html(*anchors: str) -> str:
    items = "".join(f'<li><a href="{url}">{label}</a></li>' for url, label in anchors)
    return (
        "<html><head><title>Programmes | University</title></head><body><main>"
        "<h1>Our programmes</h1>"
        "<p>Browse all the programmes this university offers across every "
        "faculty, with details about each course and how to apply for it.</p>"
        f"<ul>{items}</ul></main></body></html>"
    )


def _walker_entry() -> dict:
    return {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}


def _letter_suffix(i: int) -> str:
    letters = "abcdefghijklmnopqrstuvwxyz"
    return letters[i // 26] + letters[i % 26]


class TestCatalogWalkerContract:
    """T29 A1 scenarios R1-R10 (see the block comment above for RED modes)."""

    @staticmethod
    def registry_file(tmp_path, entry: dict) -> Path:
        path = tmp_path / "registry.json"
        path.write_text(json.dumps([entry]))
        return path

    # --- R1 ---------------------------------------------------------------

    def test_r1_walker_extracts_scored_links(self):
        """R1 walker_extracts_scored_links: the catalogue's links come out
        scored by the frozen weights, strongest first, and links that can
        never be a programme lead are hard-rejected before any fetch.

        ``score_link(url, label, degree, fields)`` follows the contract
        surface; if the walker needs sibling context for the repeating-list
        bonus it reaches it through walk_catalog, not through this call.
        """
        from app.adapters.discovery.catalog_walker import WalkerLink, extract_links, score_link

        html = _catalogue_html(
            ("/study/bsc-computer-science", "BSc Computer Science"),
            ("/study/computer-systems", "Computer Systems and Networks"),
            ("/study/student-services", "Student services and support"),
            ("/news/2026/press", "University press office contact"),
            ("/contact", "Ask us"),
            ("https://other.example.com/study/computer-science", "Their computer science"),
        )
        links = extract_links(html, "https://uni.edu/en/programmes", "uni.edu")
        assert links and all(isinstance(link, WalkerLink) for link in links)
        by_url = {link.url: link for link in links}
        assert "https://uni.edu/study/bsc-computer-science" in by_url
        # Off-domain links never enter the candidate list at all.
        assert not any("other.example" in url for url in by_url)

        degree, fields = "bachelor", ["computer science"]
        top = score_link(
            "https://uni.edu/study/bsc-computer-science", "BSc Computer Science", degree, fields
        )
        subject_only = score_link(
            "https://uni.edu/study/computer-systems",
            "Computer Systems and Networks",
            degree,
            fields,
        )
        generic = score_link(
            "https://uni.edu/study/student-services",
            "Student services and support",
            degree,
            fields,
        )
        assert top is not None and subject_only is not None and generic is not None
        assert top > subject_only >= generic
        # A news URL and a too-short label are never worth a fetch.
        assert (
            score_link(
                "https://uni.edu/news/2026/press", "University press office contact", degree, fields
            )
            is None
        )
        assert score_link("https://uni.edu/contact", "Ask us", degree, fields) is None
        for link in links:
            assert link.source, "provenance of the link must be recorded"

    # --- R2 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r2_each_link_fetched_with_outcome(self, tmp_path, profile_bachelor):
        """R2 each_link_fetched_with_outcome: the walker fetches a
        catalogue's leads and records one outcome per link — a missing page
        as the fetch vocabulary's ``http_error``, a news page as
        ``reads_as_news``, a real programme as its page type — and the
        confirmed programme reaches the candidate while the outcomes reach
        both trace.walker and adapter.walker_outcomes.
        """
        catalogue = _catalogue_html(
            ("/study/bsc-computer-science", "BSc Computer Science"),
            ("/study/closed-course", "A programme that has been discontinued"),
            ("/media/march-roundup", "University news and campus updates"),
        )
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/programmes"),
                "https://uni.edu/en/programmes": catalogue,
                "https://uni.edu/study/bsc-computer-science": program_html(),
                "https://uni.edu/media/march-roundup": _shape("news_page.html"),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
            candidate = (await adapter.discover(profile_bachelor))[0]

        walker = adapter.traces[0].walker  # KeyError/AttributeError RED on baseline
        outcomes = repr(walker["outcomes"])
        assert "http_error" in outcomes, "the 404 lead must be reported in the fetch vocabulary"
        assert "reads_as_news" in outcomes, "the news page must be reported, not silently kept"
        assert "program_detail" in outcomes, "the confirmed programme must be reported as read"
        assert walker["programs_confirmed"] == 1

        assert adapter.walker_outcomes, "walker_outcomes must be populated for the run report"
        assert all(o.category == "catalog-walker" for o in adapter.walker_outcomes)
        assert {o.url for o in adapter.walker_outcomes} >= {
            "https://uni.edu/study/closed-course",
            "https://uni.edu/media/march-roundup",
            "https://uni.edu/study/bsc-computer-science",
        }
        assert [p.url for p in candidate.programs] == ["https://uni.edu/study/bsc-computer-science"]

    # --- R3 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r3_profile_predicate_reused(self, tmp_path, profile_bachelor):
        """R3 profile_predicate_reused: the walker applies the same applicant
        predicate as _confirm_programs — an MSc page reached through an
        opaque URL ends as ``degree_level_mismatch``, never as the
        applicant's programme, while the bachelor lead the link text names
        is kept.
        """
        catalogue = _catalogue_html(
            ("/study/data-computing", "BSc Computer Science"),
            ("/study/advanced-computing", "Advanced Computing (MSc)"),
        )
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/programmes"),
                "https://uni.edu/en/programmes": catalogue,
                "https://uni.edu/study/data-computing": program_html("BSc Computer Science"),
                "https://uni.edu/study/advanced-computing": program_html("MSc Advanced Computing"),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert [p.url for p in candidate.programs] == ["https://uni.edu/study/data-computing"]
        # justified-GREEN pin: the confirm-stage rejection already holds on
        # the baseline and must survive the walker unchanged.
        assert any("degree level master" in reason for _u, reason in adapter.traces[0].rejected)

        walker = adapter.traces[0].walker  # KeyError RED on baseline
        outcomes = repr(walker["outcomes"])
        assert "degree_level_mismatch" in outcomes, "the MSc page must end in the frozen outcome"
        assert "program_detail" in outcomes

    # --- R4 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r4_off_domain_never_fetched(self, tmp_path, profile_bachelor):
        """R4 off_domain_never_fetched: a partner site's programme page is
        never fetched and never offered; the walker records it under the
        frozen ``off_domain`` outcome.
        """
        partner = "https://partner.example.com/study/computer-science"
        catalogue = _catalogue_html(
            ("/study/computer-science", "BSc Computer Science"),
            (partner, "Computer Science at the partner campus"),
        )
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/programmes"),
                "https://uni.edu/en/programmes": catalogue,
                "https://uni.edu/study/computer-science": program_html(),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
            candidate = (await adapter.discover(profile_bachelor))[0]

        # justified-GREEN pin: the same-domain boundary already holds on the
        # baseline and must survive the walker unchanged.
        assert partner not in site.requested
        assert partner not in [p.url for p in candidate.programs]

        walker = adapter.traces[0].walker  # KeyError RED on baseline
        assert "off_domain" in repr(walker["outcomes"]), "the rejection must be explained"

    # --- R5 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r5_js_json_payload_yields_programs(self, tmp_path, profile_bachelor):
        """R5 js_json_payload_yields_programs: a JS catalogue whose HTML is
        an empty shell has its JSON payload intercepted and its {name, url}
        entries fetched and confirmed — the URLs need not match any URL
        pattern, because the payload is the university's own statement of
        what its programmes are.
        """
        payload = _json_shape("js_catalog_payload.json")
        page = WalkerFakePage(
            content=_shape("js_catalog_shell.html"),
            responses=[
                FakeJsResponse(
                    "https://uni.edu/api/catalogs/programmes.json", "application/json", payload
                )
            ],
        )
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\n",
                "https://uni.edu/p/42": program_html("BSc Computer Science"),
                "https://uni.edu/p/77": program_html("BSc Mathematics"),
            }
        )
        fetcher, _renderer = _js_catalog_renderer(tmp_path, page)  # ImportError RED on baseline
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
        candidate = (await adapter.discover(profile_bachelor))[0]

        assert {p.url for p in candidate.programs} == {
            "https://uni.edu/p/42",
            "https://uni.edu/p/77",
        }, "the JSON payload's programmes must be fetched even though /p/N matches no pattern"
        walker = adapter.traces[0].walker
        assert walker["catalogs_walked"] == 1
        assert walker["programs_confirmed"] == 2
        assert "https://uni.edu/p/42" in site.requested

    # --- R6 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r6_js_unrelated_json_falls_through(self, tmp_path, profile_bachelor):
        """R6 js_unrelated_json_falls_through: JSON that carries no
        {name, url} arrays is not a programme list — the catalogue's HTML
        links drive the walk and nothing is invented from the JSON.

        justified-GREEN sub-pin: on the baseline the plain HTML links are
        already confirmed through the navigation fallback, and that must
        survive the walker unchanged.
        """
        programme = "https://uni.edu/study/bsc-computer-science"
        catalogue = _catalogue_html(
            (programme, "BSc Computer Science"),
            ("/study/physics", "BSc Physics"),
        )
        page = WalkerFakePage(
            content=catalogue,
            responses=[
                FakeJsResponse(
                    "https://uni.edu/api/analytics.json",
                    "application/json",
                    _json_shape("js_catalog_unrelated.json"),
                )
            ],
        )
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "User-agent: *\n",
                "https://uni.edu/en/programmes": catalogue,
                programme: program_html(),
            }
        )
        fetcher, _renderer = _js_catalog_renderer(tmp_path, page)  # ImportError RED on baseline
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
        candidate = (await adapter.discover(profile_bachelor))[0]

        # justified-GREEN: HTML alone already yields the programme on baseline.
        assert [p.url for p in candidate.programs] == [programme], (
            "the HTML fallback must drive, and the unrelated JSON must invent nothing"
        )
        walker = adapter.traces[0].walker  # KeyError RED on baseline
        assert walker["catalogs_walked"] == 1
        invented = {p.url for p in candidate.programs} - {programme}
        assert not invented, f"programmes fabricated from a JSON that lists none: {invented}"

    # --- R7 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r7_js_silent_shell_is_recorded_not_fatal(self, tmp_path, profile_bachelor):
        """R7 js_silent_shell_is_recorded_not_fatal: a shell with neither a
        JSON programme list nor HTML links ends the walk with the frozen
        ``js_no_program_list`` outcome — discovery completes, nothing
        crashes, and the rest of the candidate is untouched.
        """
        page = WalkerFakePage(
            content=_shape("js_catalog_shell.html"),
            responses=[
                FakeJsResponse(
                    "https://uni.edu/api/analytics.json",
                    "application/json",
                    _json_shape("js_catalog_unrelated.json"),
                )
            ],
        )
        site = StubSite({"https://uni.edu/robots.txt": "User-agent: *\n"})
        fetcher, _renderer = _js_catalog_renderer(tmp_path, page)  # ImportError RED on baseline
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
        candidate = (await adapter.discover(profile_bachelor))[0]  # must not raise

        assert candidate.programs == []
        walker = adapter.traces[0].walker  # KeyError RED on baseline
        assert "js_no_program_list" in repr(walker["outcomes"]), (
            "a silent shell must be explained, not just empty"
        )
        assert walker["catalogs_walked"] == 1

    # --- R8 ---------------------------------------------------------------

    @pytest.fixture
    def walker_source_session(self, tmp_path):
        """A migrated SQLite database (the test_source_pages.py pattern):
        migrated rather than create_all, so the migration stays under test."""
        import sqlalchemy as sa
        from sqlalchemy.orm import sessionmaker

        from app.db import migrate_to_head

        url = f"sqlite:///{tmp_path / 'walker_source_pages.db'}"
        migrate_to_head(url)
        engine = sa.create_engine(url)
        session = sessionmaker(bind=engine, future=True)()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_r8_source_pages_rows_recorded(
        self, tmp_path, profile_bachelor, walker_source_session
    ):
        """R8 source_pages_rows_recorded: with a page_recorder attached, every
        walker-fetched link with an HTTP status writes one SourcePage row with
        the frozen record kwargs — canonical url, registrable domain, the
        classifier's page type, the status (definitive errors included) and
        the fetch validators — and institution_key stays None because
        discovery does not own the claim system's mapping.

        RED on the baseline: TypeError, ``page_recorder`` is a new keyword.
        """
        from app.models import SourcePage

        catalogue = _catalogue_html(
            ("/study/bsc-computer-science", "BSc Computer Science"),
            ("/study/closed-course", "A programme that has been discontinued"),
            ("/media/march-roundup", "University news and campus updates"),
            ("/study/quick-peek", "Peek"),
        )
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/programmes"),
                "https://uni.edu/en/programmes": catalogue,
                "https://uni.edu/study/bsc-computer-science": program_html(),
                "https://uni.edu/media/march-roundup": _shape("news_page.html"),
            }
        )
        calls: list[dict] = []

        def recorder(**kwargs):
            calls.append(dict(kwargs))
            return SourcePage.record(walker_source_session, **kwargs)

        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(
                fetcher,
                self.registry_file(tmp_path, _walker_entry()),
                page_recorder=recorder,  # TypeError RED on baseline
            )
            await adapter.discover(profile_bachelor)

        walker_source_session.commit()
        frozen = {
            "url",
            "registrable_domain",
            "etag",
            "last_modified_header",
            "content_hash",
            "http_status",
            "page_type",
            "institution_key",
            "fetched_at",
        }
        assert calls, "the walker fetched pages but the recorder was never called"
        assert all(set(call) == frozen for call in calls), "record kwargs are frozen by contract"
        assert all(call["institution_key"] is None for call in calls)

        rows = {row.url: row for row in walker_source_session.query(SourcePage).all()}
        confirmed = rows["https://uni.edu/study/bsc-computer-science"]
        assert confirmed.http_status == 200
        assert confirmed.page_type == "program_detail"
        assert confirmed.registrable_domain == "uni.edu"
        assert confirmed.etag is None and confirmed.content_hash is None
        assert confirmed.fetched_at is not None
        assert confirmed.institution_key is None

        missing = rows["https://uni.edu/study/closed-course"]
        assert missing.http_status == 404, "a definitive HTTP error is still a fetch"
        assert missing.page_type == "unknown", "an unreadable page was never classified"

        news = rows["https://uni.edu/media/march-roundup"]
        assert news.http_status == 200 and news.page_type == "news"

        assert "https://uni.edu/study/quick-peek" not in rows, (
            "a link below the label floor is never fetched, so never recorded"
        )

    # --- R9 ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r9_top_n_budget(self, tmp_path, profile_bachelor):
        """R9 top_n_budget: thirty scored catalogue leads result in exactly
        WALKER_TOP_N fetches — the strongest twenty, and none of the rest.
        """
        from app.adapters.discovery.catalog_walker import WALKER_TOP_N

        assert WALKER_TOP_N == 20
        computer_science = {
            f"https://uni.edu/study/computer-science-{_letter_suffix(i)}": (
                f"https://uni.edu/study/computer-science-{_letter_suffix(i)}",
                f"BSc Computer Science group {_letter_suffix(i)}",
            )
            for i in range(20)
        }
        other = {
            f"https://uni.edu/study/student-support-{_letter_suffix(i)}": (
                f"https://uni.edu/study/student-support-{_letter_suffix(i)}",
                f"Student services and support {_letter_suffix(i)}",
            )
            for i in range(10)
        }
        anchors = [*computer_science.values(), *other.values()]
        served = {url: program_html() for url, _label in list(computer_science.values())[:2]}
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml("https://uni.edu/en/programmes"),
                "https://uni.edu/en/programmes": _catalogue_html(*anchors),
                **served,
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
            await adapter.discover(profile_bachelor)

        fetched = {u for u in site.requested if "/study/" in u}
        assert fetched == set(computer_science), (
            f"the walker's budget must stop at the top {WALKER_TOP_N} scored leads; "
            f"fetched {len(fetched)}"
        )
        assert not any("student-support" in u for u in site.requested)

    # --- R10 --------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_r10_no_catalog_byte_identical(self, tmp_path, profile_bachelor):
        """R10 no_catalog_byte_identical: with no catalogue anywhere the
        walker is inactive — it fetches nothing, trace.walker reports zeros,
        and every pre-existing trace key and the candidate keep exactly the
        baseline values.
        """
        programme = "https://uni.edu/en/education/programmes/bachelors/computer-science"
        site = StubSite(
            {
                "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/s.xml\n",
                "https://uni.edu/s.xml": sitemap_xml(programme),
                programme: program_html(),
            }
        )
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = LiveDiscoveryAdapter(fetcher, self.registry_file(tmp_path, _walker_entry()))
            candidate = (await adapter.discover(profile_bachelor))[0]

        assert set(site.requested) == {
            "https://uni.edu/robots.txt",
            "https://uni.edu/s.xml",
            programme,
        }, "without a catalogue the walker must fetch nothing"
        assert [p.url for p in candidate.programs] == [programme]

        payload = adapter.traces[0].as_dict()
        walker = payload["walker"]  # KeyError RED on baseline
        assert set(walker) == {"catalogs_walked", "candidates", "programs_confirmed", "outcomes"}
        assert walker["catalogs_walked"] == 0
        assert walker["candidates"] == []
        assert walker["programs_confirmed"] == 0
        assert walker["outcomes"] == []
        # Every pre-existing key keeps the baseline value: additive only.
        assert payload["sitemaps_read"] == ["https://uni.edu/s.xml"]
        assert payload["used_navigation_fallback"] is False
        assert payload["selected"]["program_page"] == [programme]
        assert payload["kept_by_link_text"] == []

    @pytest.mark.asyncio
    async def test_r10_demo_invariant(self, tmp_path, profile_bachelor):
        """R10 demo_invariant: in demo mode discovery is the bundled corpus —
        no university URL is ever requested and the demo adapter carries no
        walker recording surface, so there is nothing a walker or a recorder
        could be constructed from.

        justified-GREEN: trivially true on the baseline (no walker exists)
        and pinned so wiring the walker cannot silently change it.
        """
        from app.adapters.discovery.fixture_discovery import FixtureDiscoveryAdapter

        site = StubSite({})
        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            adapter = FixtureDiscoveryAdapter(fetcher)
            await adapter.discover(profile_bachelor, 5)

        assert site.requested == ["fixture://catalog.json"], (
            "demo discovery must not crawl a university site"
        )
        assert not hasattr(adapter, "walker_outcomes"), "the demo adapter must stay walker-free"

    # --- justified-GREEN pin ----------------------------------------------

    def test_justified_green_titled_js_shell_is_a_catalogue(self):
        """A titled JS shell is a PROGRAM_CATALOG already on the baseline
        (page_classifier.py:341-348 via the title fallback at :471-477).

        justified-GREEN, T27 pattern: pinned so the walker's JS tier starts
        from a catalogue the classifier already recognises, and so a later
        classifier change cannot silently drop the shell.
        """
        from app.adapters.page_classifier import PageType, classify_page

        page = classify_page(
            url="https://uni.edu/en/programmes", html=_shape("js_catalog_shell.html")
        )
        assert page.page_type == PageType.PROGRAM_CATALOG
