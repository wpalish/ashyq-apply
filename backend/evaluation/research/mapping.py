"""Lossless direct claim keys; ambiguous award/document identity stays explicit."""

from typing import Any

from .identities import IdentityMap
from .schema import Scope

CLAIM_KEYS = {
    "ielts_min_overall": "ielts.overall",
    "ielts_min_subscore": "ielts.subscores",
    "sat_policy": "sat.policy",
    "sat_min_total": "sat.minimum",
    "admission_deadline": "deadline",
    "country_specific_requirement": "country_credential",
    "tuition": "tuition",
    "mandatory_fees": "mandatory_fees",
    "application_fee": "application_fee",
    # Open/closed is not evidence of the requested intake's identity.
    "intake_open": "intake.open",
    "program_exists": "programme.exists",
}


def evidence_scope(
    raw: dict[str, Any],
    *,
    university: str,
    programme: str | None,
    degree: str | None,
) -> Scope:
    """The scope of the evidence, taken from the page wherever the page spoke.

    Before V2-22 this was built from the *request*: ``intake`` was whatever the
    applicant profile asked for, on every claim of every case, and the same
    went for the academic year. Scoring then compared a label against our own
    question, which is why a scope-match failure never meant a human-confirmed
    wrong fact — the baseline README says so in its own words.

    Now a claim carries what its page stated (``raw["scope"]``). Where the page
    stated a dimension, that is what goes in. Where it was silent, the value is
    ``None``: a gap the scorer can see, never the value we hoped for.

    The request-side fallback survives for one case only — a claim with **no**
    ``scope`` key, i.e. written before V2-22. Frozen captures are full of those
    and re-scoring one must stay exactly reproducible, so the old behaviour is
    kept deliberately, and only there.
    """
    recorded = raw.get("scope")
    if not isinstance(recorded, dict):
        return Scope(
            university=university,
            programme=programme,
            degree=degree,
            intake=raw.get("intake"),
            academic_year=raw.get("academic_year"),
        )
    return Scope(
        university=recorded.get("university") or university,
        programme=recorded.get("programme") or programme,
        degree=recorded.get("degree") or degree,
        intake=recorded.get("intake"),
        academic_year=recorded.get("academic_year"),
        population=recorded.get("population"),
    )


#: Keys the mapping derives from a claim's value rather than from its type:
#: ``programme.language`` comes from the teaching language a programme page
#: states on its ``program_exists`` claim.
DERIVED_KEYS = frozenset({"programme.language"})


def normalize_claim(
    claim_type: str, raw: dict[str, Any]
) -> tuple[str, Any, str | None, str | None]:
    value = raw.get("normalized_value")
    programme = raw.get("program")
    degree = None
    if claim_type == "program_exists" and isinstance(value, dict) and value.get("program"):
        programme = value["program"]
        degree = value.get("degree")
        value = True
    if claim_type == "ielts_min_subscore" and isinstance(value, int | float):
        # "No part less than 6.0" is one floor stated for all four sections;
        # the certified corpus writes the same statement as a map. Spelling
        # the floor out is a change of representation, not an equivalence:
        # it says nothing the page did not say.
        value = {band: float(value) for band in IELTS_BANDS}
    return CLAIM_KEYS.get(claim_type, "unmapped." + claim_type), value, programme, degree


IELTS_BANDS = ("listening", "reading", "speaking", "writing")


AWARD_KEYS = {
    "scholarship_international_eligible": "applicability.international",
    "scholarship_citizenship_restriction": "applicability.nationality",
    "scholarship_program_restriction": "applicability.degree",
    "scholarship_application_mode": "applicability.application_mode",
    "scholarship_amount": "amount",
    "scholarship_deadline": "deadline",
    "scholarship_renewable": "renewable",
    "scholarship_renewal_requirement": "renewal",
    "scholarship_duration_years": "duration_years",
    "scholarship_stackable": "stackable",
    "scholarship_count": "count",
    "scholarship_min_test_score": "minimum_test_score",
    # The corpus files a stated allowance under coverage and a duration given
    # in words under "duration" (NTU Nanyang: S$6,500 a year; "normal
    # programme duration"). Same statements, the corpus's own keys.
    "scholarship_living_allowance": "coverage.living",
    "scholarship_duration": "duration",
}
COVERAGE_KEYS = {"mandatory_fees": "fees", "health_insurance": "insurance"}
DOCUMENT_TYPES = {"required_document", "essay_prompt", "recommendation_requirement"}


def normalize_subject_claims(
    claim_type: str, raw: dict[str, Any], identities: IdentityMap
) -> list[tuple[str, Any, str | None, str | None]]:
    """Split independent fields only after an exact source/subject identity match.

    Preserve values that carry conditions; a yes/no coverage table is not a money
    allowance, a citizenship restriction list is not all-nationality eligibility,
    and a degree verdict is not proof of full-time programme applicability.
    """
    fallback = normalize_claim(claim_type, raw)
    _, value, programme, degree = fallback
    if isinstance(value, str) and value.upper() == "UNKNOWN":
        value = None
        fallback = (fallback[0], value, programme, degree)
    source = raw.get("source_url", "")
    if claim_type == "program_exists":
        # The page's stated teaching language rides on the existence claim; the
        # owner settled one key for it on 2026-09-23. Only a language the page
        # stated is emitted, capitalised as the corpus writes it ("English").
        stated = raw.get("normalized_value")
        language = stated.get("language") if isinstance(stated, dict) else None
        if isinstance(language, str) and language.strip():
            return [fallback, ("programme.language", language.strip().title(), programme, degree)]
        return [fallback]
    if claim_type.startswith("scholarship_"):
        subject = raw.get("subject_key")
        # Existence itself names the award, but two disagreeing identities cannot bind.
        if claim_type == "scholarship_exists":
            if subject is not None and subject != value:
                return [fallback]
            subject = value
        prefix = identities.resolve("award", source, subject)
        if prefix is None:
            return [fallback]
        if claim_type == "scholarship_exists":
            return [(prefix + ".exists", True, programme, degree)]
        if claim_type == "scholarship_coverage":
            if not isinstance(value, dict) or not value:
                return [fallback]
            # Unknown categories are retained, never silently dropped or reinterpreted.
            known = {
                "tuition",
                "mandatory_fees",
                "housing",
                "meals",
                "health_insurance",
                "books",
                "travel",
                "visa",
                "personal",
            }
            if any(
                k not in known or v not in {"yes", "no", "partial", "unknown"}
                for k, v in value.items()
                if isinstance(v, str)
            ) or any(not isinstance(v, str) for v in value.values()):
                return [fallback]
            return [
                (
                    prefix + ".coverage." + COVERAGE_KEYS.get(k, k),
                    None if v == "unknown" else v,
                    programme,
                    degree,
                )
                for k, v in sorted(value.items())
            ]
        if claim_type in AWARD_KEYS:
            if value == "unknown" or (
                claim_type == "scholarship_program_restriction"
                and isinstance(value, dict)
                and value.get("applies") == "unknown"
            ):
                value = None
            return [(prefix + "." + AWARD_KEYS[claim_type], value, programme, degree)]
    elif claim_type in DOCUMENT_TYPES:
        if claim_type != "essay_prompt" and not isinstance(value, str):
            return [fallback]
        subject = value.get("document") if isinstance(value, dict) else value
        prefix = identities.resolve("document", source, subject)
        if prefix is None:
            return [fallback]
        if claim_type == "essay_prompt":
            if not isinstance(value, dict) or set(value) != {"document", "word_limit"}:
                return [fallback]
            limit = value["word_limit"]
            if type(limit) is not int or limit <= 0:
                return [fallback]
            return [(prefix + ".maximum_words", limit, programme, degree)]
        return [(prefix + ".required", True, programme, degree)]
    return [fallback]
