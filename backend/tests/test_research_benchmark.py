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
    "suffix", ["", ".draft2", ".draft3", ".draft4", ".draft5", ".draft6", ".draft7", ".draft8"]
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
    [
        "",
        ".draft2",
        ".draft3",
        ".draft4",
        ".draft5",
        ".draft6",
        ".draft7",
        ".reviewed",
        ".draft8",
        ".reviewed8",
        ".reviewed9",
    ],
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


def test_the_draft8_signature_scores_strictly_and_moves_no_number():
    """Signed by Диас on 2026-10-05 ("Подписываю draft8"): strict, and equal to draft8."""
    import json

    root = Path(__file__).resolve().parents[1] / "evaluation/research"
    dataset = Dataset.model_validate_json(
        (root / "data/ground_truth.reviewed8.json").read_text(encoding="utf-8")
    )
    capture = Capture.model_validate_json(
        (root / "baseline/capture.json").read_text(encoding="utf-8")
    )
    assert len(dataset.cases) == 10
    assert all(c.review.status == "human_verified" and c.review.reviewer for c in dataset.cases)
    report = score(dataset, capture)
    assert report["provisional"] is False
    draft8 = json.loads((root / "baseline/metrics.draft8.json").read_text(encoding="utf-8"))
    assert report["metrics"] == draft8["metrics"]


def test_certification_changes_no_measured_value():
    """Signing a corpus says who vouches for it; it may never move a number."""
    import json

    root = Path(__file__).resolve().parents[1] / "evaluation/research"
    reviewed = json.loads((root / "baseline/metrics.reviewed.json").read_text(encoding="utf-8"))
    draft7 = json.loads((root / "baseline/metrics.draft7.json").read_text(encoding="utf-8"))
    assert reviewed["metrics"] == draft7["metrics"]
    # The one amendment since signing (owner, 2026-09-23): Aalto's
    # `programme.teaching_language.primary` became `programme.language`, the
    # key Vienna and Warsaw already used. Its field row moves into that key's
    # denominators; nothing else may differ.
    old_fields = dict(draft7["fields"])
    moved = old_fields.pop("programme.teaching_language.primary")
    merged = old_fields["programme.language"]
    for part in ("coverage", "recall"):
        merged[part]["numerator"] += moved[part]["numerator"]
        merged[part]["denominator"] += moved[part]["denominator"]
        merged[part]["value"] = (
            merged[part]["numerator"] / merged[part]["denominator"]
            if merged[part]["denominator"]
            else None
        )
    assert reviewed["fields"] == old_fields


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


@pytest.mark.parametrize("override", [None, "tavily", "none", "fake"])
def test_live_provider_selection_reaches_child_and_capture(tmp_path, monkeypatch, capsys, override):
    import subprocess
    import sys

    from app.config import Settings
    from evaluation.research import live
    from evaluation.research.schema import Observation

    secret = "synthetic-provider-key-never-print"
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("UNIMATCH_TAVILY_API_KEY", secret)
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", secret)
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENVIRONMENT", "development")
    command = ["live", "--live", "--case", "groningen", "--out", str(tmp_path)]
    if override:
        command.extend(["--search-provider", override])
    else:
        # Ordinary captures retain their existing startup behavior.
        monkeypatch.setattr(
            Settings,
            "_validate_search",
            lambda self: pytest.fail("implicit provider must not add a new validation gate"),
        )
    monkeypatch.setattr(sys, "argv", command)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    expected = override or "serper"

    def child(command, **kwargs):
        assert kwargs["env"]["UNIMATCH_SEARCH_PROVIDER"] == expected
        assert ("--search-provider" in command) == bool(override)
        if override:
            assert command[command.index("--search-provider") + 1] == expected
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture_path = next(tmp_path.rglob("capture.json"))
    capture_text = capture_path.read_text(encoding="utf-8")
    capture = Capture.model_validate_json(capture_text)
    stdout = capsys.readouterr().out
    assert capture.config["search_provider"] == expected
    assert f"search provider: {expected}" in stdout
    assert stdout.splitlines()[-1] == str(capture_path)
    assert secret not in stdout + capture_text


@pytest.mark.parametrize(
    ("provider", "environment", "message"),
    [
        ("unknown", "development", "invalid choice"),
        ("tavily", "development", "needs UNIMATCH_TAVILY_API_KEY"),
        ("fake", "production", "must not be 'fake' in production"),
    ],
)
def test_live_explicit_provider_fails_before_capture(
    tmp_path, monkeypatch, capsys, provider, environment, message
):
    import subprocess
    import sys

    from evaluation.research import live

    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", "synthetic-unrelated-key")
    monkeypatch.setenv("UNIMATCH_TAVILY_API_KEY", "")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENVIRONMENT", environment)
    monkeypatch.setattr(
        sys,
        "argv",
        ["live", "--live", "--out", str(tmp_path), "--search-provider", provider],
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("must not start capture")
    )
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: pytest.fail("must fail before git")
    )
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    assert message in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_live_child_provider_override_replaces_cached_settings(tmp_path, monkeypatch, capsys):
    import sys

    from app.config import Settings, get_settings
    from evaluation.research import live

    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", "synthetic-serper-key")
    monkeypatch.setenv("UNIMATCH_TAVILY_API_KEY", "synthetic-tavily-key")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    get_settings.cache_clear()
    assert get_settings().search_provider == "serper"
    calls = []

    async def capture(case_id, output, max_pages, seconds):
        calls.append(case_id)
        assert Settings().search_provider == "tavily"
        assert get_settings().search_provider == "tavily"

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            "groningen",
            "--out",
            str(tmp_path),
            "--search-provider",
            "tavily",
        ],
    )
    try:
        live.main()
        assert calls == ["groningen"]
        assert "search provider: tavily" in capsys.readouterr().out
        assert Settings().search_provider == "serper"
    finally:
        get_settings.cache_clear()


def test_live_provider_choices_follow_factory_allowlist(tmp_path, monkeypatch):
    import subprocess
    import sys

    from app.adapters import search
    from app.config import Settings
    from evaluation.research import live
    from evaluation.research.schema import Observation

    provider = "future_provider"
    monkeypatch.setattr(
        search, "KNOWN_SEARCH_PROVIDERS", search.KNOWN_SEARCH_PROVIDERS | {provider}
    )
    validated = []
    monkeypatch.setattr(
        Settings, "_validate_search", lambda self: validated.append(self.search_provider)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(tmp_path),
            "--search-provider",
            provider,
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")

    def child(command, **kwargs):
        assert kwargs["env"]["UNIMATCH_SEARCH_PROVIDER"] == provider
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert validated == [provider]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert capture.config["search_provider"] == provider


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


def test_live_accepts_a_dev2_case_and_passes_it_to_the_child(tmp_path, monkeypatch):
    """Rule 0: a university with no registry entry can be captured."""
    import subprocess
    import sys

    from evaluation.research import live
    from evaluation.research.schema import Observation

    monkeypatch.setattr(sys, "argv", ["live", "--live", "--case", "ethz", "--out", str(tmp_path)])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    started = []

    def child(command, **kwargs):
        started.append(command[command.index("--case") + 1])
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="ethz").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert started == ["ethz"]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert [o.case_id for o in capture.observations] == ["ethz"]


def test_every_dev2_case_has_a_seed_row_and_an_official_domain():
    import json

    from app.adapters.discovery.live_discovery import REGISTRY_PATH, registrable_domain
    from evaluation.research import live

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_hosts = {registrable_domain(entry["homepage"]) for entry in registry}
    assert set(live.DEV2) == set(live.DEV2_DOMAINS)
    assert not set(live.DEV2) & (set(live.COHORT) | set(live.HELDOUT))
    for case_id, domain in live.DEV2_DOMAINS.items():
        assert live.CASE_DOMAINS[case_id] == domain
        entry = live.dev2_entry(case_id)
        assert set(entry) == {"name", "country", "city", "homepage"}
        assert entry["homepage"] in {f"https://www.{domain}/", f"https://{domain}/"}
        assert domain not in registry_hosts
    assert live.dev2_entry("khalifa")["homepage"] == "https://www.ku.ac.ae/"


def test_every_dev4_case_has_an_identity_and_shares_no_domain_with_the_heldout_nine():
    import json

    from app.adapters.discovery.live_discovery import REGISTRY_PATH, registrable_domain
    from app.catalogue.importer import SEED_PATH
    from evaluation.research import live

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_hosts = {registrable_domain(entry["homepage"]) for entry in registry}
    seed_names = {
        row["name"] for row in json.loads(SEED_PATH.read_text(encoding="utf-8"))["universities"]
    }
    assert set(live.DEV4_DOMAINS) == set(live.DEV4_SEEDS) | set(live.DEV4_OFF_SEED)
    assert not set(live.DEV4_SEEDS) & set(live.DEV4_OFF_SEED)
    assert not set(live.DEV4_DOMAINS) & (set(live.COHORT) | set(live.HELDOUT) | set(live.DEV2))
    # Ticket 04 Q4: no registrable domain in common with any heldout university.
    assert not set(live.DEV4_DOMAINS.values()) & set(live.HELDOUT.values())
    for case_id, domain in live.DEV4_DOMAINS.items():
        assert live.CASE_DOMAINS[case_id] == domain
        entry = live.dev2_entry(case_id)
        assert set(entry) == {"name", "country", "city", "homepage"}
        assert entry["homepage"] in {f"https://www.{domain}/", f"https://{domain}/"}
        assert registrable_domain(entry["homepage"]) == domain
        assert domain not in registry_hosts
    for case_id, (name, _, _) in live.DEV4_OFF_SEED.items():
        assert name not in seed_names, case_id
    assert live.dev2_entry("vut") == {
        "name": "Brno University of Technology",
        "country": "Czechia",
        "city": "Brno",
        "homepage": "https://www.vut.cz/",
    }


def test_an_off_seed_dev4_university_gets_a_row_only_in_the_canary_database():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.catalogue.importer import identity_key, import_catalogue, stable_id
    from app.models.base import Base
    from app.models.university import University
    from evaluation.research import live
    from scripts import canary_discovery as canary

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    import_catalogue(session)
    entry = live.dev2_entry("taltech")
    with pytest.raises(SystemExit):
        canary._install_identified_sites(session, [entry])
    session.rollback()
    import_catalogue(session)
    install = live.with_off_seed_rows(canary._install_identified_sites)
    install(session, [entry, live.dev2_entry("ctu")])
    uni = session.get(University, stable_id(identity_key(entry["name"], entry["country"])))
    assert uni is not None and uni.registry_entry == entry and uni.domain == "taltech.ee"
    # A name the canary cannot match is still refused for every other entry.
    with pytest.raises(SystemExit):
        install(session, [{**live.dev2_entry("ctu"), "name": "Not A University"}])


def test_live_accepts_a_dev4_case(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live
    from evaluation.research.schema import Observation

    monkeypatch.setattr(sys, "argv", ["live", "--live", "--case", "ktu", "--out", str(tmp_path)])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    started = []

    def child(command, **kwargs):
        started.append(command[command.index("--case") + 1])
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="ktu").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert started == ["ktu"]


def test_the_dev4_draft_labels_the_programme_page_and_nothing_else():
    from app.adapters.discovery.live_discovery import registrable_domain
    from evaluation.research import live
    from evaluation.research.identities import IdentityMap

    data = Path(live.__file__).parent / "data"
    dev4 = Dataset.model_validate_json((data / "dev4.draft1.json").read_text(encoding="utf-8"))
    assert dev4.version == "2026-10-18.dev4-draft1" and dev4.split == "development"
    assert {case.id for case in dev4.cases} == set(live.DEV4_DOMAINS)
    for case in dev4.cases:
        assert case.domain == live.DEV4_DOMAINS[case.id]
        assert case.review.status == "draft"
        assert [label.key for label in case.labels] == ["programme.exists"]
        assert case.programme_status == "known" and 1 <= len(case.programme_urls) <= 2
        for url in [*case.programme_urls, *(e.url for e in case.programme_evidence)]:
            assert registrable_domain(str(url)) == case.domain
            assert registrable_domain(str(url)) not in set(live.HELDOUT.values())
    bindings = IdentityMap.model_validate_json(
        (data / "identity_bindings.dev4-draft1.json").read_text(encoding="utf-8")
    )
    assert bindings.version == dev4.version and bindings.bindings == []


@pytest.mark.asyncio
async def test_a_dev2_capture_hands_the_canary_a_homepage_not_a_selector(tmp_path, monkeypatch):
    from evaluation.research.live import capture_one
    from scripts import canary_discovery as canary

    calls = []

    async def fake_canary(selector, verbose, batch=None, *, entries=None):
        calls.append((selector, batch, entries))
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    await capture_one("ethz", tmp_path / "ethz.json", 4)
    await capture_one("khalifa", tmp_path / "khalifa.json", 4)
    assert calls == [
        (
            None,
            None,
            [
                {
                    "name": "ETH Zurich",
                    "country": "Switzerland",
                    "city": "Zurich",
                    "homepage": "https://ethz.ch/",
                }
            ],
        ),
        (
            None,
            None,
            [
                {
                    "name": "Khalifa University",
                    "country": "United Arab Emirates",
                    "city": "Abu Dhabi",
                    "homepage": "https://www.ku.ac.ae/",
                }
            ],
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["exa", "exa_mcp"])
async def test_capture_counts_the_search_calls_it_used_to_report_as_zero(
    tmp_path, monkeypatch, provider_name
):
    """`search_calls` was initialised to 0 and never incremented, so a case
    that spent its wall clock on search reported that it had searched nothing."""
    from app.adapters.search.exa import ExaSearchProvider
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider
    from evaluation.research.live import capture_one
    from scripts import canary_discovery as canary

    async def quiet_search(provider, *args, **kwargs):
        return []

    provider_class = {"exa": ExaSearchProvider, "exa_mcp": ExaMcpSearchProvider}[provider_name]
    monkeypatch.setattr(provider_class, "search", quiet_search)
    wrapped: list[object] = []

    async def fake_canary(selector, verbose):
        wrapped.append(provider_class.search)
        await provider_class.search(None, query="computer science")
        await provider_class.search(None, query="admissions")
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "observation.json"
    await capture_one("groningen", output, 4)
    from evaluation.research.schema import Observation

    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.search_calls == 2
    assert wrapped[0] is not quiet_search
    assert provider_class.search is quiet_search


class TestWhichWayAQuoteSupports:
    """Owner decision 2026-09-23: the reviewer's words inside a short quote of ours count."""

    def test_both_directions_and_the_cap(self):
        from evaluation.research.metrics import SUPPORTING_QUOTE_MAX, quote_supports

        assert quote_supports("IELTS 6.5", "Bachelor CS IELTS 6.5")
        assert quote_supports(
            "Applicants need Bachelor CS IELTS 6.5 overall.", "Bachelor CS IELTS 6.5"
        )
        long_quote = "x " * SUPPORTING_QUOTE_MAX + "Bachelor CS IELTS 6.5"
        assert not quote_supports(long_quote, "Bachelor CS IELTS 6.5")
        assert quote_supports("Bachelor  CS\nIELTS 6.5", "Bachelor CS IELTS 6.5")
        assert not quote_supports("", "Bachelor CS IELTS 6.5")
        assert not quote_supports("IELTS 7.0 overall", "IELTS 6.5")

    def test_a_sentence_around_the_reviewers_words_now_scores(self):
        dataset, capture, evidence = inputs()
        ours = dict(
            evidence, excerpt="Applicants need Bachelor CS IELTS 6.5 overall, per band 6.0."
        )
        raw = capture.model_dump()
        raw["observations"] = [
            {
                "case_id": "example",
                "predictions": [{"key": "ielts.overall", "value": 6.5, "evidence": ours}],
            }
        ]
        result = score(dataset, Capture.model_validate(raw), allow_drafts=True)
        assert result["metrics"]["claim_recall"]["numerator"] == 1
        assert result["metrics"]["verbatim_evidence_rate"]["numerator"] == 1


def test_live_scoring_resolves_an_owner_approved_award_identity():
    """Owner decision 2026-09-23: live capture maps with the reviewed bindings,
    so an NTU Nanyang Global claim lands on its certified key instead of
    ``unmapped.scholarship_exists``."""
    from evaluation.research.identities import IdentityMap
    from evaluation.research.live import REVIEWED_BINDINGS
    from evaluation.research.mapping import normalize_subject_claims

    identities = IdentityMap.model_validate_json(REVIEWED_BINDINGS.read_text(encoding="utf-8"))
    raw = {
        "claim_type": "scholarship_exists",
        "normalized_value": "Nanyang Global Scholarship",
        "subject_key": "Nanyang Global Scholarship",
        "source_url": "https://www.ntu.edu.sg/admissions/undergraduate/scholarships/"
        "scholarship-opportunities/detail/nanyang-scholarship",
    }
    [(key, value, _, _)] = normalize_subject_claims("scholarship_exists", raw, identities)
    assert (key, value) == ("scholarships.nanyang_global.exists", True)


def test_scope_compares_case_blind_outside_the_programme():
    """ "Fall 2027" from a page and "fall 2027" in the corpus are one intake."""
    from evaluation.research.metrics import scope_matches
    from evaluation.research.schema import Scope

    label = Scope(university="Example", intake="fall 2027")
    assert scope_matches(label, Scope(university="Example", intake="Fall 2027"))
    assert not scope_matches(label, Scope(university="Example", intake="Spring 2027"))
    assert not scope_matches(label, Scope(university="Example"))


def test_a_child_stopped_by_its_own_clock_keeps_what_it_filed(tmp_path, monkeypatch):
    """Runs 59-62: UBC's kill came mid-funding and every claim it had filed was lost."""
    import asyncio

    from evaluation.research import live
    from evaluation.research.schema import Observation
    from scripts import canary_discovery as canary

    async def slow(*_args, **_kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr(canary, "run_canary", slow)
    output = tmp_path / "groningen.json"

    asyncio.run(live.capture_one("groningen", output, max_pages=5, seconds=0.05))

    observation = Observation.model_validate_json(output.read_text(encoding="utf-8"))
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"


def test_the_oracle_compares_band_maps_regardless_of_key_order():
    from evaluation.research.oracle import _matches

    expected = {"reading": 6.0, "listening": 6.0, "speaking": 6.0, "writing": 6.0}
    produced = {"listening": 6.0, "reading": 6.0, "speaking": 6.0, "writing": 6.0}
    assert _matches(expected, produced)
    assert not _matches(expected, {**produced, "writing": 5.5})


def test_a_descriptive_corpus_population_accepts_silence_but_not_a_wrong_value():
    from evaluation.research.metrics import scope_matches
    from evaluation.research.schema import Scope

    expected = Scope(university="U", population="Vancouver applicants using IELTS Academic")
    assert scope_matches(expected, Scope(university="U"))
    assert not scope_matches(expected, Scope(university="U", population="transfer"))
    # D2 (owner, 2026-10-05): another description is compatible with the note.
    assert scope_matches(
        Scope(university="U", population="full-time undergraduate scholarship applicants"),
        Scope(university="U", population="Singapore PRs and international students"),
    )
    # A controlled population must still be recorded.
    assert not scope_matches(Scope(university="U", population="non-EU/EEA"), Scope(university="U"))
    assert scope_matches(
        Scope(university="U", population="non-EU/EEA"),
        Scope(university="U", population="non-eu/eea"),
    )


def test_the_controlled_populations_match_the_scope_reader():
    from app.adapters import scope_reader
    from evaluation.research.metrics import CONTROLLED_POPULATIONS

    assert {v.casefold() for _p, v in scope_reader._POPULATIONS} == CONTROLLED_POPULATIONS


def test_a_leading_the_is_not_part_of_a_university_name():
    from evaluation.research.metrics import dimension_matches

    assert dimension_matches("university", "University of Hong Kong", "The University of Hong Kong")
    assert not dimension_matches("university", "University of Hong Kong", "Hong Kong University")


NTU_GLOBAL = (
    "https://www.ntu.edu.sg/admissions/undergraduate/scholarships/"
    "scholarship-opportunities/detail/nanyang-scholarship"
)


def _extra_bindings_file(tmp_path, bindings):
    import json

    path = tmp_path / "identity_bindings.extra.json"
    path.write_text(json.dumps({"version": "test-extra", "bindings": bindings}), encoding="utf-8")
    return path


def test_extra_bindings_merge_after_the_reviewed_ones_and_never_override_them(tmp_path):
    """M-1: a draft binding file adds identities; a reviewed binding wins a clash."""
    from evaluation.research.live import load_identities
    from evaluation.research.mapping import normalize_subject_claims

    extra = _extra_bindings_file(
        tmp_path,
        [
            {
                "kind": "award",
                "source_url": "https://ethz.ch/en/studies/financial/scholarships/excellence.html",
                "subject": "Excellence Scholarship & Opportunity Programme",
                "key": "scholarships.ethz_esop",
                "notes": "synthetic draft binding",
            },
            {
                # Same (kind, source_url, subject) as a reviewed binding, other key.
                "kind": "award",
                "source_url": NTU_GLOBAL,
                "subject": "Nanyang Global Scholarship",
                "key": "scholarships.hijacked",
                "notes": "synthetic clash",
            },
        ],
    )
    reviewed = load_identities()
    merged = load_identities([extra])
    assert len(merged.bindings) == len(reviewed.bindings) + 1
    assert merged.version.endswith("+test-extra")

    def key(identities, url, subject):
        raw = {
            "claim_type": "scholarship_exists",
            "normalized_value": subject,
            "subject_key": subject,
            "source_url": url,
        }
        [(mapped, _, _, _)] = normalize_subject_claims("scholarship_exists", raw, identities)
        return mapped

    eth = ("https://ethz.ch/en/studies/financial/scholarships/excellence.html",)
    eth_subject = "Excellence Scholarship & Opportunity Programme"
    assert key(reviewed, *eth, eth_subject).startswith("unmapped.")
    assert key(merged, *eth, eth_subject) == "scholarships.ethz_esop.exists"
    assert (
        key(merged, NTU_GLOBAL, "Nanyang Global Scholarship")
        == "scholarships.nanyang_global.exists"
    )


def test_the_shipped_draft_binding_files_merge_cleanly():
    from evaluation.research.live import REVIEWED_BINDINGS, load_identities

    data = REVIEWED_BINDINGS.parent
    merged = load_identities(
        [data / "identity_bindings.draft2.json", data / "identity_bindings.dev2-draft1.json"]
    )
    assert len(merged.bindings) > len(load_identities().bindings)


def test_extra_bindings_reach_the_child_and_the_capture_config(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live
    from evaluation.research.schema import Observation

    extra = _extra_bindings_file(tmp_path, [])
    second = tmp_path / "second.json"
    second.write_text(extra.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(tmp_path / "out"),
            "--extra-bindings",
            str(extra),
            "--extra-bindings",
            str(second),
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    [command] = commands
    passed = [command[i + 1] for i, value in enumerate(command) if value == "--extra-bindings"]
    assert passed == [str(extra), str(second)]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert capture.config["identity_bindings"] == [
        "evaluation/research/data/identity_bindings.reviewed.json",
        str(extra),
        str(second),
    ]


def test_the_child_maps_with_the_extra_bindings(tmp_path, monkeypatch):
    import sys

    from evaluation.research import live

    extra = _extra_bindings_file(tmp_path, [])
    received = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        received.append(kwargs.get("extra_bindings"))

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            "groningen",
            "--out",
            str(tmp_path / "o.json"),
            "--extra-bindings",
            str(extra),
        ],
    )
    live.main()
    assert received == [[extra]]


def test_a_missing_extra_bindings_file_fails_before_capture(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live

    monkeypatch.setattr(
        sys,
        "argv",
        [
            *("live", "--live", "--case", "groningen", "--out", str(tmp_path)),
            *("--extra-bindings", str(tmp_path / "missing.json")),
        ],
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("must not start capture")
    )
    with pytest.raises(SystemExit):
        live.main()
