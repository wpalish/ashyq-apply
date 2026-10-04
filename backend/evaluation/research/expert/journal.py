"""Pure append-only checkpoints for the public compact selector protocol.

Candidate construction establishes structural and recorded-action consistency.
The caller must independently validate the complete trace and every saved-source
citation before replacing or persisting its accepted journal reference.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Self, cast

from pydantic import Field, model_validator

from .compact import (
    CompactAction,
    CompactDecision,
    CompactFact,
    CompactFinding,
    CompactStrict,
    Nonempty,
    _compatible_facts,
    _load_json,
    expand_submission,
    parse_compact_decision,
)
from .models import Action

_HASH_PATTERN = r"^[0-9a-f]{64}$"
_OBSERVATION = "Submit the complete journal; all proposed evidence remains unreviewed."


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _reject_conflicts(facts: Sequence[CompactFact]) -> None:
    """No question or fact ID can hide a conflict for the same public key/scope."""
    values: dict[tuple[str, str], str] = {}
    for fact in facts:
        key = fact.claim_key, _canonical_json(fact.scope.model_dump(mode="json"))
        value = _canonical_json(fact.decoded_value())
        if key in values and values[key] != value:
            raise ValueError("Journal facts conflict for the same claim key and declared scope")
        values[key] = value


class JournalDecision(CompactStrict):
    kind: Literal["action", "record", "submit"]
    observation: Nonempty
    journal_sha256: str = Field(pattern=_HASH_PATTERN)
    action: CompactAction | None
    facts: list[CompactFact] = Field(max_length=16)
    question_findings: list[CompactFinding] = Field(max_length=7)

    @model_validator(mode="after")
    def checkpoint_shape(self) -> Self:
        if not self.observation.strip():
            raise ValueError("Journal observation must contain text")
        if self.kind == "action":
            if self.action is None:
                raise ValueError("Action decision needs exactly one controlled action")
        elif self.action is not None:
            raise ValueError("Record and submit decisions require action=null")
        if self.kind == "record" and not (self.facts or self.question_findings):
            raise ValueError("Record needs new facts or question findings")
        if len({fact.id for fact in self.facts}) != len(self.facts):
            raise ValueError("New journal fact IDs must be unique")
        if len({finding.question for finding in self.question_findings}) != len(
            self.question_findings
        ):
            raise ValueError("New journal question findings must be unique")
        # A finding may reference a retained fact absent from this small delta.
        # The complete CompactDecision validates those references in candidate().
        return self


class _JournalSnapshot(CompactStrict):
    schema_version: Literal["1"]
    journal_sha256: str = Field(pattern=_HASH_PATTERN)
    facts: list[CompactFact] = Field(max_length=128)
    question_findings: list[CompactFinding] = Field(max_length=7)


def parse_journal_decision(
    value: JournalDecision | str | Mapping[str, Any],
) -> JournalDecision:
    """Reject duplicate JSON and revalidate mutable input models without coercion."""
    if isinstance(value, JournalDecision):
        value = value.model_dump(mode="json")
    elif isinstance(value, str):
        value = _load_json(value)
    return JournalDecision.model_validate(value)


def journal_schema() -> dict[str, Any]:
    """Provider-facing schema; local CompactAction retains typed HttpUrl validation."""
    schema = JournalDecision.model_json_schema()

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


@dataclass(frozen=True, slots=True)
class AcceptedJournal:
    """Immutable retained records; acceptance also requires the caller's raw-log gate.

    Private state is immutable canonical JSON, so returned Pydantic models and
    snapshots cannot mutate retained facts through their nested dictionaries/lists.
    Only explicitly submitted sparse findings are stored. Synthesized unresolved
    findings belong to expansion and never become immutable journal entries.
    """

    _facts_json: tuple[str, ...] = ()
    _findings_json: tuple[str, ...] = ()
    _sha256: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self._facts_json, tuple) or not isinstance(self._findings_json, tuple):
            raise TypeError("Journal storage must be immutable tuples")
        if any(not isinstance(value, str) for value in (*self._facts_json, *self._findings_json)):
            raise TypeError("Journal storage must contain immutable JSON strings")
        submission = self.as_submission()
        _reject_conflicts(submission.facts)
        by_id = {fact.id: fact for fact in submission.facts}
        for finding in submission.question_findings:
            if finding.status in {"found", "not_published"}:
                _compatible_facts(finding, [by_id[fact_id] for fact_id in finding.fact_ids])
        object.__setattr__(
            self,
            "_facts_json",
            tuple(_canonical_json(fact.model_dump(mode="json")) for fact in submission.facts),
        )
        object.__setattr__(
            self,
            "_findings_json",
            tuple(
                _canonical_json(finding.model_dump(mode="json"))
                for finding in submission.question_findings
            ),
        )
        object.__setattr__(
            self,
            "_sha256",
            hashlib.sha256(_canonical_json(self._payload()).encode("utf-8")).hexdigest(),
        )

    @classmethod
    def initial(cls) -> Self:
        return cls()

    @property
    def sha256(self) -> str:
        """Digest of canonical complete facts/findings only, with no timestamp."""
        return self._sha256

    @property
    def facts(self) -> tuple[CompactFact, ...]:
        return tuple(CompactFact.model_validate(_load_json(value)) for value in self._facts_json)

    @property
    def question_findings(self) -> tuple[CompactFinding, ...]:
        return tuple(
            CompactFinding.model_validate(_load_json(value)) for value in self._findings_json
        )

    def _payload(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "facts": [cast(dict[str, Any], _load_json(value)) for value in self._facts_json],
            "question_findings": [
                cast(dict[str, Any], _load_json(value)) for value in self._findings_json
            ],
        }

    def as_submission(self, observation: str | None = None) -> CompactDecision:
        """Fresh complete submission; no previously accepted fields are regenerated."""
        return parse_compact_decision(
            {
                "kind": "submit",
                "observation": _OBSERVATION if observation is None else observation,
                "action": None,
                **self._payload(),
            }
        )

    def snapshot(self) -> dict[str, Any]:
        """Fresh strict persisted mapping; serializing it is the caller's responsibility."""
        return {"schema_version": "1", "journal_sha256": self.sha256, **self._payload()}

    @classmethod
    def from_snapshot(cls, value: str | Mapping[str, Any]) -> Self:
        """Verify content, structure and SHA; raw sources still require caller validation."""
        if isinstance(value, str):
            value = _load_json(value)
        parsed = _JournalSnapshot.model_validate(value)
        restored = cls(
            _facts_json=tuple(
                _canonical_json(fact.model_dump(mode="json")) for fact in parsed.facts
            ),
            _findings_json=tuple(
                _canonical_json(finding.model_dump(mode="json"))
                for finding in parsed.question_findings
            ),
        )
        if restored.sha256 != parsed.journal_sha256:
            raise ValueError("Journal snapshot SHA does not match its complete retained content")
        return restored

    def candidate(
        self,
        decision: JournalDecision | str | Mapping[str, Any],
        actions: Sequence[Action | Mapping[str, Any]],
        *,
        ended_at: datetime,
        case_id: str | None = None,
    ) -> Self:
        """Return a new candidate atomically; never replace or persist accepted state.

        A navigation decision may append a delta before choosing its next action.
        Facts can reference only already completed current-case source reads.
        All retained facts/findings are re-expanded against the supplied ledger.
        The caller must validate the complete trace and every raw citation before
        accepting this returned object, including facts assigned to OTHER.
        """
        parsed = parse_journal_decision(decision)
        if parsed.journal_sha256 != self.sha256:
            raise ValueError("Decision prior journal SHA is stale or does not match")
        known_ids = {fact.id for fact in self.facts}
        if any(fact.id in known_ids for fact in parsed.facts):
            raise ValueError("Existing journal fact ID cannot be appended again, even identically")
        known_questions = {finding.question for finding in self.question_findings}
        if any(finding.question in known_questions for finding in parsed.question_findings):
            raise ValueError(
                "Existing journal question finding is immutable and cannot be repeated"
            )
        result = type(self)(
            _facts_json=self._facts_json
            + tuple(_canonical_json(fact.model_dump(mode="json")) for fact in parsed.facts),
            _findings_json=self._findings_json
            + tuple(
                _canonical_json(finding.model_dump(mode="json"))
                for finding in parsed.question_findings
            ),
        )
        expand_submission(
            result.as_submission(parsed.observation), actions, ended_at=ended_at, case_id=case_id
        )
        if parsed.action is not None and parsed.action.tool == "view":
            recorded_steps = {
                action.step if isinstance(action, Action) else action["step"] for action in actions
            }
            if parsed.action.source_step not in recorded_steps:
                raise ValueError("Stored view source_step must refer to an already recorded action")
        return result


JOURNAL_INSTRUCTIONS = """Return one complete JSON object matching the journal schema.
Every object must include the exact journal_sha256 currently shown by the
controller. This binds the prior retained facts/findings; never invent or reuse
an older SHA. The controller may accept a small checkpoint before the next action.

Use kind=action to choose exactly one controlled CompactAction. You may also
include a delta of at most16 NEW facts and at most7 NEW question findings from
already completed source reads. Use kind=record with action=null for a nonempty
delta alone. Use kind=submit with action=null to close: facts=[] and
question_findings=[] are enough to commit the current journal by hash. A final
object may instead carry a last new delta. Do not regenerate previously recorded
quotes, repeat a fact ID, or repeat any explicitly recorded question finding.

Each new fact has a unique id, question Q0-Q6 or OTHER, exact public claim_key,
JSON-encoded value_json STRING, one successful same-policy page-read source_step,
an exact 1-600 character quotation, structural location, and all eight explicit
scope fields: university, programme, degree, field, intake, population,
qualification, academic_year. University must be a nonempty source-supported
string. Unstated dimensions are null; never fill them from the request. For
programme.exists, value_json=\"true\" means source-established exact existence;
value_json=\"false\" means explicitly established nonexistence. Preserve typed
false and all other source values, conditions and years; never union values or
take the last conflicting value. Source URL/date derive solely from that recorded
action's final URL and timestamp. Do not supply them or infer scholarship IDs.

Use any declared public claim_key, including programme.*, intake.*, ielts.*,
sat.*, deadline, tuition, mandatory_fees, application_fee, country_credential.*,
subjects.*, english_evidence.*, documents.*, scholarships.<public-award>.*, or
unmapped.<claim_type>. Keep the full namespace and declared public subject;
an unresolved award identity is never an inferred private ID.

Location uses text, document_ir with exact block_id/section_path, or pdf with an
exact one-based page1-40. All location fields are explicit; unused block_id/page
are null and unused section_path is []. Navigation uses tool=fetcher for an
explicit official URL, search_provider for query/domains/max_results, or view
for an ALREADY RECORDED source_step and optional page/offset/section_offset/
link_offset. View reads saved bytes and performs no new university request.
Set irrelevant action parameters to null and domains=[] when not searching.
An upcoming action cannot support a fact or supply a view's source_step.

Q0 asks exact bachelor programme existence; Q1 international English tests; Q2
international secondary qualification eligibility; Q3 the correct international
intake deadline; Q4 the international fee for the correct academic year; Q5
bachelor scholarship existence; Q6 international eligibility for that scholarship.
Question findings are sparse and may reference NEW or RETAINED fact_ids assigned
to that same question, with compatible explicit scopes. For found or
not_published, supporting_steps=[] derives from those facts; not_published needs
an explicit official publication statement. A limited search never proves
nonpublication. Inaccessible needs fact_ids=[] and actual failed/blocked
same-policy page-read supporting_steps. Every explicitly recorded finding is
immutable, including unresolved/inaccessible. Omit unresolved/inaccessible until
closing if the question may later resolve. Mechanically synthesized unresolved
defaults are NOT recorded journal entries and do not prevent a later finding.
Omitted questions remain unresolved at expansion; empty facts imply no absence.

The controller rejects the entire candidate for a stale SHA, repeated ID/question,
bad references, incompatible scopes or conflicting same-key/scope values,
including OTHER. It independently validates the whole trace and EVERY raw-source
quotation/location before accepting a candidate. Returned candidates are not
automatically accepted. A later invalid or timed-out selector retains earlier
accepted checkpoints for audit; this does not establish a completed clean run.
Partial timeout text is never a journal decision. All facts stay unreviewed.
"""
