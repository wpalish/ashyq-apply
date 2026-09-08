"""Reading the shortlist, recording decisions, and inspecting evidence."""

from __future__ import annotations

import math
import re
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.paywall import access_for_run, require_full_access
from app.api.tenancy import owned_run
from app.config import get_settings
from app.db import get_session
from app.domain.enums import Bucket, ClaimStatus, UserDecision
from app.domain.ranking_v2 import Quotas, ShortlistCandidate, build_shortlist, rank_result
from app.export import calendar, tabular
from app.jobs.source_scanner import enqueue_reextract
from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    ClaimRow,
    ConflictRow,
    ProgramResultRow,
    SourcePage,
)
from app.payments.entitlements import free_view, truncate_shortlist
from app.pipeline.runner import apply_fit_labels, store_result
from app.schemas.profile import (
    ApplicantProfileIn,
    FundingNeeds,
    Preferences,
    PriorityGroup,
    ScoringWeights,
)
from app.schemas.result import DecisionIn, ProgramResult
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/runs/{run_id}", tags=["results"])


class ShortlistSummary(BaseModel):
    total: int
    by_eligibility: dict[str, int]
    by_funding: dict[str, int]
    by_decision: dict[str, int]
    with_conflicts: int
    with_open_questions: int
    demo_data: bool


def _safe_filename_stem(value: str) -> str:
    """A filename stem that cannot break out of a quoted header value."""
    cleaned = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return cleaned or "ashyq-export"


def _results(session: Session, run_id: str, **filters) -> list[ProgramResultRow]:
    q = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id)
    if filters.get("decision"):
        q = q.filter(ProgramResultRow.user_decision == filters["decision"])
    if filters.get("eligibility"):
        q = q.filter(ProgramResultRow.eligibility == filters["eligibility"])
    if filters.get("funding"):
        q = q.filter(ProgramResultRow.funding_classification == filters["funding"])
    if filters.get("country"):
        q = q.filter(ProgramResultRow.country == filters["country"])
    if filters.get("bucket"):
        q = q.filter(ProgramResultRow.bucket == filters["bucket"])
    return q.order_by(ProgramResultRow.score_total.desc(), ProgramResultRow.university).all()


#: Sorts the shortlist screen offers. `key` is the stored order; the rest read
#: the document, because fit and coverage are not columns.
Sort = Literal["key", "fit", "coverage", "gap", "deadline"]


def _sorted(results: list[ProgramResult], sort: Sort) -> list[ProgramResult]:
    """Order by one visible quantity, with unknowns last and ties by name.

    Unknowns sort last on purpose: a programme whose cost could not be read is
    not the cheapest one, and a missing deadline is not the most urgent.
    """
    if sort == "key":
        return results

    def gap_of(r: ProgramResult) -> float:
        g = r.funding_gap
        return g.gap.amount if (g and g.computable and g.gap) else math.inf

    def deadline_of(r: ProgramResult) -> date:
        return r.admission_deadline or date.max

    keys = {
        "fit": lambda r: (-(r.ranking.fit or 0.0) if r.ranking else 0.0, r.university),
        "coverage": lambda r: (-(r.ranking.coverage if r.ranking else 0.0), r.university),
        "gap": lambda r: (gap_of(r), r.university),
        "deadline": lambda r: (deadline_of(r), r.university),
    }
    return sorted(results, key=keys[sort])


@router.get("/results", response_model=list[ProgramResult])
def list_results(
    run_id: str,
    decision: str | None = None,
    eligibility: str | None = None,
    funding: str | None = None,
    country: str | None = None,
    bucket: str | None = None,
    sort: Sort = "key",
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[ProgramResult]:
    _profile_id, allowed = access_for_run(session, run_id, principal)
    rows = _results(
        session,
        run_id,
        decision=decision,
        eligibility=eligibility,
        funding=funding,
        country=country,
        bucket=bucket,
    )
    results = _sorted([ProgramResult.model_validate(r.payload) for r in rows], sort)
    if allowed:
        return results
    # Truncated, not refused: a free user must see that results exist and
    # roughly what they are, or there is nothing to buy. Cut after sorting, so
    # the visible rows are the top of the ranking rather than an arbitrary slice.
    settings = get_settings()
    return [free_view(r) for r in truncate_shortlist(results, settings.free_shortlist_rows)]


@router.get("/summary", response_model=ShortlistSummary)
def summary(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ShortlistSummary:
    owned_run(session, run_id, principal)
    rows = _results(session, run_id)
    results = [ProgramResult.model_validate(r.payload) for r in rows]

    def tally(key) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in rows:
            out[getattr(r, key)] = out.get(getattr(r, key), 0) + 1
        return out

    return ShortlistSummary(
        total=len(rows),
        by_eligibility=tally("eligibility"),
        by_funding=tally("funding_classification"),
        by_decision=tally("user_decision"),
        with_conflicts=sum(1 for r in results if r.conflicts),
        with_open_questions=sum(1 for r in results if r.unresolved),
        demo_data=any(u.startswith("fixture://") for r in results for u in r.source_urls),
    )


@router.get("/results/{result_id}", response_model=ProgramResult)
def get_result(
    run_id: str,
    result_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ProgramResult:
    require_full_access(session, run_id, principal)
    row = session.get(ProgramResultRow, result_id)
    if row is None or row.run_id != run_id:
        raise HTTPException(404, "Result not found")
    return ProgramResult.model_validate(row.payload)


class RefreshOut(BaseModel):
    status: str
    pages: int
    job_ids: list[str]
    skipped_urls: list[str]


@router.post("/results/{result_id}/refresh", response_model=RefreshOut, status_code=202)
def refresh_result(
    run_id: str,
    result_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RefreshOut:
    """Schedule a re-read of the pages behind one result's live evidence.

    Nothing is fetched here — the request only resolves the result's live
    claims to their tracked source pages and enqueues one ``reextract_page``
    job per (page, result) under a generation key, so a double click costs
    one job set. A claim over a URL no source-page row tracks is reported in
    ``skipped_urls`` rather than silently dropped; a result with no live
    claims is a valid no-op.
    """
    # Ownership first (404 across tenants, never a leak), then the paywall.
    require_full_access(session, run_id, principal)
    run = owned_run(session, run_id, principal)
    if run.demo_mode:
        # A demo run is a bundled rehearsal, not a fetchable one.
        raise HTTPException(409, "demo runs are read-only")

    live_urls = (
        session.query(ClaimRow.source_url)
        .filter(
            ClaimRow.run_id == run_id,
            ClaimRow.result_id == result_id,
            ClaimRow.status != ClaimStatus.SUPERSEDED.value,
        )
        .distinct()
        .all()
    )
    job_ids: list[str] = []
    skipped: list[str] = []
    for (url,) in sorted(live_urls):
        page = session.query(SourcePage).filter(SourcePage.url == url).first()
        if page is None:
            skipped.append(url)
            continue
        job_ids.append(
            enqueue_reextract(
                session,
                source_page_id=page.id,
                url=url,
                reason="manual",
                run_id=run_id,
                result_id=result_id,
            )
        )
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="refresh_requested",
            entity_type="result",
            entity_id=result_id,
            detail={"pages": len(job_ids), "skipped_urls": len(skipped)},
        )
    )
    session.commit()
    return RefreshOut(
        status="refresh_scheduled",
        pages=len(job_ids),
        job_ids=job_ids,
        skipped_urls=skipped,
    )


@router.post("/results/{result_id}/decision", response_model=ProgramResult)
def set_decision(
    run_id: str,
    result_id: str,
    decision: DecisionIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ProgramResult:
    """Record Approve / Reject / Maybe.

    A rejected row is kept, with its reason, so the same programme is not
    proposed again on a later run unless something material changed.
    """
    # The result id alone is not authority: resolve the run through the
    # principal's organization first, exactly as every read route does.
    owned_run(session, run_id, principal)
    row = session.get(ProgramResultRow, result_id)
    if row is None or row.run_id != run_id:
        raise HTTPException(404, "Result not found")

    result = ProgramResult.model_validate(row.payload)
    result.user_decision = decision.decision
    result.user_decision_reason = decision.reason
    result.user_notes = decision.notes or result.user_notes
    result.decided_at = datetime.now(UTC)

    row.user_decision = decision.decision.value
    row.user_decision_reason = decision.reason
    row.user_notes = result.user_notes
    row.decided_at = result.decided_at
    row.payload = result.model_dump(mode="json")

    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="decision_recorded",
            entity_type="result",
            entity_id=result_id,
            detail={"decision": decision.decision.value},
        )
    )
    session.commit()
    return result


class NotesIn(BaseModel):
    notes: str = Field(default="", max_length=20_000)


@router.patch("/results/{result_id}/notes", response_model=ProgramResult)
def set_notes(
    run_id: str,
    result_id: str,
    payload: NotesIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ProgramResult:
    """Save a note without touching the decision.

    Editing a note used to re-POST the decision, which stamped `decided_at` on
    a row the applicant had not decided anything about - so an undecided row
    started claiming it was decided the moment they typed a reminder in it.
    """
    owned_run(session, run_id, principal)
    row = session.get(ProgramResultRow, result_id)
    if row is None or row.run_id != run_id:
        raise HTTPException(404, "Result not found")

    result = ProgramResult.model_validate(row.payload)
    result.user_notes = payload.notes
    row.user_notes = payload.notes
    row.payload = result.model_dump(mode="json")
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="note_saved",
            entity_type="result",
            entity_id=result_id,
            detail={},
        )
    )
    session.commit()
    return result


@router.get("/claims")
def list_claims(
    run_id: str,
    response: Response,
    result_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=500, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Evidence for this run, paged.

    A run holds hundreds of claims and the sources screen fetched all of them
    at once; the old cap of 2000 was silent, so a large run simply lost the
    tail with nothing to say it had.
    """
    require_full_access(session, run_id, principal)
    q = session.query(ClaimRow).filter(ClaimRow.run_id == run_id)
    if result_id:
        q = q.filter(ClaimRow.result_id == result_id)
    if status:
        q = q.filter(ClaimRow.status == status)
    response.headers["X-Total-Count"] = str(q.count())
    return [
        {"id": c.id, "result_id": c.result_id, **c.payload}
        for c in q.order_by(ClaimRow.claim_type).limit(limit).offset(offset).all()
    ]


@router.get("/conflicts")
def list_conflicts(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    require_full_access(session, run_id, principal)
    rows = session.query(ConflictRow).filter(ConflictRow.run_id == run_id).all()
    return [{"id": c.id, "result_id": c.result_id, **c.payload} for c in rows]


@router.get("/questions")
def open_questions(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Everything the pipeline could not settle from official sources."""
    require_full_access(session, run_id, principal)
    out: list[dict] = []
    for row in _results(session, run_id):
        result = ProgramResult.model_validate(row.payload)
        for q in result.unresolved:
            out.append(
                {
                    "result_id": row.id,
                    "university": result.university,
                    "program": result.program,
                    **q.model_dump(mode="json"),
                }
            )
        for c in result.conflicts:
            out.append(
                {
                    "result_id": row.id,
                    "university": result.university,
                    "program": result.program,
                    "topic": "source conflict",
                    "question": c.question_for_admissions,
                    "why_it_matters": f"Official sources disagree on {c.subject}: {c.values}",
                    "blocking": True,
                    "conflict": c.model_dump(mode="json"),
                }
            )
    return out


@router.get("/deadlines.ics")
def deadlines_ics(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Every confirmed deadline as a calendar file.

    Only dates the pipeline actually confirmed become events: an unknown
    deadline produces no event rather than a placeholder somebody might plan
    around.
    """
    # An export of every confirmed deadline is paid material, exactly as
    # export.{fmt} is.
    require_full_access(session, run_id, principal)
    results = [ProgramResult.model_validate(r.payload) for r in _results(session, run_id)]
    body = calendar.to_ics(results, run_id=run_id, now=datetime.now(UTC))
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_safe_filename_stem(f"ashyq-{run_id[:8]}-deadlines")}.ics"'
            )
        },
    )


@router.get("/deadlines")
def deadlines(
    run_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """The nearest deadlines, soonest first, with passed ones marked."""
    # Spans every result, including the rows a free tier does not show, so it
    # would otherwise leak past the truncated shortlist.
    require_full_access(session, run_id, principal)
    results = [ProgramResult.model_validate(r.payload) for r in _results(session, run_id)]
    return calendar.upcoming(results, today=datetime.now(UTC).date(), limit=limit)


@router.get("/export.{fmt}")
def export(
    run_id: str,
    fmt: str,
    decision: str | None = Query(default=None, description="Filter, e.g. 'approved'"),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    require_full_access(session, run_id, principal)
    run = owned_run(session, run_id, principal)
    # The filter goes into the Content-Disposition header, so it is validated
    # against the enum rather than trusted: `?decision=approved" ; x-injected="1`
    # used to land inside the header verbatim.
    if decision is not None and decision not in {d.value for d in UserDecision}:
        raise HTTPException(
            400,
            f"Unknown decision filter {decision!r}. Use one of: "
            f"{', '.join(sorted(d.value for d in UserDecision))}.",
        )
    rows = _results(session, run_id, decision=decision)
    results = [ProgramResult.model_validate(r.payload) for r in rows]
    meta = {
        "run_id": run_id,
        "demo_mode": run.demo_mode,
        "stage": run.stage,
        "filter": {"decision": decision},
    }
    # Belt and braces: even a validated value is rebuilt from a safe alphabet,
    # so no future caller can smuggle a quote or a newline into the header.
    stem = _safe_filename_stem(f"ashyq-{run_id[:8]}{'-' + decision if decision else ''}")

    if fmt == "csv":
        return Response(
            tabular.to_csv(results),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'},
        )
    if fmt == "json":
        return Response(
            tabular.to_json(results, meta),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
        )
    if fmt == "xlsx":
        return Response(
            tabular.to_xlsx(results, meta),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{stem}.xlsx"'},
        )
    raise HTTPException(400, "Supported formats: csv, json, xlsx")


class RerankIn(BaseModel):
    """What to change before re-ranking. Everything is optional."""

    priorities: list[PriorityGroup] | None = None
    preferences: Preferences | None = None
    funding: FundingNeeds | None = None
    weights: ScoringWeights | None = None
    gamma: float | None = Field(default=None, ge=0.0, le=2.0)
    #: Off by default: trying an ordering out must not silently rewrite the
    #: applicant's stored profile.
    persist: bool = False


class RerankOut(BaseModel):
    rows: int
    gamma: float
    weights_source: str


@router.post("/rerank", response_model=RerankOut)
def rerank(
    run_id: str,
    payload: RerankIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RerankOut:
    """Re-rank a finished run against changed preferences, fetching nothing.

    Every input the ranking needs is already stored on the row, so changing
    what matters is arithmetic — not a reason to crawl twenty universities
    again and wait five minutes for the same pages.
    """
    settings = get_settings()
    run = owned_run(session, run_id, principal)
    profile_row = session.get(ApplicantProfileRow, run.profile_id)
    if profile_row is None:  # pragma: no cover - a run cannot outlive its profile
        raise HTTPException(404, "Applicant case not found")

    profile = ApplicantProfileIn.model_validate(profile_row.payload)
    if payload.preferences is not None:
        profile.preferences = payload.preferences
    if payload.priorities is not None:
        profile.preferences.priorities = payload.priorities
    if payload.funding is not None:
        profile.funding = payload.funding
    if payload.weights is not None:
        profile.weights = payload.weights
        # Moving a slider by hand is the statement that the sliders are in use.
        profile.weights_override = True

    gamma = payload.gamma if payload.gamma is not None else settings.ranking_gamma
    rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).all()
    source = "priorities_roc"
    for row in rows:
        result = ProgramResult.model_validate(row.payload)
        apply_fit_labels(result, profile)
        result.ranking = rank_result(result, profile, gamma=gamma)
        source = result.ranking.weights_source
        store_result(row, result, ranking_version=settings.ranking_version)
        session.add(row)

    if payload.persist:
        profile_row.payload = profile.model_dump(mode="json")
        session.add(profile_row)
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="results_reranked",
            entity_type="run",
            entity_id=run_id,
            detail={"rows": len(rows), "gamma": gamma, "persisted": payload.persist},
        )
    )
    session.commit()
    return RerankOut(rows=len(rows), gamma=gamma, weights_source=source)


class ShortlistOut(BaseModel):
    chosen: list[ProgramResult]
    notes: list[str]
    quotas: dict[str, int]


@router.get("/shortlist", response_model=ShortlistOut)
def shortlist(
    run_id: str,
    size: int = Query(default=10, ge=1, le=50),
    min_well_placed: int = Query(default=2, ge=0, le=50),
    min_plausible: int = Query(default=4, ge=0, le=50),
    max_ambitious: int = Query(default=3, ge=0, le=50),
    max_per_country: int = Query(default=3, ge=1, le=50),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ShortlistOut:
    """A balanced list, not the top ten of one sort column.

    Twenty ambitious options ranked by fit is a list nobody can act on, so the
    quotas are filled first and any shortfall is stated in `notes`.
    """
    # Returns whole ProgramResult rows, so without this it is a way round the
    # truncated shortlist. Not truncated here instead: cutting a
    # quota-balanced portfolio to five rows would make its own notes untrue.
    require_full_access(session, run_id, principal)
    quotas = Quotas(
        size=size,
        min_well_placed=min_well_placed,
        min_plausible=min_plausible,
        max_ambitious=max_ambitious,
        max_per_country=max_per_country,
    )
    rows = {
        r.id: r
        for r in session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).all()
        # A rejected row is out of the portfolio; the reason stays on the row.
        if r.user_decision != UserDecision.REJECTED.value
    }
    candidates = [
        ShortlistCandidate(
            id=r.id,
            country=r.country,
            bucket=Bucket(r.bucket) if r.bucket else Bucket.NEEDS_CLARIFICATION,
            sort_key=r.score_total,
        )
        for r in rows.values()
    ]
    chosen, notes = build_shortlist(candidates, quotas)
    return ShortlistOut(
        chosen=[ProgramResult.model_validate(rows[c.id].payload) for c in chosen],
        notes=notes,
        quotas=asdict(quotas),
    )
