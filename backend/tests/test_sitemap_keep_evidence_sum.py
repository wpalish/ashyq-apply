"""Plan v3 rule R3 (SK-1): the sitemap stage keeps a URL on subject+level evidence.

``keep()`` dropped a URL the moment it carried no structural programme word,
before the subject and level bonuses were added, so 7 of the 39 development
gold URLs never reached the confirm stage although their slug names the subject
(URL lexicon audit, wayfinder ticket 09). Decision (ticket 18): keep such a URL
when the slug names the subject *and* the level, or the subject as an exact
field slug; at most 10 of the 40 programme slots, never displacing a URL with a
structural score; the confirm order stays score-descending. Offline: the seven
gold URL shapes and the negatives are served from a stub, nothing is fetched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    MAX_CANDIDATES_PER_CATEGORY,
    MAX_EVIDENCE_ONLY_CANDIDATES,
    PageCategory,
    canonical_url,
    categorise_url,
    evidence_only_score,
    hold_evidence_only,
    merge_evidence_only,
)
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, program_html, sitemap_xml

FIELDS = ["computer science"]
UM = "https://study.um.edu.my"
UM_GOLD = [
    f"{UM}/bachelor-of-computer-science-software-engineering",
    f"{UM}/bachelor-of-computer-science-information-system",
    f"{UM}/bachelor-of-computer-science-data-science",
    f"{UM}/bachelor-of-computer-science-computer-system-and-network",
]
UBA_GOLD = "https://ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/"
VIENNA_GOLD = "https://aufnahmeverfahren.univie.ac.at/en/computer-science"
PSACLAY_GOLD = "https://www.universite-paris-saclay.fr/formation/licence/informatique"
GOLD = [*UM_GOLD, UBA_GOLD, VIENNA_GOLD, PSACLAY_GOLD]


@pytest.fixture
def r3(monkeypatch):
    monkeypatch.setattr(live_discovery, "SITEMAP_KEEP_EVIDENCE_SUM", True)


@pytest.fixture
def profile_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


def _registry(tmp_path, homepage: str, country: str = "Malaysia"):
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps([{"name": "U", "country": country, "city": "X", "homepage": homepage}])
    )
    return path


async def _discover(tmp_path, profile, homepage: str, pages: dict, country: str = "Malaysia"):
    site = StubSite(pages)
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = live_discovery.LiveDiscoveryAdapter(
            fetcher, _registry(tmp_path, homepage, country)
        )
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0], site


def _programme_reads(site: StubSite, origin: str) -> list[str]:
    """The confirm reads, in order: every request that is not robots or a sitemap."""
    return [
        url
        for url in site.requested
        if url.startswith(origin)
        and not url.endswith((".xml", "robots.txt"))
        and url != origin + "/"
    ]


class TestTheSevenGoldShapes:
    @pytest.mark.parametrize("url", GOLD)
    def test_no_structural_word_today(self, url: str) -> None:
        # Why they were dropped: categorise_url files none of them.
        assert categorise_url(url) == (None, 0)

    @pytest.mark.parametrize("url", [*UM_GOLD, UBA_GOLD, PSACLAY_GOLD])
    def test_subject_and_level_qualify(self, url: str) -> None:
        assert evidence_only_score(url, FIELDS, "bachelor") > 0

    def test_a_bare_exact_field_slug_on_an_admissions_host_qualifies(self) -> None:
        # Vienna names no level: the exact field slug is the evidence.
        assert evidence_only_score(VIENNA_GOLD, FIELDS, "bachelor") == 16

    def test_the_score_is_the_subject_and_level_bonuses(self) -> None:
        assert evidence_only_score(UM_GOLD[0], FIELDS, "bachelor") == 16 + 4
        assert evidence_only_score(UBA_GOLD, FIELDS, "bachelor") == 16 + 4
        # LI-1/R1 localized alias "informatique" and degree word "licence".
        assert evidence_only_score(PSACLAY_GOLD, FIELDS, "bachelor") == 8 + 4


class TestNegatives:
    @pytest.mark.parametrize(
        "url",
        [
            # News and events that name the subject and the level.
            f"{UM}/news/bachelor-of-computer-science-students-win",
            f"{UM}/events/bachelor-computer-science",
            f"{UM}/2025/10/bachelor-computer-science-intake",
            f"{UM}/bachelor-of-computer-science-students-win-hackathon",
            f"{UM}/bachelor-computer-science-open-day",
            f"{UM}/bachelor-computer-science-seminar-2025-10-01",
            f"{UM}/computer-science-bachelor-award-winners",
            # Research, people, money.
            f"{UM}/research/computer-science",
            f"{UM}/research/computer-science-lab",
            f"{UM}/staff/computer-science",
            f"{UM}/computer-science-bachelor-tuition-fees",
            f"{UM}/bachelor-computer-science-scholarship",
            # Another level, whatever the subject.
            f"{UM}/master-of-computer-science",
            f"{UM}/master-of-computer-science-software-engineering",
            f"{UM}/phd-computer-science",
            "https://www.universite-paris-saclay.fr/formation/master/informatique",
            # The subject alone, not as an exact slug; or no subject.
            f"{UM}/en/computer-science-department-history",
            f"{UM}/bachelor-of-economics",
            # One word of the field is not the field (whole-phrase test).
            "https://ingresantes.exactas.uba.ar/licenciatura-en-ciencias-biologicas/",
            f"{UM}/bachelor-of-materials-science",
            f"{UM}/bachelor-of-computer-engineering",
            f"{UM}/about",
        ],
    )
    def test_does_not_qualify(self, url: str) -> None:
        assert evidence_only_score(url, FIELDS, "bachelor") == 0

    def test_a_master_applicant_does_not_get_the_bachelor_slugs(self) -> None:
        assert evidence_only_score(UM_GOLD[0], FIELDS, "master") == 0
        assert evidence_only_score(f"{UM}/master-of-computer-science", FIELDS, "master") == 20

    def test_no_requested_field_no_evidence(self) -> None:
        assert evidence_only_score(UM_GOLD[0], [], "bachelor") == 0


class TestTheCap:
    def test_at_most_ten_held_and_the_best_are_kept(self) -> None:
        held: list[tuple[int, str]] = []
        for i in range(MAX_EVIDENCE_ONLY_CANDIDATES + 5):
            hold_evidence_only(held, 12, f"{UM}/bachelor-of-informatics-{i}")
        assert len(held) == MAX_EVIDENCE_ONLY_CANDIDATES == 10
        assert hold_evidence_only(held, 20, UM_GOLD[0])
        assert len(held) == 10 and (20, UM_GOLD[0]) in held
        assert not hold_evidence_only(held, 12, f"{UM}/bachelor-of-informatics-late")

    def test_never_displaces_a_structural_pick(self) -> None:
        structural = [(9, f"{UM}/programmes/x-{i}") for i in range(MAX_CANDIDATES_PER_CATEGORY)]
        held = [(20, url) for url in UM_GOLD]
        assert merge_evidence_only(structural, held) == []
        assert len(merge_evidence_only(structural[:38], held)) == 2
        assert len(merge_evidence_only([], held)) == 4

    async def test_a_site_full_of_slugs_fills_only_the_free_slots(
        self, tmp_path, profile_bachelor, r3
    ) -> None:
        structural = [f"{UM}/programmes/bachelor-computer-science-{i}" for i in range(35)]
        slugs = [f"{UM}/bachelor-of-computer-science-track-{i}" for i in range(15)]
        _, trace, _ = await _discover(
            tmp_path,
            profile_bachelor,
            f"{UM}/",
            {
                f"{UM}/robots.txt": f"Sitemap: {UM}/s.xml\n",
                f"{UM}/s.xml": sitemap_xml(*slugs, *structural),
            },
        )
        # 35 structural + 10 held evidence picks passed keep(); 5 of the 10 fit.
        assert trace.sitemap_urls_kept == 45
        no_slot = [u for u, r in trace.rejected if r.startswith("R3: no slot left")]
        assert len(no_slot) == 5


class TestThroughTheSitemapStage:
    async def test_on_the_um_gold_page_is_kept_read_and_confirmed(
        self, tmp_path, profile_bachelor, r3
    ) -> None:
        candidate, trace, _site = await _discover(
            tmp_path,
            profile_bachelor,
            f"{UM}/",
            {
                f"{UM}/robots.txt": f"Sitemap: {UM}/s.xml\n",
                f"{UM}/s.xml": sitemap_xml(
                    f"{UM}/news/bachelor-of-computer-science-students-win",
                    f"{UM}/master-of-computer-science",
                    *UM_GOLD,
                ),
                UM_GOLD[0]: program_html("Bachelor of Computer Science (Software Engineering)"),
            },
        )
        assert candidate.programs and candidate.programs[0].url == UM_GOLD[0]
        read = [url for url, _verdict in trace.pages_read]
        assert UM_GOLD[0] in read
        assert f"{UM}/news/bachelor-of-computer-science-students-win" not in read
        assert f"{UM}/master-of-computer-science" not in read

    async def test_off_the_um_gold_page_is_dropped_before_the_confirm_stage(
        self, tmp_path, profile_bachelor
    ) -> None:
        assert live_discovery.SITEMAP_KEEP_EVIDENCE_SUM is False
        candidate, trace, _site = await _discover(
            tmp_path,
            profile_bachelor,
            f"{UM}/",
            {
                f"{UM}/robots.txt": f"Sitemap: {UM}/s.xml\n",
                f"{UM}/s.xml": sitemap_xml(*UM_GOLD),
                UM_GOLD[0]: program_html("Bachelor of Computer Science (Software Engineering)"),
            },
        )
        assert candidate.programs == []
        assert trace.sitemap_urls_kept == 0
        assert UM_GOLD[0] not in [url for url, _verdict in trace.pages_read]

    async def test_on_the_uba_gold_page_is_kept_and_read(
        self, tmp_path, profile_bachelor, r3
    ) -> None:
        origin = "https://ingresantes.exactas.uba.ar"
        _candidate, trace, site = await _discover(
            tmp_path,
            profile_bachelor,
            f"{origin}/",
            {
                f"{origin}/robots.txt": f"Sitemap: {origin}/s.xml\n",
                f"{origin}/s.xml": sitemap_xml(
                    f"{origin}/licenciatura-en-ciencias-biologicas/",
                    UBA_GOLD,
                ),
            },
            country="Argentina",
        )
        # Kept (the biology licence names no requested subject) and read.
        assert trace.sitemap_urls_kept == 1
        assert _programme_reads(site, origin)[:1] == [canonical_url(UBA_GOLD)]

    async def test_structural_leads_with_the_subject_are_read_first(
        self, tmp_path, profile_bachelor, r3
    ) -> None:
        # A structural pick naming subject and level outscores any evidence
        # pick (structure + subject + level), so it is read before them.
        structural = f"{UM}/programmes/bachelor-computer-science"
        _candidate, _trace, site = await _discover(
            tmp_path,
            profile_bachelor,
            f"{UM}/",
            {
                f"{UM}/robots.txt": f"Sitemap: {UM}/s.xml\n",
                f"{UM}/s.xml": sitemap_xml(*UM_GOLD, structural),
            },
        )
        reads = _programme_reads(site, UM)
        assert reads[0] == structural
        assert set(reads[1:5]) == set(UM_GOLD)

    async def test_the_confirm_order_stays_score_descending(
        self, tmp_path, profile_bachelor, r3
    ) -> None:
        # A structural lead without the subject scores below an evidence pick
        # that names subject and level; the queue is not reordered by kind.
        weak = f"{UM}/programmes/bachelor-mathematics"
        assert categorise_url(weak) == (PageCategory.PROGRAM_PAGE, 4)
        _candidate, _trace, site = await _discover(
            tmp_path,
            profile_bachelor,
            f"{UM}/",
            {
                f"{UM}/robots.txt": f"Sitemap: {UM}/s.xml\n",
                f"{UM}/s.xml": sitemap_xml(weak, UM_GOLD[0]),
            },
        )
        reads = _programme_reads(site, UM)
        assert reads.index(UM_GOLD[0]) < reads.index(weak)


def test_the_rule_is_off_by_default() -> None:
    assert live_discovery.SITEMAP_KEEP_EVIDENCE_SUM is False


def test_the_harness_flag_turns_it_on_and_is_passed_to_repetitions() -> None:
    from evaluation.research import live

    source = Path(live.__file__).read_text(encoding="utf-8")
    assert '"--sitemap-keep-evidence-sum",' in source
    assert "r3_module.SITEMAP_KEEP_EVIDENCE_SUM = True" in source
    assert '["--sitemap-keep-evidence-sum"]' in source
