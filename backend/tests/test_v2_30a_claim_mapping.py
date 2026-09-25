"""V2-30A: every certified fact has a claim type that can express it.

The mapping builds a structured key from what the claim names and refuses a
claim that does not name it exactly; nothing is guessed.
"""

from __future__ import annotations

from evaluation.research.identities import IdentityMap
from evaluation.research.mapping import normalize_claim, normalize_subject_claims

_BINDINGS = IdentityMap.model_validate(
    {
        "version": "test",
        "bindings": [
            {
                "kind": "document",
                "source_url": "https://uni.edu/docs",
                "subject": "Full academic transcript",
                "key": "documents.admission.transcript",
                "notes": "test",
            },
            {
                "kind": "award",
                "source_url": "https://uni.edu/award",
                "subject": "Global Award",
                "key": "scholarships.global",
                "notes": "test",
            },
        ],
    }
)


def _key_value(claim_type: str, value: object) -> tuple[str, object]:
    key, mapped, _programme, _degree = normalize_claim(claim_type, {"normalized_value": value})
    return key, mapped


def test_structured_keys_are_built_from_what_the_claim_names():
    assert _key_value(
        "credential_requirement",
        {"credential": "nis_grade12", "field": "minimum_grades", "value": {"all_subjects": "A"}},
    ) == ("country_credential.nis_grade12.minimum_grades", {"all_subjects": "A"})
    assert _key_value("subject_requirement", {"subject": "mathematics", "required": True}) == (
        "subjects.mathematics.required",
        True,
    )
    assert _key_value(
        "other_language_minimum", {"language": "german", "stage": "enrolment", "level": "C1"}
    ) == ("german.enrolment_minimum", "C1")
    assert _key_value("english_evidence_minimum", {"test": "sat", "minimum": 1250}) == (
        "english_evidence.sat.minimum",
        1250,
    )


def test_plain_keys():
    assert _key_value("intake_term", "fall 2027") == ("intake", "fall 2027")
    assert _key_value("program_faculty", "School of Computing") == (
        "programme.faculty",
        "School of Computing",
    )
    assert _key_value("admission_route", "undeclared_then_major_selection")[0] == (
        "programme.admission_route"
    )


def test_a_structured_claim_that_does_not_name_its_fields_is_not_guessed():
    assert _key_value("subject_requirement", {"required": True})[0] == (
        "unmapped.subject_requirement"
    )
    # A name that is not a slug could inject a key segment.
    assert _key_value("english_evidence_minimum", {"test": "sat.minimum.x", "minimum": 1})[0] == (
        "unmapped.english_evidence_minimum"
    )
    assert _key_value("other_language_minimum", "C1")[0] == "unmapped.other_language_minimum"


def test_a_document_form_by_completion_binds_through_the_document_identity():
    raw = {
        "source_url": "https://uni.edu/docs",
        "normalized_value": {
            "document": "Full academic transcript",
            "status": "not_completed",
            "form": "school_course_list",
        },
    }
    assert normalize_subject_claims("document_by_completion", raw, _BINDINGS) == [
        ("documents.admission.transcript.not_completed", "school_course_list", None, None)
    ]
    raw["normalized_value"]["status"] = "maybe"
    assert normalize_subject_claims("document_by_completion", raw, _BINDINGS)[0][0] == (
        "unmapped.document_by_completion"
    )


def test_bond_and_offer_are_award_fields():
    for claim_type, value, field in (
        ("scholarship_bond", {"years": 3}, "bond"),
        ("scholarship_offer_required", True, "applicability.offer"),
    ):
        raw = {"source_url": "https://uni.edu/award", "subject_key": "Global Award"}
        raw["normalized_value"] = value
        assert normalize_subject_claims(claim_type, raw, _BINDINGS) == [
            ("scholarships.global." + field, value, None, None)
        ]
