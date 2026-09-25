"""An offline decision model for tests: answers from a table, never the network."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from app.adapters.decisions.base import (
    Answer,
    Choice,
    DecisionResponse,
    DecisionUnavailable,
    Question,
)


class FakeDecisionModel:
    name = "fake"

    def __init__(
        self,
        answer: Callable[[Mapping[str, object], str, Question], float] | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self._answer = answer or (lambda _state, _qid, _q: 0.5)
        self._fail = fail
        self.calls: list[tuple[Mapping[str, object], Mapping[str, Question]]] = []

    async def ask(
        self, state: Mapping[str, object], questions: Mapping[str, Question]
    ) -> DecisionResponse:
        self.calls.append((state, questions))
        if self._fail:
            raise DecisionUnavailable("fake provider told to fail")
        answers: dict[str, Answer] = {}
        for qid, question in questions.items():
            p = self._answer(state, qid, question)
            if isinstance(question, Choice):
                best = next(iter(question.criteria))
                answers[qid] = Answer(p, choice=best, probabilities={best: p})
            else:
                answers[qid] = Answer(p)
        return DecisionResponse(provider=self.name, model="fake-0", answers=answers)
