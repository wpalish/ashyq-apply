"""A usable local catalogue even before a research run or during an outage."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.tenancy import owned_profile
from app.catalogue.retrieval import retrieve
from app.db import get_session
from app.models import University
from app.schemas.profile import ApplicantProfileIn
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/universities", tags=["universities"])


@router.get("")
def universities(
    q: str = Query(default="", max_length=200),
    country: str = Query(default="", max_length=100),
    profile_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> dict:
    preferred: list[str] = []
    excluded: list[str] = []
    if profile_id:
        row = owned_profile(session, profile_id, principal)
        profile = ApplicantProfileIn.model_validate(row.payload)
        preferred = profile.preferences.preferred_countries
        excluded = profile.preferences.excluded_countries
    all_rows = list(session.scalars(select(University)))
    rows = retrieve(session, query=q, country=country, preferred=preferred, excluded=excluded)
    return {
        "total": len(rows),
        "catalogue_total": len(all_rows),
        "seed_count": sum(u.seed_snapshot is not None for u in all_rows),
        "countries": sorted({u.country for u in all_rows}),
        "items": [view(u) for u in rows[offset : offset + limit]],
    }


def view(u: University) -> dict:
    snapshot = u.seed_snapshot or {}
    record = snapshot.get("record") or {}
    return {
        "id": u.id,
        "name": u.name,
        "country": u.country,
        "city": u.city,
        "aliases": u.aliases,
        "domain": u.domain,
        "domain_status": u.domain_status,
        "identity_status": "curated" if u.registry_entry else "seed",
        "programme_status": "needs_research",
        "admissions_status": "unknown",
        "tuition_status": "needs_verification",
        "funding_status": "needs_research",
        "seed_tuition_usd": record.get("tuition_usd_estimate"),
        "seed_ranking": {"year": 2027, "rank": record.get("qs_rank_2027"), "status": "seed"}
        if record
        else None,
        "seed_version": u.seed_version,
        "observed_at": None,
        "sources": record.get("sources", {}),
    }
