"""Bounded model decisions (Phase 4). Ask :func:`get_decision_model` for one."""

from __future__ import annotations

from app.adapters.decisions.base import (
    Answer,
    Choice,
    DecisionModel,
    DecisionResponse,
    DecisionUnavailable,
    Noul,
    Question,
)

KNOWN_DECISION_PROVIDERS = frozenset({"none", "fake", "typesafe"})

__all__ = [
    "KNOWN_DECISION_PROVIDERS",
    "Answer",
    "Choice",
    "DecisionModel",
    "DecisionResponse",
    "DecisionUnavailable",
    "Noul",
    "Question",
    "get_decision_model",
]


def get_decision_model() -> DecisionModel | None:
    """The configured model, or None: every caller runs without one."""
    from app.config import get_settings

    settings = get_settings()
    if settings.decision_provider == "typesafe":
        from app.adapters.decisions.typesafe import TypeSafeDecisionModel

        return TypeSafeDecisionModel(settings.typesafe_api_key.get_secret_value())
    if settings.decision_provider == "fake":
        from app.adapters.decisions.fake import FakeDecisionModel

        return FakeDecisionModel()
    return None
