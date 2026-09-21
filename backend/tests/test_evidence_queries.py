"""Plan V2-20 exit criterion — the questions the evidence must answer.

Each test is one of the questions the phase guide lists, asked of a small
synthetic run.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.claim_scope import ClaimScope, RequestedScope
from app.domain.enums import ClaimType
from app.domain.evidence_queries import (
    conflicting,
    live,
    scoped_to,
    stale,
    superseded_history,
    supporting,
    unknown_for,
)
from tests.conftest import make_claim as C

NOW = datetime(2026, 9, 21, tzinfo=UTC)


class TestWhichEvidenceSupportsThis:
    def test_it_returns_the_pages_not_a_verdict(self):
        """The product's promise is that a user can see the evidence."""
        claims = [
            C("ielts_min_overall", 6.5, url="https://example.edu/entry"),
            C("ielts_min_overall", 6.5, url="https://example.edu/international"),
            C("min_gpa", 3.0),
        ]
        found = supporting(claims, ClaimType.IELTS_MIN_OVERALL)
        assert [c.source_url for c in found] == [
            "https://example.edu/entry",
            "https://example.edu/international",
        ]

    def test_two_awards_are_two_answers_not_two_opinions(self):
        claims = [
            C("scholarship_amount", 5000, subject_key="Merit"),
            C("scholarship_amount", 9000, subject_key="Excellence"),
        ]
        found = supporting(claims, ClaimType.SCHOLARSHIP_AMOUNT, subject_key="Merit")
        assert [c.normalized_value for c in found] == [5000]

    def test_history_never_supports_anything(self):
        claims = [C("ielts_min_overall", 6.0, status="SUPERSEDED")]
        assert supporting(claims, ClaimType.IELTS_MIN_OVERALL) == []
        assert live(claims) == []


class TestWhichEvidenceIsAboutMe:
    def test_only_a_page_that_says_so_answers_a_scoped_question(self):
        """A page silent on the intake is not an answer to a question about it."""
        says = C("ielts_min_overall", 6.5, scope=ClaimScope(intake="Fall 2027"))
        silent = C("ielts_min_overall", 6.0, url="https://example.edu/x", scope=ClaimScope())
        unread = C("ielts_min_overall", 7.0, url="https://example.edu/y")
        found = scoped_to([says, silent, unread], RequestedScope(intake="fall 2027"))
        assert [c.normalized_value for c in found] == [6.5]


class TestWhatIsStaleConflictingOrMissing:
    def test_stale_is_answered_per_claim_type_window(self):
        old = C("admission_deadline", "2027-01-15", accessed_at=NOW - timedelta(days=400))
        fresh = C("admission_deadline", "2027-01-15", accessed_at=NOW)
        assert [c.accessed_at for c in stale([old, fresh], now=NOW)] == [old.accessed_at]

    def test_conflicting_claims_are_the_ones_marked_so(self):
        marked = C("ielts_min_overall", 6.5, status="CONFLICTING")
        assert conflicting([marked, C("min_gpa", 3.0)]) == [marked]

    def test_an_unanswered_fact_is_reported_as_a_missing_type(self):
        """Nothing to show for a fact nobody established, so it is named."""
        missing = unknown_for(
            [C("ielts_min_overall", 6.5)],
            [ClaimType.IELTS_MIN_OVERALL, ClaimType.MIN_GPA, ClaimType.TUITION],
        )
        assert missing == [ClaimType.MIN_GPA, ClaimType.TUITION]

    def test_a_superseded_claim_does_not_hide_a_gap(self):
        missing = unknown_for([C("min_gpa", 3.0, status="SUPERSEDED")], [ClaimType.MIN_GPA])
        assert missing == [ClaimType.MIN_GPA]


class TestWhatItUsedToSay:
    def test_history_comes_back_oldest_first(self):
        first = C(
            "ielts_min_overall", 6.0, status="SUPERSEDED", accessed_at=NOW - timedelta(days=60)
        )
        second = C(
            "ielts_min_overall", 6.5, status="SUPERSEDED", accessed_at=NOW - timedelta(days=30)
        )
        current = C("ielts_min_overall", 7.0, accessed_at=NOW)
        history = superseded_history([current, second, first], ClaimType.IELTS_MIN_OVERALL)
        assert [c.normalized_value for c in history] == [6.0, 6.5]
