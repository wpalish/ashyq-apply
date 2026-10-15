"""Pure local input observation; no persistence, queries, applicant values or network."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from app.schemas.profile import ApplicantProfileIn
from app.schemas.research_read import (
    PROFILE_SECTIONS,
    ProfileInputFingerprintV1,
    ProfileSection,
    ResearchInputObservationV1,
    ResearchInputStatusReadV1,
    fingerprint_digest,
)
from pydantic import ValidationError

INPUT_OBSERVATION_KEY = "profile_input_observation_v1"


def pending_input_observation() -> dict:
    return ResearchInputObservationV1(
        state="pending", first=None, last=None, mixed_sections=[]
    ).model_dump(mode="json")


def profile_fingerprint(profile: ApplicantProfileIn) -> ProfileInputFingerprintV1:
    normalized = ApplicantProfileIn.model_validate(profile.model_dump(mode="python")).model_dump(
        mode="json"
    )
    sections: dict[ProfileSection, str] = {
        name: hashlib.sha256(
            json.dumps(
                normalized[name],
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        for name in PROFILE_SECTIONS
    }
    return ProfileInputFingerprintV1(digest=fingerprint_digest(sections), sections=sections)


def parse_observation(raw: object) -> ResearchInputObservationV1 | None:
    try:
        return ResearchInputObservationV1.model_validate(raw)
    except (ValidationError, ValueError, TypeError):
        return None


def observe_actual_inputs(raw: object, profile: ApplicantProfileIn) -> dict | None:
    previous = parse_observation(raw)
    # Absence/corruption stays unknown; a read cannot backfill an old run from today's profile.
    if previous is None:
        return None
    try:
        actual = profile_fingerprint(profile)
    except (ValidationError, ValueError, TypeError):
        return None
    if previous.state == "pending":
        return ResearchInputObservationV1(
            state="observed", first=actual, last=actual, mixed_sections=[]
        ).model_dump(mode="json")
    if previous.first is None:
        return None
    changed = set(previous.mixed_sections) | {
        name for name in PROFILE_SECTIONS if previous.first.sections[name] != actual.sections[name]
    }
    return ResearchInputObservationV1(
        state="mixed" if changed else "observed",
        first=previous.first,
        last=actual,
        mixed_sections=[name for name in PROFILE_SECTIONS if name in changed],
    ).model_dump(mode="json")


def input_status(
    raw: object, profile: ApplicantProfileIn | None, now: datetime
) -> ResearchInputStatusReadV1:
    previous = parse_observation(raw)
    if previous is None or profile is None:
        return ResearchInputStatusReadV1(state="unknown", observed_at=now)
    if previous.state == "pending":
        return ResearchInputStatusReadV1(state="pending", observed_at=now)
    try:
        actual = profile_fingerprint(profile)
    except (ValidationError, ValueError, TypeError):
        return ResearchInputStatusReadV1(state="unknown", observed_at=now)
    if previous.first is None:
        return ResearchInputStatusReadV1(state="unknown", observed_at=now)
    changed = set(previous.mixed_sections) | {
        name for name in PROFILE_SECTIONS if previous.first.sections[name] != actual.sections[name]
    }
    return ResearchInputStatusReadV1(
        state="mixed" if previous.state == "mixed" else "changed" if changed else "current",
        changed_sections=[name for name in PROFILE_SECTIONS if name in changed],
        observed_at=now,
    )
