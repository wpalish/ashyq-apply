"""V2-13 — the cheap pass and the ranking on top of it.

The baseline this has to beat is programme-page recall 1/10 with every claim
out of scope, so two things matter here and are tested hardest: the prefilter
must not throw away the right page, and the ranking must not promote a
neighbouring field into a match.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.search.base import SearchResult
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.prefilter import (
    ALLOWED_SCHEMES,
    Rejection,
    prefilter,
)
from app.adapters.search.retrieval import (
    SIGNAL_WEIGHTS,
    discover_candidates,
    rank_candidates,
    tokenize,
)
from app.domain.enums import DegreeLevel

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def result(url: str, title: str = "", snippet: str = "", rank: int = 1) -> SearchResult:
    return SearchResult(
        url=url, title=title, snippet=snippet, provider="fake", rank=rank, retrieved_at=NOW
    )


def an_intent(**kw) -> DiscoveryIntent:
    return DiscoveryIntent(
        **{
            "institution": "Nazarbayev University",
            "domain": "nu.edu.kz",
            "degree": DegreeLevel.BACHELOR,
            "field": "computer science",
            **kw,
        }
    )


def run(results, **kw):
    return prefilter(results, domain="nu.edu.kz", degree=DegreeLevel.BACHELOR, **kw)


class TestThePrefilterDropsWhatIsCheapToKnowIsWrong:
    def test_a_non_http_scheme_never_reaches_a_fetch(self):
        outcome = run([result("mailto:admissions@nu.edu.kz"), result("javascript:void(0)")])

        assert outcome.kept == ()
        assert set(outcome.rejection_counts) == {Rejection.SCHEME}
        assert set(ALLOWED_SCHEMES) == {"http", "https"}

    def test_another_institution_is_rejected_even_when_the_name_looks_right(self):
        outcome = run([result("https://notnu.edu.kz/programmes/computer-science")])

        assert outcome.rejection_counts == {Rejection.OTHER_INSTITUTION: 1}

    def test_a_subdomain_of_the_institution_is_kept(self):
        """``edu.kz`` is a multipart suffix; naive matching loses admissions hosts."""
        outcome = run([result("https://admissions.nu.edu.kz/bachelor/cs")])

        assert [c.url for c in outcome.kept] == ["https://admissions.nu.edu.kz/bachelor/cs"]

    @pytest.mark.parametrize(
        "url",
        [
            "https://nu.edu.kz/news/cs-wins",
            "https://nu.edu.kz/events/open-day",
            "https://nu.edu.kz/jobs/lecturer",
            "https://nu.edu.kz/media/banner.png",
        ],
    )
    def test_news_events_jobs_and_media_are_rejected(self, url):
        assert run([result(url)]).rejection_counts == {Rejection.NOT_A_PROGRAMME_PAGE: 1}

    def test_the_wrong_degree_level_is_a_rejection_not_a_penalty(self):
        """An MSc page is not a weak bachelor lead; it is the wrong page."""
        outcome = run([result("https://nu.edu.kz/programmes/msc-computer-science")])

        assert outcome.rejection_counts == {Rejection.WRONG_DEGREE_LEVEL: 1}

    def test_a_page_that_names_no_level_survives(self):
        """Most catalogue pages name no level; rejecting them would lose the field."""
        outcome = run([result("https://nu.edu.kz/programmes/computer-science")])

        assert len(outcome.kept) == 1

    def test_a_pdf_is_flagged_and_kept(self):
        """§9: a PDF can be the programme handbook or a credential table."""
        outcome = run([result("https://nu.edu.kz/programmes/handbook.pdf")])

        assert outcome.kept[0].is_pdf is True

    def test_the_same_page_under_two_urls_is_kept_once(self):
        outcome = run(
            [
                result("https://nu.edu.kz/programmes/cs?utm_source=x", rank=1),
                result("https://nu.edu.kz/programmes/cs#overview", rank=2),
            ]
        )

        assert len(outcome.kept) == 1
        assert outcome.rejection_counts == {Rejection.DUPLICATE: 1}

    def test_the_best_ranked_copy_is_the_one_kept(self):
        outcome = run(
            [
                result("https://nu.edu.kz/programmes/cs", rank=1),
                result("https://nu.edu.kz/programmes/cs/", rank=7),
            ]
        )

        assert outcome.kept[0].rank == 1

    def test_every_rejection_says_why(self):
        """Forty news articles and nothing found look identical without reasons."""
        outcome = run(
            [
                result("mailto:x@nu.edu.kz"),
                result("https://elsewhere.test/cs"),
                result("https://nu.edu.kz/news/a"),
                result("https://nu.edu.kz/programmes/phd-cs"),
            ]
        )

        assert outcome.rejection_counts == {
            Rejection.SCHEME: 1,
            Rejection.OTHER_INSTITUTION: 1,
            Rejection.NOT_A_PROGRAMME_PAGE: 1,
            Rejection.WRONG_DEGREE_LEVEL: 1,
        }
        assert all(r.reason for r in outcome.rejected)


class TestTheRankingKeepsTheFieldBoundary:
    def test_the_requested_field_outranks_a_neighbouring_one(self):
        outcome = run(
            [
                result("https://nu.edu.kz/programmes/bsc-data-science", "BSc Data Science", rank=1),
                result(
                    "https://nu.edu.kz/programmes/bsc-computer-science",
                    "BSc Computer Science",
                    rank=2,
                ),
            ]
        )

        ranked = rank_candidates(outcome, an_intent())

        assert ranked[0].url.endswith("bsc-computer-science")
        assert "strong_alias_in_title" in ranked[0].signals

    def test_a_neighbour_is_kept_but_marked_as_one(self):
        """V2-12's rule, carried into the ranking: a candidate, never a match."""
        outcome = run([result("https://nu.edu.kz/programmes/bsc-data-science", "BSc Data Science")])

        ranked = rank_candidates(outcome, an_intent())

        assert ranked[0].signals[0] == "related_field_only"
        assert SIGNAL_WEIGHTS["related_field_only"] < 0

    def test_a_strong_alias_counts_as_the_field(self):
        """``computing science`` is the same field; the ranking must agree."""
        outcome = run(
            [result("https://nu.edu.kz/programmes/computing-science", "Computing Science")]
        )

        ranked = rank_candidates(outcome, an_intent())

        assert "strong_alias_in_title" in ranked[0].signals

    def test_every_candidate_explains_its_own_score(self):
        outcome = run(
            [result("https://nu.edu.kz/programmes/bsc-computer-science", "BSc Computer Science")]
        )

        ranked = rank_candidates(outcome, an_intent())

        assert ranked[0].explanation
        assert all(s in SIGNAL_WEIGHTS for s in ranked[0].signals)

    def test_an_empty_prefilter_result_ranks_to_nothing(self):
        assert rank_candidates(run([]), an_intent()) == ()

    def test_ties_break_on_url_so_the_order_is_stable(self):
        outcome = run(
            [
                result("https://nu.edu.kz/b/computer-science", "Computer Science"),
                result("https://nu.edu.kz/a/computer-science", "Computer Science"),
            ]
        )

        first = [c.url for c in rank_candidates(outcome, an_intent())]
        second = [c.url for c in rank_candidates(outcome, an_intent())]

        assert first == second == sorted(first)

    def test_tokenize_splits_slugs_and_keeps_non_latin(self):
        assert tokenize("BSc-Computer_Science/2027") == ["bsc", "computer", "science", "2027"]
        assert tokenize("информатика") == ["информатика"]


class TestTheWholeRunIsBoundedAndReported:
    def _provider(self, rows, intent):
        corpus = {q.text: rows for q in queries_for(intent, budget=99)}
        return FakeSearchProvider(corpus, now=NOW)

    async def test_it_finds_the_programme_page_and_says_how(self):
        intent = an_intent()
        rows = [
            ("https://nu.edu.kz/programmes/bsc-computer-science", "BSc Computer Science", ""),
            ("https://nu.edu.kz/news/cs-wins", "CS wins", ""),
            ("https://nu.edu.kz/programmes/msc-computer-science", "MSc Computer Science", ""),
        ]

        report = await discover_candidates(self._provider(rows, intent), intent)

        assert report.candidates[0].url.endswith("bsc-computer-science")
        assert report.rejection_counts[Rejection.NOT_A_PROGRAMME_PAGE]
        assert report.rejection_counts[Rejection.WRONG_DEGREE_LEVEL]
        assert report.ontology_version
        assert report.provider == "fake"

    async def test_top_k_bounds_what_comes_back(self):
        intent = an_intent()
        rows = [
            (f"https://nu.edu.kz/programmes/cs-{i}", f"Computer Science {i}", "") for i in range(30)
        ]

        report = await discover_candidates(self._provider(rows, intent), intent, top_k=5)

        assert len(report.candidates) == 5

    async def test_a_failing_query_is_reported_not_folded_into_a_smaller_result(self):
        """A degraded run must look degraded, not like a run that found less."""
        intent = an_intent()
        provider = FakeSearchProvider({}, fail_with="quota exhausted")

        report = await discover_candidates(provider, intent)

        assert report.candidates == ()
        assert len(report.failed_queries) == len(report.queries_run)

    async def test_the_query_budget_is_respected(self):
        intent = an_intent()
        provider = self._provider([], intent)

        report = await discover_candidates(provider, intent, query_budget=2)

        assert len(report.queries_run) == 2
        assert len(provider.calls) == 2

    async def test_every_query_is_restricted_to_the_institution(self):
        intent = an_intent()
        provider = self._provider([], intent)

        await discover_candidates(provider, intent)

        assert all(domains == ("nu.edu.kz",) for _, domains, _ in provider.calls)

    async def test_top_k_below_one_is_refused(self):
        with pytest.raises(ValueError, match="top_k"):
            await discover_candidates(FakeSearchProvider(), an_intent(), top_k=0)


class TestTheRemainingSignals:
    def test_a_catalogue_path_is_a_positive_signal(self):
        outcome = run([result("https://nu.edu.kz/education/programmes", "Programmes")])

        assert "catalogue_path" in rank_candidates(outcome, an_intent())[0].signals

    def test_a_pdf_scores_below_an_equivalent_html_page(self):
        """Not a rejection — a handbook is real — but a page is preferred."""
        outcome = run(
            [
                result("https://nu.edu.kz/programmes/computer-science.pdf", "Computer Science"),
                result("https://nu.edu.kz/programmes/computer-science", "Computer Science"),
            ]
        )

        ranked = rank_candidates(outcome, an_intent())

        assert not ranked[0].is_pdf
        assert ranked[1].is_pdf
        assert "pdf" in ranked[1].signals

    def test_bm25_scores_an_empty_document_as_zero_rather_than_dividing_by_it(self):
        from app.adapters.search.retrieval import _Bm25

        assert _Bm25([[], ["computer", "science"]]).score(0, ["computer"]) == 0.0
