"""Detached result reads only; saved facts, evaluations, receipts and order stay exact."""

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
    read.is_stale = is_stale(read.claim_type, read.accessed_at, now) or read.status in {
        ClaimStatus.POSSIBLY_STALE,
        ClaimStatus.SUPERSEDED,
    }
    read.status = apply_freshness(read.status, read.claim_type, read.accessed_at, now)
    return read


def result_read(
    result: ProgramResult, now: datetime, *, evidence_available: bool = True
) -> ProgramResultReadV1:
    read = result.model_copy(deep=True)
    if evidence_available:
        read.claims = [claim_read(claim, now) for claim in read.claims]
    return ProgramResultReadV1.model_validate(
        {
            **read.model_dump(mode="python"),
            "read_freshness": ResultFreshnessReadV1(
                observed_at=now,
                evidence="observed" if evidence_available else "not_available",
                stale_claim_count=sum(claim.is_stale for claim in read.claims)
                if evidence_available
                else None,
            ),
        }
    )
