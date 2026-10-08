"""Strict, auditable shape for expert intervention records."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, TypeAdapter, model_serializer, model_validator

QuestionID = Literal["Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
QUESTIONS = ("Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6")
QUESTION_DESCRIPTIONS = {
    "Q0": "Exact bachelor programme existence",
    "Q1": "English language tests for the international applicant",
    "Q2": "International secondary qualification eligibility",
    "Q3": "Deadline for the correct international intake",
    "Q4": "International tuition fee for the correct academic year",
    "Q5": "Bachelor scholarship existence",
    "Q6": "International applicant eligibility for that scholarship",
}
MissCause = Literal[
    "NOT_DISCOVERED",
    "BUDGET",
    "SLOT",
    "CLASSIFIER",
    "EXTRACTOR",
    "OTHER_PAGE",
    "PDF",
    "JS",
    "SCOPE",
    "ACCESS",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Action(Strict):
    step: int = Field(ge=1)
    at: datetime
    observed_before: str = Field(min_length=1)
    observed_from_step: int | None = Field(default=None, ge=1)
    tool: Literal["search_provider", "fetcher", "browser", "pdf_parser", "internal_index", "other"]
    action: str = Field(min_length=1)
    outcome_status: Literal["success", "failure", "blocked"]
    outcome: str = Field(min_length=1)
    stage: Literal[
        "access",
        "candidate_generation",
        "ranking",
        "page_understanding",
        "representation",
        "extraction",
        "identity_scope",
        "schema",
        "conflict_freshness",
    ]
    policy_mode: Literal["same_policy", "outside_policy"]
    url: HttpUrl | None = None
    final_url: HttpUrl | None = None
    request: dict[str, JsonValue] | None = None
    raw_log_path: str = Field(min_length=1)
    raw_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    elapsed_ms: int = Field(ge=0)
    fetcher_calls_cumulative: int = Field(ge=0)
    search_queries_cumulative: int | None = Field(default=None, ge=0)
    elapsed_ms_cumulative: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def flag_other_tool(self) -> Self:
        if self.tool == "other" and self.policy_mode != "outside_policy":
            raise ValueError("Unlisted tools must be outside_policy")
        if self.at.tzinfo is None:
            raise ValueError("Action time must include a timezone")
        path = Path(self.raw_log_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Raw log path must stay relative to the log directory")
        return self


class Proposal(Strict):
    claim_key: str = Field(min_length=1)
    value: JsonValue
    source_url: HttpUrl
    excerpt: str = Field(min_length=1)
    accessed_on: date
    scope: dict[str, str | None]
    supporting_steps: list[int] = Field(min_length=1)
    status: Literal["unreviewed"] = "unreviewed"


class EvidenceLocation(Strict):
    """Coordinates in the saved source, using production text or DocumentIR."""

    kind: Literal["text", "document_ir", "pdf"]
    block_id: str | None = Field(default=None, min_length=1)
    section_path: list[str] = Field(default_factory=list)
    page: int | None = Field(default=None, ge=1, le=40)

    @model_validator(mode="after")
    def coordinates(self) -> Self:
        if self.kind == "document_ir" and self.block_id is None:
            raise ValueError("DocumentIR evidence needs its exact block ID")
        if self.kind != "document_ir" and (self.block_id is not None or self.section_path):
            raise ValueError("Block and section coordinates require DocumentIR evidence")
        if (self.kind == "pdf") != (self.page is not None):
            raise ValueError("PDF evidence needs a page number; other evidence cannot have one")
        return self


class SourceEvidence(Strict):
    action_step: int = Field(ge=1)
    source_url: HttpUrl
    excerpt: str = Field(min_length=1)
    location: EvidenceLocation


class QuestionFinding(Strict):
    question: QuestionID
    status: Literal["found", "not_published", "inaccessible", "unresolved"]
    supporting_steps: list[int] = Field(default_factory=list)
    proposal_indices: list[int] = Field(
        default_factory=list, description="Zero-based proposal indices"
    )
    evidence: list[SourceEvidence] = Field(default_factory=list)
    scope: dict[str, str | None] = Field(default_factory=dict)
    observation: str = Field(min_length=1)

    @model_validator(mode="after")
    def evidence_obligations(self) -> Self:
        if len(self.supporting_steps) != len(set(self.supporting_steps)) or any(
            step < 1 for step in self.supporting_steps
        ):
            raise ValueError("Finding supporting steps must be unique positive action numbers")
        if len(self.proposal_indices) != len(set(self.proposal_indices)) or any(
            index < 0 for index in self.proposal_indices
        ):
            raise ValueError("Finding proposal indices must be unique zero-based indices")
        if self.status in {"found", "not_published"} and not self.evidence:
            raise ValueError("Found and not_published findings need official source evidence")
        if self.status == "found" and not self.proposal_indices:
            raise ValueError("Every found answer needs a proposed fact")
        if self.status == "inaccessible" and not self.supporting_steps:
            raise ValueError("Inaccessible findings need a recorded failed or blocked page read")
        if any(evidence.action_step not in self.supporting_steps for evidence in self.evidence):
            raise ValueError("Finding evidence must cite its supporting actions")
        return self


class ControllerObservation(Strict):
    """A visible log field supporting a later diagnosis, never expert reasoning."""

    action_step: int = Field(ge=1)
    field: str = Field(min_length=1, description="Dot-separated path in the raw controller log")
    value: JsonValue


class MissAdjudication(Strict):
    question: QuestionID
    cause: MissCause
    supporting_steps: list[int] = Field(min_length=1)
    observations: list[ControllerObservation] = Field(min_length=1)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def observable_support(self) -> Self:
        if any(
            observation.action_step not in self.supporting_steps
            for observation in self.observations
        ):
            raise ValueError("Miss causes need observable support from their recorded actions")
        return self


class TraceAdjudication(Strict):
    """Evaluator-only record linked to an already submitted blind trace."""

    trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    misses: list[MissAdjudication]
    review_status: Literal["unreviewed"] = "unreviewed"


class ExpertTrace(Strict):
    schema_version: Literal["1"] = "1"
    case_id: str = Field(min_length=1)
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_pipeline_sha: str = Field(min_length=7)
    max_fetcher_calls: int = Field(ge=1)
    max_elapsed_ms: int | None = Field(ge=1)
    timing_policy: Literal["legacy_active", "expert_wall_only"] = "legacy_active"
    protective_wall_ms: int | None = Field(default=None, ge=1)
    max_search_queries: int | None = Field(default=None, ge=1)
    initial_fetcher_calls: int = Field(ge=0)
    initial_elapsed_ms: int = Field(ge=0)
    initial_search_queries: int = Field(default=0, ge=0)
    started_at: datetime
    ended_at: datetime
    actions: list[Action] = Field(min_length=1)
    proposals: list[Proposal] = Field(default_factory=list)
    question_findings: list[QuestionFinding] | None = None
    review_status: Literal["unreviewed"] = "unreviewed"

    @model_validator(mode="before")
    @classmethod
    def wall_raw_types(cls, value):
        if isinstance(value, dict) and value.get("timing_policy") == "expert_wall_only":
            for key in ("max_fetcher_calls", "max_search_queries", "protective_wall_ms", "initial_fetcher_calls", "initial_elapsed_ms", "initial_search_queries"):
                if type(value.get(key)) is not int:
                    raise ValueError("Independent raw counters must be exact integers")
        return value

    @model_serializer(mode="wrap")
    def keep_legacy_fields(self, handler):
        value = handler(self)
        if self.timing_policy == "legacy_active":
            value.pop("timing_policy", None)
            value.pop("protective_wall_ms", None)
        return value

    @model_validator(mode="after")
    def ordered_actions(self) -> Self:
        if self.timing_policy == "legacy_active" and (self.max_elapsed_ms is None or self.protective_wall_ms is not None):
            raise ValueError("Legacy trace requires its active cap")
        if self.timing_policy == "expert_wall_only" and (self.max_elapsed_ms is not None or self.protective_wall_ms != 900_000 or self.max_fetcher_calls != 60 or self.max_search_queries != 6):
            raise ValueError("Wall-only trace requires null active cap and900s wall")
        if self.started_at.tzinfo is None or self.ended_at.tzinfo is None:
            raise ValueError("Trace times must include a timezone")
        if self.timing_policy == "expert_wall_only" and (self.ended_at - self.started_at).total_seconds() > 900:
            raise ValueError("Expert trace exceeds protective wall")
        if self.ended_at < self.started_at:
            raise ValueError("Trace ends before it starts")
        if [action.step for action in self.actions] != list(range(1, len(self.actions) + 1)):
            raise ValueError("Actions must have consecutive 1-based steps")
        if len({action.raw_log_path for action in self.actions}) != len(self.actions):
            raise ValueError("Every action needs its own raw tool log")
        previous = self.started_at
        used_calls = self.initial_fetcher_calls
        used_ms = self.initial_elapsed_ms
        used_queries = self.initial_search_queries
        for action in self.actions:
            if not previous <= action.at <= self.ended_at:
                raise ValueError("Actions must be chronologically ordered within the trace")
            if action.step == 1 and action.observed_from_step is not None:
                raise ValueError("First action must observe the baseline packet")
            if action.step > 1 and (
                action.observed_from_step is None or action.observed_from_step >= action.step
            ):
                raise ValueError("Later actions must cite an earlier observation step")
            if action.fetcher_calls_cumulative < used_calls:
                raise ValueError("Fetcher call count must not decrease")
            if (
                action.tool == "fetcher"
                and action.outcome_status != "blocked"
                and action.fetcher_calls_cumulative == used_calls
            ):
                raise ValueError("A Fetcher action must consume a Fetcher call")
            if action.elapsed_ms_cumulative < used_ms + action.elapsed_ms:
                raise ValueError("Cumulative elapsed time must include the action")
            if action.search_queries_cumulative is not None:
                if action.search_queries_cumulative < used_queries:
                    raise ValueError("Search query count must not decrease")
                if (
                    action.policy_mode == "same_policy"
                    and self.max_search_queries is not None
                    and action.search_queries_cumulative > self.max_search_queries
                ):
                    raise ValueError("Same-policy action exceeds the bounded search budget")
                used_queries = action.search_queries_cumulative
            if action.policy_mode == "same_policy" and (
                action.fetcher_calls_cumulative > self.max_fetcher_calls
                or (self.max_elapsed_ms is not None and action.elapsed_ms_cumulative > self.max_elapsed_ms)
            ):
                raise ValueError("Same-policy action exceeds the bounded run budget")
            previous = action.at
            used_calls = action.fetcher_calls_cumulative
            used_ms = action.elapsed_ms_cumulative
        steps = {action.step for action in self.actions}
        if any(set(proposal.supporting_steps) - steps for proposal in self.proposals):
            raise ValueError("Every proposed fact must cite recorded actions")
        for proposal in self.proposals:
            if not any(
                action.step in proposal.supporting_steps
                and action.tool in {"fetcher", "browser"}
                and action.policy_mode == "same_policy"
                and action.outcome_status == "success"
                and proposal.source_url in {action.url, action.final_url}
                for action in self.actions
            ):
                raise ValueError(
                    "Proposed evidence needs a same-policy page read of its source URL"
                )
        if self.question_findings is not None:
            if sorted(finding.question for finding in self.question_findings) != list(QUESTIONS):
                raise ValueError("Question findings must contain Q0-Q6 exactly once")
            by_step = {action.step: action for action in self.actions}
            for finding in self.question_findings:
                if set(finding.supporting_steps) - steps:
                    raise ValueError("Finding must cite recorded actions")
                if any(index >= len(self.proposals) for index in finding.proposal_indices):
                    raise ValueError("Finding must cite recorded proposals by zero-based index")
                for evidence in finding.evidence:
                    action = by_step[evidence.action_step]
                    if not (
                        action.tool in {"fetcher", "browser"}
                        and action.policy_mode == "same_policy"
                        and action.outcome_status == "success"
                        and evidence.source_url in {action.url, action.final_url}
                    ):
                        raise ValueError(
                            "Finding evidence needs a successful same-policy exact source read"
                        )
                if finding.status == "found":
                    for index in finding.proposal_indices:
                        proposal = self.proposals[index]
                        if not any(
                            evidence.source_url == proposal.source_url
                            and evidence.excerpt == proposal.excerpt
                            and evidence.action_step in proposal.supporting_steps
                            for evidence in finding.evidence
                        ):
                            raise ValueError(
                                "Found proposals need matching source, quote and action evidence"
                            )
                        if not set(proposal.supporting_steps) <= set(finding.supporting_steps):
                            raise ValueError(
                                "Found proposals must cite the finding's recorded actions"
                            )
                if finding.status == "inaccessible" and not any(
                    by_step[step].tool in {"fetcher", "browser"}
                    and by_step[step].outcome_status in {"failure", "blocked"}
                    for step in finding.supporting_steps
                ):
                    raise ValueError("Inaccessible findings need a failed or blocked page read")
        return self


@dataclass
class _SourceRead:
    url: HttpUrl
    text: str
    document: Any = None
    pdf_pages: list[str] | None = None


_URL = TypeAdapter(HttpUrl)
_CONTROLLER_KEYS = {
    "request",
    "phase",
    "response",
    "elapsed_ms",
    "fetcher_calls_cumulative",
    "policy_mode",
}


def _structured_log(record: Any) -> bool:
    return isinstance(record, dict) and bool(_CONTROLLER_KEYS & record.keys())


def _outcome(record: dict[str, Any]) -> tuple[str, str]:
    response = record.get("response") or {}
    outcome = (
        record.get("outcome")
        or response.get("outcome")
        or ("error" if "error" in response else "ok")
    )
    if record.get("outcome"):
        status = "blocked"
    elif ("results" in response and not response.get("error")) or (
        response.get("ok") is True and outcome in {"ok", "cached"}
    ):
        status = "success"
    elif outcome in {
        "blocked",
        "refused_privacy",
        "robots_disallowed",
        "robots_crawl_delay",
        "blocked_by_final_url_policy",
    }:
        status = "blocked"
    else:
        status = "failure"
    return str(outcome), status


def _check_controller_action(
    action: Action,
    record: dict[str, Any],
    previous_calls: int,
    previous_ms: int,
    previous_queries: int,
) -> tuple[int, int, int]:
    required = {
        "request",
        "at",
        "phase",
        "elapsed_ms",
        "fetcher_calls_cumulative",
        "elapsed_ms_cumulative",
        "policy_mode",
    }
    if required - record.keys():
        raise ValueError(f"Incomplete controller log at step {action.step}")
    request = record["request"]
    if not isinstance(request, dict) or request.get("tool") != action.tool:
        raise ValueError(f"Controller tool mismatch at step {action.step}")
    if record.get("response") is not None and not isinstance(record["response"], dict):
        raise ValueError("Controller response must be structured")
    if not isinstance(record["at"], str) or any(
        type(record[key]) is not int
        for key in ("elapsed_ms", "fetcher_calls_cumulative", "elapsed_ms_cumulative")
    ):
        raise ValueError("Controller timestamp and counters have invalid types")
    if record["phase"] != "actions":
        raise ValueError("An expert action cannot cite a baseline replay log")
    if action.request is not None and action.request != request:
        raise ValueError(f"Controller request mismatch at step {action.step}")
    if action.tool in {"fetcher", "browser"}:
        if action.url is None or _URL.validate_python(request.get("url")) != action.url:
            raise ValueError(f"Controller request URL mismatch at step {action.step}")
    elif action.request is None:
        raise ValueError("Structured search actions must declare the exact controller request")
    if datetime.fromisoformat(record["at"]) != action.at:
        raise ValueError(f"Controller timestamp mismatch at step {action.step}")
    for key in ("elapsed_ms", "fetcher_calls_cumulative", "elapsed_ms_cumulative", "policy_mode"):
        if record[key] != getattr(action, key):
            raise ValueError(f"Controller {key} mismatch at step {action.step}")
    outcome, status = _outcome(record)
    if action.outcome != outcome or action.outcome_status != status:
        raise ValueError(f"Controller outcome mismatch at step {action.step}")
    response = record.get("response") or {}
    if status == "success" and action.tool in {"fetcher", "browser"}:
        http_status = response.get("status_code")
        if not isinstance(http_status, int) or not (
            200 <= http_status < 300 or (outcome == "cached" and http_status == 304)
        ):
            raise ValueError("Successful controller read has an unsuccessful HTTP status")
    for declared in (record.get("outcome_status"), response.get("outcome_status")):
        if declared is not None and declared != status:
            raise ValueError("Controller outcome status disagrees with its raw response")
    if action.final_url is not None and (
        _URL.validate_python(response.get("final_url")) != action.final_url
    ):
        raise ValueError(f"Controller final URL mismatch at step {action.step}")
    executed = record.get("executed", bool(record.get("response")))
    if not isinstance(executed, bool):
        raise ValueError("Controller executed flag must be boolean")
    if executed != bool(record.get("response")):
        raise ValueError("Controller executed flag disagrees with its recorded response")
    calls = int(executed and action.tool in {"fetcher", "browser"})
    if action.fetcher_calls_cumulative != previous_calls + calls:
        raise ValueError(f"Controller Fetcher accounting mismatch at step {action.step}")
    if "elapsed_ms_before" in record or "charged_elapsed_ms" in record:
        before = record.get("elapsed_ms_before")
        charged = record.get("charged_elapsed_ms")
        if (
            type(before) is not int
            or type(charged) is not int
            or before < previous_ms
            or charged < action.elapsed_ms
            or action.elapsed_ms_cumulative != before + charged
        ):
            raise ValueError(f"Controller elapsed accounting mismatch at step {action.step}")
    elif action.elapsed_ms_cumulative != previous_ms + action.elapsed_ms:
        raise ValueError(f"Controller elapsed accounting mismatch at step {action.step}")
    queries = previous_queries
    if "search_queries_cumulative" in record:
        queries += int(executed and action.tool == "search_provider")
        if (
            record["search_queries_cumulative"] != queries
            or action.search_queries_cumulative != queries
        ):
            raise ValueError(f"Controller search accounting mismatch at step {action.step}")
    return action.fetcher_calls_cumulative, action.elapsed_ms_cumulative, queries


def _source_read(record: dict[str, Any]) -> _SourceRead | None:
    from app.adapters.document_ir import build_document_ir
    from app.adapters.extraction import pdf_to_text, readable_text

    response = record.get("response") or {}
    if "content_b64" not in response:
        return None
    status = _outcome(record)[1]
    if status != "success" and response["content_b64"] == "":
        # Policy refusals retain an opaque fingerprint of suppressed bytes.
        # They have no readable payload and can never support a source quote.
        return None
    try:
        body = base64.b64decode(response["content_b64"], validate=True)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("Invalid raw controller source payload") from exc
    if hashlib.sha256(body).hexdigest() != response.get("content_sha256"):
        raise ValueError("Raw controller source payload hash mismatch")
    if status != "success" or record["request"]["tool"] not in {"fetcher", "browser"}:
        return None
    source_url = _URL.validate_python(response.get("final_url") or record["request"].get("url"))
    content_type = str(response.get("content_type") or "").lower()
    if "html" in content_type:
        html = body.decode("utf-8", errors="replace")
        return _SourceRead(
            source_url, readable_text(html), build_document_ir(html, str(source_url))
        )
    if "pdf" in content_type:
        import io

        from pypdf import PdfReader

        text = pdf_to_text(body)
        try:
            pages = [(page.extract_text() or "") for page in PdfReader(io.BytesIO(body)).pages[:40]]
        except Exception:
            pages = []
        return _SourceRead(source_url, text, pdf_pages=pages)
    if any(kind in content_type for kind in ("text/plain", "xml")):
        return _SourceRead(source_url, body.decode("utf-8", errors="replace"))
    return _SourceRead(source_url, "")


def _quote_matches(
    excerpt: str, source: _SourceRead, location: EvidenceLocation | None = None
) -> bool:
    from app.domain.claim_verifier import is_verbatim_excerpt, normalize_text

    if not normalize_text(excerpt):
        return False

    if location is not None:
        if location.kind == "document_ir":
            return source.document is not None and any(
                block.id == location.block_id
                and list(block.section_path) == location.section_path
                and is_verbatim_excerpt(excerpt, block.text)
                for block in source.document.blocks
            )
        if location.kind == "pdf":
            return (
                bool(source.pdf_pages)
                and location.page is not None
                and (
                    location.page <= len(source.pdf_pages or [])
                    and is_verbatim_excerpt(excerpt, (source.pdf_pages or [])[location.page - 1])
                )
            )
        if source.pdf_pages is not None:
            return False
    return is_verbatim_excerpt(excerpt, source.text) or (
        location is None
        and source.document is not None
        and any(is_verbatim_excerpt(excerpt, block.text) for block in source.document.blocks)
    )


def _official_source(url: HttpUrl, case: dict[str, Any]) -> bool:
    from app.domain.claim_verifier import url_matches_domains

    parts = urlsplit(str(url))
    domains = [case["domain"], *case.get("official_domains", [])]
    return not parts.username and not parts.password and url_matches_domains(str(url), domains)


def _scope_findings(parsed: ExpertTrace, case: dict[str, Any], profile: dict[str, Any]) -> None:
    request = case["request"]
    for finding in parsed.question_findings or []:
        if finding.status not in {"found", "not_published"}:
            continue
        required = {"degree"}
        if finding.question == "Q0":
            required.add("programme")
        if finding.question in {"Q1", "Q2", "Q3", "Q4", "Q6"}:
            required.add("population")
        if finding.question == "Q2":
            required.add("qualification")
        if finding.question == "Q3":
            required.add("intake")
        if finding.question == "Q4":
            required.add("academic_year")
        if any(not finding.scope.get(key) for key in required):
            raise ValueError(f"{finding.question} needs explicit scope: {sorted(required)}")
        expected = {
            **request,
            "population": request.get("population") or "international",
            "qualification": request.get("qualification") or profile.get("education_system"),
        }
        for key, value in finding.scope.items():
            if value is not None and expected.get(key) is not None and value != expected[key]:
                raise ValueError(f"{finding.question} scope differs from public request: {key}")
        if finding.scope["degree"] != "bachelor":
            raise ValueError(f"{finding.question} is outside the bachelor audit scope")
        if finding.question == "Q4" and not request.get("academic_year"):
            intake_years = re.findall(r"\b20\d{2}\b", request.get("intake") or "")
            fee_years = re.findall(r"\b20\d{2}\b", finding.scope["academic_year"] or "")
            if intake_years and (not fee_years or fee_years[0] != intake_years[0]):
                raise ValueError("Q4 fee year does not cover the requested intake")
        if finding.status == "found":
            for index in finding.proposal_indices:
                for key, value in finding.scope.items():
                    if value is not None and parsed.proposals[index].scope.get(key) != value:
                        raise ValueError("Proposal scope disagrees with its question finding")


_UNPUBLISHED = re.compile(
    r"\b(?:not\s+(?:yet\s+)?(?:been\s+)?(?:published|announced|released)|"
    r"(?:will|to)\s+be\s+(?:published|announced|released)|"
    r"(?:do|does)\s+not\s+publish|no\s+.{0,50}\b(?:published|announced)\b)",
    re.IGNORECASE,
)
_QUESTION_TOPIC = {
    "Q0": r"program(?:me)?|course|degree",
    "Q1": r"english|ielts|toefl|language",
    "Q2": r"qualificat|secondary|diploma|school",
    "Q3": r"deadline|application|intake",
    "Q4": r"fee|tuition|cost",
    "Q5": r"scholarship|award|funding",
    "Q6": r"scholarship|award|eligib",
}


def _publication_status(finding: QuestionFinding) -> None:
    if finding.status == "not_published" and not any(
        _UNPUBLISHED.search(evidence.excerpt)
        and re.search(
            _QUESTION_TOPIC[finding.question],
            " ".join([evidence.excerpt, *evidence.location.section_path]),
            re.IGNORECASE,
        )
        for evidence in finding.evidence
    ):
        raise ValueError(
            "not_published needs an explicit official publication statement; otherwise unresolved"
        )


def _year_label(value: str) -> str:
    match = re.search(r"\b(20\d{2})(?:\s*[/–—-]\s*(20\d{2}|\d{2}))?\b", value)
    if match is None:
        return ""
    first, second = match.groups()
    return first + (f"/{second[-2:]}" if second else "")


def _evidence_scope(
    finding: QuestionFinding, evidence: SourceEvidence, source: _SourceRead
) -> None:
    """Reject visible contradictions; semantic applicability stays unreviewed."""
    from app.adapters.scope_reader import read_scope
    from app.domain.claim_verifier import is_verbatim_excerpt

    context = evidence.excerpt
    local_context = context
    if evidence.location.kind == "document_ir":
        block = next(
            block for block in source.document.blocks if block.id == evidence.location.block_id
        )
        local_context = " ".join(
            [
                *block.row_headers,
                *block.column_headers,
                block.label,
                block.caption,
                block.text,
            ]
        )
        context = " ".join([*block.section_path, local_context])
    local_scope, section_scope = read_scope(local_context), read_scope(context)
    observed_degree = local_scope.degree or section_scope.degree
    observed_population = local_scope.population or section_scope.population
    observed_intake = local_scope.intake or section_scope.intake
    if observed_degree is not None and observed_degree != finding.scope.get("degree"):
        raise ValueError("Official evidence states a different degree scope")
    if observed_population == "domestic" and finding.scope.get("population") == "international":
        raise ValueError("Official evidence states domestic applicant scope")
    if finding.question == "Q0" and not is_verbatim_excerpt(
        finding.scope["programme"] or "", context
    ):
        raise ValueError("Q0 exact programme name is absent from the official evidence location")
    if finding.question == "Q3" and observed_intake is not None:
        declared = (finding.scope.get("intake") or "").casefold()
        if observed_intake.casefold() != declared:
            # A named September start may state the same fall intake. The
            # production scope reader already normalizes programme starts.
            raise ValueError("Official evidence states a different intake scope")
    if finding.question == "Q4":
        declared_year = _year_label(finding.scope.get("academic_year") or "")
        year_context = local_context if re.search(r"\b20\d{2}\b", local_context) else context
        published_years = {
            _year_label(match.group(0))
            for match in re.finditer(r"\b20\d{2}(?:\s*[/–—-]\s*(?:20\d{2}|\d{2}))?\b", year_context)
        }
        if not declared_year or declared_year not in published_years:
            raise ValueError("Q4 fee year is absent from its official evidence location")


def _controller_budget(
    parsed: ExpertTrace, action: Action, record: dict[str, Any], comparison_mode: str | None
) -> None:
    from .controller import BLOCKED_HOSTS, STRICT_PROVIDERS, _allowed_url

    policy = record.get("tool_policy") or {}
    if policy.get("timing_policy", "legacy_active") != parsed.timing_policy:
        raise ValueError("Raw timing policy differs from trace")
    if parsed.timing_policy == "expert_wall_only" and (policy.get("protective_wall_ms") != 900_000 or policy.get("thinking_in_tool_ms") is not False or record.get("budget_origin") != "independent_full_budget"):
        raise ValueError("Raw independent wall policy incomplete")
    if parsed.timing_policy == "expert_wall_only":
        wb = record.get("wall_elapsed_ms_before")
        wa = record.get("wall_elapsed_ms_cumulative")
        if type(wb) is not int or type(wa) is not int or not 0 <= wb <= wa <= 900_000:
            raise ValueError("Raw protective wall counter invalid")
    if "case_id" in record and record["case_id"] != parsed.case_id:
        raise ValueError("Controller log belongs to a different case")
    if comparison_mode is not None and record.get("budget_origin") != comparison_mode:
        raise ValueError("Controller budget origin differs from the packet comparison mode")
    bounds = record.get("budgets")
    if bounds is not None:
        if not isinstance(bounds, dict) or (bounds.get("max_calls"), bounds.get("max_ms")) != (
            parsed.max_fetcher_calls,
            parsed.max_elapsed_ms,
        ):
            raise ValueError("Controller budget differs from the declared trace budget")
        query_cap = bounds.get("max_search_queries")
        if query_cap is not None and parsed.max_search_queries != query_cap:
            raise ValueError("Controller search budget differs from the declared trace budget")
        if (
            action.policy_mode == "same_policy"
            and query_cap is not None
            and (action.search_queries_cumulative or 0) > query_cap
        ):
            raise ValueError("Same-policy action exceeds the controller search budget")
    policy = record.get("tool_policy")
    if policy is not None and not isinstance(policy, dict):
        raise ValueError("Controller tool policy must be structured")
    if policy is not None and bounds is not None:
        for policy_key, bound_key in (
            ("max_fetcher_calls", "max_calls"),
            ("max_elapsed_ms", "max_ms"),
            ("max_search_queries", "max_search_queries"),
        ):
            if policy_key in policy and policy[policy_key] != bounds.get(bound_key):
                raise ValueError("Controller tool policy disagrees with its recorded budget")
    if (
        policy is not None
        and policy.get("budget_origin") is not None
        and (policy["budget_origin"] != record.get("budget_origin"))
    ):
        raise ValueError("Controller tool policy disagrees with its budget origin")
    if policy is not None and policy.get("strict_budget"):
        domains = policy.get("official_domains")
        if (
            not isinstance(domains, list)
            or not domains
            or any(not isinstance(d, str) for d in domains)
        ):
            raise ValueError(
                "Strict controller policy requires independently resolved official domains"
            )
        denied = policy.get("blocked_hosts")
        if not isinstance(denied, list) or not set(BLOCKED_HOSTS) <= set(denied):
            raise ValueError("Strict controller policy must block repository and benchmark hosts")
        if action.policy_mode == "same_policy":
            if action.tool == "fetcher":
                response = record.get("response") or {}
                if not _allowed_url(str(action.url), tuple(domains)) or (
                    action.outcome_status == "success"
                    and (
                        not _allowed_url(str(response.get("final_url")), tuple(domains))
                        or response.get("fetch_tier") == "browser"
                    )
                ):
                    raise ValueError(
                        "Same-policy source read contradicts the recorded controller policy"
                    )
            elif action.tool == "search_provider":
                if record.get("provider") not in STRICT_PROVIDERS:
                    raise ValueError("Same-policy query contradicts the recorded provider policy")
                response = record.get("response") or {}
                if any(
                    not _allowed_url(str(hit.get("url")), tuple(domains))
                    for hit in response.get("results", [])
                ):
                    raise ValueError(
                        "Controller search result contradicts the recorded tool policy"
                    )


def validate_trace(
    trace: dict[str, Any], packet: dict[str, Any], *, logs_dir: Path | None = None
) -> ExpertTrace:
    """Check linkage, then independent controller results and saved source quotes.

    Legacy unstructured logs only establish byte integrity. Question findings
    require structured controller records when a log directory is supplied.
    None of these checks is a human adjudication of the proposed fact's meaning.
    """
    from .packet import digest

    parsed = ExpertTrace.model_validate(trace)
    if parsed.packet_sha256 != digest(packet):
        raise ValueError("Trace was not made against this exact packet")
    if parsed.case_id not in {case["case_id"] for case in packet["cases"]}:
        raise ValueError("Unknown case ID")
    if parsed.baseline_pipeline_sha != packet["baseline_pipeline_sha"]:
        raise ValueError("Wrong baseline pipeline")
    budget = packet["baseline_budget"]
    if parsed.timing_policy != budget.get("timing_policy", "legacy_active"):
        raise ValueError("Packet timing policy differs from trace")
    if parsed.timing_policy == "expert_wall_only" and (packet.get("comparison_mode") != "independent_full_budget" or budget.get("protective_wall_ms") != 900_000):
        raise ValueError("Independent packet wall policy incomplete")
    if (parsed.max_fetcher_calls, parsed.max_elapsed_ms) != (
        budget["max_fetcher_calls"],
        budget["max_elapsed_ms"],
    ):
        raise ValueError("Trace budget differs from the baseline packet")
    if "max_search_queries" in budget and parsed.max_search_queries != budget["max_search_queries"]:
        raise ValueError("Trace search budget differs from the baseline packet")
    if not budget["browser_enabled"] and any(
        action.tool == "browser" and action.policy_mode == "same_policy"
        for action in parsed.actions
    ):
        raise ValueError("Browser action is outside the baseline policy")
    case = next(case for case in packet["cases"] if case["case_id"] == parsed.case_id)
    _scope_findings(parsed, case, packet.get("public_profile", {}))
    for finding in parsed.question_findings or []:
        _publication_status(finding)
        if finding.status == "inaccessible" and not any(
            (url := parsed.actions[step - 1].url) is not None
            and _official_source(url, case)
            and parsed.actions[step - 1].outcome_status in {"failure", "blocked"}
            for step in finding.supporting_steps
        ):
            raise ValueError("Inaccessible findings need an observed failure on an official source")
    if logs_dir is not None:
        root = logs_dir.resolve()
        sources: dict[int, _SourceRead] = {}
        records: dict[int, dict[str, Any]] = {}
        calls, elapsed, queries = (
            parsed.initial_fetcher_calls,
            parsed.initial_elapsed_ms,
            parsed.initial_search_queries,
        )
        for action in parsed.actions:
            path = (root / action.raw_log_path).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Raw log path escapes the log directory")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != action.raw_log_sha256:
                raise ValueError(f"Raw tool log hash mismatch at step {action.step}")
            try:
                record = json.loads(data)
            except (ValueError, UnicodeDecodeError):
                record = None
            if _structured_log(record):
                calls, elapsed, queries = _check_controller_action(
                    action, record, calls, elapsed, queries
                )
                _controller_budget(parsed, action, record, packet.get("comparison_mode"))
                records[action.step] = record
                source = _source_read(record)
                if source is not None:
                    sources[action.step] = source
            elif parsed.question_findings is not None:
                raise ValueError("Question findings require independent structured controller logs")
            else:
                calls, elapsed = action.fetcher_calls_cumulative, action.elapsed_ms_cumulative
                if action.search_queries_cumulative is not None:
                    queries = action.search_queries_cumulative
        for proposal in parsed.proposals:
            structured_support = [step for step in proposal.supporting_steps if step in records]
            if structured_support and not any(
                step in sources
                and parsed.actions[step - 1].policy_mode == "same_policy"
                and sources[step].url == proposal.source_url
                and _official_source(sources[step].url, case)
                and proposal.accessed_on == datetime.fromisoformat(records[step]["at"]).date()
                and _quote_matches(proposal.excerpt, sources[step])
                for step in structured_support
            ):
                raise ValueError(
                    "Proposed quote needs a successful same-policy official exact source payload"
                )
        for finding in parsed.question_findings or []:
            for evidence in finding.evidence:
                source = sources.get(evidence.action_step)
                if (
                    source is None
                    or source.url != evidence.source_url
                    or not _official_source(source.url, case)
                    or not _quote_matches(evidence.excerpt, source, evidence.location)
                ):
                    raise ValueError(
                        "Finding quote or structural location is absent from its exact official source"
                    )
                if finding.status in {"found", "not_published"}:
                    _evidence_scope(finding, evidence, source)
    return parsed


def validate_trace_adjudication(
    adjudication: dict[str, Any], trace: dict[str, Any], *, logs_dir: Path
) -> TraceAdjudication:
    """Bind a separate post-submission diagnosis to observable raw log fields."""
    from .packet import digest

    parsed = TraceAdjudication.model_validate(adjudication)
    submitted = ExpertTrace.model_validate(trace)
    if parsed.trace_sha256 != digest(trace):
        raise ValueError("Adjudication was not made against this exact submitted trace")
    actions = {action.step: action for action in submitted.actions}
    root = logs_dir.resolve()
    for miss in parsed.misses:
        if set(miss.supporting_steps) - actions.keys():
            raise ValueError("Miss cause must cite recorded actions")
        for observation in miss.observations:
            action = actions[observation.action_step]
            path = (root / action.raw_log_path).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Raw log path escapes the log directory")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != action.raw_log_sha256:
                raise ValueError("Raw tool log hash mismatch during adjudication")
            record = json.loads(data)
            if not _structured_log(record):
                raise ValueError("Miss causes require observable controller records")
            value = record
            try:
                for part in observation.field.split("."):
                    value = value[int(part)] if isinstance(value, list) else value[part]
            except (KeyError, ValueError, TypeError, IndexError) as exc:
                raise ValueError("Miss observation does not identify a recorded field") from exc
            if value != observation.value:
                raise ValueError("Miss observation differs from the recorded controller field")
    return parsed
