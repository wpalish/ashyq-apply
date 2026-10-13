from pathlib import Path
import json,hashlib
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';paths=['backend/app/schemas/research_read.py','backend/app/domain/profile_input_provenance.py','backend/app/domain/result_read.py','backend/app/api/routes_research.py','backend/app/api/routes_results.py','backend/app/pipeline/runner.py','backend/tests/test_research_input_provenance.py','backend/tests/test_result_read_freshness.py'];out=s/'inputs6a-proposal';out.mkdir(exist_ok=False);rows={}
for p in paths:
 f=r/p;raw=f.read_bytes() if f.exists() else None;rows[p]=hashlib.sha256(raw).hexdigest() if raw is not None else None
 if raw is not None:q=s/'inputs6a-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(s/'INPUTS_6A_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_PROPOSAL_NOT_GRANTED_NOT_APPLIED','baseline':'4d006602','paths':rows,'scope':'Existing settings_snapshot closed observation namespace; real runner input hashes/section names only, pending new-run marker, no legacy backfill, permanent mixed on A→B→A and existing lease/CAS fence. Detached result/claim read freshness, stored assessments unmodified and source-free reads. No migration/new DB/network/provider/heldout/main/prod. API/profile read consumers require final review.'},indent=2)+'\n')
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
put(paths[0],'''"""Read context and closed own research-input metadata; never an admissions verdict."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal, Self
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from app.schemas.result import ProgramResult
ProfileSection = Literal["context", "academics", "activities", "achievements", "preferences", "funding", "weights", "weights_override"]
PROFILE_SECTIONS: tuple[ProfileSection, ...] = ("context", "academics", "activities", "achievements", "preferences", "funding", "weights", "weights_override")
Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
class ReadBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
def fingerprint_digest(sections: dict[ProfileSection, str]) -> str:
    return hashlib.sha256(json.dumps({"schema_version": "research-profile-fingerprint-v1", "sections": sections}, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
class ProfileInputFingerprintV1(ReadBase):
    schema_version: Literal["research-profile-fingerprint-v1"] = "research-profile-fingerprint-v1"
    digest: Digest
    sections: dict[ProfileSection, Digest]
    @model_validator(mode="after")
    def _closed_sections(self) -> Self:
        if set(self.sections) != set(PROFILE_SECTIONS) or self.digest != fingerprint_digest(self.sections):
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
''')
put(paths[1],'''"""Pure local input observation; no persistence, queries, applicant values or network."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pydantic import ValidationError
from app.schemas.profile import ApplicantProfileIn
from app.schemas.research_read import (PROFILE_SECTIONS, ProfileInputFingerprintV1, ProfileSection, ResearchInputObservationV1, ResearchInputStatusReadV1, fingerprint_digest)
INPUT_OBSERVATION_KEY = "profile_input_observation_v1"
def pending_input_observation() -> dict:
    return ResearchInputObservationV1(state="pending", first=None, last=None, mixed_sections=[]).model_dump(mode="json")
def profile_fingerprint(profile: ApplicantProfileIn) -> ProfileInputFingerprintV1:
    normalized = ApplicantProfileIn.model_validate(profile.model_dump(mode="python")).model_dump(mode="json")
    sections: dict[ProfileSection, str] = {name: hashlib.sha256(json.dumps(normalized[name], sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest() for name in PROFILE_SECTIONS}
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
        return ResearchInputObservationV1(state="observed", first=actual, last=actual, mixed_sections=[]).model_dump(mode="json")
    if previous.first is None:
        return None
    changed = set(previous.mixed_sections) | {name for name in PROFILE_SECTIONS if previous.first.sections[name] != actual.sections[name]}
    return ResearchInputObservationV1(state="mixed" if changed else "observed", first=previous.first, last=actual,
        mixed_sections=[name for name in PROFILE_SECTIONS if name in changed]).model_dump(mode="json")

def input_status(raw: object, profile: ApplicantProfileIn | None, now: datetime) -> ResearchInputStatusReadV1:
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
    changed = set(previous.mixed_sections) | {name for name in PROFILE_SECTIONS if previous.first.sections[name] != actual.sections[name]}
    return ResearchInputStatusReadV1(state="mixed" if previous.state == "mixed" else "changed" if changed else "current",
        changed_sections=[name for name in PROFILE_SECTIONS if name in changed], observed_at=now)
''')
put(paths[2],'''"""Detached result reads only; saved facts, evaluations, receipts and order stay exact."""
from __future__ import annotations
from datetime import datetime
from app.domain.enums import ClaimStatus
from app.domain.freshness import age_days, apply_freshness, is_stale
from app.schemas.claim import ClaimOut
from app.schemas.research_read import ProgramResultReadV1, ResultFreshnessReadV1
from app.schemas.result import ProgramResult

def claim_read(claim: ClaimOut, now: datetime) -> ClaimOut:
    read = claim.model_copy(deep=True)
    read.age_days = age_days(read.accessed_at, now)
    read.is_stale = is_stale(read.claim_type, read.accessed_at, now) or read.status in {ClaimStatus.POSSIBLY_STALE, ClaimStatus.SUPERSEDED}
    read.status = apply_freshness(read.status, read.claim_type, read.accessed_at, now)
    return read

def result_read(result: ProgramResult, now: datetime, *, evidence_available: bool = True) -> ProgramResultReadV1:
    read = result.model_copy(deep=True)
    if evidence_available:
        read.claims = [claim_read(claim, now) for claim in read.claims]
    return ProgramResultReadV1.model_validate({**read.model_dump(mode="python"), "read_freshness": ResultFreshnessReadV1(
        observed_at=now, evidence="observed" if evidence_available else "not_available",
        stale_claim_count=sum(claim.is_stale for claim in read.claims) if evidence_available else None)})
''')
print('External closed schemas and pure provenance/freshness proposals prepared. Native API/runner/test proposals pending; nothing applied or imported.')
