"""Throwaway QA probe plugin (c2-t32 VERIFY, read-only wrt the repo).

Freezes app.pipeline.runner's ``datetime`` to 2026-09-07 23:59:30 UTC — the
moment the golden was captured — to test the hypothesis that the R6 demo
golden failure is purely the UTC-date rollover (today.isoformat() in the
payload is date-only and unmasked), not a T32 code drift.
"""

from datetime import UTC, datetime


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # noqa: ARG003
        return datetime(2026, 9, 7, 23, 59, 30, tzinfo=UTC)


def pytest_configure(config):
    import app.pipeline.runner as runner_mod

    runner_mod.datetime = _FrozenDateTime
