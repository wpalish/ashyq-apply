"""Reading the shortlist, recording decisions, and inspecting evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.tenancy import owned_run
from app.db import get_session
from app.export import tabular
from app.models import AuditEvent, ClaimRow, ConflictRow, ProgramResultRow
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
    return q.order_by(ProgramResultRow.score_total.desc(), ProgramResultRow.university).all()


@router.get("/results", response_model=list[ProgramResult])
def list_results(
    run_id: str,
    decision: str | None = None,
    eligibility: str | None = None,
    funding: str | None = None,
    country: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[ProgramResult]:
    owned_run(session, run_id, principal)
    rows = _results(
        session,
        run_id,
        decision=decision,
        eligibility=eligibility,
        funding=funding,
        country=country,
    )
    return [ProgramResult.model_validate(r.payload) for r in rows]


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
    owned_run(session, run_id, principal)
    row = session.get(ProgramResultRow, result_id)
    if row is None or row.run_id != run_id:
        raise HTTPException(404, "Result not found")
    return ProgramResult.model_validate(row.payload)


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


@router.get("/claims")
def list_claims(
    run_id: str,
    result_id: str | None = None,
    status: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    owned_run(session, run_id, principal)
    q = session.query(ClaimRow).filter(ClaimRow.run_id == run_id)
    if result_id:
        q = q.filter(ClaimRow.result_id == result_id)
    if status:
        q = q.filter(ClaimRow.status == status)
    return [
        {"id": c.id, "result_id": c.result_id, **c.payload}
        for c in q.order_by(ClaimRow.claim_type).limit(2000).all()
    ]


@router.get("/conflicts")
def list_conflicts(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    owned_run(session, run_id, principal)
    rows = session.query(ConflictRow).filter(ConflictRow.run_id == run_id).all()
    return [{"id": c.id, "result_id": c.result_id, **c.payload} for c in rows]


@router.get("/questions")
def open_questions(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Everything the pipeline could not settle from official sources."""
    owned_run(session, run_id, principal)
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


@router.get("/export.{fmt}")
def export(
    run_id: str,
    fmt: str,
    decision: str | None = Query(default=None, description="Filter, e.g. 'approved'"),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    run = owned_run(session, run_id, principal)
    rows = _results(session, run_id, decision=decision)
    results = [ProgramResult.model_validate(r.payload) for r in rows]
    meta = {
        "run_id": run_id,
        "demo_mode": run.demo_mode,
        "stage": run.stage,
        "filter": {"decision": decision},
    }
    stem = f"unimatch-{run_id[:8]}{'-' + decision if decision else ''}"

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
