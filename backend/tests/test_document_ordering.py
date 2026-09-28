"""Phase 3 §9: a document may depend on another action.

`depends_on` has been populated since the offer-letter step, and the ordered
plan ignored it: it sorted by lead time alone, so it could tell the applicant
to notarize a translation before getting the translation. A numbered list is
an instruction.
"""

from __future__ import annotations

from app.adapters.documents.web_documents import _order_steps
from app.domain.enums import DocumentOwner, DocumentPurpose
from app.schemas.result import DocumentItem


def _doc(
    name: str, *, lead: int | None = None, depends_on: list[str] | None = None
) -> DocumentItem:
    return DocumentItem(
        name=name,
        purpose=DocumentPurpose.ADMISSION,
        owner=DocumentOwner.APPLICANT,
        lead_time_days=lead,
        depends_on=depends_on or [],
    )


def _position(steps: list[str], name: str) -> int:
    return next(i for i, s in enumerate(steps) if name in s)


class TestAPrerequisiteComesFirst:
    def test_a_dependency_beats_a_longer_lead_time(self):
        """The failure this step exists for: lead time used to decide alone."""
        steps = _order_steps(
            [
                _doc("Notarized translation", lead=30, depends_on=["Certified translation"]),
                _doc("Certified translation", lead=5),
            ]
        )
        assert _position(steps, "Certified translation") < _position(steps, "Notarized translation")

    def test_the_step_says_what_it_waits_for(self):
        steps = _order_steps(
            [
                _doc("Scholarship application", depends_on=["Offer letter"]),
                _doc("Offer letter"),
            ]
        )
        assert any("after Offer letter" in s for s in steps)

    def test_a_chain_is_ordered_end_to_end(self):
        steps = _order_steps(
            [
                _doc("Final review", depends_on=["Credential evaluation"]),
                _doc("Credential evaluation", depends_on=["Certified translation"]),
                _doc("Certified translation"),
            ]
        )
        assert (
            _position(steps, "Certified translation")
            < _position(steps, "Credential evaluation")
            < _position(steps, "Final review")
        )


class TestNothingIsLost:
    def test_lead_time_still_decides_when_nothing_depends_on_anything(self):
        """Most of the demo is this case, and its order must not change."""
        steps = _order_steps([_doc("Transcript", lead=5), _doc("Diploma", lead=21)])
        assert _position(steps, "Diploma") < _position(steps, "Transcript")

    def test_a_dependency_on_something_not_on_the_list_is_said_but_orders_nothing(self):
        """§9's own example: an offer letter is a milestone, not a list item.

        It cannot be ordered against — there is no step for it — and hiding it
        would leave the applicant not knowing to wait.
        """
        steps = _order_steps(
            [
                _doc("Scholarship form", depends_on=["admission offer letter"]),
                _doc("Transcript", lead=30),
            ]
        )
        assert len(steps) == 2
        assert any("after admission offer letter" in s for s in steps)
        # Lead time still decides between them: nothing here is orderable.
        assert _position(steps, "Transcript") < _position(steps, "Scholarship form")

    def test_a_cycle_keeps_every_step(self):
        steps = _order_steps(
            [
                _doc("A", depends_on=["B"]),
                _doc("B", depends_on=["A"]),
                _doc("C", lead=10),
            ]
        )
        assert len(steps) == 3
        # C can be ordered honestly; A and B cannot, so they come last.
        assert _position(steps, "C") < _position(steps, ": A")
        assert _position(steps, "C") < _position(steps, ": B")

    def test_a_document_that_depends_on_itself_does_not_hang(self):
        steps = _order_steps([_doc("A", depends_on=["A"])])
        assert len(steps) == 1
