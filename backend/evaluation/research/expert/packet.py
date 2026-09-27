"""Export a case without copying answers from the certified corpus."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

REQUEST_FIELDS = (
    "university",
    "programme",
    "degree",
    "field",
    "intake",
    "population",
    "qualification",
    "academic_year",
)


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_packet(
    dataset: dict[str, Any], capture: dict[str, Any], case_ids: Sequence[str]
) -> dict[str, Any]:
    """Copy an explicit allowlist; never serialize a source case wholesale."""
    wanted = list(case_ids)
    if not wanted or len(wanted) != len(set(wanted)):
        raise ValueError("Choose at least one unique case ID")
    cases = {case["id"]: case for case in dataset["cases"]}
    observations = {item["case_id"]: item for item in capture["observations"]}
    if len(observations) != len(capture["observations"]):
        raise ValueError("Duplicate baseline observation")
    missing = set(wanted) - (cases.keys() & observations.keys())
    if missing:
        raise ValueError(f"Missing case or observation: {sorted(missing)}")
    output = []
    for case_id in wanted:
        case, observation = cases[case_id], observations[case_id]
        output.append(
            {
                "case_id": case_id,
                "university": case["university"],
                "domain": case["domain"],
                "request": {key: case["request"].get(key) for key in REQUEST_FIELDS},
                "baseline": {
                    "ranked_urls": observation.get("ranked_urls"),
                    "programme_urls": observation.get("programme_urls", []),
                    "prediction_count": len(observation.get("predictions", [])),
                    "error": observation.get("error"),
                    "telemetry": {
                        key: observation.get("telemetry", {}).get(key)
                        for key in (
                            "http_fetches",
                            "pdf_fetches",
                            "browser_fetches",
                            "latency_seconds",
                        )
                    },
                },
            }
        )
    return {
        "schema_version": "1",
        "dataset_version": dataset["version"],
        "dataset_sha256": digest(dataset),
        "capture_sha256": digest(capture),
        "baseline_pipeline_sha": capture["pipeline_sha"],
        "baseline_captured_at": capture["captured_at"],
        "baseline_budget": {
            "max_fetcher_calls": capture["config"]["max_fetcher_calls_per_case"],
            "max_elapsed_ms": capture["config"]["seconds_per_case"] * 1000,
            "browser_enabled": capture["config"]["browser_enabled"],
        },
        "cases": output,
    }
