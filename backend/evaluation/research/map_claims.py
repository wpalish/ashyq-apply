"""Offline raw-claim mapping; no imports of the production app or expected labels."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import JsonValue

from .identities import IdentityMap
from .mapping import evidence_scope, normalize_subject_claims
from .schema import Capture, Evidence, Prediction


def map_predictions(
    claims: list[dict[str, Any]], identities: IdentityMap, university: str
) -> list[Prediction]:
    predictions = []
    for raw in claims:
        claim_type = raw.get("claim_type")
        if not isinstance(claim_type, str) or not claim_type:
            raise ValueError("Each raw claim requires claim_type")
        for key, value, programme, degree in normalize_subject_claims(claim_type, raw, identities):
            evidence = None
            excerpt = raw.get("original_text_excerpt")
            source = raw.get("source_url", "")
            if excerpt and source.startswith(("https://", "http://")):
                accessed = raw.get("accessed_at")
                if not isinstance(accessed, str):
                    raise ValueError("Evidence requires original accessed_at, not mapping time")
                evidence = Evidence(
                    url=source,
                    excerpt=excerpt,
                    scope=evidence_scope(
                        raw, university=university, programme=programme, degree=degree
                    ),
                    accessed_on=accessed[:10],
                    source_type="official" if raw.get("official_domain") is True else "unknown",
                    # The production claim contract truncates at 600 characters.
                    # At the cap we cannot establish that the quote is complete.
                    excerpt_truncated=len(excerpt) >= 600 or raw.get("excerpt_truncated") is True,
                )
            # Production confidence/status are NOT human evidence adjudication.
            predictions.append(Prediction(key=key, value=value, evidence=evidence))
    return predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True, help="Saved .raw.json with claims array")
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument(
        "--university", required=True, help="Observed institution name, not a label"
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--capture", type=Path, help="Optionally produce a new replay capture")
    parser.add_argument("--case-id", help="Observation to replace when --capture is supplied")
    args = parser.parse_args()
    if bool(args.capture) != bool(args.case_id):
        parser.error("--capture and --case-id must be supplied together")
    inputs = {args.raw.resolve(), args.bindings.resolve()}
    if args.capture:
        inputs.add(args.capture.resolve())
    if args.out.resolve() in inputs:
        parser.error("Output must not overwrite either input")
    raw_bytes = args.raw.read_bytes()
    binding_bytes = args.bindings.read_bytes()
    identities = IdentityMap.model_validate_json(binding_bytes)
    raw = json.loads(raw_bytes)
    if not isinstance(raw, dict) or not isinstance(raw.get("claims"), list):
        parser.error("Raw input must contain a claims array")
    if any(not isinstance(c, dict) for c in raw["claims"]):
        parser.error("Each raw claim must be an object")
    predictions = map_predictions(raw["claims"], identities, args.university)
    result: dict[str, JsonValue] = {
        "mapping_version": "1",
        "identity_version": identities.version,
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "bindings_sha256": hashlib.sha256(binding_bytes).hexdigest(),
        "mapper_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
            + Path(__file__).with_name("mapping.py").read_bytes()
            + Path(__file__).with_name("identities.py").read_bytes()
        ).hexdigest(),
        "raw_claim_count": len(raw["claims"]),
        "prediction_count": len(predictions),
        "unmapped_prediction_count": sum(p.key.startswith("unmapped.") for p in predictions),
        "predictions": [p.model_dump(mode="json") for p in predictions],
    }
    if args.capture:
        capture_bytes = args.capture.read_bytes()
        capture = Capture.model_validate_json(capture_bytes)
        cases = [o for o in capture.observations if o.case_id == args.case_id]
        if len(cases) != 1:
            parser.error("Case must identify exactly one existing observation")
        # A canary sidecar has an observed institution; reject a wrong-file join.
        institutions = raw.get("canary", {}).get("institutions", [])
        if not institutions or any(r.get("institution") != args.university for r in institutions):
            parser.error("Replay requires canary institution matching --university")
        observed_names = {p.evidence.scope.university for p in cases[0].predictions if p.evidence}
        if observed_names and observed_names != {args.university}:
            parser.error("University differs from the existing observation")
        cases[0].predictions = predictions
        capture.mode = "replay"
        capture.config["claim_mapping"] = {k: v for k, v in result.items() if k != "predictions"}
        capture.config["claim_mapping_case"] = args.case_id
        capture.config["parent_capture_sha256"] = hashlib.sha256(capture_bytes).hexdigest()
        result = capture.model_dump(mode="json")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
