"""Neutral native capture admission; no gold, scorer or network.

Port of reviewed4fa validator. All original assertions retained.
"""

import math
from datetime import UTC, datetime


def validate_algorithm(
    case,
    capture,
    observed,
    budget,
    raw,
    *,
    plan,
    source_manifest,
    identities,
    require_complete_job=True,
):
    """Admit evidence, never infer a completed Job from a terminal capture.

    Raw JSON types are checked before equality or schema coercion. The optional
    partial lane retains an honest bounded stop without calling it Job success.
    """
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def number(value):
        if type(value) not in (int, float):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False

    def text(value):
        return type(value) is str and bool(value.strip())

    def objects(value):
        return type(value) is list and all(type(row) is dict for row in value)

    for name, value in [
        ("capture", capture),
        ("observation", observed),
        ("budget", budget),
        ("raw", raw),
    ]:
        require(type(value) is dict, "invalid object " + name)
    if errors:
        return errors
    config = capture.get("config", {})
    canary = raw.get("canary")
    require(type(config) is dict, "invalid capture config")
    require(type(canary) is dict, "invalid raw canary")
    telemetry = observed.get("telemetry")
    require(type(telemetry) is dict, "invalid telemetry")
    require(objects(capture.get("observations")), "invalid observation rows")
    require(objects(raw.get("claims")), "invalid raw claims")
    if errors:
        return errors
    protocol = canary.get("job_protocol")
    case_budgets = config.get("case_budgets")
    require(type(protocol) is dict, "invalid Job protocol")
    require(type(case_budgets) is dict, "invalid capture budgets")
    require(
        objects(canary.get("institutions")) and len(canary.get("institutions", [])) == 1,
        "missing/invalid institution",
    )
    require(type(canary.get("totals")) is dict, "missing/invalid raw totals")
    require(
        type(canary.get("batch")) is list
        and bool(canary.get("batch"))
        and all(text(row) for row in canary.get("batch", [])),
        "missing/invalid raw batch",
    )
    if errors:
        return errors
    institution = canary["institutions"][0]
    require(
        text(institution.get("institution")) and text(institution.get("domain")),
        "missing/invalid institution identity",
    )
    require(
        type(institution.get("programs")) is list
        and all(
            text(url) and url.startswith(("http://", "https://"))
            for url in institution.get("programs", [])
        ),
        "missing/invalid raw programme URLs",
    )
    require(
        {
            "case_id",
            "programme_urls",
            "ranked_urls",
            "predictions",
            "telemetry",
            "page_outcomes",
            "error",
        }
        <= set(observed),
        "missing explicit observation fields",
    )
    require(
        {"schema_version", "pipeline_sha", "captured_at", "mode", "config", "observations"}
        <= set(capture),
        "missing explicit capture fields",
    )
    require(
        {"native_ledger", "control_error", "control_message", "run_unknowns", "run_errors"}
        <= set(protocol),
        "missing explicit Job reporting fields",
    )
    for name in ("run_unknowns", "run_errors"):
        require(
            type(protocol.get(name)) is list and all(type(row) is str for row in protocol[name]),
            "invalid Job reporting " + name,
        )
    copied_budget = case_budgets.get(case)
    require(type(copied_budget) is dict, "missing/invalid physical budget copy")
    require(objects(protocol.get("claim_records")), "invalid claim records")
    require(objects(protocol.get("page_outcomes")), "invalid page outcomes")
    if errors:
        return errors
    # Schema validation rejects malformed predictions/URLs/extra fields. Raw
    # counters below still require exact ints, rather than coerced booleans.
    try:
        from evaluation.research.schema import Capture, Observation

        Capture.model_validate(capture)
        Observation.model_validate(observed)
    except (ValueError, TypeError):
        errors.append("capture/observation schema invalid")
    require(capture.get("schema_version") == "1", "schema version mismatch")
    require(capture.get("mode") == "live", "capture mode mismatch")
    require(capture.get("pipeline_sha") == plan["source_head"], "pipeline source mismatch")
    require(text(capture.get("captured_at")), "missing capture timestamp")
    manifest = source_manifest
    for name, path in [
        ("harness_sha256", "backend/evaluation/research/live.py"),
        ("mapping_sha256", "backend/evaluation/research/mapping.py"),
    ]:
        require(config.get(name) == manifest["files"][path], name + " mismatch")
    require(config.get("cohort") == [case], "wrong case/cohort")
    require(config.get("search_provider") == "exa_mcp", "provider mismatch")
    require(config.get("fenced_research_job") is True, "not fenced")
    require(config.get("university_read_budget") is False, "native flag mismatch")
    require(config.get("research_job_protocol") == "genuine-research-job", "wrong Job protocol")
    for name, expected in {
        "strict_expert_budget": True,
        "shared_query_budget": True,
        "browser_enabled": False,
        "cold_fetcher_reads": True,
        "site_branding_identity": False,
        "subject_phrase_match": False,
        "programme_identity_before_funding": False,
    }.items():
        require(config.get(name) is expected, "config flag mismatch " + name)
    for name, expected in {
        "seconds_per_case": 120,
        "child_active_seconds": 120,
        "max_fetcher_calls_per_case": 60,
        "max_search_queries_per_case": 6,
        "finalization_reserve_ms": 1000,
        "source_work_deadline_ms": 119000,
        "parent_process_reserve_seconds": 15,
        "parent_process_timeout_seconds": 135,
    }.items():
        require(
            number(config.get(name)) and config[name] == expected, "config cap mismatch " + name
        )
    require(
        config.get("page_budget_counts")
        == "every Fetcher.get invocation; cache hits consume a call",
        "wrong physical read semantics",
    )
    for name, expected in {
        "batch_attempted_case_ids": [case],
        "batch_completed_case_ids": [case],
        "batch_remaining_case_ids": [],
        "batch_stop_reason": None,
    }.items():
        require(name in config and config[name] == expected, "batch mismatch " + name)
    rows = capture.get("observations", [])
    require(len(rows) == 1 and rows[0] == observed, "capture/observation mismatch")
    require(observed.get("case_id") == case, "wrong observation identity")
    require(observed.get("error") != "CAPTURE_IN_PROGRESS", "unfinished observation")
    require(protocol.get("kind") == "genuine-research-job", "wrong raw protocol")
    require(protocol.get("started") is True, "Job never started")
    require(
        all(
            text(protocol.get(name))
            for name in ("job_id", "run_id", "worker_id", "sqlite_case_database")
        ),
        "missing actual Job provenance",
    )
    require(
        all(
            type(protocol.get(name)) is int and protocol[name] == 1
            for name in ("claim_token", "lease_token")
        ),
        "nonfresh claim token",
    )
    require(
        protocol.get("native_enabled") is False and protocol.get("native_ledger") is None,
        "OFF ledger fabricated",
    )
    require(protocol.get("observation_available") is True, "raw reporting unavailable")
    require(raw.get("protocol_observation_available") is True, "raw observation unavailable")
    require(
        type(protocol.get("heartbeat_tasks")) is int and protocol["heartbeat_tasks"] == 1,
        "invalid heartbeat count",
    )
    require(
        type(protocol.get("heartbeat_done")) is list
        and len(protocol["heartbeat_done"]) == 1
        and protocol["heartbeat_done"][0] is True,
        "heartbeat not joined",
    )
    require(
        type(protocol.get("heartbeat_cancelled")) is list
        and len(protocol["heartbeat_cancelled"]) == 1
        and type(protocol["heartbeat_cancelled"][0]) is bool,
        "invalid heartbeat cancellation",
    )
    job_status = protocol.get("job_status")
    require(
        type(job_status) is str
        and job_status in {"succeeded", "queued", "running", "failed", "dead", "cancelled"},
        "unknown actual Job state",
    )
    for name in ("worker_jobs_done", "worker_jobs_failed"):
        require(
            type(protocol.get(name)) is int and 0 <= protocol[name] <= 1,
            "invalid worker outcome " + name,
        )
    require(
        "recorded_worker_id" in protocol
        and (protocol["recorded_worker_id"] is None or text(protocol["recorded_worker_id"])),
        "invalid recorded worker identity",
    )
    if job_status == "running":
        require(
            protocol.get("recorded_worker_id") == protocol.get("worker_id"),
            "running Job owner mismatch",
        )
    else:
        require(protocol.get("recorded_worker_id") is None, "terminal/queued Job still owned")
    if job_status != "succeeded":
        require(protocol.get("worker_jobs_done") == 0, "partial Job fabricated worker completion")
    for name, limit in [("fetcher_calls", 60), ("search_queries", 6), ("elapsed_ms", 120000)]:
        value = budget.get(name)
        require(type(value) is int and 0 <= value <= limit, "missing/over-budget " + name)
    for name in ("blocked_search_queries", "network_http_requests"):
        require(
            type(budget.get(name)) is int and budget[name] >= 0, "invalid physical counter " + name
        )
    for name, expected in {
        "max_fetcher_calls": 60,
        "max_search_queries": 6,
        "max_active_seconds": 120,
        "finalization_reserve_ms": 1000,
        "source_work_deadline_ms": 119000,
    }.items():
        require(
            number(budget.get(name)) and budget[name] == expected, "physical cap mismatch " + name
        )
    require(
        budget.get("strict_expert_budget") is True and budget.get("provider") == "exa_mcp",
        "physical protocol mismatch",
    )
    active_basis = "capture_one entry; includes canary setup and all pipeline stages, cancellation cleanup, output/raw persistence and final checkpoint work; final metering-envelope persistence is audit only"
    require(
        budget.get("active_time_basis") == active_basis
        and config.get("active_time_basis") == active_basis,
        "clock basis mismatch",
    )
    for physical_name in budget:
        require(
            physical_name in copied_budget
            and type(copied_budget[physical_name]) is type(budget[physical_name])
            and copied_budget[physical_name] == budget[physical_name],
            "physical copy mismatch " + physical_name,
        )
    expected_parent = {
        "parent_process_elapsed_seconds",
        "process_error",
        "active_checkpoint_available",
    }
    require(
        set(copied_budget) == set(budget) | expected_parent, "missing/extra physical copied fields"
    )
    require(copied_budget.get("active_checkpoint_available") is True, "physical checkpoint missing")
    require(
        "process_error" in copied_budget and copied_budget["process_error"] is None,
        "parent process error",
    )
    require(
        number(copied_budget.get("parent_process_elapsed_seconds"))
        and 0 <= copied_budget["parent_process_elapsed_seconds"] <= 135,
        "parent process ceiling exceeded/missing",
    )
    for name, expected in {
        "http_fetches": budget.get("fetcher_calls"),
        "search_calls": budget.get("search_queries"),
        "browser_fetches": 0,
        "model_input_tokens": 0,
        "jev_input_tokens": 0,
    }.items():
        require(
            type(telemetry.get(name)) is int and telemetry[name] == expected,
            "telemetry mismatch " + name,
        )
    require(
        number(telemetry.get("latency_seconds")) and 0 <= telemetry["latency_seconds"] <= 120,
        "active telemetry missing/over-budget",
    )
    require(
        "provider_failure" in budget and budget["provider_failure"] is None,
        "provider refusal/missing proof",
    )
    require(budget.get("protocol_persistence_error") is None, "artifact persistence failed")
    require(
        "stop_reason" in budget
        and (budget["stop_reason"] is None or type(budget["stop_reason"]) is str),
        "invalid stop reason",
    )
    stop_reason = budget.get("stop_reason")
    require(
        stop_reason
        in (
            None,
            "page_budget_exhausted",
            "search_budget_exhausted",
            "source_work_deadline_exhausted",
            "wall_clock_budget_exhausted",
        ),
        "refusal/unrecognized stop reason",
    )
    if stop_reason == "page_budget_exhausted":
        require(budget.get("fetcher_calls") == 60, "page stop before actual cap")
    if stop_reason == "search_budget_exhausted":
        require(budget.get("search_queries") == 6, "search stop before actual cap")
    claim_records = protocol["claim_records"]
    require(
        raw["claims"] == [record.get("payload") for record in claim_records],
        "raw/actual claims mismatch",
    )
    try:
        from app.schemas.claim import Claim
        from evaluation.research.identities import IdentityMap
        from evaluation.research.mapping import evidence_scope, normalize_subject_claims
        from evaluation.research.schema import Evidence, Observation, PageOutcome, Prediction

        identities = IdentityMap.model_validate(identities.model_dump(mode="json"))
        expected_predictions = []
        ids = set()
        native_observed = Observation.model_validate(observed)
        for record in claim_records:
            if not (
                {"id", "claim_type", "source_url", "accessed_at", "payload"} <= set(record)
                and all(
                    text(record.get(name))
                    for name in ("id", "claim_type", "source_url", "accessed_at")
                )
                and type(record.get("payload")) is dict
            ):
                raise ValueError("incomplete actual ClaimRow provenance")
            if record["id"] in ids:
                raise ValueError("duplicate actual ClaimRow identity")
            ids.add(record["id"])
            payload = record["payload"]
            if "original_text_excerpt" in payload and (
                type(payload["original_text_excerpt"]) is not str
                or len(payload["original_text_excerpt"]) > 600
            ):
                raise ValueError("non-native claim excerpt")
            if "official_domain" in payload and type(payload["official_domain"]) is not bool:
                raise ValueError("non-native official flag")
            claim = Claim.model_validate(payload)
            accessed = datetime.fromisoformat(record["accessed_at"])

            # SQLite drops timezone metadata from the stored UTC timestamp.
            def utc_naive(value):
                return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value

            if (
                record["claim_type"] != claim.claim_type.value
                or record["source_url"] != claim.source_url
                or utc_naive(accessed) != utc_naive(claim.accessed_at)
            ):
                raise ValueError("ClaimRow/payload provenance mismatch")
            for key, value, programme, degree in normalize_subject_claims(
                record["claim_type"], payload, identities
            ):
                evidence = None
                excerpt = payload.get("original_text_excerpt")
                if excerpt and record["source_url"].startswith(("http://", "https://")):
                    # Candidate name or case fallback is the actual caller's
                    # only unrecorded university fallback; recorded scope wins.
                    i = len(expected_predictions)
                    candidate = (
                        native_observed.predictions[i].evidence
                        if i < len(native_observed.predictions)
                        else None
                    )
                    university = institution.get("institution")
                    recorded = payload.get("scope")
                    if not (type(recorded) is dict and recorded.get("university")) and candidate:
                        if candidate.scope.university not in (case, university):
                            raise ValueError("invented evidence university")
                        university = candidate.scope.university
                    evidence = Evidence(
                        url=record["source_url"],
                        excerpt=excerpt,
                        scope=evidence_scope(
                            payload, university=university, programme=programme, degree=degree
                        ),
                        accessed_on=accessed.date(),
                        source_type="official" if payload.get("official_domain") else "unknown",
                    )
                expected_predictions.append(Prediction(key=key, value=value, evidence=evidence))
        require(
            [p.model_dump(mode="json") for p in native_observed.predictions]
            == [p.model_dump(mode="json") for p in expected_predictions],
            "predictions differ from actual claim mapping",
        )
        expected_pages = [
            PageOutcome(
                **{**row, "characters": int(row["characters"]) if row.get("characters") else None}
            )
            for row in protocol["page_outcomes"]
        ]
        require(
            [p.model_dump(mode="json") for p in native_observed.page_outcomes]
            == [p.model_dump(mode="json") for p in expected_pages],
            "raw/observation page outcomes mismatch",
        )
    except Exception as exc:
        errors.append("raw claim/page provenance invalid: " + type(exc).__name__)
    raw_error = canary.get("run_error")
    control_error = protocol.get("control_error")
    error = observed.get("error")
    require("run_error" in canary and type(raw_error) is str, "invalid raw terminal error")
    require(
        "control_error" in protocol and (control_error is None or type(control_error) is str),
        "invalid raw control error",
    )
    require((raw_error or None) == (control_error or None), "raw/control error mismatch")
    if raw_error:
        control_type = protocol.get("control_type")
        reason = protocol.get("control_reason")
        message = protocol.get("control_message")
        require(
            text(control_type)
            and (reason is None or text(reason))
            and (message is None or text(message)),
            "invalid typed partial cause",
        )
        if (
            text(control_type)
            and (reason is None or text(reason))
            and (message is None or text(message))
        ):
            detail = reason or message
            require(
                raw_error == control_type + (": " + detail if detail else ""),
                "original typed partial cause mismatch",
            )
    if require_complete_job:
        require(
            job_status == "succeeded"
            and raw_error in (None, "")
            and control_error is None
            and error is None
            and stop_reason is None,
            "partial is not a completed Job result",
        )
    elif raw_error or error or job_status != "succeeded" or stop_reason:
        control_type = protocol.get("control_type")
        reason = protocol.get("control_reason")
        require(
            control_type
            in (
                None,
                "CancelledError",
                "RunCancelled",
                "TimeoutError",
                "RuntimeError",
                "LeaseLost",
                "UniversityReadStopped",
            ),
            "unsupported partial control",
        )
        if control_type == "UniversityReadStopped":
            require(reason == "checkpoint_busy", "native-OFF readguard anomaly")
            require(
                job_status == "running" and protocol.get("worker_jobs_failed") == 1,
                "checkpoint busy Worker/state mismatch",
            )
        if control_type == "RuntimeError":
            require(
                raw_error == "RuntimeError: BENCHMARK_PAGE_BUDGET_EXHAUSTED"
                and stop_reason == "page_budget_exhausted",
                "unsupported RuntimeError partial",
            )
            require(
                job_status in ("queued", "dead") and protocol.get("worker_jobs_failed") == 1,
                "page-cap Worker/state mismatch",
            )
        if control_type == "TimeoutError":
            require(
                job_status in ("queued", "dead") and protocol.get("worker_jobs_failed") == 1,
                "timeout Worker/state mismatch",
            )
        if control_type in ("CancelledError", "LeaseLost"):
            require(
                job_status == "running" and protocol.get("worker_jobs_failed") == 0,
                "escaped control Worker/state mismatch",
            )
        if control_type == "RunCancelled":
            require(
                job_status == "cancelled" and raw_error == "RunCancelled",
                "cancellation state mismatch",
            )
            require(
                protocol.get("worker_jobs_failed") == 0, "RunCancelled fabricated Worker failure"
            )
        if stop_reason in ("source_work_deadline_exhausted", "wall_clock_budget_exhausted"):
            require(
                type(budget.get("elapsed_ms")) is int and budget["elapsed_ms"] >= 119000,
                "deadline before source clock",
            )
            require(
                error
                in (
                    "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED",
                    "TimeoutError: BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED",
                ),
                "deadline missing original diagnostic",
            )
        else:
            require(error == (raw_error or None), "partial observation/raw error mismatch")
        require(bool(raw_error or stop_reason), "silent unfinished Job")
    else:
        require(error is None and control_error is None, "silent observation/control error")
    if job_status == "succeeded":
        require(
            protocol.get("worker_jobs_done") == 1
            and protocol.get("worker_jobs_failed") == 0
            and protocol.get("recorded_worker_id") is None,
            "completed Job state inconsistency",
        )
    if not raw_error and error is None:
        try:
            from pydantic import HttpUrl

            require(
                [str(url) for url in Observation.model_validate(observed).programme_urls]
                == [str(HttpUrl(url)) for url in institution["programs"]],
                "raw/observation programme URLs mismatch",
            )
        except Exception as exc:
            errors.append("raw programme URL invalid: " + type(exc).__name__)
    return errors
