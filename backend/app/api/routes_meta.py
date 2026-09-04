"""Health, capability and vocabulary endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.domain import enums
from app.domain.currency import (
    RATE_DATE,
    RATE_SOURCE,
    rate_age_days,
    rates_are_stale,
    supported_currencies,
)
from app.models import CURRENT_SCHEMA_VERSION, AuditEvent
from app.security import Principal, get_principal

log = logging.getLogger("unimatch.meta")

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health(response: Response) -> dict:
    """Liveness that actually touches the database.

    Reporting the configuration alone made every probe green while PostgreSQL
    was down: Fly kept routing traffic to a machine that could not answer a
    single real request. A degraded answer is a 503 so the platform's own
    health check fails with it.
    """
    s = get_settings()
    body = {
        "status": "ok",
        "database": "ok",
        "demo_mode": s.demo_mode,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "respect_robots": s.respect_robots,
        "browser_tier": s.enable_browser_tier,
    }
    try:
        # Resolved at call time, not import time: the engine is swapped both by
        # the test suite and by anything that reconnects after a failure.
        import app.db as db_module

        with db_module.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # any driver error means we cannot serve
        log.error("health check could not reach the database: %s", exc)
        body["status"] = "degraded"
        body["database"] = "unavailable"
        response.status_code = 503
    return body


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
            "rate_age_days": rate_age_days(),
            # The snapshot is deliberately static; saying nothing about its age
            # is what would make it dishonest.
            "stale_warning": (
                f"These conversions use exchange rates from {RATE_DATE.isoformat()}, "
                f"{rate_age_days()} days old. Treat converted amounts as indicative and "
                f"check the current rate before relying on one."
                if rates_are_stale()
                else ""
            ),
        },
        # What live mode can actually reach today. The number matters: a user
        # switching demo mode off imagines the open web and gets a curated list
        # of ten institutions, with programme-page recall of one in ten. Saying
        # so here is cheaper than letting them discover it from an empty
        # shortlist.
        "live_coverage": live_coverage(),
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
        "applicant_status": [e.value for e in enums.ApplicantStatus],
    }


@router.get("/audit")
def audit_log(
    limit: int = Query(default=200, ge=1, le=1000),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Append-only trail. Holds ids and actions only — never applicant data."""
    rows = (
        session.query(AuditEvent)
        .filter(AuditEvent.organization_id == principal.organization_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
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


def live_coverage() -> dict:
    """How far live mode reaches, read from the registry rather than asserted."""
    import json
    from pathlib import Path

    registry = Path(__file__).resolve().parent.parent / "adapters" / "discovery"
    path = registry / "institution_registry.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # a missing registry is a limitation, not a crash
        return {
            "institutions": 0,
            "countries": [],
            "recall_note": "The institution registry could not be read; live mode has no seeds.",
        }
    entries = raw if isinstance(raw, list) else raw.get("institutions", [])
    countries = sorted({e.get("country", "") for e in entries if e.get("country")})
    return {
        "institutions": len(entries),
        "countries": countries,
        "recall_note": (
            f"Live mode searches {len(entries)} curated institutions in "
            f"{len(countries)} countries, not the open web. Category pages "
            f"(fees, scholarships, admissions) are read reliably; an individual "
            f"programme page is reached at about one site in ten today. See "
            f"docs/LIVE_DISCOVERY_REPORT.md."
        ),
    }
