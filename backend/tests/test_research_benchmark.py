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


def test_claim_mapping_preserves_programme_scope_and_does_not_guess_award_identity():
    from evaluation.research.mapping import normalize_claim

    assert normalize_claim("admission_deadline", {"normalized_value": "2027-01-15"})[:2] == (
        "deadline",
        "2027-01-15",
    )
    assert normalize_claim(
        "program_exists",
        {"normalized_value": {"program": "Unrelated engineering", "degree": "master"}},
    ) == ("programme.exists", True, "Unrelated engineering", "master")
    assert normalize_claim("scholarship_exists", {"normalized_value": "Tuition Grant"})[:2] == (
        "unmapped.scholarship_exists",
        "Tuition Grant",
    )


def test_explicit_rejection_overrides_automatic_excerpt_match():
    dataset, capture, evidence = inputs()
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "predictions": [
                {"key": "ielts.overall", "value": 6.5, "evidence": evidence, "supported": False}
            ],
        }
    ]
    result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
    assert result["metrics"]["claim_precision"]["value"] == 0
    assert result["metrics"]["unsupported_claim_rate"]["value"] == 1


def test_boolean_is_not_equal_to_numeric_one_in_json_claims():
    dataset, capture, evidence = inputs()
    data = dataset.model_dump()
    data["cases"][0]["labels"][0]["value"] = True
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "predictions": [
                {"key": "ielts.overall", "value": 1, "evidence": evidence, "supported": True}
            ],
        }
    ]
    result = score(Dataset.model_validate(data), Capture.model_validate(raw), allow_drafts=True)
    assert result["metrics"]["claim_precision"]["value"] == 0


def test_published_short_excerpt_does_not_create_automatic_support():
    dataset, capture, evidence = inputs()
    evidence["excerpt_truncated"] = True
    raw = capture.model_dump()
    raw["observations"] = [
        {
            "case_id": "example",
            "predictions": [{"key": "ielts.overall", "value": 6.5, "evidence": evidence}],
        }
    ]
    result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
    assert result["metrics"]["claim_precision"]["value"] == 0
    assert result["metrics"]["support_adjudication_rate"]["value"] == 0


def test_ground_truth_rejects_secondary_sources_and_unexplained_na():
    from pydantic import ValidationError

    from evaluation.research.schema import Label

    _, _, evidence = inputs()
    evidence["source_type"] = "aggregator"
    with pytest.raises(ValidationError, match="primary official"):
        Label(key="ielts.overall", status="known", value=6.5, evidence=[evidence])
    with pytest.raises(ValidationError, match="reason"):
        Label(key="sat.minimum", status="not_applicable")


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


@pytest.mark.parametrize(
    "suffix", ["", ".draft2", ".draft3", ".draft4", ".draft5", ".draft6", ".draft7"]
)
def test_draft_dataset_has_ten_cases_without_fabricated_human_signoff(suffix):
    root = Path(__file__).resolve().parents[1]
    dataset = Dataset.model_validate_json(
        (root / f"evaluation/research/data/ground_truth{suffix}.json").read_text(encoding="utf-8")
    )
    assert len(dataset.cases) == 10
    assert all(c.review.reviewer is None for c in dataset.cases if c.review.status == "draft")


@pytest.mark.parametrize(
    "suffix",
    ["", ".draft2", ".draft3", ".draft4", ".draft5", ".draft6", ".draft7", ".reviewed"],
)
def test_published_baseline_replays_exactly_without_network(monkeypatch, suffix):
    """Scoring the frozen capture must reproduce the published numbers exactly.

    This guards against a metric moving by accident. When it moves on
    purpose — as `wrong_scope_claim_rate` did on 2026-09-22, when the owner
    settled that the scorer compares programme identity rather than strings —
    the published files are regenerated from the same frozen capture and the
    reason is recorded in VERSIONS.md, the same discipline the golden demo
    hash follows. A number computed under a changed definition is not
    comparable to the one it replaces, and saying so is the point.
    """
    import json
    import socket

    root = Path(__file__).resolve().parents[1] / "evaluation/research"
    dataset = Dataset.model_validate_json(
        (root / f"data/ground_truth{suffix}.json").read_text(encoding="utf-8")
    )
    capture = Capture.model_validate_json(
        (root / "baseline/capture.json").read_text(encoding="utf-8")
    )

    def no_network(*args, **kwargs):
        raise AssertionError("Published baseline attempted network")

    monkeypatch.setattr(socket, "socket", no_network)
    assert score(dataset, capture, allow_drafts=True) == json.loads(
        (root / f"baseline/metrics{suffix}.json").read_text(encoding="utf-8")
    )


def test_the_reviewed_corpus_is_signed_and_scores_strictly():
    """The V2-01 acceptance gate: a named human signed every case, so no flag is needed."""
    import json

    root = Path(__file__).resolve().parents[1] / "evaluation/research"
    dataset = Dataset.model_validate_json(
        (root / "data/ground_truth.reviewed.json").read_text(encoding="utf-8")
    )
    capture = Capture.model_validate_json(
        (root / "baseline/capture.json").read_text(encoding="utf-8")
    )

    assert len(dataset.cases) == 10
    for case in dataset.cases:
        assert case.review.status == "human_verified", case.id
        assert case.review.reviewer, case.id
        assert case.review.verified_on, case.id

    report = score(dataset, capture)
    assert report["provisional"] is False
    assert report == json.loads(
        (root / "baseline/metrics.reviewed.json").read_text(encoding="utf-8")
    )


def test_certification_changes_no_measured_value():
    """Signing a corpus says who vouches for it; it may never move a number."""
    import json

    root = Path(__file__).resolve().parents[1] / "evaluation/research"
    reviewed = json.loads((root / "baseline/metrics.reviewed.json").read_text(encoding="utf-8"))
    draft7 = json.loads((root / "baseline/metrics.draft7.json").read_text(encoding="utf-8"))
    assert reviewed["metrics"] == draft7["metrics"]
    assert reviewed["fields"] == draft7["fields"]


def test_scholarship_dimensions_freshness_and_review_have_separate_metrics():
    dataset, capture, evidence = inputs()
    raw_data = dataset.model_dump(mode="json")
    keys = [
        "scholarships.award.exists",
        "scholarships.award.applicability.degree",
        "scholarships.award.coverage.tuition",
    ]
    raw_data["cases"][0]["labels"] = [
        {"key": key, "status": "known", "value": True, "evidence": [evidence]} for key in keys
    ]
    raw_capture = capture.model_dump()
    raw_capture["observations"] = [
        {
            "case_id": "example",
            "predictions": [
                {
                    "key": key,
                    "value": True,
                    "evidence": evidence,
                    "current": False,
                    "conflict_visible": True,
                }
                for key in keys
            ],
            "telemetry": {"human_review_required": True, "latency_seconds": 3.5},
        }
    ]
    result = score(
        Dataset.model_validate(raw_data), Capture.model_validate(raw_capture), allow_drafts=True
    )
    for key in (
        "scholarship_discovery_recall",
        "scholarship_applicability_precision",
        "scholarship_applicability_recall",
        "scholarship_coverage_precision",
        "human_review_rate",
    ):
        assert result["metrics"][key]["value"] == 1
    assert result["metrics"]["current_evidence_rate"]["value"] == 0
    assert result["metrics"]["conflict_visibility_rate"]["value"] == 1
    assert result["operations"]["latency_percentiles"]["p95"] == 3.5


def test_non_applicable_does_not_reduce_coverage():
    dataset, capture, _ = inputs()
    raw = dataset.model_dump()
    raw["cases"][0]["labels"] = [
        {"key": "sat.minimum", "status": "not_applicable", "notes": "Synthetic"}
    ]
    result = score(Dataset.model_validate(raw), capture, allow_drafts=True)
    assert result["metrics"]["critical_field_coverage"]["denominator"] == 0


@pytest.mark.parametrize("partial", [False, True])
def test_live_parent_records_timeout_without_calling_real_network(tmp_path, monkeypatch, partial):
    import subprocess
    import sys

    from evaluation.research import live

    monkeypatch.setattr(
        sys, "argv", ["live", "--live", "--case", "groningen", "--out", str(tmp_path)]
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")

    def timeout(*args, **kwargs):
        assert kwargs["env"]["UNIMATCH_ENABLE_BROWSER_TIER"] == "false"
        assert kwargs["env"]["UNIMATCH_DEMO_MODE"] == "false"
        if partial:
            from evaluation.research.schema import Observation, Telemetry

            command = args[0]
            output = Path(command[command.index("--out") + 1])
            output.write_text(
                Observation(
                    case_id="groningen",
                    telemetry=Telemetry(http_fetches=7),
                    ranked_urls=["https://example.edu/cs"],
                ).model_dump_json(),
                encoding="utf-8",
            )
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert capture.observations[0].error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert capture.observations[0].telemetry.http_fetches == (7 if partial else None)
    assert bool(capture.observations[0].ranked_urls) == partial


@pytest.mark.asyncio
async def test_capture_reads_canary_output_without_loading_ground_truth(tmp_path, monkeypatch):
    from evaluation.research.live import capture_one
    from scripts import canary_discovery as canary

    original = canary.CanaryRunner

    async def fake_canary(selector, verbose):
        assert selector == "rug.nl"
        assert canary.CanaryRunner is not original
        return {"institutions": [{"programs": ["https://example.edu/programme"]}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "observation.json"
    await capture_one("groningen", output, 4)
    from evaluation.research.schema import Observation

    observation = Observation.model_validate_json(output.read_text())
    assert str(observation.programme_urls[0]) == "https://example.edu/programme"
    assert observation.predictions == []
    assert canary.CanaryRunner is original


@pytest.mark.asyncio
async def test_capture_counts_the_search_calls_it_used_to_report_as_zero(tmp_path, monkeypatch):
    """`search_calls` was initialised to 0 and never incremented, so a case
    that spent its wall clock on search reported that it had searched nothing."""
    from app.adapters.search.exa import ExaSearchProvider
    from evaluation.research.live import capture_one
    from scripts import canary_discovery as canary

    async def quiet_search(provider, *args, **kwargs):
        return []

    monkeypatch.setattr(ExaSearchProvider, "search", quiet_search)
    wrapped: list[object] = []

    async def fake_canary(selector, verbose):
        wrapped.append(ExaSearchProvider.search)
        await ExaSearchProvider.search(None, query="computer science")
        await ExaSearchProvider.search(None, query="admissions")
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "observation.json"
    await capture_one("groningen", output, 4)
    from evaluation.research.schema import Observation

    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.search_calls == 2
    assert wrapped[0] is not quiet_search
    assert ExaSearchProvider.search is quiet_search
