"""Health, capability and vocabulary endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.domain import enums
from app.domain.currency import (
    MAX_RATE_AGE_DAYS,
    FxUnavailable,
    provider_for,
    supported_currencies,
)
from app.models import CURRENT_SCHEMA_VERSION, AuditEvent
from app.security import Principal, get_principal
from app.jobs.versioning import (
    BUILD_VERSION,
    PAYLOAD_SCHEMA_VERSION,
    SUPPORTED_PAYLOAD_SCHEMA_VERSIONS,
)

router = APIRouter(prefix="/api", tags=["meta"])


def _currency_limit(settings) -> str:
    """One sentence about this instance's rates, true for this instance."""
    meta = _currency_meta(settings)
    if not meta["available"]:
        return (
            f"No exchange rate is available ({meta.get('reason', 'unknown reason')}); "
            "amounts stay in their source currency and funding gaps are not computed."
        )
    if not meta.get("authoritative", False):
        return (
            f"Currency rates are a bundled snapshot dated {meta['rate_date']}, not a "
            "live feed, and every converted amount is labelled an estimate."
        )
    return (
        f"Currency rates come from {meta['provider']}, observed {meta['rate_date']}. "
        f"A rate older than {meta['max_age_days']} days, or a currency the provider "
        "does not publish, is refused rather than guessed."
    )


def _currency_meta(settings) -> dict:
    """What rates a run on *this* instance would use.

    Built from the configuration, not from process state: there is no global
    provider any more, and reporting a default would describe an instance
    nobody is running. When the provider cannot be reached, `supported` is
    empty — advertising the bundled table's currencies as available live
    conversions is exactly the silent fallback this product refuses.
    """
    provider = provider_for(settings.fx_provider, demo=settings.demo_mode)
    try:
        snap = provider.snapshot()
    except FxUnavailable as exc:
        return {
            "supported": [],
            "provider": getattr(provider, "provider_id", "unknown"),
            "available": False,
            "reason": str(exc),
            "max_age_days": MAX_RATE_AGE_DAYS,
        }
    return {
        "supported": supported_currencies(provider),
        "provider": snap.provider_id,
        "available": True,
        "rate_date": snap.observed_on.isoformat(),
        "rate_source": snap.source_url,
        "age_days": snap.age_days,
        "max_age_days": MAX_RATE_AGE_DAYS,
        # False means a dated bundled table, and every conversion made from it
        # is labelled an estimate.
        "authoritative": snap.authoritative,
    }


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "demo_mode": s.demo_mode,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "respect_robots": s.respect_robots,
        "browser_tier": s.enable_browser_tier,
        # Deployment metadata. During a rolling deployment two builds are
        # alive; when the queue stalls, the first question is which pair
        # disagreed, and this answers it without reading anyone's data.
        "build": BUILD_VERSION,
        "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
        "supported_payload_schema_versions": sorted(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS),
    }


@router.get("/capabilities")
def capabilities() -> dict:
    """What this build can and cannot do — surfaced in the UI, not buried."""
    s = get_settings()
    return {
        "demo_mode": s.demo_mode,
        "data_origin": "bundled synthetic corpus" if s.demo_mode else "live official sources",
        "adapters": [
            {"name": "fixture-catalog", "role": "discovery", "live": False},
            {"name": "fixture-rankings", "role": "ranking (discovery only)", "live": False},
            {"name": "live-institution-registry", "role": "discovery", "live": True},
            {"name": "web-requirements", "role": "admission requirements", "live": True},
            {"name": "web-costs", "role": "cost of attendance (HTML + PDF)", "live": True},
            {"name": "web-scholarships", "role": "scholarships and coverage", "live": True},
            {"name": "web-documents", "role": "document checklist", "live": True},
            {"name": "web-government", "role": "post-study work rules", "live": True},
        ],
        "fetch_tiers": ["structured data", "plain HTTP", "Playwright render", "PDF parsing"],
        "currency": _currency_meta(s),
        "guarantees": [
            "robots.txt is honoured before every fetch, including the browser tier",
            "applicant data is never placed in an outbound URL",
            "no page behind a login is fetched, and no CAPTCHA is bypassed",
            "no application is submitted, signed or paid for",
            "unknown values are reported as unknown, never inferred",
        ],
        "limits": [
            "The product reports published criteria only. It cannot predict an admission or an award.",
            "Grade conversions are approximations and are never applied without the user accepting one.",
            # Stated from the configured provider. It read "a dated static
            # snapshot, not a live feed" unconditionally, which was untrue on
            # any instance configured for live rates.
            _currency_limit(s),
        ],
    }


@router.get("/vocabulary")
def vocabulary() -> dict:
    """The controlled vocabularies, so the UI never hard-codes a status string."""
    return {
        "degree_level": [e.value for e in enums.DegreeLevel],
        "curriculum_type": [e.value for e in enums.CurriculumType],
        "eligibility": [e.value for e in enums.EligibilityStatus],
        "admissions_fit": [e.value for e in enums.AdmissionsFit],
        "funding_fit": [e.value for e in enums.FundingFit],
        "funding_classification": [e.value for e in enums.FundingClassification],
        "claim_status": [e.value for e in enums.ClaimStatus],
        "source_specificity": [e.value for e in enums.SourceSpecificity],
        "user_decision": [e.value for e in enums.UserDecision],
        "pipeline_stage": [e.value for e in enums.PipelineStage],
        "cost_category": [e.value for e in enums.CostCategory],
        "scholarship_type": [e.value for e in enums.ScholarshipType],
        "application_mode": [e.value for e in enums.ApplicationMode],
        "document_owner": [e.value for e in enums.DocumentOwner],
    }


@router.get("/audit")
def audit_log(
    limit: int = 200,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Append-only trail. Holds ids and actions only — never applicant data."""
    rows = (
        session.query(AuditEvent)
        .filter(AuditEvent.organization_id == principal.organization_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(min(limit, 1000))
        .all()
    )
    return [
        {
            "id": r.id,
            "at": r.created_at.isoformat(),
            "actor": r.actor,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "detail": r.detail,
        }
        for r in rows
    ]
