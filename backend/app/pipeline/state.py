"""The research state machine.

State lives in the database, not in a running task, so a run survives a restart
and a failed stage can be retried without repeating the ones before it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.domain.enums import STAGE_ORDER, PipelineStage
from app.models.base import ensure_utc

#: A run in one of these stages should have a live worker behind it.
IN_PROGRESS_STAGES = {
    PipelineStage.QUEUED,
    PipelineStage.PROFILE_VALIDATION,
    PipelineStage.CANDIDATE_DISCOVERY,
    PipelineStage.PROGRAM_VERIFICATION,
    PipelineStage.FUNDING_DISCOVERY,
    PipelineStage.ASSESSMENT,
    PipelineStage.DOCUMENT_COLLECTION,
}

#: How long a worker may go silent before its run is treated as abandoned.
#: Long enough to cover a slow page fetch with its retries and backoff. This is
#: only the fallback: the live value is UNIMATCH_JOB_LEASE_SECONDS, and holding
#: a second copy here is how the API came to call a healthy run stale while the
#: worker considered its lease perfectly valid.
DEFAULT_LEASE_SECONDS = 120



@dataclass
class StageState:
    status: str = "pending"  # pending | running | done | failed | skipped
    started_at: str | None = None
    finished_at: str | None = None
    error: str = ""
    detail: str = ""
    items_done: int = 0
    items_total: int = 0

    def start(self, total: int = 0, detail: str = "") -> None:
        self.status = "running"
        self.started_at = datetime.now(UTC).isoformat()
        self.items_total = total
        self.items_done = 0
        self.detail = detail

    def finish(self, detail: str = "") -> None:
        self.status = "done"
        self.finished_at = datetime.now(UTC).isoformat()
        if detail:
            self.detail = detail

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.finished_at = datetime.now(UTC).isoformat()
        self.error = error[:1000]


@dataclass
class RunState:
    stages: dict[str, StageState] = field(default_factory=dict)

    @classmethod
    def load(cls, raw: dict | None) -> RunState:
        stages = {
            name: StageState(**data) for name, data in (raw or {}).items() if isinstance(data, dict)
        }
        for stage in STAGE_ORDER:
            stages.setdefault(stage.value, StageState())
        return cls(stages=stages)

    def dump(self) -> dict:
        return {name: asdict(state) for name, state in self.stages.items()}

    def __getitem__(self, stage: PipelineStage) -> StageState:
        return self.stages.setdefault(stage.value, StageState())

    def progress(self) -> float:
        # This endpoint reports *research* progress. Waiting for the applicant
        # and the optional post-approval document collection are later workflow
        # phases, so a finished shortlist must read 100%, not 71% or 86%.
        tracked = [
            PipelineStage.PROFILE_VALIDATION,
            PipelineStage.CANDIDATE_DISCOVERY,
            PipelineStage.PROGRAM_VERIFICATION,
            PipelineStage.FUNDING_DISCOVERY,
            PipelineStage.ASSESSMENT,
        ]
        done = sum(1 for s in tracked if self[s].status in ("done", "skipped"))
        return round(done / len(tracked), 3) if tracked else 0.0


def is_lease_expired(
    stage: str,
    heartbeat_at: datetime | None,
    *,
    now: datetime | None = None,
    lease_seconds: int | None = None,
) -> bool:
    """Whether a run claims to be working but nothing is behind it.

    A run that never started has no heartbeat and is not abandoned; it is
    waiting to be picked up. Only a run that beat and then stopped is.
    """
    try:
        current = PipelineStage(stage)
    except ValueError:
        return False
    if current not in IN_PROGRESS_STAGES:
        return False
    heartbeat_at = ensure_utc(heartbeat_at)
    if heartbeat_at is None:
        return False
    if lease_seconds is None:
        from app.config import get_settings

        lease_seconds = get_settings().job_lease_seconds
    reference = now or datetime.now(UTC)
    return (reference - heartbeat_at).total_seconds() > lease_seconds


#: `can_transition` used to live here: a rule set that forbade any backwards
#: move along STAGE_ORDER while permitting any forward jump. Nothing called it,
#: and both halves were wrong for this pipeline - retry-from-stage and the
#: freshness recheck move a run backwards on purpose, while a forward jump over
#: unfinished work is exactly what it let through. Deleted rather than
#: repaired: the invariant that matters is enforced where the work happens, by
#: `_maybe` skipping only stages already marked done, and by the API resetting
#: a stage to pending before a re-run can enter it.
