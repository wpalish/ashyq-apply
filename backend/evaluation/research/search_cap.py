"""A per-run ledger and hard cap on provider queries (free-search ticket 02).

``--max-search-queries N`` on ``evaluation.research.live`` (and the workflow's
``max_search_queries`` input) names how many queries one run may send to a
provider that can spend an allowance or a paid key. The run refuses to start
when its plan (6 per case, the brief's budget, times the cases it captures)
exceeds what the ledger has left; every query reserves one unit before it is
sent, and the (N+1)th is refused locally with ``SearchUnavailable``, no
request sent. The run then stops cleanly with ``search_budget_exhausted``.

The ledger is one small JSON file that every capture of a run shares (the
paired workflow starts four captures per university, five universities at a
time), updated under an OS file lock, so the cap holds across processes.

Only ``none``, ``fake`` and ``recorded`` are uncapped: none of them sends a
query anywhere. Every other provider needs an explicit cap, so a run that
forgot to say how much it may spend spends nothing.

Evaluation tooling only: nothing under ``app/`` may import it.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Providers that send no query anywhere: no allowance and no key can be spent.
UNCAPPED_PROVIDERS = frozenset({"none", "fake", "recorded"})
#: The brief's per-university query budget, the unit a run is planned in.
QUERIES_PER_CASE = 6
#: What a capture records when the run's cap refused a query.
RUN_CAP_STOP_REASON = "search_budget_exhausted"


class SearchCapError(ValueError):
    """The ledger cannot be opened as asked (a different cap, a corrupt file)."""


def needs_cap(provider: str) -> bool:
    """Whether a run on ``provider`` must name its query cap before it starts."""
    return provider not in UNCAPPED_PROVIDERS


def planned_queries(cases: int, columns: int = 1, extra: int = 0) -> int:
    """The brief's ceiling for a run: 6 per case per column, plus ``extra`` (pre-flight)."""
    return QUERIES_PER_CASE * cases * columns + extra


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    """An exclusive OS lock on ``path``'s sidecar, released even when the holder dies."""
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+b") as handle:
        try:
            import fcntl
        except ImportError:  # pragma: no cover - Windows self-hosted runner
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
            return
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@dataclass(frozen=True)
class SearchQueryLedger:
    """One run's query count against its cap, in a file every capture shares."""

    path: Path
    cap: int

    @classmethod
    def open(cls, path: Path, cap: int) -> SearchQueryLedger:
        """The ledger at ``path``, created with ``cap`` if absent.

        An existing ledger must carry the same cap: a later capture of a run
        cannot raise the cap the run started under.
        """
        if type(cap) is not int or cap < 1:
            raise SearchCapError("the search query cap must be a positive integer")
        path.parent.mkdir(parents=True, exist_ok=True)
        ledger = cls(path, cap)
        with _locked(path):
            if path.exists():
                recorded = ledger._read()["max_search_queries"]
                if recorded != cap:
                    raise SearchCapError(
                        f"the run's search ledger was opened with a cap of {recorded}, not {cap}"
                    )
            else:
                ledger._write({"max_search_queries": cap, "used": 0, "refused": 0})
        return ledger

    def _read(self) -> dict[str, Any]:
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SearchCapError(f"unreadable search ledger: {type(exc).__name__}") from None
        if not isinstance(state, dict) or not all(
            type(state.get(key)) is int and state[key] >= 0
            for key in ("max_search_queries", "used", "refused")
        ):
            raise SearchCapError("malformed search ledger")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_name(f"{self.path.name}.{os.getpid()}.pending")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def state(self) -> dict[str, int]:
        with _locked(self.path):
            state = self._read()
        return {key: state[key] for key in ("max_search_queries", "used", "refused")}

    def remaining(self) -> int:
        state = self.state()
        return max(0, state["max_search_queries"] - state["used"])

    def reserve(self) -> bool:
        """Charge one query; False (and counted as refused) when the cap is reached."""
        with _locked(self.path):
            state = self._read()
            allowed = state["used"] < state["max_search_queries"]
            state["used" if allowed else "refused"] += 1
            self._write(state)
        return allowed

    def exhausted(self) -> bool:
        return self.remaining() == 0
