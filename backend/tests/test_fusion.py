"""V2-16 — merging candidate lists without inventing a number.

The property worth protecting is that fusion never compares two scores that
were never comparable, and never loses the attribution that makes a fused row
trustworthy.
"""

from __future__ import annotations

import pytest

from app.adapters.search.fusion import (
    GENERATOR_WEIGHTS,
    RRF_K,
    FusedCandidate,
    Generator,
    SourcedCandidate,
    fuse,
)

CS = "https://nu.edu.kz/programmes/cs"
NEWS = "https://nu.edu.kz/news/cs"


def c(url: str, generator: Generator, rank: int = 1, title: str = "") -> SourcedCandidate:
    return SourcedCandidate(url=url, generator=generator, rank=rank, title=title)


class TestProvenanceSurvives:
    def test_a_url_found_three_ways_is_one_row_naming_all_three(self):
        fused = fuse(
            [
                c(CS, Generator.SITEMAP, 3),
                c(CS, Generator.WEB_SEARCH, 1),
                c(CS, Generator.REGISTRY, 1),
            ]
        )

        assert len(fused) == 1
        assert fused[0].agreement == 3
        assert set(fused[0].generators) == {
            Generator.SITEMAP,
            Generator.WEB_SEARCH,
            Generator.REGISTRY,
        }

    def test_each_attribution_keeps_the_rank_that_generator_gave(self):
        fused = fuse([c(CS, Generator.SITEMAP, 7), c(CS, Generator.REGISTRY, 2)])

        ranks = {a.generator: a.rank for a in fused[0].attributions}

        assert ranks == {Generator.SITEMAP: 7, Generator.REGISTRY: 2}
        assert fused[0].best_rank == 2

    def test_the_strongest_generator_is_named_first(self):
        fused = fuse([c(CS, Generator.SITEMAP, 1), c(CS, Generator.REGISTRY, 1)])

        assert fused[0].generators[0] is Generator.REGISTRY

    def test_provenance_reads_back(self):
        fused = fuse([c(CS, Generator.REGISTRY, 1), c(CS, Generator.SITEMAP, 4)])

        assert fused[0].provenance == "registry#1, sitemap#4"

    def test_the_same_page_under_two_urls_is_one_row(self):
        fused = fuse(
            [
                c(CS, Generator.REGISTRY, 1),
                c(f"{CS}?utm_source=mail", Generator.WEB_SEARCH, 1),
                c(f"{CS}/", Generator.SITEMAP, 2),
            ]
        )

        assert len(fused) == 1
        assert fused[0].agreement == 3

    def test_one_generator_listing_a_url_twice_is_one_attribution_at_its_best_rank(self):
        fused = fuse([c(CS, Generator.SITEMAP, 9), c(CS, Generator.SITEMAP, 2)])

        assert fused[0].agreement == 1
        assert fused[0].attributions[0].rank == 2


class TestFusionIsByRankNotByScore:
    def test_agreement_beats_a_single_first_place(self):
        """Two independent generators agreeing is stronger than one being sure."""
        fused = fuse(
            [
                c(NEWS, Generator.WEB_SEARCH, 1),
                c(CS, Generator.SITEMAP, 5),
                c(CS, Generator.CATALOGUE_WALKER, 5),
            ]
        )

        assert fused[0].url == CS

    def test_a_missing_generator_contributes_nothing_rather_than_skewing_the_result(self):
        """Web search is absent until a provider exists; that must be harmless."""
        with_web = fuse([c(CS, Generator.SITEMAP, 1), c(CS, Generator.WEB_SEARCH, 1)])
        without = fuse([c(CS, Generator.SITEMAP, 1)])

        assert with_web[0].score > without[0].score
        assert without[0].url == CS

    def test_an_earlier_rank_scores_higher_within_one_generator(self):
        fused = fuse([c(CS, Generator.SITEMAP, 1), c(NEWS, Generator.SITEMAP, 2)])

        assert [f.url for f in fused] == [CS, NEWS]

    def test_a_trusted_generator_outweighs_a_weak_one_at_the_same_rank(self):
        fused = fuse([c(NEWS, Generator.SITEMAP, 1), c(CS, Generator.REGISTRY, 1)])

        assert fused[0].url == CS

    def test_the_weights_are_a_named_table_and_order_trust_deliberately(self):
        assert GENERATOR_WEIGHTS[Generator.REGISTRY] > GENERATOR_WEIGHTS[Generator.WEB_SEARCH]
        assert GENERATOR_WEIGHTS[Generator.WEB_SEARCH] > GENERATOR_WEIGHTS[Generator.SITEMAP]
        assert set(GENERATOR_WEIGHTS) == set(Generator)

    def test_weights_can_be_overridden_for_an_experiment(self):
        weights = {Generator.SITEMAP: 10.0, Generator.REGISTRY: 0.1}

        fused = fuse([c(NEWS, Generator.SITEMAP, 1), c(CS, Generator.REGISTRY, 1)], weights=weights)

        assert fused[0].url == NEWS

    def test_the_rrf_constant_is_the_published_one(self):
        assert RRF_K == 60


class TestTheOutputIsBoundedAndDeterministic:
    def test_top_k_bounds_the_result(self):
        candidates = [c(f"https://nu.edu.kz/p/{i}", Generator.SITEMAP, i + 1) for i in range(30)]

        assert len(fuse(candidates, top_k=5)) == 5

    def test_top_k_below_one_is_refused(self):
        with pytest.raises(ValueError, match="top_k"):
            fuse([], top_k=0)

    def test_nothing_in_nothing_out(self):
        assert fuse([]) == ()

    def test_ties_resolve_the_same_way_every_time(self):
        candidates = [
            c("https://nu.edu.kz/b", Generator.SITEMAP, 1),
            c("https://nu.edu.kz/a", Generator.SITEMAP, 1),
        ]

        assert [f.url for f in fuse(candidates)] == [f.url for f in fuse(candidates)]
        assert [f.url for f in fuse(candidates)] == [
            "https://nu.edu.kz/a",
            "https://nu.edu.kz/b",
        ]

    def test_a_title_is_taken_from_the_first_generator_that_supplies_one(self):
        fused = fuse(
            [
                c(CS, Generator.REGISTRY, 1),
                c(CS, Generator.SITEMAP, 2, title="BSc Computer Science"),
            ]
        )

        assert fused[0].title == "BSc Computer Science"


class TestTheMappingFormAndItsGuard:
    def test_streams_can_be_given_per_generator(self):
        fused = fuse(
            {
                Generator.REGISTRY: [c(CS, Generator.REGISTRY, 1)],
                Generator.SITEMAP: [c(NEWS, Generator.SITEMAP, 1)],
            }
        )

        assert [f.url for f in fused] == [CS, NEWS]

    def test_a_candidate_filed_under_the_wrong_generator_is_refused(self):
        """A wrong attribution is worse than none: it is what a reviewer trusts."""
        with pytest.raises(ValueError, match="filed under"):
            fuse({Generator.REGISTRY: [c(CS, Generator.SITEMAP, 1)]})


class TestTheCandidateTypesRefuseNonsense:
    def test_rank_is_one_based(self):
        with pytest.raises(ValueError, match="1-based"):
            c(CS, Generator.SITEMAP, 0)

    def test_a_candidate_needs_a_url(self):
        with pytest.raises(ValueError, match="without a URL"):
            c("", Generator.SITEMAP, 1)

    def test_a_fused_candidate_reports_agreement_directly(self):
        from app.adapters.search.fusion import Attribution

        fused = FusedCandidate(
            url=CS,
            title="",
            score=1.0,
            attributions=(
                Attribution(Generator.REGISTRY, 1),
                Attribution(Generator.SITEMAP, 4),
            ),
        )

        assert fused.agreement == 2
        assert fused.best_rank == 1
