"""TypeSafe's Jev behind the decision seam.

Contract (docs.typesafe.ai/api, read 2026-09-25): ``POST /v1/systemone`` with a
Bearer key and ``{"state", "model", "questions"}``; each answer is
``{"type": "noul", "noul": p}`` or ``{"type": "choice", "choice", "probabilities",
"confidence"}``. The model is pinned: an alias may move to a new model and
change answers under a benchmark (the provider's own warning).

Fails closed with :class:`DecisionUnavailable`, one attempt, short timeout:
the caller falls back to its heuristics.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import httpx

from app.adapters.decisions.base import (
    Answer,
    Choice,
    DecisionResponse,
    DecisionUnavailable,
    Question,
)
from app.adapters.network_policy import BlockedRequest, check_url

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-1.13.0"
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 512 * 1024


class TypeSafeDecisionModel:
    name = "typesafe"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError(
                "TypeSafeDecisionModel needs an API key, read from the environment only."
            )
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._client = client

    async def ask(
        self, state: Mapping[str, object], questions: Mapping[str, Question]
    ) -> DecisionResponse:
        if not questions:
            raise ValueError("ask needs at least one question")
        try:
            check_url(TYPESAFE_URL)
        except BlockedRequest as exc:
            raise DecisionUnavailable(f"decision endpoint blocked by policy: {exc}") from exc
        payload = {
            "state": dict(state),
            "model": self._model,
            "questions": {qid: _wire(q) for qid, q in questions.items()},
        }
        client = self._client
        owns = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        began = time.monotonic()
        try:
            response = await client.post(
                TYPESAFE_URL,
                json=payload,
                headers={"authorization": f"Bearer {self._api_key}"},
            )
        except httpx.HTTPError as exc:
            raise DecisionUnavailable(f"TypeSafe did not answer: {type(exc).__name__}") from exc
        finally:
            if owns:
                await client.aclose()
        if response.status_code != httpx.codes.OK:
            # The body is external text; not repeated.
            raise DecisionUnavailable(f"TypeSafe answered {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise DecisionUnavailable("TypeSafe response over the size cap")
        try:
            body = response.json()
            answers = {qid: _answer(body["answers"][qid], questions[qid]) for qid in questions}
            usage = body.get("usage") or {}
            return DecisionResponse(
                provider=self.name,
                model=str(body.get("model") or self._model),
                answers=answers,
                input_tokens=int(usage.get("input_tokens") or 0),
                latency_seconds=time.monotonic() - began,
            )
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise DecisionUnavailable(f"TypeSafe body unreadable: {exc}") from exc


def _wire(question: Question) -> dict[str, Any]:
    if isinstance(question, Choice):
        return {
            "type": "choice",
            "instructions": question.instructions,
            "criteria": dict(question.criteria),
        }
    return {"type": "noul", "instructions": question.instructions}


def _probability(value: object) -> float:
    p = float(value)  # type: ignore[arg-type]
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"probability out of range: {p}")
    return p


def _answer(raw: Mapping[str, Any], question: Question) -> Answer:
    if isinstance(question, Choice):
        choice = str(raw["choice"])
        if choice not in question.criteria:
            raise ValueError(f"choice {choice!r} is not one of the options")
        probabilities = {k: _probability(v) for k, v in (raw.get("probabilities") or {}).items()}
        conf = raw.get("confidence")
        return Answer(
            probability=probabilities.get(choice, 0.0),
            choice=choice,
            probabilities=probabilities,
            confidence=None if conf is None else _probability(conf),
        )
    return Answer(probability=_probability(raw["noul"]))
