"""Fresh original-ten collection only. Prepare by default; no evaluator entry.

Every external dispatch is reserved and guarded. A retained prior STOP is never
cleared. Independent selectors receive only public requests and their own source
views, while algorithm outputs and other expert work remain OS sealed.
"""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from .expert import controller, selector
from .expert.blind_cli import Isolation
from .expert.citations import validate_fact_citations
from .expert.compact import expand_submission
from .expert.journal import AcceptedJournal, JOURNAL_INSTRUCTIONS
from .expert.models import Action, validate_trace, _source_read
from .expert.packet import digest
from .expert.representation import (
    journal_schema_for_case,
    parse_bound_journal_decision,
    representation_card,
    validate_award_subjects,
)
from .pilot_admission import validate_algorithm

COHORT = ("groningen", "delft", "aalto", "vienna", "warsaw", "ubc", "toronto", "hku", "ntu", "kaist")
PROVIDER = "exa_mcp"
WALL_MS = 900_000
REQUEST_FIELDS = ("university", "programme", "degree", "field", "intake", "population", "qualification", "academic_year")


def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Pinned artifact must be a regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    from .expert.compact import _load_json
    return _load_json(path.read_text(encoding="utf-8"))


def store(path: Path, value: Any) -> str:
    """Create one immutable original; collision or symlink is an admission failure."""
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    return hashlib.sha256(data).hexdigest()


def clean_env() -> dict[str, str]:
    # Normal existing Codex login remains usable; user configuration is ignored
    # by its command. No credential file or key value is read by this controller.
    names = ("HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")
    env = {key: os.environ[key] for key in names if key in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", UNIMATCH_DEMO_MODE="false", UNIMATCH_ENABLE_BROWSER_TIER="false", UNIMATCH_RESPECT_ROBOTS="true", UNIMATCH_SEARCH_PROVIDER=PROVIDER, UNIMATCH_FETCH_CONTACT="https://github.com/wpalish/ashyq-apply")
    return env


def verify_binding(plan: dict[str, Any]) -> None:
    if plan.get("provider") != PROVIDER or plan.get("cases") != list(COHORT):
        raise ValueError("Only original10 and pinned Exa MCP are admitted")
    for row in plan["pins"]:
        if sha(Path(row["path"])) != row["sha256"]:
            raise ValueError("Pinned source/executable/input changed")
    if sha(Path(plan["retained_stop"]["path"])) != plan["retained_stop"]["sha256"]:
        raise ValueError("Retained STOP changed")
    source = Path(plan["source_snapshot"])
    if (source / "backend/.env").exists():
        raise ValueError("Frozen source must not contain a .env")
    actual = Path(controller.__file__).resolve()
    if actual != source / "backend/evaluation/research/expert/controller.py":
        raise ValueError("Use the exact pinned source interpreter/modules")


def public_cases(value: Any) -> list[dict[str, Any]]:
    if type(value) is not dict or set(value) != {"schema_version", "public_profile", "cases"} or value["schema_version"] != "1":
        raise ValueError("Fresh public input needs only profile and original10 public cases")
    if type(value["public_profile"]) is not dict or set(value["public_profile"]) != {"education_system"}:
        raise ValueError("Public profile allowlist is education_system only")
    cases = value["cases"]
    if type(cases) is not list or [c.get("case_id") if type(c) is dict else None for c in cases] != list(COHORT):
        raise ValueError("Public case order must be exact original10")
    for case in cases:
        if set(case) != {"case_id", "university", "domain", "request"}:
            raise ValueError("Public case must contain only identity/request")
        if any(type(case[k]) is not str or not case[k].strip() for k in ("case_id", "university", "domain")):
            raise ValueError("Invalid public identity")
        domain = controller._domain(case["domain"])
        if domain != case["domain"] or controller.blocked("https://" + domain):
            raise ValueError("Official domain must be independently resolved")
        request = case["request"]
        if type(request) is not dict or set(request) != set(REQUEST_FIELDS):
            raise ValueError("Public request must declare all eight dimensions, no extra data")
        if request["university"] != case["university"] or request["degree"] != "bachelor" or request["field"] != "computer science" or request["intake"] != "fall 2027" or request["population"] != "international" or request["qualification"] != "KZ national secondary":
            raise ValueError("Public request differs from current canary profile")
        if any(v is not None and (type(v) is not str or not v.strip()) for v in request.values()):
            raise ValueError("Malformed public scope")
    return cases


def prepare(source_manifest: Path, public_input: Path, retained_stop: Path, out: Path, *, selector_model: str, sealed_roots: list[Path]) -> Path:
    """No process/model/provider dispatch, SQL, dataset or scorer reads."""
    if out.exists() or not selector_model.strip() or selector_model != selector_model.strip():
        raise ValueError("Fresh output directory and explicit selector model are required")
    manifest = read(source_manifest)
    public = read(public_input)
    public_cases(public)
    source = Path(manifest["snapshot"]).resolve()
    if manifest.get("source_status") != "" or not manifest.get("source_head") or not manifest.get("source_tree_sha256"):
        raise ValueError("Source manifest must bind clean tested source")
    pins = []
    # Opaque executable-source hashes only. No gold/answer JSON is opened here.
    for relative, expected in manifest["files"].items():
        if relative.startswith(("backend/app/", "backend/evaluation/", "backend/scripts/", "backend/tests/", "frontend/")) and Path(relative).suffix in {".py", ".ts", ".tsx", ".js", ".css"}:
            path = source / relative
            if sha(path) != expected:
                raise ValueError("Frozen executable source hash mismatch")
            pins.append({"path": str(path), "sha256": expected})
    bindings = source / "backend/evaluation/research/data/identity_bindings.reviewed.json"
    # Explicit identity bindings are public output identities, not expected facts.
    if sha(bindings) != manifest["files"][str(bindings.relative_to(source))]:
        raise ValueError("Identity binding artifact changed")
    pins.extend({"path": str(p), "sha256": sha(p)} for p in (source_manifest, public_input, bindings))
    executables = {"python": source / "backend/.venv/bin/python", "codex": Path(shutil.which("codex") or ""), "sandbox": Path(shutil.which("sandbox-exec") or "")}
    if any(not p.is_file() for p in executables.values()):
        raise ValueError("Existing pinned Python/Codex/sandbox runtime required; no installs")
    for name, path in executables.items():
        resolved = path.resolve()
        pins.append({"path": str(resolved), "sha256": sha(resolved)})
        executables[name] = str(path)
    protected = tuple(p.resolve() for p in sealed_roots)
    if not protected or not all(any(p.is_relative_to(root) for root in protected) for p in (source, Path(manifest["repository"]).resolve(), out.resolve())):
        raise ValueError("Explicit sealed roots must cover source/repository/output history; do not probe answers")
    plan = {"schema_version": "1", "cycle_id": uuid.uuid4().hex, "status": "PREPARED_NOT_EXECUTED", "source_head": manifest["source_head"], "source_tree_sha256": manifest["source_tree_sha256"], "source_manifest": str(source_manifest.resolve()), "source_snapshot": str(source), "public_input": str(public_input.resolve()), "provider": PROVIDER, "selector_model": selector_model, "cases": list(COHORT), "pins": pins, "executables": executables, "retained_stop": {"path": str(retained_stop.resolve()), "sha256": sha(retained_stop)}, "algorithm_policy": {"reads": 60, "queries": 6, "full_ms": 120000, "source_ms": 119000, "fenced_job": True, "native_enabled": False}, "expert_policy": {"reads": 60, "queries": 6, "timing_policy": "expert_wall_only", "active_cap_ms": None, "protective_wall_ms": WALL_MS, "thinking_in_tool_ms": False}, "sealed_roots": [*[str(p) for p in protected], str(Path.home() / ".codex/memories"), str(Path.home() / ".codex/skills")], "no_evaluator_dispatch": True}
    verify_binding(plan)
    out.mkdir(parents=True)
    store(out / "PLAN.json", plan)
    store(out / "public-input.original.json", public)
    return out / "PLAN.json"


class Stopped(RuntimeError):
    pass


class Gate:
    def __init__(self, root: Path, plan: dict[str, Any]):
        self.root, self.plan = root, plan
        self.stop = root / "FIRST-REFUSAL.json"
        self.serial = 0
        self.events = []

    def check(self) -> None:
        verify_binding(self.plan)
        if self.stop.exists():
            raise Stopped("Fresh cycle stopped; no additional dispatch")

    def reserve(self, kind: str, case: str, expert: str | None, details: dict[str, Any]) -> Path:
        self.check()
        self.serial += 1
        path = self.root / "dispatch" / f"{self.serial:04d}.reserved.json"
        store(path, {"cycle_id": self.plan["cycle_id"], "kind": kind, "case_id": case, "expert": expert, "time": datetime.now(UTC).isoformat(), "details": details, "outcome": "reserved-before-dispatch"})
        self.events.append(str(path.relative_to(self.root)))
        self.check()
        return path

    def refuse(self, kind: str, case: str, *, raw_paths: list[Path], diagnostic: dict[str, Any]) -> None:
        value = {"cycle_id": self.plan["cycle_id"], "case_id": case, "kind": kind, "time": datetime.now(UTC).isoformat(), "diagnostic": diagnostic, "original_raw": [{"path": str(p.relative_to(self.root)), "sha256": sha(p)} for p in raw_paths], "retained_stop": self.plan["retained_stop"]}
        try:
            store(self.stop, value)
        except FileExistsError:
            pass
        raise Stopped("First failure retained; all remaining actions unrun")


def algorithm_command(plan: dict[str, Any], case: str, out: Path, stop: Path) -> list[str]:
    return [plan["executables"]["python"], "-m", "evaluation.research.live", "--live", "--case", case, "--search-provider", PROVIDER, "--strict-expert-budget", "--shared-query-budget", "--fenced-research-job", "--no-university-read-budget", "--seconds-per-case", "120", "--max-pages", "60", "--finalization-reserve-ms", "1000", "--stop-file", str(stop), "--out", str(out)]


def collect_algorithm(gate: Gate, case: dict[str, Any], process_run=selector.run_owned_process) -> dict[str, Any]:
    case_id = case["case_id"]
    out = gate.root / "private/algorithm" / case_id
    command = algorithm_command(gate.plan, case_id, out, gate.stop)
    gate.reserve("algorithm", case_id, None, {"argv": command, "cwd": str(Path(gate.plan["source_snapshot"]) / "backend")})
    try:
        completed = process_run(command, cwd=Path(gate.plan["source_snapshot"]) / "backend", env=clean_env(), capture_output=True, timeout=135, check=False)
        original = {"stdout": completed.stdout.decode(errors="replace") if isinstance(completed.stdout, bytes) else completed.stdout, "stderr": completed.stderr.decode(errors="replace") if isinstance(completed.stderr, bytes) else completed.stderr, "returncode": completed.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        original = {"error_type": type(exc).__name__, "stdout": str(getattr(exc, "stdout", "") or ""), "stderr": str(getattr(exc, "stderr", "") or "")}
    raw_process = out / "process.original.json"
    store(raw_process, original)
    # The harness may write the shared stop itself. Preserve it and fail closed.
    if gate.stop.exists():
        raise Stopped("Algorithm recorded shared first refusal")
    captures = list(out.glob("*/capture.json"))
    if original.get("returncode") != 0 or len(captures) != 1:
        gate.refuse("algorithm_protocol_failure", case_id, raw_paths=[raw_process], diagnostic={"reason": "missing_or_failed_capture"})
    folder = captures[0].parent
    try:
        capture, observed, budget, raw = (read(p) for p in (captures[0], folder / f"{case_id}.json", folder / f"{case_id}.budget.json", folder / f"{case_id}.raw.json"))
        if budget.get("provider_failure") is not None or budget.get("stop_reason") in {"http_429", "provider_failure", "external_provider_failure"}:
            gate.refuse("provider_failure", case_id, raw_paths=[raw_process, folder / f"{case_id}.budget.json", folder / f"{case_id}.raw.json"], diagnostic={"provider_failure": budget.get("provider_failure"), "stop_reason": budget.get("stop_reason")})
        errors = validate_algorithm(case_id, capture, observed, budget, raw, plan=gate.plan, source_manifest=read(Path(gate.plan["source_manifest"])))
        if raw["canary"]["institutions"][0]["institution"] != case["university"] or raw["canary"]["institutions"][0]["domain"] != case["domain"]:
            errors.append("Public identity differs from actual native institution")
    except Stopped:
        raise
    except Exception as exc:
        errors = ["neutral admission " + type(exc).__name__]
    if errors:
        gate.refuse("algorithm_protocol_failure", case_id, raw_paths=[raw_process, captures[0]], diagnostic={"errors": errors})
    protocol = raw["canary"]["job_protocol"]
    result = {"case_id": case_id, "terminal_kind": "completed_job" if protocol["job_status"] == "succeeded" and observed["error"] is None and budget["stop_reason"] is None else "bounded_partial", "actual_job_status": protocol["job_status"], "capture_path": str(captures[0]), "capture_sha256": sha(captures[0]), "programme_count": len(observed["programme_urls"]), "unknowns_not_absence": True}
    store(out / "admission.json", result)
    return result


def expert_packet(plan: dict[str, Any], public: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    # This packet deliberately includes no algorithm outputs or hidden answers.
    return {"schema_version": "1", "comparison_mode": "independent_full_budget", "baseline_pipeline_sha": plan["source_head"], "baseline_budget": {"max_fetcher_calls": 60, "max_search_queries": 6, "max_elapsed_ms": None, "browser_enabled": False, "timing_policy": "expert_wall_only", "protective_wall_ms": WALL_MS}, "public_profile": public["public_profile"], "cases": [case]}


def selected_contexts(submission, actions: list[Action], raw_dir: Path) -> dict[str, str]:
    contexts = {}
    for fact in submission.facts:
        action = actions[fact.source_step - 1]
        source = _source_read(read(raw_dir / action.raw_log_path))
        if source is None:
            raise ValueError("Fact has no readable source")
        location = fact.location
        if location.kind == "pdf":
            context = source.pdf_pages[location.page - 1]
        elif source.document is not None:
            if location.kind == "document_ir":
                blocks = [b for b in source.document.blocks if b.id == location.block_id and list(b.section_path) == location.section_path]
            else:
                from app.domain.claim_verifier import is_verbatim_excerpt
                blocks = [b for b in source.document.blocks if is_verbatim_excerpt(fact.quotation, b.text)]
            if len(blocks) != 1:
                raise ValueError("Fact context is ambiguous")
            block = blocks[0]
            context = "\n".join([*block.section_path, block.text, *getattr(block, "headers", [])])
        else:
            context = source.text
        contexts[fact.id] = context
    return contexts


def neutral_checkpoint(journal, decision, actions, packet, raw_dir, started, ended):
    candidate = journal.candidate(decision, actions, ended_at=ended, case_id=packet["cases"][0]["case_id"])
    submission = candidate.as_submission(decision.observation)
    expanded = expand_submission(submission, actions, ended_at=ended, case_id=packet["cases"][0]["case_id"])
    if not actions:
        if submission.facts:
            raise ValueError("No-action checkpoint cannot contain evidence")
        return candidate, None, []
    trace = {"schema_version": "1", "case_id": packet["cases"][0]["case_id"], "packet_sha256": digest(packet), "baseline_pipeline_sha": packet["baseline_pipeline_sha"], "max_fetcher_calls": 60, "max_search_queries": 6, "max_elapsed_ms": None, "timing_policy": "expert_wall_only", "protective_wall_ms": WALL_MS, "initial_fetcher_calls": 0, "initial_search_queries": 0, "initial_elapsed_ms": 0, "started_at": started.isoformat(), "ended_at": ended.isoformat(), "actions": [a.model_dump(mode="json") for a in actions], **expanded, "review_status": "unreviewed"}
    validate_trace(trace, packet, logs_dir=raw_dir)
    citations = validate_fact_citations(submission, actions, logs_dir=raw_dir, packet=packet)
    awards = validate_award_subjects(submission, contexts_by_fact_id=selected_contexts(submission, actions, raw_dir))
    return candidate, trace, [{"citations": citations, "awards": awards}]


async def collect_expert(gate: Gate, public: dict[str, Any], case: dict[str, Any], expert: str, *, isolate=Isolation.local, select=selector.select, run_tool=controller.run, clock=time.monotonic) -> dict[str, Any]:
    case_id = case["case_id"]
    root = gate.root / "private/experts" / expert / case_id
    root.mkdir(parents=True)
    began, started = clock(), datetime.now(UTC)
    wall_elapsed = lambda: max(0, math.ceil((clock() - began) * 1000))
    packet = expert_packet(gate.plan, public, case)
    store(root / "packet.original.json", packet)
    journal, actions, summary = AcceptedJournal.initial(), [], None
    thinking_ms = 0
    status = "partial_no_submission"
    processed = 0
    accepted_trace = None
    turn_index = 0
    # Public workspace is outside every sealed private/source/repository root.
    with tempfile.TemporaryDirectory(prefix="ashyq-blind-expert-") as temporary:
        workspace = Path(temporary)
        allowed = workspace / "allowed.sentinel"
        allowed.write_text("public isolation sentinel")
        sealed = root / "sealed.sentinel"
        sealed.write_text("private isolation sentinel")
        isolation = isolate(workspace, [Path(p) for p in gate.plan["sealed_roots"]] + [gate.root, Path(controller.__file__).resolve().parents[4]])
        if isolation.codex_executable != gate.plan["executables"]["codex"] or isolation.sandbox_executable != gate.plan["executables"]["sandbox"]:
            raise ValueError("Isolation executables differ from pinned runtime")
        gate.reserve("isolation_probe", case_id, expert, {"workspace": str(workspace)})
        proof = isolation.prove_access(allowed, sealed)
        store(root / "isolation.original.json", proof)
        outputs = []
        while wall_elapsed() < WALL_MS:
            gate.check()
            turn_index += 1
            schema_path = workspace / f"schema-{turn_index:04d}.json"
            schema_path.write_text(json.dumps(journal_schema_for_case(journal_sha256=journal.sha256, canonical_university=case["university"])))
            output = workspace / f"answer-{turn_index:04d}.json"
            remaining = (WALL_MS - wall_elapsed()) / 1000
            prompt = {"public_packet": packet, "journal": journal.snapshot(), "source_views": outputs, "instructions": JOURNAL_INSTRUCTIONS + representation_card(case["university"]), "remaining_wall_ms": max(0, WALL_MS - wall_elapsed()), "tool_counters": summary["final"] if summary else {"fetcher_calls": 0, "search_queries": 0, "elapsed_ms": 0}, "timing": "Thinking is recorded separately and has no active120s ceiling; all work spends one original900s protective wall."}
            gate.reserve("model_selector", case_id, expert, {"schema_sha256": sha(schema_path), "timeout_seconds": remaining, "model": gate.plan["selector_model"]})
            remaining = (WALL_MS - wall_elapsed()) / 1000
            if remaining <= 0:
                status = "protective_wall_expired"
                break
            prompt_path = root / f"selector-{turn_index:04d}.prompt.json"
            store(prompt_path, prompt)
            turn = select(isolation, schema_path, output, prompt, timeout_seconds=remaining, model=gate.plan["selector_model"], timeout_policy="expert_wall_only")
            thinking_ms += turn.elapsed_ms
            original = root / f"selector-{turn_index:04d}.original.json"
            store(original, {"stdout": turn.stdout, "stderr": turn.stderr, "returncode": turn.returncode, "error_kind": turn.error_kind, "answer_file": output.read_text() if output.is_file() else None, "elapsed_ms": turn.elapsed_ms, "wall_elapsed_ms": wall_elapsed()})
            if turn.error_kind is not None or turn.answer is None:
                gate.refuse("model_or_protocol_failure", case_id, raw_paths=[original], diagnostic={"error_kind": turn.error_kind, "returncode": turn.returncode, "expert": expert})
            if wall_elapsed() >= WALL_MS:
                status = "protective_wall_expired"
                break
            decision = parse_bound_journal_decision(turn.answer, journal_sha256=journal.sha256, canonical_university=case["university"])
            candidate, trace, proof = neutral_checkpoint(journal, decision, actions, packet, root / "raw", started, datetime.now(UTC))
            # Persist one full accepted checkpoint event before replacing memory.
            store(root / f"journal-{turn_index:04d}.accepted.json", {"snapshot": candidate.snapshot(), "prior_snapshot": journal.snapshot(), "decision": turn.answer, "trace": trace, "proof": proof, "processed_through_action_count": len(actions), "selector_original_sha256": sha(original), "wall_elapsed_ms": wall_elapsed(), "thinking_ms": thinking_ms})
            journal, accepted_trace, processed = candidate, trace, len(actions)
            if decision.kind == "submit":
                from .expert.blind_cli import selector_answer
                replay = read(original)
                if replay["returncode"] != 0 or replay["error_kind"] is not None or selector_answer(replay["stdout"], replay["answer_file"]) != turn.answer:
                    raise ValueError("Final original streams/output do not prove a completed submit")
                status = "submitted_unreviewed" if actions else "partial_no_source_actions"
                break
            if decision.kind == "record":
                continue
            action = decision.action
            if action.tool == "view":
                recorded = actions[action.source_step - 1]
                raw_record = read(root / "raw" / recorded.raw_log_path)
                outputs.append({"source_step": recorded.step, "view": controller.expert_view(raw_record, **{k: v for k, v in action.controller_request().items() if k not in {"tool", "source_step"}})})
                continue
            gate.reserve("expert_tool", case_id, expert, {"request": action.controller_request(), "wall_remaining_ms": WALL_MS - wall_elapsed()})
            if wall_elapsed() >= WALL_MS:
                status = "protective_wall_expired"
                break
            action_plan = {"case_id": case_id, "provider": PROVIDER, "log_prefix": case_id, "strict_budget": True, "max_calls": 60, "max_search_queries": 6, "max_ms": None, "timing_policy": "expert_wall_only", "protective_wall_ms": WALL_MS, "budget_origin": "independent_full_budget", "official_domains": [case["domain"]], "actions": [action.controller_request()]}
            if summary is not None:
                action_plan["resume_summary"] = summary
            plan_path = root / f"tool-{len(actions)+1:04d}.plan.json"
            store(plan_path, action_plan)
            try:
                from app.adapters.search import exa_mcp
                # The whole route is sequential. Every provider failure escapes
                # after its first attempt; no restoration races/alternate provider.
                with patch.object(exa_mcp, "RATE_LIMIT_RETRY", False), patch.object(exa_mcp, "RETRY_429_ONCE", False):
                    async with asyncio.timeout(max(0.001, (WALL_MS - wall_elapsed()) / 1000)):
                        summary = await run_tool(plan_path, root / "raw", root / "cache")
            except TimeoutError:
                status = "protective_wall_expired_pending_tool"
                break
            except Exception as exc:
                original_error = root / f"tool-{len(actions)+1:04d}.setup-error.json"
                store(original_error, {"type": type(exc).__name__, "wall_elapsed_ms": wall_elapsed()})
                gate.refuse("tool_setup_failure", case_id, raw_paths=[original_error], diagnostic={"type": type(exc).__name__})
            store(root / f"tool-{len(actions)+1:04d}.summary.json", summary)
            row = summary["actions"][-1]
            raw_path = root / "raw" / row["raw_log_path"]
            raw = read(raw_path)
            if action.tool == "search_provider" and (raw.get("executed") is True and raw.get("outcome_status") != "success" or raw.get("outcome") == "search_provider_not_configured"):
                gate.refuse("provider_failure", case_id, raw_paths=[raw_path], diagnostic={"http_status": (raw.get("response") or {}).get("http_status"), "failure_reason": (raw.get("response") or {}).get("failure_reason")})
            new_action = Action(step=len(actions)+1, at=row["at"], observed_before=decision.observation, observed_from_step=len(actions) or None, tool=row["tool"], action=decision.observation, outcome_status=row["outcome_status"], outcome=row["outcome"], stage="candidate_generation" if action.tool == "search_provider" else "page_understanding", policy_mode=row["policy_mode"], url=action.url, final_url=row["final_url"], request=row["request"], raw_log_path=row["raw_log_path"], raw_log_sha256=row["raw_log_sha256"], elapsed_ms=row["elapsed_ms"], elapsed_ms_cumulative=row["elapsed_ms_cumulative"], fetcher_calls_cumulative=row["fetcher_calls_cumulative"], search_queries_cumulative=row["search_queries_cumulative"])
            actions.append(new_action)
            outputs.append({"source_step": new_action.step, "view": controller.expert_view(raw)})
        elapsed = wall_elapsed()
    receipt = {"case_id": case_id, "expert": expert, "status": status, "complete_eligible": status == "submitted_unreviewed" and processed == len(actions) and elapsed <= WALL_MS, "processed_through_action_count": processed, "recorded_action_count": len(actions), "protective_wall_ms": WALL_MS, "wall_elapsed_ms": elapsed, "thinking_ms": thinking_ms, "tool_ms": summary["final"]["elapsed_ms"] if summary else 0, "fetcher_calls": summary["final"]["fetcher_calls"] if summary else 0, "search_queries": summary["final"]["search_queries"] if summary else 0, "journal_sha256": journal.sha256, "trace": accepted_trace, "review_status": "unreviewed", "unknown_not_absence": True}
    store(root / "receipt.json", receipt)
    return receipt


def authorize(plan_path: Path, grant_path: Path, grant_sha256: str, retained_sha256: str) -> dict[str, Any]:
    plan, grant = read(plan_path), read(grant_path)
    verify_binding(plan)
    if sha(grant_path) != grant_sha256 or retained_sha256 != plan["retained_stop"]["sha256"]:
        raise ValueError("Explicit grant/retained STOP acknowledgement mismatch")
    expected = {"schema_version": "1", "approved_by": "human-owner", "plan_sha256": sha(plan_path), "cycle_id": plan["cycle_id"], "source_tree_sha256": plan["source_tree_sha256"], "retained_stop_sha256": retained_sha256, "provider": PROVIDER, "cases": list(COHORT), "two_independent_experts": True, "selector_model": plan["selector_model"], "expert_timing_policy": "expert_wall_only", "protective_wall_ms": WALL_MS}
    if type(grant) is not dict or set(grant) != set(expected) | {"authorization_id"} or any(type(grant.get(k)) is not type(v) or grant[k] != v for k,v in expected.items()) or type(grant.get("authorization_id")) is not str or not grant["authorization_id"].strip():
        raise ValueError("Trusted owner grant must bind this exact fresh cycle")
    # This validates a trusted owner-supplied artifact, not human identity or
    # authority cryptographically. Never create the grant from model text.
    return plan


def execute(plan_path: Path, grant_path: Path, grant_sha256: str, retained_sha256: str, *, process_run=selector.run_owned_process, isolate=Isolation.local, select=selector.select, run_tool=controller.run) -> dict[str, Any]:
    root = plan_path.parent
    plan = authorize(plan_path, grant_path, grant_sha256, retained_sha256)
    public = read(Path(plan["public_input"]))
    cases = public_cases(public)
    # Exclusive fresh lock plus immutable START reject retry/resume/duplicate.
    with (root / ".execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        store(root / "EXECUTION-START.original.json", {"plan_sha256": sha(plan_path), "grant_sha256": grant_sha256, "time": datetime.now(UTC).isoformat(), "status": "STARTED_UNSCORED"})
        gate = Gate(root, plan)
        algorithms, experts, error = [], [], None
        attempted_algorithms, attempted_experts = [], []
        try:
            for case in cases:
                attempted_algorithms.append(case["case_id"])
                algorithms.append(collect_algorithm(gate, case, process_run))
            # These are two isolated independent experts per public request.
            # Algorithm raw outputs never enter their workspace or prompt.
            with patch.dict(os.environ, clean_env(), clear=True):
                for case in cases:
                    for expert in ("A", "B"):
                        attempted_experts.append((case["case_id"],expert))
                        experts.append(asyncio.run(collect_expert(gate, public, case, expert, isolate=isolate, select=select, run_tool=run_tool)))
        except Exception as exc:
            error = type(exc).__name__
            if not gate.stop.exists():
                try:
                    gate.refuse("protocol_failure", cases[min(len(algorithms),9)]["case_id"], raw_paths=[root / "EXECUTION-START.original.json"], diagnostic={"type": error})
                except Stopped:
                    pass
        result = {"cycle_id": plan["cycle_id"], "status": "COLLECTION_SEALED_UNREVIEWED" if error is None and len(algorithms)==10 and len(experts)==20 else "STOPPED_PARTIAL_UNSCORED", "error_type": error, "algorithms": algorithms, "experts": experts, "attempted_algorithms": attempted_algorithms, "attempted_experts": [{"case_id": c,"expert": e} for c,e in attempted_experts], "unrun_algorithms": [c for c in COHORT if c not in attempted_algorithms], "unrun_experts": [{"case_id": c,"expert": e} for c in COHORT for e in ("A","B") if (c,e) not in attempted_experts], "evaluator_access_authorized": False, "score": None}
        store(root / "COLLECTION-RECEIPT.json", result)
        originals = {str(p.relative_to(root)): {"sha256":sha(p),"bytes":p.stat().st_size} for p in root.rglob("*") if p.is_file() and not p.is_symlink() and p.name != '.execution.lock'}
        store(root / "SEALED-MANIFEST.json", {"files": originals, "status": result['status'], "copies_are_not_experiments": True})
        gate.check() if error is None else None
        return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest',type=Path)
    parser.add_argument('--public-input',type=Path)
    parser.add_argument('--retained-stop',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--selector-model')
    parser.add_argument('--sealed-root',type=Path,action='append')
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--grant',type=Path)
    parser.add_argument('--grant-sha256')
    parser.add_argument('--resume-stop-sha256')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    if not args.execute:
        if not all((args.source_manifest,args.public_input,args.retained_stop,args.out,args.selector_model,args.sealed_root)):
            parser.error('Prepare requires current tested manifest/public input/old STOP/fresh out/model; no dispatch')
        print(prepare(args.source_manifest,args.public_input,args.retained_stop,args.out,selector_model=args.selector_model,sealed_roots=args.sealed_root))
        return
    if not all((args.plan,args.grant,args.grant_sha256,args.resume_stop_sha256)):
        parser.error('Execute requires trusted explicit bound grant and oldSTOP SHA acknowledgement')
    print(json.dumps(execute(args.plan,args.grant,args.grant_sha256,args.resume_stop_sha256)))


if __name__=='__main__':
    main()
