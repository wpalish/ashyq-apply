"""Phase 3 §10 — conditional wording is not a settled requirement.

The guide lists "wording is conditional" as grounds for escalation and says
the answer is NEEDS_OFFICIAL_CLARIFICATION. Nothing checked it: a page saying
applicants are *typically* expected to have IELTS 6.5 produced a
VERIFIED_CURRENT claim, and a verified claim the applicant misses is a hard
filter — a university eliminated on a hedge.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder
from app.domain.claim_verifier import states_a_requirement_without_settling_it as hedge
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity


class TestWhatCountsAsAHedge:
    def test_a_typical_expectation_is_not_a_requirement(self):
        assert (
            hedge("Applicants are typically expected to have an IELTS band of 6.5.", 6.5)
            == "typically"
        )

    def test_a_plain_statement_is_left_alone(self):
        assert hedge("A minimum IELTS overall band of 6.5 is required.", 6.5) == ""

    def test_an_approximate_amount_is_hedged(self):
        assert hedge("Tuition is approximately 12,000 EUR per year.", 12000) == "approximately"

    def test_a_single_sentence_boolean_claim_is_covered(self):
        """ "An interview may be required" cannot be located by value, and it
        is exactly the shape where hedging matters."""
        assert hedge("An interview may be required at the discretion of staff.", True) == "may be"


class TestWhatMustNotCountAsAHedge:
    def test_a_hedge_in_a_neighbouring_sentence_does_not_reach_the_claim(self):
        """The false positive this rule was rewritten to fix: an excerpt is a
        window of a page, not a sentence. A deadline came back "conditional"
        because a credential-evaluation sentence sat beside it."""
        excerpt = (
            "The deadline is 15 January 2027. Applicants from outside the country may be "
            "asked to provide a credential evaluation."
        )
        assert hedge(excerpt, "2027-01-15") == ""

    def test_may_in_a_date_is_not_a_hedge(self):
        assert hedge("Applications close on 15 May 2027.", "2027-05-15") == ""

    def test_a_value_that_cannot_be_located_keeps_todays_status(self):
        """Missing a hedge leaves the product where it is; inventing one
        downgrades a requirement that was never in doubt."""
        excerpt = "Requirements vary. The published minimum is six point five overall."
        assert hedge(excerpt, 6.5) == ""


class TestWhatTheClaimEndsUpAs:
    def _builder(self) -> ClaimBuilder:
        return ClaimBuilder(
            source_url="https://example.edu/entry",
            official_domain=True,
            specificity=SourceSpecificity.PROGRAM,
            accessed_at=datetime(2026, 9, 22, tzinfo=UTC),
        )

    def test_a_hedged_claim_is_evidence_but_not_settled(self):
        claim = self._builder().add(
            ClaimType.IELTS_MIN_OVERALL,
            6.5,
            "Applicants are typically expected to have an IELTS band of 6.5.",
        )
        assert claim is not None, "the claim is kept: it is still evidence"
        assert claim.normalized_value == 6.5
        assert claim.status is ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert "typically" in claim.notes

    def test_an_unhedged_claim_on_an_official_page_stays_verified(self):
        claim = self._builder().add(
            ClaimType.IELTS_MIN_OVERALL, 6.5, "A minimum IELTS overall band of 6.5 is required."
        )
        assert claim is not None
        assert claim.status is ClaimStatus.VERIFIED_CURRENT
        assert claim.notes == ""

    def test_an_explicitly_passed_status_still_wins_for_a_weaker_one(self):
        """The rule only ever weakens a VERIFIED_CURRENT; it never promotes."""
        claim = self._builder().add(
            ClaimType.IELTS_MIN_OVERALL,
            6.5,
            "Applicants are typically expected to have 6.5.",
            status=ClaimStatus.UNVERIFIED,
        )
        assert claim is not None
        assert claim.status is ClaimStatus.UNVERIFIED
