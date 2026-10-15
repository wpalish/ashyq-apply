"""Read-only page observations; neither requirements nor an admission assessment."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, TypedDict
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import DegreeLevel

MAX_OBSERVATIONS = 150
MAX_READ_PROOFS = 60
Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
PublicText = Annotated[str, Field(strict=True, min_length=1, max_length=300)]


def observation_id(institution: str, domain: str, url: str) -> str:
    identity = [institution, domain.casefold(), url]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


class PageReadProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_hash: Digest
    fetched_at: AwareDatetime
    page_type: Literal["program_detail", "intake_specific_program"]
    classified_degree: DegreeLevel | None
    classified_subject: PublicText | None

    @field_validator("fetched_at", mode="before")
    @classmethod
    def explicit_instant(cls, value: object) -> object:
        if not isinstance(value, str | datetime):
            raise ValueError("A read needs an explicit aware timestamp")
        return value

    @field_validator("fetched_at")
    @classmethod
    def utc_instant(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ProgrammeObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["programme-page-observation-v1"] = "programme-page-observation-v1"
    id: Digest
    institution: PublicText
    domain: PublicText
    programme_url: Annotated[str, Field(strict=True, min_length=1, max_length=2048)]
    requested_degree: DegreeLevel
    confirmation_basis: Literal["existing_discovery_page_predicate"] = (
        "existing_discovery_page_predicate"
    )
    requirements_state: Literal["unknown"] = "unknown"
    compatibility: Literal["not_assessed"] = "not_assessed"
    reads: Annotated[tuple[PageReadProof, ...], Field(min_length=1, max_length=MAX_READ_PROOFS)]
    further_reads_omitted: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def identity_binding(self) -> ProgrammeObservation:
        parts = urlsplit(self.programme_url)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
            or self.id != observation_id(self.institution, self.domain, self.programme_url)
        ):
            raise ValueError("Invalid public programme observation identity")
        return self


class ProgrammeObservationSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["programme-observation-set-v1"] = "programme-observation-set-v1"
    items: Annotated[tuple[ProgrammeObservation, ...], Field(max_length=MAX_OBSERVATIONS)] = ()
    additional_observations_omitted: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def unique_identities(self) -> ProgrammeObservationSet:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Duplicate observation identity")
        return self

    def add(self, incoming: ProgrammeObservation) -> ProgrammeObservationSet:
        # Revalidate copied/model_construct values at the persistence boundary.
        incoming = ProgrammeObservation.model_validate(incoming.model_dump(mode="json"))
        values = list(self.items)
        for index, previous in enumerate(values):
            if previous.id != incoming.id:
                continue
            if previous.requested_degree != incoming.requested_degree:
                raise ValueError("A saved observation cannot silently change requested degree")
            reads = list(previous.reads)
            omitted = previous.further_reads_omitted or incoming.further_reads_omitted
            for proof in incoming.reads:
                if proof not in reads:
                    if len(reads) < MAX_READ_PROOFS:
                        reads.append(proof)
                    else:
                        omitted = True
            values[index] = previous.model_copy(
                update={"reads": tuple(reads), "further_reads_omitted": omitted}
            )
            return self.model_copy(update={"items": tuple(values)})
        if len(values) >= MAX_OBSERVATIONS:
            return self.model_copy(update={"additional_observations_omitted": True})
        return self.model_copy(update={"items": (*self.items, incoming)})


class ObservationProjection(TypedDict):
    programme_observations: list[dict[str, Any]]
    programme_observation_state: Literal["readable", "unavailable"]
    additional_programme_observations_omitted: bool


def observation_projection(raw: object) -> ObservationProjection:
    """The own run view and export share safe read-only interpretation."""
    try:
        saved = (
            ProgrammeObservationSet()
            if raw is None
            else ProgrammeObservationSet.model_validate(raw)
        )
        return {
            "programme_observations": [item.model_dump(mode="json") for item in saved.items],
            "programme_observation_state": "readable",
            "additional_programme_observations_omitted": saved.additional_observations_omitted,
        }
    except (ValueError, TypeError, RecursionError):
        return {
            "programme_observations": [],
            "programme_observation_state": "unavailable",
            "additional_programme_observations_omitted": False,
        }
