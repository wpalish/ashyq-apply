"""Lossless direct claim keys; ambiguous award/document identity stays explicit."""

from typing import Any

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
    return CLAIM_KEYS.get(claim_type, "unmapped." + claim_type), value, programme, degree
