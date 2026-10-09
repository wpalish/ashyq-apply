"""Bounded semantic proposals with independent critique and deterministic proof.

Providers receive only public evidence fragments and question IDs. This seam
does not grant a model network access or authority to establish a fact.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import Field

from app.adapters.document_ir import DocumentIR
from app.research.contracts import PolicyRule, StrictModel
from app.research.evidence import validate_rule


class PublicFragment(StrictModel):
    url: str
    block_id: str
    text: str = Field(max_length=16000)
    section_path: tuple[str, ...]
    row_headers: tuple[str, ...] = ()
    column_headers: tuple[str, ...] = ()


class SemanticRequest(StrictModel):
    questions: tuple[str, ...] = Field(min_length=1)
    fragments: tuple[PublicFragment, ...] = Field(min_length=1, max_length=40)


class SemanticResponse(StrictModel):
    rules: tuple[PolicyRule, ...] = Field(max_length=24)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    model: str = Field(min_length=1)


class SemanticProvider(Protocol):
    async def propose(
        self, request: SemanticRequest, *, max_output_tokens: int
    ) -> SemanticResponse: ...


class CritiqueResponse(StrictModel):
    rejected_ids: frozenset[str]
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    model: str = Field(min_length=1)


class ExceptionCritic(Protocol):
    async def critique(
        self, request: SemanticRequest, rules: tuple[PolicyRule, ...], *, max_output_tokens: int
    ) -> CritiqueResponse: ...


@dataclass
class SemanticBudget:
    # Cumulative per institution/experiment, serialized by its durable owner.
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0
    max_calls: int = 12
    max_input_tokens: int = 200000
    max_output_tokens: int = 20000


async def semantic_fallback(
    request: SemanticRequest,
    provider: SemanticProvider,
    critic: ExceptionCritic,
    budget: SemanticBudget,
    documents: dict[str, DocumentIR],
    official_urls: set[str],
    now: datetime,
    proof: Callable[[PolicyRule, SemanticRequest], bool],
) -> list[PolicyRule]:
    # A proposal without an independent critique can never become an answer.
    # Do not spend the last dispatch on a predictably unusable proposal.
    if budget.calls + 2 > budget.max_calls:
        raise ValueError("semantic budget exhausted")

    def reserve(input_bytes: int) -> int:
        # Reserve serialized public input and a hard output cap BEFORE calls.
        # Failed dispatches retain their reservations; no implicit retries.
        cap = min(2000, budget.max_output_tokens - budget.output_tokens)
        if (
            budget.calls >= budget.max_calls
            or cap <= 0
            or budget.input_tokens + input_bytes > budget.max_input_tokens
        ):
            raise ValueError("semantic budget exhausted")
        budget.calls += 1
        budget.input_tokens += input_bytes
        budget.output_tokens += cap
        return cap

    def account(
        result: SemanticResponse | CritiqueResponse, input_cap: int, output_cap: int
    ) -> None:
        if result.input_tokens > input_cap or result.output_tokens > output_cap:
            budget.cost_usd = None
            raise ValueError("semantic provider exceeded token budget")
        budget.cost_usd = (
            None
            if result.cost_usd is None or budget.cost_usd is None
            else budget.cost_usd + result.cost_usd
        )

    input_cap = len(request.model_dump_json().encode("utf-8"))
    output_cap = reserve(input_cap)
    try:
        response = await provider.propose(request, max_output_tokens=output_cap)
    except Exception:
        budget.cost_usd = None
        raise
    account(response, input_cap, output_cap)
    critic_input = input_cap + sum(len(r.model_dump_json().encode("utf-8")) for r in response.rules)
    critic_cap = reserve(critic_input)
    try:
        review = await critic.critique(request, response.rules, max_output_tokens=critic_cap)
    except Exception:
        budget.cost_usd = None
        raise
    account(review, critic_input, critic_cap)
    rejected = review.rejected_ids
    allowed_blocks = {(f.url, f.block_id) for f in request.fragments}
    accepted = []
    for rule in response.rules:
        if rule.id in rejected or rule.question not in request.questions:
            continue
        if not all((str(e.source_url), e.block_id) in allowed_blocks for e in rule.evidence):
            continue
        try:
            validate_rule(rule, documents, official_urls, now)
        except ValueError:
            continue
        # Type-specific deterministic proof must establish the proposed value
        # and conditions. Authentic text alone never establishes entailment.
        if proof(rule, request):
            accepted.append(rule)
    return accepted
