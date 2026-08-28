"""Health, capability and vocabulary endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.domain import enums
from app.domain.currency import RATE_DATE, RATE_SOURCE, supported_currencies
from app.models import CURRENT_SCHEMA_VERSION, AuditEvent

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "demo_mode": s.demo_mode,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "respect_robots": s.respect_robots,
        "browser_tier": s.enable_browser_tier,
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
        "currency": {
            "supported": supported_currencies(),
            "rate_date": RATE_DATE.isoformat(),
            "rate_source": RATE_SOURCE,
        },
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
            "Currency rates are a dated static snapshot, not a live feed.",
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
def audit_log(limit: int = 200, session: Session = Depends(get_session)) -> list[dict]:
    """Append-only trail. Holds ids and actions only — never applicant data."""
    rows = (
        session.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit, 1000)).all()
    )
    return [
        {"id": r.id, "at": r.created_at.isoformat(), "actor": r.actor, "action": r.action,
         "entity_type": r.entity_type, "entity_id": r.entity_id, "detail": r.detail}
        for r in rows
    ]
