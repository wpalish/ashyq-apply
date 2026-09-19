"""Adversarial benchmark checks: abstention and leakage must not look successful."""

import ast
from pathlib import Path

import pytest

from evaluation.research.metrics import score
from evaluation.research.schema import Capture, Dataset


def inputs():
    scope = {"university": "Example", "programme": "CS", "degree": "bachelor"}
    evidence = {
        "url": "https://example.edu/cs",
        "excerpt": "Bachelor CS IELTS 6.5",
        "scope": scope,
        "accessed_on": "2026-09-20",
        "source_type": "official",
    }
    dataset = Dataset.model_validate(
        {
            "version": "test",
            "split": "development",
            "cases": [
                {
                    "id": "example",
                    "dataset_version": "test",
                    "university": "Example",
                    "domain": "example.edu",
                    "country": "Test",
                    "site_types": ["synthetic"],
                    "request": scope,
                    "programme_status": "known",
                    "programme_urls": [evidence["url"]],
                    "programme_evidence": [evidence],
                    "labels": [
                        {
                            "key": "ielts.overall",
                            "status": "known",
                            "value": 6.5,
                            "evidence": [evidence],
                        }
                    ],
                    "review": {"prepared_by": "test", "notes": "Synthetic; not human verified"},
                }
            ],
        }
    )
    capture = Capture(
        pipeline_sha="test", captured_at="test", mode="synthetic", config={}, observations=[]
    )
    return dataset, capture, evidence


def test_unknown_is_zero_coverage_and_recall_not_perfect_precision():
    dataset, capture, _ = inputs()
    result = score(dataset, capture, allow_drafts=True)
    assert result["metrics"]["critical_field_coverage"]["value"] == 0
    assert result["metrics"]["claim_recall"]["value"] == 0
    assert result["metrics"]["claim_precision"]["value"] is None
    assert result["metrics"]["programme_page_recall"]["value"] == 0


def test_drafts_cannot_be_reported_as_human_verified():
    dataset, capture, _ = inputs()
    with pytest.raises(ValueError, match="human"):
        score(dataset, capture)


def test_wrong_scope_and_duplicate_answers_do_not_raise_recall():
    dataset, capture, evidence = inputs()
    evidence["scope"]["degree"] = "master"
    capture = capture.model_copy(update={"observations": []})
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "programme_urls": ["https://example.edu/"],
            "predictions": [
                {"key": "ielts.overall", "value": 6.5, "evidence": evidence, "supported": True}
            ]
            * 2,
        }
    ]
    result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
    assert result["metrics"]["wrong_scope_claim_rate"]["value"] == 1
    assert result["metrics"]["claim_recall"]["value"] == 0
    assert result["metrics"]["programme_page_precision"]["value"] == 0


def test_production_does_not_import_or_read_evaluation_answers():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "app").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not n.name.startswith(("evaluation", "tests")) for n in node.names), path
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("evaluation", "tests")), path
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert "evaluation/research" not in node.value.replace("\\", "/"), path
                assert "ground_truth.json" not in node.value, path
    assert "evaluation/" in (root / ".dockerignore").read_text()
    assert "backend/evaluation/" in (root.parent / ".dockerignore").read_text()


def test_correct_supported_answer_has_independent_precision_and_coverage():
    dataset, capture, evidence = inputs()
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "programme_urls": [evidence["url"]] * 2,
            "ranked_urls": ["https://example.edu/"] * 8 + [evidence["url"]],
            "predictions": [{"key": "ielts.overall", "value": 6.5, "evidence": evidence}] * 2,
        }
    ]
    result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
    for name in (
        "claim_precision",
        "claim_recall",
        "programme_page_precision",
        "critical_field_coverage",
    ):
        assert result["metrics"][name]["value"] == 1
    assert result["metrics"]["claim_precision"]["denominator"] == 1
    assert result["metrics"]["recall_at_5"]["value"] == 1


def test_wrong_value_is_not_made_correct_by_a_valid_excerpt():
    dataset, capture, evidence = inputs()
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "predictions": [{"key": "ielts.overall", "value": 9, "evidence": evidence}],
        }
    ]
    result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
    assert result["metrics"]["claim_precision"]["value"] == 0
    assert result["metrics"]["unsupported_claim_rate"]["value"] == 1
    assert result["metrics"]["critical_field_coverage"]["value"] == 1


def test_unlabelled_predictions_remain_unadjudicated():
    dataset, capture, evidence = inputs()
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "predictions": [{"key": "unknown-key", "value": 9, "evidence": evidence}],
        }
    ]
    result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
    assert result["metrics"]["claim_precision"]["value"] is None
    assert result["metrics"]["claim_adjudication_rate"]["value"] == 0
    assert result["metrics"]["unsupported_claim_rate"]["value"] is None


@pytest.mark.parametrize("case_ids", [["example", "example"], ["foreign"]])
def test_capture_rejects_duplicate_and_foreign_case_ids(case_ids):
    dataset, capture, _ = inputs()
    raw = capture.model_dump()
    raw["observations"] = [{"case_id": value} for value in case_ids]
    with pytest.raises(ValueError, match="case IDs"):
        score(dataset, Capture.model_validate(raw), allow_drafts=True)


def test_url_identity_preserves_query_and_path_case():
    from evaluation.research.metrics import canonical_url

    assert canonical_url("https://example.edu/CS?id=1") != canonical_url(
        "https://example.edu/cs?id=1"
    )
    assert canonical_url("https://example.edu/cs?id=1") != canonical_url(
        "https://example.edu/cs?id=2"
    )


def test_known_label_requires_evidence_and_human_review_requires_identity():
    from pydantic import ValidationError

    from evaluation.research.schema import Label, Review

    with pytest.raises(ValidationError):
        Label(key="tuition", status="known", value=100)
    with pytest.raises(ValidationError):
        Review(status="human_verified", prepared_by="agent", notes="not reviewed")


def test_offline_cli_is_deterministic_without_sockets(tmp_path, monkeypatch):
    import socket
    import sys

    from evaluation.research.__main__ import main

    dataset, capture, _ = inputs()

    def no_network(*args, **kwargs):
        raise AssertionError("offline benchmark attempted network")

    monkeypatch.setattr(socket, "socket", no_network)
    data = tmp_path / "data.json"
    observations = tmp_path / "capture.json"
    out = tmp_path / "metrics.json"
    data.write_text(dataset.model_dump_json(), encoding="utf-8")
    observations.write_text(capture.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--dataset",
            str(data),
            "--capture",
            str(observations),
            "--out",
            str(out),
            "--allow-drafts",
        ],
    )
    main()
    first = out.read_bytes()
    main()
    assert out.read_bytes() == first


def test_live_budget_limits_and_explicit_opt_in(monkeypatch):
    import sys

    from evaluation.research.live import main

    monkeypatch.setattr(sys, "argv", ["live", "--out", "unused"])
    with pytest.raises(SystemExit):
        main()
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--out", "unused", "--max-pages", "1000"])
    with pytest.raises(SystemExit):
        main()


def test_draft_dataset_has_ten_cases_without_fabricated_human_signoff():
    root = Path(__file__).resolve().parents[1]
    dataset = Dataset.model_validate_json(
        (root / "evaluation/research/data/ground_truth.json").read_text(encoding="utf-8")
    )
    assert len(dataset.cases) == 10
    assert all(c.review.status == "draft" and c.review.reviewer is None for c in dataset.cases)
