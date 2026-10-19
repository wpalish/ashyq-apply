"""W4 (WF-03a): the harness is ready for a single-column record run.

A record run captures every development case once on a keyed provider, so its
``<case>.search.json`` logs can become a ``recorded-search/2`` store. Offline
only: every workflow step runs with substitute executables, no provider is
called and no key is real.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from evaluation.research import live, recorded_search, scorecard
from tests.test_expert_workflow import measurement_bindings, substitute_python

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/benchmark-capture.yml"
SECRET = "synthetic-key-never-printed"
#: The 44 development ids R1 captures: cohort, dev2, dev3, dev4.
DEV_IDS = [case for members in recorded_search.DEV_SETS.values() for case in members]


def step(name: str, occurrence: int = 0) -> str:
    """The ``run`` script of the ``occurrence``-th step called ``name``."""
    section = WORKFLOW.read_text().split(f"      - name: {name}\n")[occurrence + 1]
    section = section.split("      - ", 1)[0]
    script = section.split("        run: |\n", 1)[1]
    return "\n".join(line[10:] for line in script.splitlines()) + "\n"


def _guard(
    tmp_path: Path, provider: str, cap: str, cases: str, columns: str = "1"
) -> tuple[subprocess.CompletedProcess[str], str, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    substitute_python(tmp_path)
    github_env = tmp_path / "github.env"
    github_env.write_text("")
    result = subprocess.run(
        ["bash", "-c", step("Search query cap (refuse a provider run without one)", 1)],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "GITHUB_ENV": str(github_env),
            "UNIMATCH_SEARCH_PROVIDER": provider,
            "REQUESTED_CAP": cap,
            "REQUESTED_MODE": "expert_paired",
            "REQUESTED_COLUMNS": columns,
            "REQUESTED_CASE": cases,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    config = tmp_path / "out" / "config.txt"
    return result, github_env.read_text(), config.read_text() if config.exists() else ""


def test_the_development_sets_are_the_44_ids_r1_plans_for() -> None:
    assert len(DEV_IDS) == 44 and len(set(DEV_IDS)) == 44
    assert not set(DEV_IDS) & (set(live.HELDOUT) | set(live.DEV5_DOMAINS))


# --- the cap plan of the single-column mode -----------------------------------------


@pytest.mark.parametrize("provider", ["exa", "tavily", "brave"])
def test_a_record_run_of_the_44_ids_plans_264_and_263_is_refused(
    tmp_path: Path, provider: str
) -> None:
    cases = " ".join(DEV_IDS)
    short, github_env, _ = _guard(tmp_path / "short", provider, "263", cases)
    assert short.returncode == 1
    assert "plans 264 provider queries (44 case(s) x 1 capture(s) x 6 + 0 pre-flight)" in (
        short.stdout
    )
    assert "--max-search-queries" not in github_env
    enough, github_env, config = _guard(tmp_path / "enough", provider, "264", cases)
    assert enough.returncode == 0, enough.stdout + enough.stderr
    assert "SEARCH_CAP_ARGS=--max-search-queries 264 --search-ledger " in github_env
    assert f"max_search_queries=264 planned=264 provider={provider}" in config


def test_a_serper_record_run_also_plans_its_preflight(tmp_path: Path) -> None:
    short, _, _ = _guard(tmp_path / "short", "serper", "60", " ".join(DEV_IDS[:10]))
    assert "plans 61 provider queries" in short.stdout and short.returncode == 1


def test_the_paired_default_still_plans_four_columns(tmp_path: Path) -> None:
    result, _, _ = _guard(tmp_path, "exa", "47", "ethz uppsala", columns="4")
    assert result.returncode == 1 and "plans 48 provider queries" in result.stdout


def test_a_column_count_other_than_one_or_four_is_refused(tmp_path: Path) -> None:
    result, github_env, _ = _guard(tmp_path, "exa", "1000", "ethz", columns="2")
    assert result.returncode == 1 and "columns must be 4" in result.stdout
    assert "--max-search-queries" not in github_env


@pytest.mark.parametrize("provider", ["none", "recorded"])
def test_a_dry_dispatch_checks_the_plan_and_passes_no_ledger(tmp_path: Path, provider: str) -> None:
    cases = " ".join(DEV_IDS)
    short, _, _ = _guard(tmp_path / "short", provider, "263", cases)
    assert short.returncode == 1 and "plans 264 provider queries" in short.stdout
    enough, github_env, config = _guard(tmp_path / "enough", provider, "264", cases)
    assert enough.returncode == 0, enough.stdout + enough.stderr
    assert github_env == "SEARCH_CAP_ARGS=\n"
    assert f"max_search_queries=264 planned=264 provider={provider} dry=yes" in config
    # Without a cap they still start uncapped, as before W4.
    uncapped, github_env, _ = _guard(tmp_path / "uncapped", provider, "", cases)
    assert uncapped.returncode == 0 and github_env == "SEARCH_CAP_ARGS=\n"


# --- the search layer: tavily and brave, failing fast without their secret -------------


def _select(
    tmp_path: Path, occurrence: int, requested: str, keys: dict[str, str]
) -> tuple[subprocess.CompletedProcess[str], str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    github_env = tmp_path / "github.env"
    github_env.write_text("")
    env = {
        "PATH": "/usr/bin:/bin",
        "GITHUB_ENV": str(github_env),
        "REQUESTED_SEARCH_PROVIDER": requested,
        "REQUESTED_BASE_ARGS": "",
        "REQUESTED_EXTRA_ARGS": "",
        "UNIMATCH_EXA_API_KEY": "",
        "UNIMATCH_TAVILY_API_KEY": "",
        "UNIMATCH_BRAVE_API_KEY": "",
        "UNIMATCH_SERPER_API_KEY": "",
        **keys,
    }
    result = subprocess.run(
        ["bash", "-c", step("Select the search layer", occurrence)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, github_env.read_text()


def test_the_workflow_offers_tavily_and_brave() -> None:
    text = WORKFLOW.read_text()
    options = text.split("      search_provider:\n", 1)[1].split("permissions:", 1)[0]
    for provider in ("exa", "exa_mcp", "tavily", "brave", "none", "recorded"):
        assert f"          - {provider}\n" in options


@pytest.mark.parametrize("occurrence", [0, 1])  # the benchmark job, the expert job
@pytest.mark.parametrize(
    ("provider", "secret"),
    [
        ("tavily", "UNIMATCH_TAVILY_API_KEY"),
        ("brave", "UNIMATCH_BRAVE_API_KEY"),
        ("exa", "UNIMATCH_EXA_API_KEY"),
    ],
)
def test_an_explicit_keyed_provider_needs_its_own_secret(
    tmp_path: Path, occurrence: int, provider: str, secret: str
) -> None:
    # Another provider's key does not stand in for the one asked for.
    others = {
        k: SECRET
        for k in ("UNIMATCH_EXA_API_KEY", "UNIMATCH_TAVILY_API_KEY", "UNIMATCH_BRAVE_API_KEY")
        if k != secret
    }
    missing, github_env = _select(tmp_path / "missing", occurrence, provider, others)
    assert missing.returncode == 1
    assert f"::error::{provider} requires {secret}; no capture started" in missing.stdout
    assert "UNIMATCH_SEARCH_PROVIDER" not in github_env
    present, github_env = _select(tmp_path / "present", occurrence, provider, {secret: SECRET})
    assert present.returncode == 0, present.stdout + present.stderr
    assert f"UNIMATCH_SEARCH_PROVIDER={provider}\n" in github_env
    assert f"decided by explicit input and {secret}" in present.stdout
    for result in (missing, present):
        assert SECRET not in result.stdout + result.stderr
    assert SECRET not in github_env


# --- the single-column capture loop -----------------------------------------------------


def test_a_record_run_captures_each_case_once_on_the_on_arm(tmp_path: Path) -> None:
    substitute_python(tmp_path)
    cases = "ethz tcd uio ctu"
    script = (
        step("Paired rule experiment (same runner, ABBA order)")
        .replace("${{ inputs.seconds_per_case }}", "120")
        .replace("${{ inputs.max_pages }}", "60")
        .replace("${{ inputs.base_args }}", "")
        .replace("${{ inputs.extra_args }}", "")
        .replace("${{ inputs.case }}", cases)
        .replace("${{ inputs.case_parallelism }}", "5")
    )
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "PAIRED_COLUMNS": "1",
            "UNIMATCH_SEARCH_PROVIDER": "exa",
            "SEARCH_CAP_ARGS": "--max-search-queries 24 --search-ledger /x/search_ledger.json",
            "MEASUREMENT_BINDINGS": measurement_bindings(),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert sorted(call[call.index("--case") + 1] for call in calls) == sorted(cases.split())
    assert {call[call.index("--out") + 1] for call in calls} == {
        f"out/{case}-on" for case in cases.split()
    }
    for call in calls:
        assert call[call.index("--max-search-queries") + 1] == "24"
        assert call[call.index("--search-provider") + 1] == "exa"
    assert "order=single-on-5" in (tmp_path / "out" / "config.txt").read_text()


# --- make_v2_store ---------------------------------------------------------------------


def _write_on_capture(root: Path, case_id: str, log: bool) -> None:
    target = root / f"{case_id}-on" / "20261020T000001Z"
    target.mkdir(parents=True)
    trace = {
        "institution": "University of Oslo",
        "domain": "www.uio.no",
        "search_results": [],
    }
    raw = {"canary": {"institutions": [{"country": "Norway", "discovery_trace": trace}]}}
    (target / f"{case_id}.raw.json").write_text(json.dumps(raw))
    if log:
        requests = [
            {
                "provider": "exa",
                "method": "search",
                "kind": "topic",
                "query": "uio.no application deadline",
                "domains": ["uio.no"],
                "hl": None,
                "gl": None,
                "max_results": 10,
                "results": [
                    {"rank": 1, "url": "https://www.uio.no/a", "title": "T", "snippet": "S"}
                ],
            }
        ]
        document = {"schema": live.SEARCH_LOG_SCHEMA, "case": case_id, "requests": requests}
        (target / f"{case_id}.search.json").write_text(json.dumps(document))


def test_make_v2_store_reads_every_set_the_case_list_touches() -> None:
    sources = recorded_search.record_run_sources("9", "t", "sha", Path("out"), DEV_IDS)
    assert [s[0] for s in sources] == ["cohort", "dev2", "dev3", "dev4"]
    assert all(s[1:] == ("9", "t", "sha", Path("out")) for s in sources)
    assert [
        s[0] for s in recorded_search.record_run_sources("9", "t", "s", Path("o"), ["uio"])
    ] == ["dev3"]


@pytest.mark.parametrize("outsider", ["tum", "lmu"])  # a heldout id, a dev5 id
def test_make_v2_store_refuses_a_case_outside_the_development_sets(
    tmp_path: Path, outsider: str
) -> None:
    out = tmp_path / "store.json"
    argv = ["--record-run", "9", "t", "s", str(tmp_path), "--cases", "uio", outsider]
    with pytest.raises(SystemExit):
        recorded_search.main([*argv, "--out", str(out)])
    assert not out.exists()


def test_make_v2_store_writes_v2_and_refuses_to_write_v1(tmp_path: Path) -> None:
    logged = tmp_path / "logged"
    _write_on_capture(logged, "uio", log=True)
    out = tmp_path / "recorded_search.r1.json"
    argv = ["--record-run", "9", "2026-10-20T00:00:00Z", "abc", str(logged), "--cases", "uio"]
    assert recorded_search.main([*argv, "--out", str(out)]) == 0
    document = json.loads(out.read_text())
    assert document["schema"] == "recorded-search/2"
    assert document["provenance"]["sources"][0]["set"] == "dev3"
    assert document["entries"][0]["kind"] == "topic"
    unlogged = tmp_path / "unlogged"
    _write_on_capture(unlogged, "uio", log=False)
    v1 = tmp_path / "v1.json"
    argv = ["--record-run", "9", "2026-10-20T00:00:00Z", "abc", str(unlogged), "--cases", "uio"]
    assert recorded_search.main([*argv, "--out", str(v1)]) == 1
    assert not v1.exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["--out", "x"],
        ["--cases", "uio", "--out", "x"],
        ["--record-run", "9", "t", "s", "d", "--out", "x"],
        "--source dev3 9 t s d --record-run 9 t s d --cases uio --out x".split(),
    ],
)
def test_the_builder_takes_one_kind_of_source(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        recorded_search.main(argv)


def test_the_workflow_step_calls_make_v2_store_with_the_run_and_its_cases(
    tmp_path: Path,
) -> None:
    substitute_python(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "git").write_text("#!/bin/sh\necho headsha\n")
    (bin_dir / "git").chmod(0o700)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "REQUESTED_CASE": "groningen uio ctu",
        "STORE_TAG": "r1",
        "RUN_ID": "123",
        "UNIMATCH_SEARCH_PROVIDER": "exa",
    }
    script = step("Build the recorded-search v2 store (make_v2_store)")
    result = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    (call,) = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert call[:2] == ["-m", "evaluation.research.recorded_search"]
    run = call[call.index("--record-run") + 1 : call.index("--record-run") + 5]
    assert run[0] == "123" and run[2] == "headsha" and run[3] == "out"
    assert call[call.index("--cases") + 1 : call.index("--out")] == ["groningen", "uio", "ctu"]
    assert call[-1] == "out/recorded_search.r1.json"
    for skipped in ("none", "recorded"):
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=tmp_path,
            env={**env, "UNIMATCH_SEARCH_PROVIDER": skipped},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0 and "make_v2_store skipped" in result.stdout
    bad = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={**env, "STORE_TAG": "../x"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode == 1 and "not a file-name token" in bad.stdout


# --- the scorecard target row of a v2 replay ------------------------------------------------


def _replayed(topic: int, scholarship: int, schema: str | None) -> dict[str, Any]:
    from tests.test_scorecard import DEADLINE, capture

    cap = capture([DEADLINE])
    cap["config"]["search_provider"] = "recorded"
    if schema is not None:
        cap["config"]["recorded_search_store"] = {"file": "s.json", "schema": schema}
    cap["observations"][0]["telemetry"].update(
        recorded_search_hits=4,
        recorded_search_misses=topic + scholarship,
        recorded_search_misses_discovery=0,
        recorded_search_misses_topic=topic,
        recorded_search_misses_scholarship=scholarship,
        recorded_search_misses_identity=0,
    )
    return cap


def _v2_rows(card: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        r["arm"]: r
        for r in card["targets"]
        if r["metric"] == "recorded_search_misses_topic_scholarship"
    }


def test_a_v2_replay_that_still_misses_a_topic_or_scholarship_search_is_flagged(
    tmp_path: Path,
) -> None:
    from tests.test_scorecard import dataset, write_run

    v2 = "recorded-search/2"
    run = write_run(
        tmp_path / "run",
        {
            "off": [_replayed(0, 0, v2), _replayed(0, 0, v2)],
            "on": [_replayed(0, 0, v2), _replayed(1, 2, v2)],
        },
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    rows = _v2_rows(card)
    assert rows["off"] == {
        "arm": "off",
        "metric": "recorded_search_misses_topic_scholarship",
        "worst": 0,
        "target": "== 0 (v2 store)",
        "met": True,
    }
    assert rows["on"]["worst"] == 3 and rows["on"]["met"] is False
    assert "| on | recorded_search_misses_topic_scholarship | 3 | == 0 (v2 store) | NO |" in (
        scorecard.render(card)
    )


@pytest.mark.parametrize("schema", ["recorded-search/1", None])
def test_a_v1_or_unlabelled_replay_keeps_its_old_targets(
    tmp_path: Path, schema: str | None
) -> None:
    from tests.test_scorecard import dataset, write_run

    run = write_run(
        tmp_path / "run", {"off": [_replayed(5, 6, schema)], "on": [_replayed(5, 6, schema)]}
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert not _v2_rows(card)


def test_the_capture_config_names_the_replayed_store_schema(tmp_path: Path) -> None:
    store = tmp_path / "store.json"
    store.write_text(json.dumps({"schema": "recorded-search/2", "provenance": {}, "entries": []}))
    config = live.recorded_store_config(store)["recorded_search_store"]
    assert config["schema"] == "recorded-search/2" and config["file"] == "store.json"
