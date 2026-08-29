"""Writing a result and its evidence, idempotently.

Split out of the runner so the stages can be read without the SQL, and so the
idempotency rules live in one place. Those rules are not incidental: a run that
is retried after a crash re-enters a stage whose rows already exist, and the
first version collided on the (run_id, dedupe_key) unique index instead of
refreshing what was there.

Every method here is safe to call twice with the same result.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import dedupe
from app.models import ClaimRow, ConflictRow, ProgramResultRow
from app.models.base import new_id
from app.schemas.result import ProgramResult


class ResultStore:
    """The run's results, claims and conflicts."""

    def __init__(self, session: Session, run) -> None:
        self._session = session
        self._run = run
        self._run_id = run.id

    def rows(self) -> list[ProgramResultRow]:
        return (
            self._session.query(ProgramResultRow)
            .filter(ProgramResultRow.run_id == self._run_id)
            .order_by(ProgramResultRow.id)
            .all()
        )

    def persist_result(self, result: ProgramResult, claims, conflicts) -> None:
        """Write a result, or refresh the one a previous attempt wrote.

        A retry after a crash re-derives results the first attempt already
        stored. Inserting blindly violates the (run_id, dedupe_key) unique
        index and fails the retry, so an existing row is updated in place and
        its evidence replaced rather than appended to.
        """
        dedupe_key = dedupe.program_key(
            result.university, result.program, result.degree, result.intake, result.country
        )
        existing = (
            self._session.query(ProgramResultRow)
            .filter(
                ProgramResultRow.run_id == self._run_id,
                ProgramResultRow.dedupe_key == dedupe_key,
            )
            .one_or_none()
        )
        if existing is not None:
            result.id = existing.id
            self._replace_evidence(existing.id)
            self.update_result(existing, result, extra_claims=claims, conflicts=conflicts)
            return

        # The row's primary key is authoritative; the result document adopts it
        # so every claim, conflict and checklist points at the same identifier.
        row = ProgramResultRow(
            id=new_id(),
            run_id=self._run_id,
            dedupe_key=dedupe_key,
            university=result.university,
            university_key=result.university_id,
            country=result.country,
            program=result.program,
            eligibility=result.eligibility.value,
            admissions_fit=result.admissions_fit.value,
            funding_fit=result.funding_fit.value,
            funding_classification=result.best_funding_classification.value,
            score_total=0.0,
            payload=result.model_dump(mode="json"),
        )
        result.id = row.id
        row.payload = result.model_dump(mode="json")
        self._session.add(row)
        self._session.flush()
        self._store_claims(row.id, claims)
        self._store_conflicts(row.id, conflicts)

    def update_result(
        self, row: ProgramResultRow, result: ProgramResult, extra_claims=None, conflicts=None
    ) -> None:
        result.id = row.id
        row.payload = result.model_dump(mode="json")
        row.eligibility = result.eligibility.value
        row.admissions_fit = result.admissions_fit.value
        row.funding_fit = result.funding_fit.value
        row.funding_classification = result.best_funding_classification.value
        row.score_total = result.preference_score.total if result.preference_score else 0.0
        self._session.add(row)
        if extra_claims:
            self._store_claims(row.id, extra_claims)
        if conflicts:
            self._store_conflicts(row.id, conflicts)

    def _replace_evidence(self, result_id: str) -> None:
        """Drop the evidence a previous attempt stored for this result.

        Re-running a stage re-reads the same pages, so keeping both copies
        would inflate the claim count and show the user duplicate evidence.
        """
        self._session.query(ClaimRow).filter(ClaimRow.result_id == result_id).delete(
            synchronize_session=False
        )
        self._session.query(ConflictRow).filter(ConflictRow.result_id == result_id).delete(
            synchronize_session=False
        )

    def _store_claims(self, result_id: str, claims) -> None:
        for c in claims:
            self._session.add(
                ClaimRow(
                    run_id=self._run_id,
                    result_id=result_id,
                    claim_type=c.claim_type.value,
                    status=c.status.value,
                    source_url=c.source_url,
                    source_specificity=c.source_specificity.value,
                    accessed_at=c.accessed_at,
                    payload=c.model_dump(mode="json"),
                )
            )

    def _store_conflicts(self, result_id: str, conflicts) -> None:
        for c in conflicts:
            self._session.add(
                ConflictRow(
                    run_id=self._run_id,
                    result_id=result_id,
                    claim_type=c.claim_type.value,
                    unresolved=c.unresolved,
                    payload=c.model_dump(mode="json"),
                )
            )


# --- small helpers ------------------------------------------------------
