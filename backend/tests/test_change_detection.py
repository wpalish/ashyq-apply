"""V2-24a — telling a real change from a re-render.

The pipeline can already tell whether a page's bytes changed. These tests are
about the question after it: did anything a user could act on change.
"""

from __future__ import annotations

from app.domain.change_detection import (
    ChangeKind,
    classify_changes,
    is_material,
    summarise,
)
from tests.conftest import make_claim as C


class TestWhatCounts:
    def test_a_re_render_with_identical_values_is_not_a_change(self):
        before = [C("ielts_min_overall", 6.5), C("admission_deadline", "2027-01-15")]
        after = [C("ielts_min_overall", 6.5), C("admission_deadline", "2027-01-15")]
        changes = classify_changes(before, after)
        assert {c.kind for c in changes} == {ChangeKind.UNCHANGED}
        assert is_material(changes) is False
        assert "no material change" in summarise(changes)

    def test_a_changed_minimum_is_material_and_says_both_values(self):
        changes = classify_changes([C("ielts_min_overall", 6.5)], [C("ielts_min_overall", 7.0)])
        assert [c.kind for c in changes] == [ChangeKind.VALUE_CHANGED]
        assert is_material(changes)
        assert changes[0].describe() == "ielts_min_overall: 6.5 -> 7.0"

    def test_a_claim_the_page_no_longer_states_is_a_removal(self):
        """Never "the value became null": a claim that disappeared is a finding."""
        changes = classify_changes([C("ielts_min_overall", 6.5)], [])
        assert [c.kind for c in changes] == [ChangeKind.REMOVED]
        assert "no longer stated" in changes[0].describe()

    def test_a_claim_the_page_now_states_is_an_addition(self):
        changes = classify_changes([], [C("sat_min_total", 1400)])
        assert [c.kind for c in changes] == [ChangeKind.ADDED]
        assert "now states" in changes[0].describe()

    def test_two_scholarships_are_two_statements_not_one(self):
        """The subject key is what keeps one award's amount from reading as a
        change to another's."""
        before = [
            C("scholarship_amount", 5000, subject_key="Merit"),
            C("scholarship_amount", 9000, subject_key="Excellence"),
        ]
        after = [
            C("scholarship_amount", 5000, subject_key="Merit"),
            C("scholarship_amount", 12000, subject_key="Excellence"),
        ]
        changes = {c.subject_key: c.kind for c in classify_changes(before, after)}
        assert changes == {"Merit": ChangeKind.UNCHANGED, "Excellence": ChangeKind.VALUE_CHANGED}


class TestWhatDoesNotCount:
    def test_a_reworded_sentence_around_an_unchanged_number_is_not_a_change(self):
        before = [C("ielts_min_overall", 6.5)]
        after = [C("ielts_min_overall", 6.5)]
        after[0] = after[0].model_copy(
            update={"original_text_excerpt": "We require an overall IELTS band of 6.5."}
        )
        assert is_material(classify_changes(before, after)) is False

    def test_the_same_number_written_differently_is_the_same_number(self):
        assert (
            is_material(classify_changes([C("sat_min_total", 1400.0)], [C("sat_min_total", 1400)]))
            is False
        )

    def test_a_list_in_another_order_is_the_same_list(self):
        before = [C("ielts_accepted_types", ["academic", "ukvi"])]
        after = [C("ielts_accepted_types", ["ukvi", "academic"])]
        assert is_material(classify_changes(before, after)) is False

    def test_re_reading_a_page_is_not_a_change_to_what_it_says(self):
        from datetime import UTC, datetime

        before = [C("ielts_min_overall", 6.5, accessed_at=datetime(2026, 1, 1, tzinfo=UTC))]
        after = [C("ielts_min_overall", 6.5, accessed_at=datetime(2026, 9, 21, tzinfo=UTC))]
        assert is_material(classify_changes(before, after)) is False


class TestTheLogLine:
    def test_it_names_every_material_change_and_counts_the_rest(self):
        before = [C("ielts_min_overall", 6.5), C("min_gpa", 3.0), C("sat_min_total", 1400)]
        after = [C("ielts_min_overall", 7.0), C("min_gpa", 3.0)]
        line = summarise(classify_changes(before, after))
        assert "unchanged=1" in line and "value_changed=1" in line and "removed=1" in line
        assert "ielts_min_overall: 6.5 -> 7.0" in line
        assert "sat_min_total: no longer stated" in line

    def test_a_structured_value_compares_by_content_not_by_spelling(self):
        """A dict claim (per-band minimums) written in another key order is
        the same claim."""
        before = [C("ielts_min_subscore", {"writing": 6.5, "reading": 6.0})]
        after = [C("ielts_min_subscore", {"reading": 6.0, "writing": 6.5})]
        assert is_material(classify_changes(before, after)) is False

    def test_an_unchanged_claim_describes_itself_as_unchanged(self):
        changes = classify_changes([C("ielts_min_overall", 6.5)], [C("ielts_min_overall", 6.5)])
        assert changes[0].describe() == "ielts_min_overall: unchanged"


def test_a_persisted_payload_can_be_compared_without_being_revalidated() -> None:
    """The bug this shape exists to prevent: reconstructing a full Claim from
    an older payload raised, and inside a re-extract's one transaction that
    took the supersession down with it."""
    from app.domain.change_detection import Reading

    older = Reading.from_payload(
        {"claim_type": "ielts_min_overall", "normalized_value": 6.5, "legacy_field": "gone"}
    )
    assert older.subject_key is None
    changes = classify_changes([older], [C("ielts_min_overall", 7.0)])
    assert [c.kind for c in changes] == [ChangeKind.VALUE_CHANGED]
