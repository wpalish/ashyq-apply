"""Explicit decision obligations. Only independently proved components close them."""

from app.research.contracts import PublicScope, QuestionGroup, ResearchQuestion

REQUIRED: dict[QuestionGroup, tuple[str, ...]] = {
    QuestionGroup.ENGLISH: (
        "english.options",
        "english.overall",
        "english.bands",
        "english.waiver",
    ),
    QuestionGroup.ACADEMIC: (
        "academic.qualification",
        "academic.subjects",
        "academic.grades",
        "academic.route",
    ),
    QuestionGroup.DEADLINE: ("admission.deadline",),
    QuestionGroup.TUITION: ("tuition.schedule",),
    QuestionGroup.SCHOLARSHIP_EXISTENCE: ("scholarships.offer",),
    QuestionGroup.SCHOLARSHIP_APPLICABILITY: ("scholarships.applicability",),
}


def core_questions(scope: PublicScope) -> tuple[ResearchQuestion, ...]:
    return tuple(
        ResearchQuestion(id=str(group), group=group, scope=scope, required=keys)
        for group, keys in REQUIRED.items()
    )
