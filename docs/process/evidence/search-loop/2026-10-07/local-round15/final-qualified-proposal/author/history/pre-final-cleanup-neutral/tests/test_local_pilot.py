"""Offline route controls; injected transports are ineligible runtime proof."""

from __future__ import annotations

import asyncio
import copy
import json
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation.research import local_pilot as p
from evaluation.research.expert import controller as c
from evaluation.research.expert import selector as s
from evaluation.research.expert.journal import AcceptedJournal
from evaluation.research.identities import IdentityMap
from evaluation.research.pilot_admission import validate_algorithm


@pytest.fixture(autouse=True)
def denied_network(monkeypatch):
    def denied(*_args, **_kwargs):
        raise AssertionError("Real network/DNS forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def public_input():
    domains = (
        "rug.nl",
        "tudelft.nl",
        "aalto.fi",
        "univie.ac.at",
        "uw.edu.pl",
        "ubc.ca",
        "utoronto.ca",
        "hku.hk",
        "ntu.edu.sg",
        "kaist.ac.kr",
    )
    cases = []
    for key, domain in zip(p.COHORT, domains, strict=True):
        university = "Synthetic " + key.title() + " University"
        cases.append(
            {
                "case_id": key,
                "university": university,
                "domain": domain,
                "request": {
                    "university": university,
                    "programme": None,
                    "degree": "bachelor",
                    "field": "computer science",
                    "intake": "fall 2027",
                    "population": "international",
                    "qualification": "KZ national secondary",
                    "academic_year": None,
                },
            }
        )
    return {
        "schema_version": "1",
        "public_profile": {"education_system": "KZ national secondary"},
        "cases": cases,
    }


def setup(tmp_path):
    research = Path(c.__file__).resolve().parents[1]
    backend = research.parents[1]
    source = backend.parent
    old = tmp_path / "old-stop.json"
    old.write_text('{"original":"refused"}')
    public = public_input()
    public_path = tmp_path / "public.json"
    p.store(public_path, public)
    manifest = {
        "files": {
            f"backend/evaluation/research/{name}.py": p.sha(research / f"{name}.py")
            for name in ("live", "mapping")
        }
    }
    manifest_path = tmp_path / "manifest.json"
    p.store(manifest_path, manifest)
    value = {
        "provider": "exa_mcp",
        "cases": list(p.COHORT),
        "source_snapshot": str(source),
        "source_head": "synthetic-source",
        "source_tree_sha256": "a" * 64,
        "source_manifest": str(manifest_path),
        "public_input": str(public_path),
        "cycle_id": "synthetic-fresh",
        "pins": [
            {"path": str(public_path), "sha256": p.sha(public_path)},
            {"path": str(manifest_path), "sha256": p.sha(manifest_path)},
        ],
        "retained_stop": {"path": str(old), "sha256": p.sha(old)},
        "executables": {
            "python": "/mock/python",
            "codex": "/mock/codex",
            "sandbox": "/mock/sandbox",
        },
        "selector_model": "explicit-test-model",
        "sealed_roots": [str(tmp_path)],
        "profile_contract": {"qualification": "synthetic source/argv only"},
    }
    root = tmp_path / "cycle"
    root.mkdir()
    pp = root / "PLAN.json"
    p.store(pp, value)
    grant = {
        "schema_version": "1",
        "approved_by": "human-owner",
        "plan_sha256": p.sha(pp),
        "cycle_id": value["cycle_id"],
        "source_tree_sha256": value["source_tree_sha256"],
        "retained_stop_sha256": p.sha(old),
        "provider": "exa_mcp",
        "cases": list(p.COHORT),
        "two_independent_experts": True,
        "selector_model": value["selector_model"],
        "expert_timing_policy": "expert_wall_only",
        "protective_wall_ms": 900000,
        "authorization_id": "synthetic-untrusted-test-only",
    }
    gp = tmp_path / "grant.json"
    p.store(gp, grant)
    return p.Gate(root, value), public, pp, gp


def plan(**changes):
    value = {
        "case_id": "synthetic",
        "provider": "exa_mcp",
        "log_prefix": "synthetic",
        "strict_budget": True,
        "max_calls": 60,
        "max_search_queries": 6,
        "max_ms": None,
        "timing_policy": "expert_wall_only",
        "protective_wall_ms": 900000,
        "wall_elapsed_before_ms": 0,
        "official_domains": ["example.edu"],
        "budget_origin": "independent_full_budget",
        "actions": [{"tool": "fetcher", "url": "https://example.edu/admissions"}],
    }
    value.update(changes)
    return value


async def get(url):
    return SimpleNamespace(
        url=url,
        final_url=url,
        ok=True,
        outcome="ok",
        status_code=200,
        content_type="text/plain",
        content=b"Synthetic admissions source information",
        error="",
        from_cache=False,
        fetch_tier="http",
        fetched_at=datetime.now(UTC),
    )


async def search(**_kwargs):
    return SimpleNamespace(results=[])


def run_tool(value, folder, **kwargs):
    return asyncio.run(
        c.execute(value, folder, get=get, search=search, provider_name="exa_mcp", **kwargs)
    )


def legacy_plan():
    value = plan(max_ms=120000)
    for key in ("timing_policy", "protective_wall_ms", "wall_elapsed_before_ms"):
        value.pop(key)
    return value


def capture_fixture(case, source_plan, manifest):
    basis = "capture_one entry; includes canary setup and all pipeline stages, cancellation cleanup, output/raw persistence and final checkpoint work; final metering-envelope persistence is audit only"
    budget = {
        "fetcher_calls": 0,
        "search_queries": 0,
        "elapsed_ms": 100,
        "blocked_search_queries": 0,
        "network_http_requests": 0,
        "max_fetcher_calls": 60,
        "max_search_queries": 6,
        "max_active_seconds": 120,
        "finalization_reserve_ms": 1000,
        "source_work_deadline_ms": 119000,
        "strict_expert_budget": True,
        "provider": "exa_mcp",
        "active_time_basis": basis,
        "provider_failure": None,
        "protocol_persistence_error": None,
        "stop_reason": None,
    }
    observed = {
        "case_id": case["case_id"],
        "programme_urls": [],
        "ranked_urls": None,
        "predictions": [],
        "telemetry": {
            "http_fetches": 0,
            "search_calls": 0,
            "browser_fetches": 0,
            "model_input_tokens": 0,
            "jev_input_tokens": 0,
            "latency_seconds": 0.1,
        },
        "page_outcomes": [],
        "error": None,
    }
    protocol = {
        "kind": "genuine-research-job",
        "started": True,
        "job_id": "synthetic-job",
        "run_id": "synthetic-run",
        "worker_id": "synthetic-worker",
        "sqlite_case_database": "synthetic.db",
        "claim_token": 1,
        "lease_token": 1,
        "native_enabled": False,
        "native_ledger": None,
        "observation_available": True,
        "heartbeat_tasks": 1,
        "heartbeat_done": [True],
        "heartbeat_cancelled": [True],
        "job_status": "succeeded",
        "worker_jobs_done": 1,
        "worker_jobs_failed": 0,
        "recorded_worker_id": None,
        "claim_records": [],
        "page_outcomes": [],
        "run_unknowns": [],
        "run_errors": [],
        "control_error": None,
        "control_type": None,
        "control_reason": None,
        "control_message": None,
    }
    raw = {
        "canary": {
            "institutions": [
                {"institution": case["university"], "domain": case["domain"], "programs": []}
            ],
            "totals": {},
            "batch": [case["university"]],
            "job_protocol": protocol,
            "run_error": "",
        },
        "claims": [],
        "protocol_observation_available": True,
    }
    config = {
        "harness_sha256": manifest["files"]["backend/evaluation/research/live.py"],
        "mapping_sha256": manifest["files"]["backend/evaluation/research/mapping.py"],
        "cohort": [case["case_id"]],
        "search_provider": "exa_mcp",
        "fenced_research_job": True,
        "university_read_budget": False,
        "research_job_protocol": "genuine-research-job",
        "strict_expert_budget": True,
        "shared_query_budget": True,
        "browser_enabled": False,
        "cold_fetcher_reads": True,
        "site_branding_identity": False,
        "subject_phrase_match": False,
        "programme_identity_before_funding": False,
        "seconds_per_case": 120,
        "child_active_seconds": 120,
        "max_fetcher_calls_per_case": 60,
        "max_search_queries_per_case": 6,
        "finalization_reserve_ms": 1000,
        "source_work_deadline_ms": 119000,
        "parent_process_reserve_seconds": 15,
        "parent_process_timeout_seconds": 135,
        "page_budget_counts": "every Fetcher.get invocation; cache hits consume a call",
        "batch_attempted_case_ids": [case["case_id"]],
        "batch_completed_case_ids": [case["case_id"]],
        "batch_remaining_case_ids": [],
        "batch_stop_reason": None,
        "active_time_basis": basis,
        "case_budgets": {
            case["case_id"]: {
                **budget,
                "parent_process_elapsed_seconds": 0.2,
                "process_error": None,
                "active_checkpoint_available": True,
            }
        },
    }
    capture = {
        "schema_version": "1",
        "pipeline_sha": source_plan["source_head"],
        "captured_at": datetime.now(UTC).isoformat(),
        "mode": "live",
        "config": config,
        "observations": [observed],
    }
    return capture, observed, budget, raw


def fake_process(gate, public, refusal=False):
    def run(argv, **_kwargs):
        case = next(
            row for row in public["cases"] if row["case_id"] == argv[argv.index("--case") + 1]
        )
        out = Path(argv[argv.index("--out") + 1]) / "synthetic-stamp"
        values = capture_fixture(case, gate.plan, p.read(Path(gate.plan["source_manifest"])))
        if refusal:
            values[2]["provider_failure"] = {"http_status": None, "failure_reason": "rate limited"}
        for name, value in zip(
            (
                "capture.json",
                case["case_id"] + ".json",
                case["case_id"] + ".budget.json",
                case["case_id"] + ".raw.json",
            ),
            values,
            strict=True,
        ):
            p.store(out / name, value)
        return subprocess.CompletedProcess(argv, 0, "synthetic process", "not actual Job")

    return run


class FakeIsolation:
    def __init__(self, workspace, _roots):
        self.workspace = workspace
        self.codex_executable = "/mock/codex"
        self.sandbox_executable = "/mock/sandbox"

    def prove_access(self, *_args):
        return {"synthetic": True, "not_actual_OS_admission": True}


def streams(answer):
    return "\n".join(
        json.dumps(row)
        for row in (
            {"type": "thread.started", "thread_id": "test"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {"id": "test", "type": "agent_message", "text": json.dumps(answer)},
            },
            {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
        )
    )


def adaptive_select(_isolation, _schema, output, prompt, **kwargs):
    assert kwargs["timeout_policy"] == "expert_wall_only" and 55 < kwargs["timeout_seconds"] <= 900
    assert "algorithm" not in prompt and "score" not in prompt
    if "acknowledgment" in prompt:
        answer = prompt["acknowledgment"]
        output.write_text(json.dumps(answer))
        return s.SelectorTurn(answer, 1000, streams(answer), "", 0, None)
    case = prompt["public_packet"]["cases"][0]
    observed = bool(prompt["source_views"])
    action = {
        "tool": "fetcher",
        "url": "https://" + case["domain"] + "/admissions",
        "query": None,
        "domains": [],
        "max_results": None,
        "source_step": None,
        "page": None,
        "offset": None,
        "section_offset": None,
        "link_offset": None,
    }
    answer = {
        "kind": "submit" if observed else "action",
        "observation": "Source read; leave applicant scope unknown."
        if observed
        else "Start independent official source read.",
        "journal_sha256": prompt["journal"]["journal_sha256"],
        "action": None if observed else action,
        "facts": [],
        "question_findings": [],
    }
    output.write_text(json.dumps(answer))
    return s.SelectorTurn(answer, 1000, streams(answer), "", 0, None)


async def native_tool(plan_path, raw, _cache):
    return await c.execute(p.read(plan_path), raw, get=get, search=search, provider_name="exa_mcp")


def test_legacy_default_raw_output_shape(tmp_path):
    result = run_tool(
        legacy_plan(), tmp_path, monotonic=lambda: 1.0, now=lambda: datetime(2026, 1, 1, tzinfo=UTC)
    )
    raw = p.read(tmp_path / result["actions"][0]["raw_log_path"])
    assert result["tool_policy"]["max_elapsed_ms"] == 120000 and c.STRICT_MAX_MS == 120000
    assert not {"timing_policy", "protective_wall_ms", "wall_elapsed_before_ms"} & result.keys()
    assert not {"timing_policy", "protective_wall_ms"} & result["tool_policy"].keys()
    assert not {"wall_elapsed_ms_before", "wall_elapsed_ms_cumulative"} & raw.keys()


def test_null_unknown_crossmode_and_types_fail_closed(tmp_path):
    for value in (
        legacy_plan() | {"max_ms": None},
        plan(timing_policy="unknown"),
        plan(protective_wall_ms=True),
        plan(budget_origin="baseline_intervention"),
        plan(exploration_mode="outside_policy"),
        plan(wall_elapsed_before_ms=True),
    ):
        with pytest.raises(ValueError):
            run_tool(value, tmp_path)
    assert not list(tmp_path.glob("*.json"))


def test_tool_over120_and_resume_original_wall(tmp_path):
    tick = [0.0]

    async def slow(url):
        tick[0] += 130.0
        return await get(url)

    first = asyncio.run(
        c.execute(
            plan(wall_elapsed_before_ms=200000),
            tmp_path,
            get=slow,
            search=search,
            provider_name="exa_mcp",
            monotonic=lambda: tick[0],
        )
    )
    assert (
        first["final"]["elapsed_ms"] >= 130000
        and first["actions"][0]["policy_mode"] == "same_policy"
    )
    second = run_tool(
        plan(wall_elapsed_before_ms=340000, resume_summary=first),
        tmp_path,
        monotonic=lambda: tick[0],
    )
    assert second["final"]["fetcher_calls"] == 2
    with pytest.raises(ValueError, match="wall cannot reset"):
        run_tool(plan(wall_elapsed_before_ms=1, resume_summary=second), tmp_path)
    contradictory = copy.deepcopy(second)
    contradictory["protective_wall_ms"] = 1
    with pytest.raises(ValueError, match="summary"):
        run_tool(plan(wall_elapsed_before_ms=350000, resume_summary=contradictory), tmp_path)


def test_read60_query6_no_extra_dispatch(tmp_path):
    gets = []
    queries = []

    async def getter(url):
        gets.append(url)
        return await get(url)

    async def searcher(**kwargs):
        queries.append(kwargs)
        return await search(**kwargs)

    value = plan(
        actions=[{"tool": "fetcher", "url": "https://example.edu/"}] * 61
        + [
            {
                "tool": "search_provider",
                "query": "admissions",
                "domains": ["example.edu"],
                "max_results": 1,
            }
        ]
        * 7
    )
    result = asyncio.run(
        c.execute(value, tmp_path, get=getter, search=searcher, provider_name="exa_mcp")
    )
    assert (
        len(gets) == 60
        and len(queries) == 6
        and result["final"]["fetcher_calls"] == 60
        and result["final"]["search_queries"] == 6
    )
    assert result["actions"][60]["executed"] is False and result["actions"][-1]["executed"] is False


def test_resume_legacy_to_wall_rejected(tmp_path):
    first = run_tool(legacy_plan(), tmp_path)
    with pytest.raises(ValueError, match="policy"):
        run_tool(plan(resume_summary=first), tmp_path)


def test_selector_wall_remaining_and_legacy55(tmp_path, monkeypatch):
    isolation = SimpleNamespace(workspace=tmp_path, command=lambda *_a, **_k: ["synthetic"])
    output = tmp_path / "answer.json"
    schema = tmp_path / "schema.json"
    schema.write_text("{}")
    answer = {"synthetic": "answer"}
    seen = []

    def owned(argv, **kwargs):
        seen.append(kwargs["timeout"])
        output.write_text(json.dumps(answer))
        return subprocess.CompletedProcess(argv, 0, streams(answer), "")

    monkeypatch.setattr(s, "run_owned_process", owned)
    turn = s.select(
        isolation, schema, output, {}, timeout_seconds=899, timeout_policy="expert_wall_only"
    )
    assert turn.answer == answer and seen == [899]
    with pytest.raises(ValueError):
        s.select(isolation, schema, output, {}, timeout_seconds=56)


def test_owned_process_timeout_kills_own_group(monkeypatch):
    calls = []

    class Process:
        pid = 424242
        returncode = None

        def communicate(self, **kwargs):
            if kwargs:
                raise subprocess.TimeoutExpired("synthetic", 1)
            return "drained stdout", "drained stderr"

        def wait(self):
            calls.append("wait")
            return -9

    monkeypatch.setattr(
        s.subprocess, "Popen", lambda *_a, **k: (calls.append(k["start_new_session"]) or Process())
    )
    monkeypatch.setattr(s.os, "killpg", lambda pid, signal: calls.append((pid, signal)))
    with pytest.raises(subprocess.TimeoutExpired) as stopped:
        s.run_owned_process(["synthetic"], cwd=Path("/synthetic"), timeout=1)
    assert stopped.value.stdout == "drained stdout" and stopped.value.stderr == "drained stderr"
    assert calls[0] is True and calls[1][0] == 424242 and calls[-1] == "wait"


def test_prepare_only_and_exact_owner_grant(tmp_path, monkeypatch):
    gate, _public, pp, gp = setup(tmp_path)
    assert p.authorize(pp, gp, p.sha(gp), gate.plan["retained_stop"]["sha256"]) == gate.plan
    bad = p.read(gp)
    bad["two_independent_experts"] = 1
    p.store(tmp_path / "bad.json", bad)
    with pytest.raises(ValueError):
        p.authorize(
            pp,
            tmp_path / "bad.json",
            p.sha(tmp_path / "bad.json"),
            gate.plan["retained_stop"]["sha256"],
        )
    monkeypatch.setattr(p, "execute", lambda *_a, **_k: pytest.fail("prepare must not execute"))
    with pytest.raises(SystemExit):
        p.main([])
    assert not (gate.root / "EXECUTION-START.original.json").exists()


def test_public_profile_scope_canonical_closed():
    assert len(p.public_cases(public_input())) == 10
    for target, value in (
        ("field", "data science"),
        ("population", "domestic"),
        ("intake", "fall 2026"),
        ("programme", "invented exact"),
    ):
        public = public_input()
        public["cases"][0]["request"][target] = value
        with pytest.raises(ValueError):
            p.public_cases(public)
    public = public_input()
    public["public_profile"]["education_system"] = "different"
    with pytest.raises(ValueError):
        p.public_cases(public)


def test_neutral_completed_and_honest_partial(tmp_path):
    gate, public, _pp, _gp = setup(tmp_path)
    values = capture_fixture(
        public["cases"][0], gate.plan, p.read(Path(gate.plan["source_manifest"]))
    )
    kwargs = {
        "plan": gate.plan,
        "source_manifest": p.read(Path(gate.plan["source_manifest"])),
        "identities": IdentityMap(version="synthetic", bindings=[]),
    }
    assert validate_algorithm("groningen", *values, **kwargs) == []
    from app.schemas.claim import Claim
    from evaluation.research.mapping import evidence_scope, normalize_subject_claims
    from evaluation.research.schema import Evidence, Prediction

    mapped = copy.deepcopy(values)
    native_namespace = IdentityMap(
        version="synthetic",
        bindings=[
            {
                "kind": "award",
                "source_url": "https://rug.nl/award",
                "subject": "Synthetic Merit Award",
                "key": "scholarships.synthetic_merit",
                "notes": "synthetic namespace, not correctness label",
            }
        ],
    )
    claim = Claim(
        claim_type="scholarship_exists",
        normalized_value="Synthetic Merit Award",
        subject_key="Synthetic Merit Award",
        source_url="https://rug.nl/award",
        original_text_excerpt="Synthetic Merit Award is listed.",
        official_domain=True,
        accessed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    payload = claim.model_dump(mode="json")
    record = {
        "id": "synthetic-claim",
        "claim_type": claim.claim_type.value,
        "source_url": claim.source_url,
        "accessed_at": "2026-01-01T00:00:00",
        "payload": payload,
    }
    mapped[3]["claims"] = [payload]
    mapped[3]["canary"]["job_protocol"]["claim_records"] = [record]
    predictions = []
    for key, value, programme, degree in normalize_subject_claims(
        record["claim_type"], payload, native_namespace
    ):
        predictions.append(
            Prediction(
                key=key,
                value=value,
                evidence=Evidence(
                    url=claim.source_url,
                    excerpt=claim.original_text_excerpt,
                    scope=evidence_scope(
                        payload,
                        university=public["cases"][0]["university"],
                        programme=programme,
                        degree=degree,
                    ),
                    accessed_on=claim.accessed_at.date(),
                    source_type="official",
                ),
            ).model_dump(mode="json")
        )
    mapped[1]["predictions"] = predictions
    assert (
        validate_algorithm("groningen", *mapped, **(kwargs | {"identities": native_namespace}))
        == []
    )
    assert validate_algorithm("groningen", *mapped, **kwargs)
    values[3]["canary"]["run_error"] = "CancelledError"
    values[3]["canary"]["job_protocol"].update(
        control_error="CancelledError",
        control_type="CancelledError",
        job_status="running",
        worker_jobs_done=0,
        recorded_worker_id="synthetic-worker",
    )
    values[1]["error"] = "CancelledError"
    assert validate_algorithm(
        "groningen", *values, require_complete_job=False, **kwargs
    ) == [] and validate_algorithm("groningen", *values, **kwargs)


def test_algorithm_exit0_refusal_global_stop(tmp_path):
    gate, public, pp, gp = setup(tmp_path)
    old = gate.plan["retained_stop"]["sha256"]
    result = p.execute(
        pp,
        gp,
        p.sha(gp),
        old,
        process_run=fake_process(gate, public, True),
        isolate=FakeIsolation,
        select=adaptive_select,
        run_tool=native_tool,
    )
    assert (
        result["status"] == "STOPPED_PARTIAL_UNSCORED"
        and result["attempted_algorithms"] == ["groningen"]
        and result["attempted_experts"] == []
    )
    assert (
        len(result["unrun_algorithms"]) == 9
        and len(result["unrun_experts"]) == 20
        and p.read(gate.stop)["diagnostic"]["provider_failure"]["http_status"] is None
    )
    assert p.sha(Path(gate.plan["retained_stop"]["path"])) == old


def test_algorithm_wrong_identity_stops_before_expert(tmp_path):
    gate, public, pp, gp = setup(tmp_path)
    run = fake_process(gate, public)

    def wrong(argv, **kwargs):
        completed = run(argv, **kwargs)
        out = Path(argv[argv.index("--out") + 1])
        raw = next(out.glob("*/groningen.raw.json"))
        value = p.read(raw)
        value["canary"]["institutions"][0]["domain"] = "other.edu"
        raw.write_text(json.dumps(value))
        return completed

    result = p.execute(
        pp,
        gp,
        p.sha(gp),
        gate.plan["retained_stop"]["sha256"],
        process_run=wrong,
        isolate=FakeIsolation,
        select=adaptive_select,
        run_tool=native_tool,
    )
    assert result["attempted_experts"] == [] and result["error_type"] == "Stopped"


def test_isolation_failure_partial_receipt_zero_dispatch(tmp_path):
    gate, public, _pp, _gp = setup(tmp_path)

    class Failed(FakeIsolation):
        def prove_access(self, *_a):
            raise RuntimeError("synthetic unavailable")

    with pytest.raises(RuntimeError):
        asyncio.run(
            p.collect_expert(
                gate,
                public,
                public["cases"][0],
                "A",
                isolate=Failed,
                select=lambda *_a, **_k: pytest.fail("no model"),
                run_tool=native_tool,
            )
        )
    receipt = p.read(gate.root / "private/experts/A/groningen/receipt.json")
    assert (
        receipt["complete_eligible"] is False
        and receipt["attempted_model_turns"] == receipt["attempted_source_actions"] == 0
    )


def test_complete_adaptive10_plus20_not_runtime_admitted(tmp_path):
    gate, public, pp, gp = setup(tmp_path)
    result = p.execute(
        pp,
        gp,
        p.sha(gp),
        gate.plan["retained_stop"]["sha256"],
        process_run=fake_process(gate, public),
        isolate=FakeIsolation,
        select=adaptive_select,
        run_tool=native_tool,
    )
    assert (
        result["status"] == "COLLECTION_SEALED_UNREVIEWED"
        and len(result["algorithms"]) == 10
        and len(result["experts"]) == 20
        and result["runtime_mode"] == "offline_injected"
        and result["all_expert_complete_eligible"] is False
    )
    assert all(
        row["recorded_action_count"] == row["processed_through_action_count"] == 1
        and row["complete_eligible"] is False
        for row in result["experts"]
    )
    assert (
        (gate.root / "SEALED-MANIFEST.json").is_file()
        and result["score"] is None
        and result["evaluator_access_authorized"] is False
    )
    assert len(list(gate.root.glob("private/experts/*/*/selector-*.prompt.json"))) == 40
    with pytest.raises(FileExistsError):
        p.execute(
            pp,
            gp,
            p.sha(gp),
            gate.plan["retained_stop"]["sha256"],
            process_run=fake_process(gate, public),
        )


def test_zero_source_submit_partial_not_unrun(tmp_path):
    gate, public, _pp, _gp = setup(tmp_path)

    def submit(isolation, schema, output, prompt, **kwargs):
        prompt = copy.deepcopy(prompt)
        prompt["source_views"] = [{"synthetic": True}]
        return adaptive_select(isolation, schema, output, prompt, **kwargs)

    receipt = asyncio.run(
        p.collect_expert(
            gate,
            public,
            public["cases"][0],
            "A",
            isolate=FakeIsolation,
            select=submit,
            run_tool=native_tool,
        )
    )
    assert (
        receipt["status"] == "partial_no_source_actions"
        and receipt["complete_eligible"] is False
        and receipt["trace"] is None
    )


def test_failed_later_model_preserves_journal_and_raw(tmp_path):
    gate, public, _pp, _gp = setup(tmp_path)

    def failed(isolation, schema, output, prompt, **kwargs):
        if prompt["source_views"]:
            return s.SelectorTurn(
                None, 200, "original unfinished stream", "refusal", 1, "selector_process_failed"
            )
        return adaptive_select(isolation, schema, output, prompt, **kwargs)

    with pytest.raises(p.Stopped):
        asyncio.run(
            p.collect_expert(
                gate,
                public,
                public["cases"][0],
                "A",
                isolate=FakeIsolation,
                select=failed,
                run_tool=native_tool,
            )
        )
    root = gate.root / "private/experts/A/groningen"
    receipt = p.read(root / "receipt.json")
    assert (
        receipt["attempted_model_turns"] == 2
        and receipt["attempted_source_actions"] == 1
        and receipt["complete_eligible"] is False
    )
    assert (
        len(receipt["source_raw_files"]) == 1
        and p.read(root / "selector-0002.original.json")["stdout"] == "original unfinished stream"
        and receipt["last_accepted_journal"]["journal_sha256"] == AcceptedJournal.initial().sha256
    )


def test_protective_wall_includes_thinking_no_reset(tmp_path):
    gate, public, _pp, _gp = setup(tmp_path)
    tick = [0.0]
    calls = []

    def thinking(isolation, schema, output, prompt, **kwargs):
        calls.append(kwargs["timeout_seconds"])
        tick[0] += 901
        return adaptive_select(isolation, schema, output, prompt, **kwargs)

    receipt = asyncio.run(
        p.collect_expert(
            gate,
            public,
            public["cases"][0],
            "A",
            isolate=FakeIsolation,
            select=thinking,
            run_tool=native_tool,
            clock=lambda: tick[0],
        )
    )
    assert (
        len(calls) == 1
        and receipt["wall_elapsed_ms"] >= 900000
        and receipt["fetcher_calls"] == 0
        and receipt["status"] == "protective_wall_expired"
    )


def test_stale_delta_cannot_replace_latest_journal(tmp_path):
    gate, public, _pp, _gp = setup(tmp_path)

    def stale(isolation, schema, output, prompt, **kwargs):
        turn = adaptive_select(isolation, schema, output, prompt, **kwargs)
        if prompt["source_views"]:
            value = copy.deepcopy(turn.answer)
            value["journal_sha256"] = "f" * 64
            output.write_text(json.dumps(value))
            return s.SelectorTurn(value, 1, streams(value), "", 0, None)
        return turn

    with pytest.raises(ValueError, match="journal"):
        asyncio.run(
            p.collect_expert(
                gate,
                public,
                public["cases"][0],
                "A",
                isolate=FakeIsolation,
                select=stale,
                run_tool=native_tool,
            )
        )
    receipt = p.read(gate.root / "private/experts/A/groningen/receipt.json")
    assert receipt["processed_through_action_count"] == 0 and receipt["complete_eligible"] is False


def test_prepare_real_shaped_homepage_and_opaque_bindings(tmp_path, monkeypatch):
    import sys

    gate, public, _pp, _gp = setup(tmp_path)
    source = tmp_path / "prepared-source"
    backend = source / "backend"
    scripts = backend / "scripts"
    scripts.mkdir(parents=True)
    current_backend = Path(p.__file__).resolve().parents[2]
    (scripts / "canary_discovery.py").write_bytes(
        (current_backend / "scripts/canary_discovery.py").read_bytes()
    )
    bindings = backend / "evaluation/research/data/identity_bindings.reviewed.json"
    bindings.parent.mkdir(parents=True)
    bindings.write_bytes(
        (current_backend / "evaluation/research/data/identity_bindings.reviewed.json").read_bytes()
    )
    marker = backend / "evaluation/research/expert/controller.py"
    marker.parent.mkdir()
    marker.write_bytes(Path(c.__file__).read_bytes())
    monkeypatch.setattr(c, "__file__", str(marker))
    registry = backend / "app/adapters/discovery/institution_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            [
                {"name": row["university"], "homepage": "https://www." + row["domain"] + "/"}
                for row in public["cases"]
            ]
        )
    )
    binaries = tmp_path / "binaries"
    binaries.mkdir()
    for name in ("codex", "sandbox-exec"):
        (binaries / name).write_text("synthetic binary, never executed")
    monkeypatch.setattr(p.shutil, "which", lambda name: str(binaries / name))
    venv = backend / ".venv/bin"
    venv.mkdir(parents=True)
    executable = venv / "python"
    executable.symlink_to(Path(sys.executable))
    manifest = {
        "snapshot": str(source),
        "repository": str(source),
        "source_status": "",
        "source_head": "synthetic",
        "source_tree_sha256": "b" * 64,
        "files": {
            str(file.relative_to(source)): p.sha(file)
            for file in [registry, scripts / "canary_discovery.py", bindings]
        },
    }
    import hashlib

    manifest["source_tree_sha256"] = hashlib.sha256(
        json.dumps(manifest["files"], sort_keys=True).encode()
    ).hexdigest()
    mp = tmp_path / "prepare-manifest.json"
    p.store(mp, manifest)
    full = tmp_path / "synthetic-full.json"
    p.store(
        full,
        {
            "status": "passed",
            "suite": "full",
            "steps": [{"exit_code": 0} for _ in range(13)],
            "source": manifest,
        },
    )
    corrupt = copy.deepcopy(manifest)
    corrupt["files"].pop(next(iter(corrupt["files"])))
    corrupt_path = tmp_path / "omitted-manifest.json"
    p.store(corrupt_path, corrupt)
    with pytest.raises(ValueError, match="tree digest"):
        p.prepare(
            corrupt_path,
            Path(gate.plan["public_input"]),
            Path(gate.plan["retained_stop"]["path"]),
            tmp_path / "rejected",
            selector_model="test-model",
            sealed_roots=[tmp_path, source],
            full_receipt=full,
        )
    assert not (tmp_path / "rejected").exists()
    pp = p.prepare(
        mp,
        Path(gate.plan["public_input"]),
        Path(gate.plan["retained_stop"]["path"]),
        tmp_path / "prepared",
        selector_model="test-model",
        sealed_roots=[tmp_path, source],
        full_receipt=full,
    )
    prepared = p.read(pp)
    assert (
        len(prepared["registry_contract"]["resolved"]) == 10
        and prepared["status"] == "PREPARED_NOT_EXECUTED"
    )
    assert prepared["profile_contract"]["context"]["intake_year"] == 2027
    assert (
        str(Path.home() / "Documents/Codex") in prepared["sealed_roots"]
        and str(Path.home() / ".codex/sessions") in prepared["sealed_roots"]
    )
    assert not (pp.parent / "EXECUTION-START.original.json").exists()
    target = tmp_path / "other-python"
    target.write_text("never executed")
    executable.unlink()
    executable.symlink_to(target)
    with pytest.raises(ValueError, match="executable"):
        p.verify_binding(prepared)


def test_complete_citation_chain_and_mutation_closure(tmp_path):
    from evaluation.research.expert.models import (
        Action,
        ExpertTrace,
        _controller_budget,
        validate_trace,
    )

    gate, public, _pp, _gp = setup(tmp_path)

    def evidence(isolation, schema, output, prompt, **kwargs):
        turn = adaptive_select(isolation, schema, output, prompt, **kwargs)
        if prompt.get("source_views"):
            value = copy.deepcopy(turn.answer)
            scope = {key: None for key in p.REQUEST_FIELDS}
            scope["university"] = public["cases"][0]["university"]
            value["facts"] = [
                {
                    "id": "fact1",
                    "question": "OTHER",
                    "claim_key": "unmapped.admissions_info",
                    "value_json": '"Synthetic admissions source information"',
                    "source_step": 1,
                    "quotation": "Synthetic admissions source information",
                    "location": {
                        "kind": "text",
                        "block_id": None,
                        "section_path": [],
                        "page": None,
                    },
                    "scope": scope,
                }
            ]
            output.write_text(json.dumps(value))
            return s.SelectorTurn(value, 1, streams(value), "", 0, None)
        return turn

    receipt = asyncio.run(
        p.collect_expert(
            gate,
            public,
            public["cases"][0],
            "A",
            isolate=FakeIsolation,
            select=evidence,
            run_tool=native_tool,
        )
    )
    assert receipt["trace"]["proposals"] and receipt["complete_eligible"] is False
    p.verify_admitted_outputs(gate.root, [], [receipt])
    legacy = copy.deepcopy(receipt["trace"])
    legacy["max_elapsed_ms"] = 120000
    legacy.pop("timing_policy")
    legacy.pop("protective_wall_ms")
    native_legacy = ExpertTrace.model_validate(legacy).model_dump(mode="json")
    assert "timing_policy" not in native_legacy and "protective_wall_ms" not in native_legacy
    root = gate.root / "private/experts/A/groningen"
    earlier = root / "selector-0001.original.json"
    original = earlier.read_bytes()
    earlier.write_text("{}")
    with pytest.raises(ValueError, match="selector original changed"):
        p.verify_admitted_outputs(gate.root, [], [receipt])
    earlier.write_bytes(original)
    raw = next((root / "raw").glob("*.json"))
    before = raw.read_bytes()
    raw.write_text("{}")
    with pytest.raises(ValueError, match="expert raw changed"):
        p.verify_admitted_outputs(gate.root, [], [receipt])
    raw.write_bytes(before)
    p.verify_admitted_outputs(gate.root, [], [receipt])
    summary = p.read(root / "tool-0001.summary.json")
    second_summary = run_tool(
        plan(
            case_id="groningen",
            log_prefix="groningen",
            official_domains=["rug.nl"],
            wall_elapsed_before_ms=max(100, summary["final"]["wall_elapsed_ms"]),
            resume_summary=summary,
            actions=[{"tool": "fetcher", "url": "https://rug.nl/admissions"}],
        ),
        root / "raw",
    )
    row = second_summary["actions"][0]
    second = copy.deepcopy(receipt["trace"]["actions"][0])
    second.update(
        step=2,
        at=row["at"],
        observed_before="Read the source again.",
        observed_from_step=1,
        action="Read the source again.",
        raw_log_path=row["raw_log_path"],
        raw_log_sha256=row["raw_log_sha256"],
        request=row["request"],
        final_url=row["final_url"],
        elapsed_ms=row["elapsed_ms"],
        elapsed_ms_cumulative=row["elapsed_ms_cumulative"],
        fetcher_calls_cumulative=row["fetcher_calls_cumulative"],
        search_queries_cumulative=row["search_queries_cumulative"],
    )
    full_trace = copy.deepcopy(receipt["trace"])
    full_trace["actions"].append(second)
    full_trace["ended_at"] = datetime.now(UTC).isoformat()
    packet = p.read(root / "packet.original.json")
    validate_trace(full_trace, packet, logs_dir=root / "raw")
    raw_second = root / "raw" / row["raw_log_path"]
    value = p.read(raw_second)
    value["wall_elapsed_ms_before"] = 0
    raw_second.write_text(json.dumps(value))
    full_trace["actions"][1]["raw_log_sha256"] = p.sha(raw_second)
    with pytest.raises(ValueError, match="between actions"):
        validate_trace(full_trace, packet, logs_dir=root / "raw")
    with pytest.raises(ValueError, match="structured"):
        _controller_budget(
            ExpertTrace.model_validate(legacy),
            Action.model_validate(legacy["actions"][0]),
            {"tool_policy": ["malformed"]},
            "independent_full_budget",
        )
    second_case = public["cases"][1]

    def bad(isolation, schema, output, prompt, **kwargs):
        turn = evidence(isolation, schema, output, prompt, **kwargs)
        if prompt.get("source_views"):
            value = copy.deepcopy(turn.answer)
            value["facts"][0]["scope"]["university"] = second_case["university"]
            value["facts"][0]["quotation"] = "Not in saved source"
            output.write_text(json.dumps(value))
            return s.SelectorTurn(value, 1, streams(value), "", 0, None)
        return turn

    with pytest.raises(ValueError):
        asyncio.run(
            p.collect_expert(
                gate,
                public,
                second_case,
                "B",
                isolate=FakeIsolation,
                select=bad,
                run_tool=native_tool,
            )
        )
    failed = p.read(gate.root / "private/experts/B/delft/receipt.json")
    assert failed["complete_eligible"] is False and failed["last_accepted_journal"]["facts"] == []
