"""Provenance: source hierarchy, contradiction handling and freshness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.conflicts import enforce_source_hierarchy, find_conflicts
from app.domain.enums import ClaimStatus, ClaimType
from app.domain.freshness import apply_freshness, is_stale, max_age_days, next_recheck_at
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim
from tests.conftest import make_claim as C

NOW = datetime.now(UTC)


class TestConflictDetection:
    def test_two_official_pages_disagreeing_produce_one_conflict(self):
        conflicts, updated = find_conflicts([
            C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/prog"),
            C("ielts_min_overall", 6.0, specificity="university_admissions", url="https://u/adm"),
        ])
        assert len(conflicts) == 1
        assert set(conflicts[0].values) == {6.5, 6.0}
        assert all(c.status is ClaimStatus.CONFLICTING for c in updated)

    def test_the_more_specific_source_is_marked_preferred_but_not_chosen(self):
        conflicts, _ = find_conflicts([
            C("ielts_min_overall", 6.0, specificity="university_admissions", url="https://u/adm"),
            C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/prog"),
        ])
        assert conflicts[0].preferred_claim_id == "https://u/prog"
        assert conflicts[0].unresolved is True

    def test_a_conflict_carries_a_sendable_question(self):
        conflicts, _ = find_conflicts(
            [C("admission_deadline", "2027-01-15", url="https://u/a"),
             C("admission_deadline", "2027-02-01", url="https://u/b")],
            context="BSc CS at Test University",
        )
        question = conflicts[0].question_for_admissions
        assert "Dear Admissions Office" in question
        assert "https://u/a" in question and "https://u/b" in question

    def test_two_different_awards_are_not_a_contradiction(self):
        """Different scholarships at one university have different amounts by design."""
        conflicts, _ = find_conflicts([
            C("scholarship_amount", 28350, subject_key="Talent Grant", url="https://u/s0"),
            C("scholarship_amount", 5000, subject_key="Merit Award", url="https://u/s1"),
        ])
        assert conflicts == []

    def test_two_pages_about_the_same_award_still_conflict(self):
        conflicts, _ = find_conflicts([
            C("scholarship_amount", 28350, subject_key="Talent Grant", url="https://u/s0"),
            C("scholarship_amount", 25000, subject_key="Talent Grant", url="https://u/faq"),
        ])
        assert len(conflicts) == 1

    def test_an_aggregator_cannot_create_a_conflict_with_an_official_page(self):
        conflicts, _ = find_conflicts([
            C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/prog"),
            C("ielts_min_overall", 7.0, specificity="aggregator", url="https://ranking.example"),
        ])
        assert conflicts == []

    def test_claims_for_different_programmes_are_kept_apart(self):
        conflicts, _ = find_conflicts([
            C("ielts_min_overall", 6.5, program="BSc CS"),
            C("ielts_min_overall", 7.0, program="MSc AI"),
        ])
        assert conflicts == []


class TestSourceHierarchy:
    def test_a_decision_grade_claim_from_an_aggregator_is_demoted(self):
        claims, questions = enforce_source_hierarchy(
            [C("tuition", 40000, specificity="aggregator", url="https://agg.example")]
        )
        assert claims[0].status is ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert claims[0].confidence <= 0.3
        assert len(questions) == 1

    def test_a_ranking_from_an_aggregator_is_left_alone(self):
        """Rankings are discovery input; an aggregator is their proper source."""
        claims, questions = enforce_source_hierarchy(
            [C("ranking_position", {"position": "49"}, specificity="aggregator")]
        )
        assert claims[0].status is ClaimStatus.VERIFIED_CURRENT
        assert questions == []

    def test_an_official_decision_grade_claim_survives(self):
        claims, questions = enforce_source_hierarchy(
            [C("ielts_min_overall", 6.5, specificity="program_intake")]
        )
        assert claims[0].status is ClaimStatus.VERIFIED_CURRENT
        assert questions == []


class TestFreshness:
    def test_deadlines_age_out_faster_than_policies(self):
        assert max_age_days(ClaimType.ADMISSION_DEADLINE) < max_age_days(ClaimType.MIN_GPA)

    def test_a_stale_verified_claim_is_downgraded(self):
        old = NOW - timedelta(days=45)
        assert is_stale(ClaimType.ADMISSION_DEADLINE, old)
        assert apply_freshness(ClaimStatus.VERIFIED_CURRENT, ClaimType.ADMISSION_DEADLINE, old) \
            is ClaimStatus.POSSIBLY_STALE

    def test_a_policy_claim_of_the_same_age_stays_current(self):
        old = NOW - timedelta(days=45)
        assert not is_stale(ClaimType.MIN_GPA, old)
        assert apply_freshness(ClaimStatus.VERIFIED_CURRENT, ClaimType.MIN_GPA, old) \
            is ClaimStatus.VERIFIED_CURRENT

    def test_freshness_never_upgrades_a_weaker_status(self):
        assert apply_freshness(ClaimStatus.UNVERIFIED, ClaimType.MIN_GPA, NOW) \
            is ClaimStatus.UNVERIFIED

    def test_a_recheck_time_is_offered_for_every_claim(self):
        assert next_recheck_at(ClaimType.TUITION, NOW) > NOW


class TestClaimShape:
    def test_a_long_excerpt_is_truncated_rather_than_rejected(self):
        claim = C("min_gpa", 3.0)
        claim = Claim(**{**claim.model_dump(), "original_text_excerpt": "x" * 5000})
        assert len(claim.original_text_excerpt) == MAX_EXCERPT_CHARS

    def test_a_source_url_must_be_http_or_a_fixture(self):
        try:
            Claim(claim_type=ClaimType.MIN_GPA, normalized_value=3.0,
                  source_url="javascript:alert(1)", accessed_at=NOW)
        except ValueError:
            pass
        else:
            raise AssertionError("a non-http source URL must be rejected")

    def test_a_fixture_url_is_accepted_so_demo_mode_shares_the_code_path(self):
        claim = Claim(claim_type=ClaimType.MIN_GPA, normalized_value=3.0,
                      source_url="fixture://u/page.html", accessed_at=NOW)
        assert claim.source_url.startswith("fixture://")
