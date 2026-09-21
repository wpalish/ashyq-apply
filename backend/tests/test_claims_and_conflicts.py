"""Provenance: source hierarchy, contradiction handling and freshness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.claim_scope import ClaimScope
from app.domain.conflicts import enforce_source_hierarchy, find_conflicts
from app.domain.enums import ClaimStatus, ClaimType, ConflictKind
from app.domain.freshness import apply_freshness, is_stale, max_age_days, next_recheck_at
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim
from tests.conftest import make_claim as C

NOW = datetime.now(UTC)


class TestConflictDetection:
    def test_two_official_pages_disagreeing_produce_one_conflict(self):
        conflicts, updated = find_conflicts(
            [
                C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/prog"),
                C(
                    "ielts_min_overall",
                    6.0,
                    specificity="university_admissions",
                    url="https://u/adm",
                ),
            ]
        )
        assert len(conflicts) == 1
        assert set(conflicts[0].values) == {6.5, 6.0}
        assert all(c.status is ClaimStatus.CONFLICTING for c in updated)

    def test_the_more_specific_source_is_marked_preferred_but_not_chosen(self):
        conflicts, _ = find_conflicts(
            [
                C(
                    "ielts_min_overall",
                    6.0,
                    specificity="university_admissions",
                    url="https://u/adm",
                ),
                C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/prog"),
            ]
        )
        assert conflicts[0].preferred_claim_id == "https://u/prog"
        assert conflicts[0].unresolved is True

    def test_a_conflict_carries_a_sendable_question(self):
        conflicts, _ = find_conflicts(
            [
                C("admission_deadline", "2027-01-15", url="https://u/a"),
                C("admission_deadline", "2027-02-01", url="https://u/b"),
            ],
            context="BSc CS at Test University",
        )
        question = conflicts[0].question_for_admissions
        assert "Dear Admissions Office" in question
        assert "https://u/a" in question and "https://u/b" in question

    def test_two_different_awards_are_not_a_contradiction(self):
        """Different scholarships at one university have different amounts by design."""
        conflicts, _ = find_conflicts(
            [
                C("scholarship_amount", 28350, subject_key="Talent Grant", url="https://u/s0"),
                C("scholarship_amount", 5000, subject_key="Merit Award", url="https://u/s1"),
            ]
        )
        assert conflicts == []

    def test_two_pages_about_the_same_award_still_conflict(self):
        conflicts, _ = find_conflicts(
            [
                C("scholarship_amount", 28350, subject_key="Talent Grant", url="https://u/s0"),
                C("scholarship_amount", 25000, subject_key="Talent Grant", url="https://u/faq"),
            ]
        )
        assert len(conflicts) == 1

    def test_an_aggregator_cannot_create_a_conflict_with_an_official_page(self):
        conflicts, _ = find_conflicts(
            [
                C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/prog"),
                C(
                    "ielts_min_overall",
                    7.0,
                    specificity="aggregator",
                    url="https://ranking.example",
                ),
            ]
        )
        assert conflicts == []

    def test_claims_for_different_programmes_are_kept_apart(self):
        conflicts, _ = find_conflicts(
            [
                C("ielts_min_overall", 6.5, program="BSc CS"),
                C("ielts_min_overall", 7.0, program="MSc AI"),
            ]
        )
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
        assert (
            apply_freshness(ClaimStatus.VERIFIED_CURRENT, ClaimType.ADMISSION_DEADLINE, old)
            is ClaimStatus.POSSIBLY_STALE
        )

    def test_a_policy_claim_of_the_same_age_stays_current(self):
        old = NOW - timedelta(days=45)
        assert not is_stale(ClaimType.MIN_GPA, old)
        assert (
            apply_freshness(ClaimStatus.VERIFIED_CURRENT, ClaimType.MIN_GPA, old)
            is ClaimStatus.VERIFIED_CURRENT
        )

    def test_freshness_never_upgrades_a_weaker_status(self):
        assert (
            apply_freshness(ClaimStatus.UNVERIFIED, ClaimType.MIN_GPA, NOW)
            is ClaimStatus.UNVERIFIED
        )

    def test_a_recheck_time_is_offered_for_every_claim(self):
        assert next_recheck_at(ClaimType.TUITION, NOW) > NOW


class TestClaimShape:
    def test_a_long_excerpt_is_truncated_rather_than_rejected(self):
        claim = C("min_gpa", 3.0)
        claim = Claim(**{**claim.model_dump(), "original_text_excerpt": "x" * 5000})
        assert len(claim.original_text_excerpt) == MAX_EXCERPT_CHARS

    def test_a_source_url_must_be_http_or_a_fixture(self):
        try:
            Claim(
                claim_type=ClaimType.MIN_GPA,
                normalized_value=3.0,
                source_url="javascript:alert(1)",
                accessed_at=NOW,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("a non-http source URL must be rejected")

    def test_a_fixture_url_is_accepted_so_demo_mode_shares_the_code_path(self):
        claim = Claim(
            claim_type=ClaimType.MIN_GPA,
            normalized_value=3.0,
            source_url="fixture://u/page.html",
            accessed_at=NOW,
        )
        assert claim.source_url.startswith("fixture://")


class TestAConflictSaysWhatKindItIs:
    """V2-26 — a scope difference is not a contradiction.

    Phase 2's exit criterion in its own words: conflict reasons must
    distinguish a true conflict from a difference of scope.
    """

    def test_two_fees_for_two_fee_statuses_are_both_correct(self):
        from app.domain.conflicts import find_conflicts

        claims = [
            C("tuition", 9250.0, scope=ClaimScope(residency="home")),
            C(
                "tuition",
                38000.0,
                url="https://example.edu/overseas",
                scope=ClaimScope(residency="overseas"),
            ),
        ]
        conflicts, updated = find_conflicts(claims)
        assert len(conflicts) == 1
        assert conflicts[0].kind is ConflictKind.DIFFERENT_RESIDENCY
        assert "both values can be correct" in conflicts[0].resolution_rule
        # Neither claim is poisoned: stamping them CONFLICTING would stop
        # either from ever being used, and both are right.
        assert [c.status for c in updated] == [ClaimStatus.VERIFIED_CURRENT] * 2

    def test_two_populations_are_named_as_the_reason(self):
        from app.domain.conflicts import find_conflicts

        conflicts, _ = find_conflicts(
            [
                C("ielts_min_overall", 6.5, scope=ClaimScope(population="international")),
                C(
                    "ielts_min_overall",
                    6.0,
                    url="https://example.edu/eu",
                    scope=ClaimScope(population="EU/EEA"),
                ),
            ]
        )
        assert conflicts[0].kind is ConflictKind.DIFFERENT_POPULATION
        assert "different populations" in conflicts[0].question_for_admissions

    def test_a_real_contradiction_is_still_a_real_contradiction(self):
        """Same stated scope, two values. Nothing explains it away."""
        from app.domain.conflicts import find_conflicts

        conflicts, updated = find_conflicts(
            [
                C("ielts_min_overall", 6.5, scope=ClaimScope(intake="Fall 2027")),
                C(
                    "ielts_min_overall",
                    7.0,
                    url="https://example.edu/other",
                    scope=ClaimScope(intake="Fall 2027"),
                ),
            ]
        )
        assert conflicts[0].kind is ConflictKind.TRUE_CONFLICT
        assert all(c.status is ClaimStatus.CONFLICTING for c in updated)

    def test_an_unrecorded_scope_is_never_rounded_into_a_difference(self):
        """Unknown must not explain away a conflict: that is the costly error."""
        from app.domain.enums import ClaimStatus, ConflictKind

        conflicts, updated = find_conflicts(
            [
                C("ielts_min_overall", 6.5),
                C("ielts_min_overall", 7.0, url="https://example.edu/other"),
            ]
        )
        assert conflicts[0].kind is ConflictKind.TRUE_CONFLICT
        assert all(c.status is ClaimStatus.CONFLICTING for c in updated)


class TestAGeneralRuleBesideASpecificOne:
    """Plan V2-23, the kind the first pass left out.

    The phase guide: a general rule and a programme-specific rule may both be
    true, so do not label them a conflict automatically.
    """

    def test_a_programme_page_against_a_university_page_is_not_a_contradiction(self):
        conflicts, _ = find_conflicts(
            [
                C("ielts_min_overall", 7.0, specificity="program_intake", url="https://u/prog"),
                C(
                    "ielts_min_overall",
                    6.5,
                    specificity="university_admissions",
                    url="https://u/adm",
                ),
            ]
        )
        assert conflicts[0].kind is ConflictKind.MORE_SPECIFIC_SOURCE
        assert "can both be true" in conflicts[0].resolution_rule
        assert "kept, not discarded" in conflicts[0].resolution_rule

    def test_two_pages_of_the_same_kind_disagreeing_is_still_a_contradiction(self):
        """Specificity explains a difference between levels, never within one."""
        conflicts, _ = find_conflicts(
            [
                C("ielts_min_overall", 7.0, specificity="program_intake", url="https://u/a"),
                C("ielts_min_overall", 6.5, specificity="program_intake", url="https://u/b"),
            ]
        )
        assert conflicts[0].kind is ConflictKind.TRUE_CONFLICT

    def test_a_stated_scope_difference_still_wins_over_specificity(self):
        """Two populations is a better explanation than two levels, and the
        dimension check runs first."""
        conflicts, _ = find_conflicts(
            [
                C(
                    "ielts_min_overall",
                    7.0,
                    specificity="program_intake",
                    url="https://u/prog",
                    scope=ClaimScope(population="international"),
                ),
                C(
                    "ielts_min_overall",
                    6.5,
                    specificity="university_admissions",
                    url="https://u/adm",
                    scope=ClaimScope(population="EU/EEA"),
                ),
            ]
        )
        assert conflicts[0].kind is ConflictKind.DIFFERENT_POPULATION

    def test_the_claims_keep_today_s_status_until_the_owner_decides(self):
        """Deliberate: the guide would have the specific rule stay usable, and
        an existing contract test says otherwise. Naming lands first."""
        _, updated = find_conflicts(
            [
                C("ielts_min_overall", 7.0, specificity="program_intake", url="https://u/prog"),
                C(
                    "ielts_min_overall",
                    6.5,
                    specificity="university_admissions",
                    url="https://u/adm",
                ),
            ]
        )
        assert all(c.status is ClaimStatus.CONFLICTING for c in updated)
