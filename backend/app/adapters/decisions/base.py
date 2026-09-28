"""Bounded model decisions behind one seam (Phase 4, analysis/v2/07).

A decision model answers narrow typed questions about a state the code built:
yes/no (``Noul``) or one of fixed options (``Choice``). It never returns a
URL, a number, a date or a quote. Everything a claim is made of still comes
from the page and the deterministic code; a decision only reorders what the
code already has.

**No applicant data reaches a provider.** A state carries the research target
(field, degree, intake, the missing evidence kinds) and public page text; the
builders that make states take no profile.

**Fail open to the heuristics.** :class:`DecisionUnavailable` is the only
failure; every caller must continue on its own ranking without it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class DecisionUnavailable(RuntimeError):
    """The provider could not answer: timeout, quota, transport, bad body."""


@dataclass(frozen=True, slots=True)
class Noul:
    """A yes/no question; the answer is P(yes)."""

    instructions: str


@dataclass(frozen=True, slots=True)
class Choice:
    """One of fixed options; the answer is a distribution over them."""

    instructions: str
    criteria: Mapping[str, str]


Question = Noul | Choice


@dataclass(frozen=True, slots=True)
class Answer:
    #: P(yes) for a Noul; the chosen option's probability for a Choice.
    probability: float
    choice: str | None = None
    probabilities: Mapping[str, float] = field(default_factory=dict)
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class DecisionResponse:
    provider: str
    #: The model that actually answered, as the provider reported it.
    model: str
    answers: Mapping[str, Answer]
    input_tokens: int = 0
    latency_seconds: float = 0.0


@runtime_checkable
class DecisionModel(Protocol):
    name: str

    async def ask(
        self, state: Mapping[str, object], questions: Mapping[str, Question]
    ) -> DecisionResponse: ...
