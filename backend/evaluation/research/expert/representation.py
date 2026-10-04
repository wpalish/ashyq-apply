"""Pure public representation guidance and bound V4 selector envelopes.

No identity aliases, evidence files, reviewed answers or prior cases are read.
Schema bindings constrain representation, not truth. Callers must still validate
the entire journal/trace and every recorded quotation before accepting a delta.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from pydantic import JsonValue, TypeAdapter

from ..mapping import AWARD_KEYS, CLAIM_KEYS, IELTS_BANDS, STRUCTURED_KEYS
from .compact import CompactDecision, parse_compact_decision
from .journal import JournalDecision, journal_schema, parse_journal_decision

REPRESENTATION_VERSION = "expert500-representation-v4.1"
CLOSING_OBSERVATION = "Commit the accepted journal by hash."
_HASH_PATTERN = r"^[0-9a-f]{64}$"
_JSON_VALUE: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def _journal_hash(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(_HASH_PATTERN, value) is None:
        raise ValueError("Current journal SHA must be exactly 64 lowercase hexadecimal characters")
    return value


def _university(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Canonical university must be a nonempty public packet string")
    return value


def attributed_university(
    canonical_university: str, *, source_attribution_proven: bool
) -> str | None:
    """Choose exact public attribution only after a caller-established proof.

    The flag is a trusted caller result, never a model claim or a domain heuristic
    supplied by this helper. A canonical string/enum does not establish that a
    source belongs to the university. No other scope dimension is filled.
    """
    university = _university(canonical_university)
    if type(source_attribution_proven) is not bool:
        raise ValueError("Source attribution proof must be an explicit boolean")
    return university if source_attribution_proven else None


def representation_card(canonical_university: str) -> str:
    """Return current-case public guidance based on the existing mapper/types.

    Examples describe JSON transport only. Keys without a narrower public type
    remain JsonValue; this card adds no normalizer or new fact/value shape.
    """
    university = json.dumps(_university(canonical_university), ensure_ascii=False)
    aliases = json.dumps(CLAIM_KEYS, ensure_ascii=False, separators=(",", ":"))
    structured = json.dumps(
        {
            name: {"fields": [*names, field], "output_key": template, "output_value_field": field}
            for name, (template, names, field) in STRUCTURED_KEYS.items()
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    bands = json.dumps({band: 6.0 for band in IELTS_BANDS}, separators=(",", ":"))
    award_types = ", ".join(["scholarship_coverage", *AWARD_KEYS])
    return f"""PUBLIC REPRESENTATION CARD ({REPRESENTATION_VERSION})
University: the only canonical public packet string is {university}. Use that
exact string only when controlled source attribution to this institution is
proven. A domain, requested identity or schema enum alone is not attribution
proof. Otherwise university remains null: do not emit a source fact until its
attribution is established (the local fact model requires a stated university).
Preserve literal institution wording in the exact quotation; do not invent an
alias or relabel a different institution. No private alias registry is available.

Programme: copy the literal programme title supported at the cited location,
without adding degree words or substituting the requested title. Degree=bachelor
and field=computer science are separate canonical categories only when that
source establishes them. All eight scope fields are explicit; every other
unstated degree/field/intake/population/qualification/year/programme remains null.
Never fill applicability from the request or combine incompatible scopes.

value_json is a STRING containing JSON, decoded without coercion. Synthetic
transport examples: \"true\" and \"false\" decode to booleans; \"6.0\" is a number;
\"\\\"example\\\"\" is a string; \"null\" is JSON null. These are not admissions facts.
programme.exists uses a source-established boolean, not a programme-name object.
Empty search results establish neither boolean false nor publication absence.
Keep all source values, units, conditions and years. Other values use the existing
JsonValue type (boolean/number/string/null/list/object); do not invent a universal
money/date/policy shape or drop conditions to turn an object into a scalar.
The legacy ielts_min_subscore mapper expands a numeric floor to all four bands;
use that only when the source explicitly states one floor for every band.
Synthetic four-band object: {bands}. Missing bands must not be filled.
Canonical output keys pass through unchanged. Public input aliases: {aliases}
Structured input requires exactly the declared fields, public subject slugs
[a-z0-9_]+ and the value field; mapping emits the key and preserves that field's
typed value. Public structured contracts: {structured}
Award facts: scholarship_exists has a JSON STRING containing the exact literal
official award name. For these public input types: {award_types}, value_json
contains exactly {{"subject":"verbatim official award name","value":<original
typed published value>}}. Synthetic transport example only:
{{"subject":"Example Merit Award","value":{{"currency":"EXAMPLE","amount":123}}}}.
Keep the source value's original type/conditions/units; no fixed money shape is
imposed. The subject must appear as an exact case-sensitive substring in this
fact's citation-validated selected block/headers/section, exact PDF page or plain
context. A name elsewhere on the page is not proof for a different cited block.
No private award IDs or scholarships.* keys may be guessed. Exact official
URL+subject identity resolution happens privately after sealing; an unknown
identity remains unmapped. Document private identity is never inferred either.

Question assignment: a deadline for an explicitly older/different intake is OTHER
with that source's actual intake, not the requested Q3. The same rule applies to
an explicitly different fee year for Q4. Keep the source's typed value unchanged;
do not shift a date/year or reinterpret publication date as intake. Q3/Q4 remain
unresolved without matching source scope. OTHER receives every citation/scope
check. not_published requires an explicit official publication statement.

Evidence: use an already completed successful same-policy page-read source_step,
an exact 1-600 character quotation and its real coordinates: text with block_id
and page null/section_path []; document_ir with exact block_id and section_path;
or pdf with its exact one-based page1-40. PDF evidence cannot cite aggregate text.
Unused coordinates stay null or []. URL/access date derive only from that recorded
action. No upcoming action, search snippet or request supplies evidence. Full
journal, raw-log, quotation, location and scope validation remains mandatory.
"""


def journal_schema_for_case(*, journal_sha256: str, canonical_university: str) -> dict[str, Any]:
    """Bind the current SHA and public university without changing source models.

    Null is an allowed schema representation of unknown university, even though
    a source fact with null university fails the unchanged local fact validator.
    Both fact and finding scopes share the bound CompactScope definition.
    """
    current_hash, university = _journal_hash(journal_sha256), _university(canonical_university)
    schema = journal_schema()
    schema["properties"]["journal_sha256"]["enum"] = [current_hash]
    schema["$defs"]["CompactScope"]["properties"]["university"]["enum"] = [None, university]
    return schema


def closing_schema(*, journal_sha256: str) -> dict[str, Any]:
    """The same six journal fields, with no navigation, delta or large definitions."""
    current_hash = _journal_hash(journal_sha256)
    properties: dict[str, Any] = {
        "kind": {"type": "string", "enum": ["submit"]},
        "observation": {"type": "string", "enum": [CLOSING_OBSERVATION]},
        "journal_sha256": {"type": "string", "pattern": _HASH_PATTERN, "enum": [current_hash]},
        "action": {"type": "null"},
        "facts": {"type": "array", "items": {"type": "null"}, "maxItems": 0},
        "question_findings": {"type": "array", "items": {"type": "null"}, "maxItems": 0},
    }
    return {
        "title": "JournalHashOnlySubmit",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def closing_prompt(*, journal_sha256: str) -> dict[str, str]:
    """A fresh commit prompt with only the current hash and output instructions.

    This prompt establishes no clean completion or budget eligibility by itself.
    The caller meters the completed selector and runs all final journal gates.
    """
    return {
        "task": (
            "Commit the accepted journal without adding or repeating facts/findings. "
            "Return exactly the six required fields: kind=submit, observation="
            + json.dumps(CLOSING_OBSERVATION)
            + ", journal_sha256=current hash, action=null, facts=[], question_findings=[]. "
            "Copy the current hash exactly. Do not navigate or regenerate evidence."
        ),
        "journal_sha256": _journal_hash(journal_sha256),
    }


def award_value(claim_key: str, value: JsonValue) -> tuple[str, JsonValue] | None:
    """Read a literal public subject without resolving any private identity.

    Existence uses its literal string as subject and value. Other public award
    aliases carry exactly subject/value; their published value stays typed and
    may have any existing JsonValue shape. Guessed canonical IDs are rejected.
    """
    if not isinstance(claim_key, str) or not claim_key.strip():
        raise ValueError("Award claim key must be a nonempty string")
    if claim_key.startswith("scholarships."):
        raise ValueError(
            "Award facts need a literal public subject, never guessed scholarships.* IDs"
        )
    if claim_key not in AWARD_KEYS and claim_key not in {
        "scholarship_exists",
        "scholarship_coverage",
    }:
        return None
    decoded = _JSON_VALUE.validate_python(value, strict=True)
    # JsonValue permits floats; nonfinite values still cannot be public JSON.
    json.dumps(decoded, allow_nan=False)
    if claim_key == "scholarship_exists":
        if not isinstance(decoded, str) or not decoded.strip():
            raise ValueError("scholarship_exists requires a nonempty literal award-name string")
        return decoded, decoded
    if not isinstance(decoded, dict) or set(decoded) != {"subject", "value"}:
        raise ValueError("Public award facts require exactly the subject/value wrapper")
    subject = decoded["subject"]
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Award subject must be a nonempty literal string")
    return subject, decoded["value"]


def validate_award_subjects(
    decision: JournalDecision | CompactDecision, *, contexts_by_fact_id: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Check all literal subjects in caller-validated, fact-specific contexts.

    The caller first completes raw-log/citation validation and supplies each
    fact's selected plain context, exact PDF page, or selected IR block with its
    headers/section path. A whole-page IR aggregate is not that selected context.
    This pure helper neither loads sources nor certifies their provenance. Its
    proof metadata must be sealed together with the caller's original raw proof.
    """
    if isinstance(decision, JournalDecision):
        facts = parse_journal_decision(decision).facts
    elif isinstance(decision, CompactDecision):
        facts = parse_compact_decision(decision).facts
    else:
        raise ValueError("Award subject validation needs an original parsed journal/compact model")
    proof = []
    for fact in facts:
        subject_value = award_value(fact.claim_key, fact.decoded_value())
        if subject_value is None:
            continue
        subject, _ = subject_value
        context = contexts_by_fact_id.get(fact.id)
        if not isinstance(context, str) or not context or subject not in context:
            raise ValueError("Literal award subject is absent from its validated selected context")
        proof.append(
            {
                "fact_id": fact.id,
                "literal_subject": subject,
                "subject_sha256": hashlib.sha256(subject.encode("utf-8")).hexdigest(),
                "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
                "source_step": fact.source_step,
                "location": fact.location.model_dump(mode="json"),
            }
        )
    return proof


def parse_bound_journal_decision(
    value: JournalDecision | str | Mapping[str, Any],
    *,
    journal_sha256: str,
    canonical_university: str,
    closing_only: bool = False,
) -> JournalDecision:
    """Enforce schema bindings locally, then return an unaccepted original model.

    This adds no evidence inference or acceptance. Callers must still construct
    the candidate and validate its complete recorded trace and every citation.
    """
    current_hash, university = _journal_hash(journal_sha256), _university(canonical_university)
    if type(closing_only) is not bool:
        raise ValueError("Closing-only mode must be an explicit boolean")
    decision = parse_journal_decision(value)
    if decision.journal_sha256 != current_hash:
        raise ValueError("Decision must bind the exact current journal SHA")
    for fact in decision.facts:
        award_value(fact.claim_key, fact.decoded_value())
    for scope in [fact.scope for fact in decision.facts] + [
        finding.scope for finding in decision.question_findings
    ]:
        if scope.university is not None and scope.university != university:
            raise ValueError(
                "Scope university must be null or the exact public canonical university"
            )
    if closing_only and (
        decision.kind != "submit"
        or decision.observation != CLOSING_OBSERVATION
        or decision.action is not None
        or decision.facts
        or decision.question_findings
    ):
        raise ValueError("Hash-only closing requires submit with no action, facts or findings")
    return decision
