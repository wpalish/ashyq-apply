"""Public compact selector protocol and pure expansion into unreviewed trace facts.

This module reads no corpus, bindings, requests or source files. The caller supplies
the current case's independently recorded actions and must validate the resulting
whole trace with ``validate_trace(..., logs_dir=...)`` before accepting it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Annotated, Any, Literal, Self, cast

from pydantic import (
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)

from .models import (
    QUESTIONS,
    Action,
    EvidenceLocation,
    Proposal,
    QuestionFinding,
    QuestionID,
    Strict,
)

SCOPE_DIMENSIONS = (
    "university",
    "programme",
    "degree",
    "field",
    "intake",
    "population",
    "qualification",
    "academic_year",
)
FactQuestion = Literal["Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "OTHER"]
Nonempty = Annotated[str, Field(min_length=1)]
_JSON_VALUE: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _non_json_constant(value: str) -> Any:
    raise ValueError(f"Non-JSON numeric constant: {value}")


def _load_json(value: str) -> Any:
    result = json.loads(
        value, object_pairs_hook=_unique_json_object, parse_constant=_non_json_constant
    )
    # A large exponent such as 1e999 is parsed as infinity without parse_constant.
    json.dumps(result, allow_nan=False)
    return result


class CompactStrict(Strict):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class CompactScope(CompactStrict):
    """All public evaluation dimensions are explicit; null never means universal."""

    university: Nonempty | None
    programme: Nonempty | None
    degree: Nonempty | None
    field: Nonempty | None
    intake: Nonempty | None
    population: Nonempty | None
    qualification: Nonempty | None
    academic_year: Nonempty | None

    @field_validator(*SCOPE_DIMENSIONS)
    @classmethod
    def stated_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("A stated scope dimension must contain text")
        return value


class CompactLocation(CompactStrict):
    kind: Literal["text", "document_ir", "pdf"]
    block_id: Nonempty | None
    section_path: list[Nonempty]
    page: int | None = Field(ge=1, le=40)

    @model_validator(mode="after")
    def coordinates(self) -> Self:
        EvidenceLocation.model_validate(self.model_dump())
        return self


class CompactAction(CompactStrict):
    """One bounded navigation request, including a view of already saved bytes."""

    tool: Literal["fetcher", "search_provider", "view"]
    url: HttpUrl | None
    query: Nonempty | None
    domains: list[Nonempty]
    max_results: int | None = Field(ge=1, le=100)
    source_step: int | None = Field(ge=1)
    page: int | None = Field(ge=1, le=40)
    offset: int | None = Field(ge=0)
    section_offset: int | None = Field(ge=0)
    link_offset: int | None = Field(ge=0)

    @model_validator(mode="after")
    def one_tool(self) -> Self:
        if self.tool == "view":
            if self.source_step is None:
                raise ValueError("Stored view needs its recorded source_step")
            if (
                self.url is not None
                or self.query is not None
                or self.domains
                or self.max_results is not None
            ):
                raise ValueError("Stored view cannot request a new fetch or search")
            return self
        if any(
            value is not None
            for value in (
                self.source_step,
                self.page,
                self.offset,
                self.section_offset,
                self.link_offset,
            )
        ):
            raise ValueError("Only a stored view accepts source_step and pagination")
        if self.tool == "fetcher":
            if (
                self.url is None
                or self.query is not None
                or self.domains
                or self.max_results is not None
            ):
                raise ValueError("Fetcher navigation needs only its explicit URL")
        elif (
            self.url is not None
            or self.query is None
            or not self.domains
            or self.max_results is None
        ):
            raise ValueError("Search navigation needs query, official domains and max_results")
        if self.query is not None and not self.query.strip():
            raise ValueError("Search query must contain text")
        if any(not domain.strip() for domain in self.domains):
            raise ValueError("Search domains must contain text")
        return self

    def controller_request(self) -> dict[str, Any]:
        """Remove inactive parameters without inventing a request or a view offset."""
        if self.tool == "fetcher":
            return {"tool": "fetcher", "url": str(self.url)}
        if self.tool == "search_provider":
            return {
                "tool": self.tool,
                "query": self.query,
                "domains": list(self.domains),
                "max_results": self.max_results,
            }
        return {
            key: value
            for key, value in self.model_dump(mode="json").items()
            if key in {"tool", "source_step", "page", "offset", "section_offset", "link_offset"}
            and value is not None
        }


class CompactFact(CompactStrict):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
    question: FactQuestion
    claim_key: str = Field(min_length=1, max_length=200)
    value_json: str = Field(min_length=1, max_length=16000)
    source_step: int = Field(ge=1)
    quotation: str = Field(min_length=1, max_length=600)
    location: CompactLocation
    scope: CompactScope

    @field_validator("claim_key", "quotation")
    @classmethod
    def real_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Claim key and quotation must contain text")
        return value

    @field_validator("value_json")
    @classmethod
    def json_encoded_value(cls, value: str) -> str:
        _JSON_VALUE.validate_python(_load_json(value), strict=True)
        return value

    @model_validator(mode="after")
    def stated_university(self) -> Self:
        if self.scope.university is None:
            raise ValueError("Fact university must be explicitly declared from source evidence")
        return self

    def decoded_value(self) -> JsonValue:
        return _JSON_VALUE.validate_python(_load_json(self.value_json), strict=True)


class CompactFinding(CompactStrict):
    question: QuestionID
    status: Literal["found", "not_published", "inaccessible", "unresolved"]
    fact_ids: list[Nonempty]
    scope: CompactScope
    observation: Nonempty
    supporting_steps: list[Annotated[int, Field(ge=1)]]

    @model_validator(mode="after")
    def explicit_support(self) -> Self:
        if not self.observation.strip():
            raise ValueError("Finding observation must contain text")
        if len(set(self.fact_ids)) != len(self.fact_ids):
            raise ValueError("Finding fact_ids must be unique")
        if len(set(self.supporting_steps)) != len(self.supporting_steps):
            raise ValueError("Finding supporting_steps must be unique")
        if self.status in {"found", "not_published"}:
            if not self.fact_ids:
                raise ValueError("Found and not_published need explicit supporting fact_ids")
            if self.supporting_steps:
                raise ValueError("Successful evidence steps derive only from referenced facts")
        if self.status == "inaccessible" and (self.fact_ids or not self.supporting_steps):
            raise ValueError("Inaccessible needs failed supporting steps and no source facts")
        return self


class CompactDecision(CompactStrict):
    """A single root object works with constrained model output schemas."""

    kind: Literal["action", "submit"]
    observation: Nonempty
    action: CompactAction | None
    facts: list[CompactFact] = Field(max_length=128)
    question_findings: list[CompactFinding] = Field(max_length=7)

    @model_validator(mode="after")
    def one_decision(self) -> Self:
        if not self.observation.strip():
            raise ValueError("Decision observation must contain text")
        if self.kind == "action":
            if self.action is None or self.facts or self.question_findings:
                raise ValueError("Navigation needs one action and empty submission lists")
        elif self.action is not None:
            raise ValueError("Final submission must have action=null")
        if len({fact.id for fact in self.facts}) != len(self.facts):
            raise ValueError("Submitted fact IDs must be unique")
        if len({finding.question for finding in self.question_findings}) != len(
            self.question_findings
        ):
            raise ValueError("Submitted question findings must be unique")
        facts = {fact.id: fact for fact in self.facts}
        for finding in self.question_findings:
            for fact_id in finding.fact_ids:
                if fact_id not in facts:
                    raise ValueError("Finding fact_ids must reference submitted facts")
                if facts[fact_id].question != finding.question:
                    raise ValueError("Finding references a fact assigned to a different question")
        return self


def compact_schema() -> dict[str, Any]:
    """Provider schema without unsupported URI formats; local HttpUrl stays typed."""
    schema = CompactDecision.model_json_schema()

    def remove_uri_format(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("format") == "uri":
                del value["format"]
            for child in value.values():
                remove_uri_format(child)
        elif isinstance(value, list):
            for child in value:
                remove_uri_format(child)

    remove_uri_format(schema)
    return schema


def parse_compact_decision(value: str | Mapping[str, Any] | CompactDecision) -> CompactDecision:
    """Parse a decision without coercing values, losing duplicate keys or filling scope."""
    if isinstance(value, CompactDecision):
        value = value.model_dump(mode="json")
    elif isinstance(value, str):
        value = _load_json(value)
    return CompactDecision.model_validate(value)


def _current_actions(
    actions: Sequence[Action | Mapping[str, Any]], *, ended_at: datetime, case_id: str | None
) -> dict[int, Action]:
    if ended_at.tzinfo is None:
        raise ValueError("Submission time must include a timezone")
    result: dict[int, Action] = {}
    previous: datetime | None = None
    for recorded in actions:
        raw = recorded.model_dump() if isinstance(recorded, Action) else dict(recorded)
        if "case_id" in raw and (case_id is None or raw.pop("case_id") != case_id):
            raise ValueError("Recorded source action belongs to a different case")
        action = Action.model_validate(raw)
        if action.step != len(result) + 1:
            raise ValueError("Current-case recorded actions must have consecutive unique steps")
        if action.at > ended_at:
            raise ValueError("Recorded source action is later than the submission")
        if previous is not None and action.at < previous:
            raise ValueError("Recorded source actions must be chronological")
        result[action.step] = action
        previous = action.at
    return result


def _recorded_step(step: int, actions: dict[int, Action]) -> Action:
    if step not in actions:
        raise ValueError("Evidence step must reference a recorded current-case action")
    return actions[step]


def _source_action(step: int, actions: dict[int, Action]) -> Action:
    action = _recorded_step(step, actions)
    if not (
        action.tool in {"fetcher", "browser"}
        and action.policy_mode == "same_policy"
        and action.outcome_status == "success"
        and action.url is not None
    ):
        raise ValueError("Facts need a successful same-policy recorded page read")
    return action


def _compatible_facts(finding: CompactFinding, facts: list[CompactFact]) -> None:
    declared = finding.scope.model_dump()
    for fact in facts:
        fact_scope = fact.scope.model_dump()
        if any(value is not None and fact_scope[key] != value for key, value in declared.items()):
            raise ValueError("Finding scope disagrees with its explicitly referenced fact scope")
    for index, fact in enumerate(facts):
        left = fact.scope.model_dump()
        for other in facts[index + 1 :]:
            right = other.scope.model_dump()
            if any(
                left[key] is not None and right[key] is not None and left[key] != right[key]
                for key in left
            ):
                raise ValueError("Referenced fact scopes conflict; no scope union is permitted")


def _fact_value_signature(fact: CompactFact) -> str:
    return json.dumps(fact.decoded_value(), sort_keys=True, ensure_ascii=False, allow_nan=False)


def _reject_found_conflicts(finding: CompactFinding, facts: Sequence[CompactFact]) -> None:
    relevant = [fact for fact in facts if fact.question == finding.question]
    for index, fact in enumerate(relevant):
        for other in relevant[index + 1 :]:
            if (
                fact.claim_key == other.claim_key
                and fact.scope == other.scope
                and _fact_value_signature(fact) != _fact_value_signature(other)
            ):
                raise ValueError("Submitted facts conflict; the question must remain unresolved")


def expand_submission(
    decision: CompactDecision | str | Mapping[str, Any],
    actions: Sequence[Action | Mapping[str, Any]],
    *,
    ended_at: datetime,
    case_id: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Mechanically expand; the complete trace still requires independent raw-log validation.

    Each submitted fact remains a separate proposal in its original order. The
    source URL is the selected action's final URL (or its requested URL when no
    redirect was recorded), and the access date is that same action's local date.
    No value, scope, scholarship identity or positive answer is inferred.
    """
    parsed = parse_compact_decision(decision)
    if parsed.kind != "submit":
        raise ValueError("Only a final submission can be expanded into trace facts")
    recorded = _current_actions(actions, ended_at=ended_at, case_id=case_id)
    proposals: list[dict[str, Any]] = []
    evidence: dict[str, dict[str, Any]] = {}
    fact_indices = {fact.id: index for index, fact in enumerate(parsed.facts)}
    facts = {fact.id: fact for fact in parsed.facts}
    for fact in parsed.facts:
        source = _source_action(fact.source_step, recorded)
        source_url = source.final_url or source.url
        proposal = Proposal(
            claim_key=fact.claim_key,
            value=fact.decoded_value(),
            source_url=cast(HttpUrl, source_url),
            excerpt=fact.quotation,
            accessed_on=source.at.date(),
            scope=fact.scope.model_dump(),
            supporting_steps=[source.step],
        )
        proposals.append(proposal.model_dump(mode="json"))
        evidence[fact.id] = {
            "action_step": source.step,
            "source_url": str(source_url),
            "excerpt": fact.quotation,
            "location": fact.location.model_dump(mode="json"),
        }
    submitted = {finding.question: finding for finding in parsed.question_findings}
    findings: list[dict[str, Any]] = []
    for question in QUESTIONS:
        finding = submitted.get(cast(QuestionID, question))
        if finding is None:
            expanded = QuestionFinding(
                question=cast(QuestionID, question),
                status="unresolved",
                observation="No finding was submitted for this question.",
            )
        else:
            referenced = [facts[fact_id] for fact_id in finding.fact_ids]
            if finding.status in {"found", "not_published"}:
                _compatible_facts(finding, referenced)
                _reject_found_conflicts(finding, parsed.facts)
            supporting_steps = list(finding.supporting_steps)
            for step in supporting_steps:
                supporting = _recorded_step(step, recorded)
                if finding.status == "inaccessible" and not (
                    supporting.tool in {"fetcher", "browser"}
                    and supporting.outcome_status in {"failure", "blocked"}
                    and supporting.policy_mode == "same_policy"
                    and supporting.url is not None
                ):
                    raise ValueError("Inaccessible needs failed same-policy recorded page reads")
            for fact in referenced:
                if fact.source_step not in supporting_steps:
                    supporting_steps.append(fact.source_step)
            expanded = QuestionFinding(
                question=finding.question,
                status=finding.status,
                supporting_steps=supporting_steps,
                proposal_indices=[fact_indices[fact_id] for fact_id in finding.fact_ids],
                evidence=[evidence[fact_id] for fact_id in finding.fact_ids],
                scope=finding.scope.model_dump(),
                observation=finding.observation,
            )
        findings.append(expanded.model_dump(mode="json"))
    return {"proposals": proposals, "question_findings": findings}


COMPACT_INSTRUCTIONS = """Return one JSON object matching the compact schema.
Use kind=action for exactly one navigation decision: supply action, explain the
preceding observation, and set facts=[] and question_findings=[]. Use tool=fetcher
with an explicit official URL, or tool=search_provider with a query, official
domains and max_results. Tool=view reads only an already saved source_step; it may
specify PDF page (1-40), text offset, section_offset and link_offset. A view makes
no new university request. Set irrelevant action parameters to null and domains
to []. Fetch/search cannot carry view parameters. Never invent recorded steps.

Use kind=submit for the final answer: action=null and a complete list of the facts
you are submitting. Each fact needs a unique id, its explicit question Q0-Q6 or
OTHER, a public claim_key, JSON-encoded value_json, one successful same-policy
page-read source_step, an exact quotation of 1-600 characters, location, and scope.
value_json is a STRING containing JSON: \"false\" represents boolean false;
\"6.5\" represents a number; \"\\\"text\\\"\" represents a string. Never replace an
explicit negative existence fact with true. Search snippets are discovery only.
For programme.exists, use a JSON boolean: value_json=\"true\" only when the
source explicitly establishes that exact programme exists, and value_json=\"false\"
for explicitly established nonexistence. Do not encode existence as an object.
Do not provide source_url or accessed_on: both derive from that recorded action,
including its final redirected URL and its own timestamp's date.

Use text location only for readable text, document_ir with the exact block_id and
section_path shown in the stored view, or pdf with the exact one-based page.
Every location field is explicit; unused block_id/page are null and unused
section_path is []. All eight scope fields are explicit: university, programme,
degree, field, intake, population, qualification, academic_year. Declare a nonempty
source-supported university for each fact. Use null for every dimension the
source does not establish. Never fill scope from the public request or infer
equivalence. Preserve source values, names, units, conditions and year.

The public claim_key namespace includes programme.exists, programme.language,
programme.faculty, programme.admission_route, intake, intake.open, ielts.overall,
ielts.subscores, sat.policy, sat.minimum,
deadline, tuition, mandatory_fees, application_fee, country_credential,
country_credential.<credential>.<field>, subjects.<subject>.required,
<language>.<stage>_minimum, english_evidence.<test>.minimum,
documents.<stage>.<document>, and scholarships.<declared-public-award>.<dimension>.
Keep any other public key unchanged. Never infer a private scholarship identity
or invent an award ID; if its public subject is not established, use OTHER and a
descriptive unmapped.<claim_type> key. Expansion does not resolve identities.

Question findings are sparse and explicit. Q0 asks exact bachelor programme
existence; Q1 international English tests; Q2 the applicant's international
secondary qualification; Q3 the correct international intake deadline; Q4 the
international fee in the correct academic year; Q5 bachelor scholarship existence;
Q6 international eligibility for that scholarship. Each supplied finding needs
question, status, explicit fact_ids, all eight scope fields, an observation and
supporting_steps. For found, reference compatible facts assigned to that question.
For not_published, reference exact official-page evidence explicitly saying the
requested information is not published; a limited search does not establish this.
For either status, supporting_steps=[] because steps derive from those facts.
For inaccessible, fact_ids=[] and cite failed or blocked same-policy official
page-read supporting_steps. For unresolved, record what remains unsettled and
optionally reference recorded steps/facts. Contradictory values or scopes must
remain unresolved, with separate fact IDs; do not union values or take the last.
Omitted questions become unresolved with no inferred evidence. Empty facts never
imply not_published or inaccessible. All facts remain unreviewed and the resulting
trace must pass independent saved-payload quotation, location, scope and policy
validation before acceptance.
"""
