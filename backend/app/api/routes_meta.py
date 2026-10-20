"""Health, capability and vocabulary endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.domain import enums
from app.domain.currency import (
    RATE_DATE,
    RATE_SOURCE,
    rate_age_days,
    rates_are_stale,
    supported_currencies,
)
from app.domain.message_keys import COVERAGE, match, stale_rates_message
from app.models import CURRENT_SCHEMA_VERSION, AuditEvent, University
from app.schemas.claim import MessageRef
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
def capabilities(session: Session = Depends(get_session)) -> dict:
    """What this build can and cannot do — surfaced in the UI, not buried.

    The session is read in kb mode only (the catalogue's size for the
    coverage note); live and demo mode answer from the settings alone.
    """
    s = get_settings()
    # Demo mode ignores the knowledge mode (it keeps its fixtures), so does this.
    knowledge_mode = "demo" if s.demo_mode else s.knowledge_mode
    stale_warning = (
        f"These conversions use exchange rates from {RATE_DATE.isoformat()}, "
        f"{rate_age_days()} days old. Treat converted amounts as indicative and "
        f"check the current rate before relying on one."
        if rates_are_stale()
        else ""
    )
    stale_message = stale_rates_message(stale_warning)
    return {
        "demo_mode": s.demo_mode,
        "knowledge_mode": knowledge_mode,
        "data_origin": {
            "demo": "bundled synthetic corpus",
            "kb": "verified knowledge base (bachelor's in Computer Science); no live search",
        }.get(knowledge_mode, "live official sources"),
        "adapters": adapters(knowledge_mode),
        "fetch_tiers": ["structured data", "plain HTTP", "Playwright render", "PDF parsing"],
        "currency": {
            "supported": supported_currencies(),
            "rate_date": RATE_DATE.isoformat(),
            "rate_source": RATE_SOURCE,
            "rate_age_days": rate_age_days(),
            # The snapshot is deliberately static; saying nothing about its age
            # is what would make it dishonest.
            "stale_warning": stale_warning,
            # I18N-2: its key, so ru and kk can say it; absent while fresh.
            **(
                {"stale_warning_message": stale_message.model_dump()}
                if stale_message is not None
                else {}
            ),
        },
        # Keep the scope tied to the current registry and make evidence limits visible.
        "live_coverage": live_coverage(s, session),
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


#: The adapters a live run reads the web with. A kb-mode run uses none of them
#: (no discovery, no search, no page reads), and the capabilities say so.
WEB_ADAPTERS = frozenset(
    {
        "live-institution-registry",
        "web-requirements",
        "web-costs",
        "web-scholarships",
        "web-documents",
        "web-government",
    }
)
KB_ADAPTER = {
    "name": "verified-knowledge-base",
    "role": "discovery and verification",
    "live": False,
}


def adapters(knowledge_mode: str) -> list[dict]:
    """Every adapter this build has; in kb mode, the KB first and the web ones inactive.

    ``active`` appears in kb mode only (additive): live and demo mode list the
    adapters exactly as before. ``live`` says what an adapter is, ``active``
    whether this deployment's runs use it.
    """
    rows: list[dict] = [
        {"name": "fixture-catalog", "role": "discovery", "live": False},
        {"name": "fixture-rankings", "role": "ranking (discovery only)", "live": False},
        {"name": "live-institution-registry", "role": "discovery", "live": True},
        {"name": "web-requirements", "role": "admission requirements", "live": True},
        {"name": "web-costs", "role": "cost of attendance (HTML + PDF)", "live": True},
        {"name": "web-scholarships", "role": "scholarships and coverage", "live": True},
        {"name": "web-documents", "role": "document checklist", "live": True},
        {"name": "web-government", "role": "post-study work rules", "live": True},
    ]
    if knowledge_mode != "kb":
        return rows
    return [
        {**KB_ADAPTER, "active": True},
        *({**r, "active": False} if r["name"] in WEB_ADAPTERS else r for r in rows),
    ]


@router.get("/vocabulary")
def vocabulary() -> dict:
    """The controlled vocabularies, so the UI never hard-codes a status string."""
    return {
        "degree_level": [e.value for e in enums.DegreeLevel],
        "curriculum_type": [e.value for e in enums.CurriculumType],
        "eligibility": [e.value for e in enums.EligibilityStatus],
        "admissions_fit": [e.value for e in enums.AdmissionsFit],
        "bucket": [e.value for e in enums.Bucket],
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
        "direct_message_policy": [e.value for e in enums.DirectMessagePolicy],
        "report_reason": [e.value for e in enums.ReportReason],
        "report_target": [e.value for e in enums.ReportTarget],
        "report_status": [e.value for e in enums.ReportStatus],
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


def live_coverage(settings: Settings | None = None, session: Session | None = None) -> dict:
    """How far a research run reaches, read from what the run reads rather than asserted.

    kb mode (RM-1): the verified knowledge base, its entries with verified data
    and the catalogue they sit in — no page is read, so the registry is not the
    reach. Live mode: the institution registry, as before, plus ``mode`` and the
    note's :class:`MessageRef`. Demo mode (or no settings): exactly as before.
    """
    if settings is not None and not settings.demo_mode and settings.knowledge_mode == "kb":
        return kb_coverage(settings, session)
    body = registry_coverage()
    if settings is None or settings.demo_mode:
        return body
    ref = match(COVERAGE, body["recall_note"])
    return {
        **body,
        "mode": "live",
        **({"recall_message": ref.model_dump()} if ref is not None else {}),
    }


def kb_coverage(settings: Settings, session: Session | None) -> dict:
    """The KB's reach: universities with verified data, their countries, the catalogue size."""
    from app.api.routes_universities import _knowledge_base

    kb = _knowledge_base(settings.knowledge_base_path, settings.knowledge_imported_path)
    verified = [e for e in kb.entries.values() if e.has_verified_data]
    countries = sorted({e.country for e in verified if e.country})
    total = (
        int(session.scalar(select(func.count()).select_from(University)) or 0)
        if session is not None
        else 0
    )
    params = {"universities": str(len(verified)), "total": str(total)}
    template = next(t for t in COVERAGE if t.key == "coverage.kb")
    return {
        "mode": "kb",
        "institutions": len(verified),
        "countries": countries,
        "catalogue_total": total,
        "recall_note": template.text.format(**params),
        "recall_message": MessageRef(key=template.key, params=params).model_dump(),
    }


def registry_coverage() -> dict:
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
            f"{len(countries)} countries. Results depend on the selected fields "
            "and which official pages can be accessed. Missing or unverified "
            "evidence stays visible in the results."
        ),
    }
