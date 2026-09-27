"""Locate only failure stages justified by the frozen observations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.adapters.discovery.live_discovery import canonical_url

from .packet import digest


@dataclass(frozen=True)
class FailureRecord:
    case_id: str
    legacy_stage: str
    legacy_gold_position: int | None
    legacy_error: str | None
    probe_gold_position: int | None
    probe_candidate_count: int | None
    probe_top_identity: str | None
    known_label_count: int
    note: str


def diagnose(
    dataset: dict[str, Any], capture: dict[str, Any], probe: dict[str, Any]
) -> dict[str, Any]:
    """Compare measured stages; do not infer that a ranked URL was fetched."""
    observations = {row["case_id"]: row for row in capture["observations"]}
    probes = {row["case_id"]: row for row in probe["cases"]}
    records: list[FailureRecord] = []
    for case in dataset["cases"]:
        case_id = case["id"]
        observation = observations.get(case_id)
        if observation is None:
            raise ValueError(f"No baseline observation for {case_id}")
        candidate = probes.get(case_id)
        truth = {canonical_url(url) for url in case["programme_urls"]}
        ranked = observation.get("ranked_urls")
        returned = {canonical_url(url) for url in observation.get("programme_urls", [])}
        if not truth:
            position = None
            stage = "programme_truth_unadjudicable"
        elif ranked is None:
            position = None
            stage = "legacy_queue_unmeasured"
        else:
            positions = [
                index for index, url in enumerate(ranked, start=1) if canonical_url(url) in truth
            ]
            position = min(positions) if positions else None
            if not positions:
                stage = (
                    "legacy_gold_absent_with_failure"
                    if observation.get("error")
                    else "legacy_gold_absent"
                )
            elif not truth.intersection(returned):
                stage = "legacy_confirmation_or_fetch_unresolved"
            elif not observation.get("predictions"):
                stage = "legacy_claims_not_emitted"
            else:
                stage = "legacy_claims_need_adjudication"
        records.append(
            FailureRecord(
                case_id=case_id,
                legacy_stage=stage,
                legacy_gold_position=position,
                legacy_error=observation.get("error"),
                probe_gold_position=candidate.get("correct_position") if candidate else None,
                probe_candidate_count=candidate.get("candidates") if candidate else None,
                probe_top_identity=candidate.get("top_identity") if candidate else None,
                known_label_count=sum(label["status"] == "known" for label in case["labels"]),
                note=(
                    "Probe rank is candidate order only; it does not prove a fetch, extraction, "
                    "or current claim support. Baseline and probe are different dated runs."
                ),
            )
        )
    return {
        "schema_version": "1",
        "dataset_sha256": digest(dataset),
        "capture_sha256": digest(capture),
        "probe_sha256": digest(probe),
        "dataset_version": dataset["version"],
        "capture_pipeline_sha": capture["pipeline_sha"],
        "probe_at": probe["probed_at"],
        "records": [asdict(record) for record in records],
    }
