"""Stored graph fields, never a client authority DTO.

The loader explicitly selects these existing result fields. It does not require
unrelated ranking fields or silently accept a client-supplied graph or scope.
"""

from __future__ import annotations

import json
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticSerializationError

from app.schemas.claim import UnresolvedQuestion
from app.schemas.result import DocumentChecklist, RequirementCheck, Scholarship


class StoredPreparationGraphFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_checks: list[RequirementCheck] = Field(default_factory=list)
    scholarships: list[Scholarship] = Field(default_factory=list)
    unresolved: list[UnresolvedQuestion] = Field(default_factory=list)
    checklist: DocumentChecklist | None = None

    @model_validator(mode="before")
    @classmethod
    def finite_stored_input(cls, value: Any) -> Any:
        # JSON serialization can turn nonfinite floats into null. Reject the raw
        # stored input first so invalid observations cannot gain a new digest.
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Stored preparation input must be finite JSON") from exc
        return value

    @model_validator(mode="after")
    def exact_serializable_snapshot(self) -> Self:
        if len({award.id for award in self.scholarships}) != len(self.scholarships):
            raise ValueError("Duplicate award identities cannot form a preparation slice")
        try:
            json.dumps(self.model_dump(mode="json"), allow_nan=False)
        except (TypeError, ValueError, PydanticSerializationError) as exc:
            raise ValueError(
                "Stored preparation fields must have a finite JSON representation"
            ) from exc
        return self
