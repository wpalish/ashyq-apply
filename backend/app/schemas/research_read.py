"""Read context and closed own research-input metadata; never an admissions verdict."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.result import ProgramResult

ProfileSection = Literal[
    "context",
    "academics",
    "activities",
    "achievements",
    "preferences",
    "funding",
    "weights",
    "weights_override",
]
PROFILE_SECTIONS: tuple[ProfileSection, ...] = (
    "context",
    "academics",
    "activities",
    "achievements",
    "preferences",
    "funding",
    "weights",
    "weights_override",
)
Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]


class ReadBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


def fingerprint_digest(sections: dict[ProfileSection, str]) -> str:
    return hashlib.sha256(
        json.dumps(
            {"schema_version": "research-profile-fingerprint-v1", "sections": sections},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


class ProfileInputFingerprintV1(ReadBase):
    schema_version: Literal["research-profile-fingerprint-v1"] = "research-profile-fingerprint-v1"
    digest: Digest
    sections: dict[ProfileSection, Digest]

    @model_validator(mode="after")
    def _closed_sections(self) -> Self:
        if set(self.sections) != set(PROFILE_SECTIONS) or self.digest != fingerprint_digest(
            self.sections
        ):
            raise ValueError("Input fingerprint must carry its exact closed section digest set")
        return self


class ResearchInputObservationV1(ReadBase):
    schema_version: Literal["research-input-observation-v1"] = "research-input-observation-v1"
    state: Literal["pending", "observed", "mixed"]
    first: ProfileInputFingerprintV1 | None
    last: ProfileInputFingerprintV1 | None
    mixed_sections: list[ProfileSection] = Field(max_length=8)

    @model_validator(mode="after")
    def _state(self) -> Self:
        if len(set(self.mixed_sections)) != len(self.mixed_sections):
            raise ValueError("Changed sections must be unique")
        if self.state == "pending":
            if self.first is not None or self.last is not None or self.mixed_sections:
                raise ValueError("Pending input has no fabricated observation")
        elif self.first is None or self.last is None:
            raise ValueError("Observed input needs its own fingerprint")
        elif self.state == "observed" and (self.first != self.last or self.mixed_sections):
            raise ValueError("An unchanged observation retains one actual input")
        elif self.state == "mixed" and not self.mixed_sections:
            raise ValueError("Mixed input retains named changed sections")
        return self


class ResearchInputStatusReadV1(ReadBase):
    schema_version: Literal["research-input-status-v1"] = "research-input-status-v1"
    state: Literal["unknown", "pending", "current", "changed", "mixed"]
    changed_sections: list[ProfileSection] = Field(default_factory=list, max_length=8)
    observed_at: AwareDatetime
    applicability: Literal["not_assessed"] = "not_assessed"


class ResultFreshnessReadV1(ReadBase):
    schema_version: Literal["result-freshness-read-v1"] = "result-freshness-read-v1"
    observed_at: AwareDatetime
    evidence: Literal["observed", "not_available"]
    stale_claim_count: int | None = Field(default=None, strict=True, ge=0)
    assessment: Literal["stored_evaluation"] = "stored_evaluation"


class ProgramResultReadV1(ProgramResult):
    read_freshness: ResultFreshnessReadV1
