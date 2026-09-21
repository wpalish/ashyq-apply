"""Dataset migration must preserve conditions and provenance, not invent answers."""

import hashlib
import json
from pathlib import Path

from evaluation.research.identities import IdentityMap
from evaluation.research.map_claims import map_predictions
from evaluation.research.metrics import score
from evaluation.research.schema import Capture, Dataset, Observation

ROOT = Path(__file__).resolve().parents[1] / "evaluation/research/data"


def test_document_projection_reconstructs_every_old_fact_without_losing_conditions():
    before = Dataset.model_validate_json(
        (ROOT / "ground_truth.draft2.json").read_text(encoding="utf-8")
    )
    after = Dataset.model_validate_json(
        (ROOT / "ground_truth.draft3.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((ROOT / "document_projection.draft3.json").read_text(encoding="utf-8"))
    for name, dataset in (("source", before), ("target", after)):
        assert manifest[name + "_version"] == dataset.version
        assert (
            manifest[name + "_sha256"]
            == hashlib.sha256(dataset.model_dump_json().encode()).hexdigest()
        )
    changes = {(r["case_id"], r["source_key"]): r for r in manifest["changes"]}
    assert len(changes) == len(manifest["changes"])
    assert [c.id for c in before.cases] == [c.id for c in after.cases]
    for old, new in zip(before.cases, after.cases, strict=True):
        assert old.model_dump(exclude={"labels", "dataset_version", "review"}) == new.model_dump(
            exclude={"labels", "dataset_version", "review"}
        )
        assert old.review.model_dump(exclude={"notes"}) == new.review.model_dump(exclude={"notes"})
        assert new.review.status == "draft" and new.review.reviewer is None
        remaining = {label.key: label for label in new.labels}
        for label in old.labels:
            change = changes.pop((old.id, label.key), None)
            if change is None:
                assert remaining.pop(label.key).model_dump_json() == label.model_dump_json()
                continue
            assert label.key.startswith("documents.") and label.status == "known"
            fields = {}
            for field, key in change["targets"].items():
                projected = remaining.pop(key)
                assert key == label.key + "." + field
                assert projected.model_dump(exclude={"key", "value"}) == label.model_dump(
                    exclude={"key", "value"}
                )
                fields[field] = projected.value
            if change["mode"] == "boolean_required":
                assert type(label.value) is bool
                assert json.dumps(fields, sort_keys=True) == json.dumps(
                    {"required": label.value}, sort_keys=True
                )
            else:
                assert change["mode"] == "object_fields"
                assert json.dumps(fields, sort_keys=True) == json.dumps(label.value, sort_keys=True)
        assert not remaining  # No untraced additions, including guessed required=True.
    assert not changes


def test_atomic_document_fields_join_mapper_without_inventing_evidence_support():
    dataset = Dataset.model_validate_json(
        (ROOT / "ground_truth.draft3.json").read_text(encoding="utf-8")
    )
    ntu = next(c for c in dataset.cases if c.id == "ntu")
    dataset = dataset.model_copy(update={"cases": [ntu]})
    identities = IdentityMap.model_validate(
        {
            "version": "synthetic",
            "bindings": [
                {
                    "kind": "document",
                    "source_url": "https://example.edu/award",
                    "subject": "Synthetic essay",
                    "key": "documents.scholarship.nanyang_global.essay",
                    "notes": "Synthetic mapping agreement test, not a real identity binding",
                }
            ],
        }
    )
    predictions = map_predictions(
        [
            {
                "claim_type": "required_document",
                "normalized_value": "Synthetic essay",
                "source_url": "https://example.edu/award",
            },
            {
                "claim_type": "essay_prompt",
                "normalized_value": {"document": "Synthetic essay", "word_limit": 251},
                "source_url": "https://example.edu/award",
            },
        ],
        identities,
        ntu.university,
    )
    capture = Capture(
        pipeline_sha="synthetic",
        captured_at="synthetic",
        mode="synthetic",
        config={},
        observations=[Observation(case_id="ntu", predictions=predictions)],
    )
    metrics = score(dataset, capture, allow_drafts=True)["metrics"]
    assert metrics["claim_adjudication_rate"]["numerator"] == 2
    assert metrics["critical_field_coverage"]["numerator"] == 2
    # A field-name join is not proof: no supporting evidence and the wrong word limit.
    assert metrics["claim_precision"]["denominator"] == 2
    assert metrics["claim_precision"]["numerator"] == 0
