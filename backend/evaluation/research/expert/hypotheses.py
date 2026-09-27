"""Validate candidate rules without promoting retrospective observations."""

from __future__ import annotations

from typing import Any

STATUSES = {"observed", "candidate", "tested", "rejected", "promoted"}
REQUIRED = {
    "id",
    "status",
    "case_ids",
    "observation",
    "proposed_rule",
    "integration_seam",
    "counterexample",
    "falsification",
    "evidence_artifacts",
    "policy_guard",
    "validation_artifact",
}


def validate_hypotheses(registry: dict[str, Any], diagnosis: dict[str, Any]) -> None:
    if registry.get("schema_version") != "1":
        raise ValueError("Unknown registry schema")
    cases = {record["case_id"] for record in diagnosis["records"]}
    seen: set[str] = set()
    for item in registry.get("hypotheses", []):
        if set(item) != REQUIRED:
            raise ValueError("Hypothesis fields must match the documented contract")
        if not item["id"] or item["id"] in seen:
            raise ValueError("Hypothesis IDs must be unique")
        seen.add(item["id"])
        if item["status"] not in STATUSES:
            raise ValueError("Unknown hypothesis status")
        if not item["case_ids"] or set(item["case_ids"]) - cases:
            raise ValueError("Hypothesis cites unknown or no cases")
        for field in REQUIRED - {"id", "status", "case_ids", "validation_artifact"}:
            if not item[field]:
                raise ValueError(f"Missing hypothesis {field}")
        if item["status"] in {"tested", "rejected", "promoted"} and not item["validation_artifact"]:
            raise ValueError("A test decision requires a validation artifact")
