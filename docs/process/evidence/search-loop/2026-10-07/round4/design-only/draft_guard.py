"""External executable design sketch. NOT production code or an accepted contract.

No app imports, providers or real Fetcher calls. The two proposed clocks are
explicit alternatives. Existing _save fencing is represented by MemoryStore.
"""
from __future__ import annotations

import asyncio
import copy
import math
from contextlib import contextmanager
from contextvars import ContextVar

MAX_CALLS = 60
MAX_MS = 120_000
ENVELOPE = "university_research_budget_v1"


class BudgetStopped(RuntimeError):
    pass


class InvalidBudget(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


class UserCancelled(RuntimeError):
    pass


class Clock:
    def __init__(self):
        self.monotonic_ms = 0
        self.utc_ms = 1_800_000_000_000

    def advance(self, ms):
        self.monotonic_ms += ms
        self.utc_ms += ms


class MemoryStore:
    """Simulates replacement of JSON + _save fenced transaction commit."""
    def __init__(self, settings_snapshot=None):
        self.snapshot = copy.deepcopy(settings_snapshot or {})
        self.owner_token = 1
        self.cancelled = False
        self.commits = 0
        self.json_roundtrips = 0

    def check_cancelled(self):
        if self.cancelled:
            raise UserCancelled()

    def commit(self, replacement, token):
        if token != self.owner_token:
            raise LeaseLost()
        # A true JSON round-trip: no process clock, callbacks, exception, or URL.
        import json
        self.snapshot = json.loads(json.dumps(replacement))
        self.commits += 1
        self.json_roundtrips += 1


class DraftGuard:
    def __init__(self, store, clock, *, policy, episode="job-1", token=1):
        if policy not in {"absolute", "focused"}:
            raise ValueError(policy)
        self.store, self.clock, self.token = store, clock, token
        self.current = ContextVar("draft_university_scope", default=None)
        self.local_deadlines = {}
        prior = store.snapshot.get(ENVELOPE)
        if prior is not None:
            if prior.get("episode") != episode:
                raise InvalidBudget("A new episode must be deliberately selected, never inferred here")
            if prior.get("version") != 1 or prior.get("policy") != policy or prior.get("limits") != {"calls": MAX_CALLS, "ms": MAX_MS}:
                raise InvalidBudget("Corrupt, incompatible or expanded budget")
            for state in prior.get("universities", {}).values():
                for key in ("calls", "spent_ms", "reserved_ms", "last_remaining_ms"):
                    if type(state.get(key)) is not int or state[key] < 0:
                        raise InvalidBudget(key)
                if state["calls"] > MAX_CALLS or state["spent_ms"] + state["reserved_ms"] > MAX_MS or state["last_remaining_ms"] > MAX_MS:
                    raise InvalidBudget("Cap exceeded in persisted state")
        self.envelope = copy.deepcopy(prior) if prior else {
            "version": 1, "episode": episode, "policy": policy,
            "limits": {"calls": MAX_CALLS, "ms": MAX_MS}, "universities": {},
        }
        self.policy = policy

    def persist(self):
        # Replace the entire JSON field. Preserve unrelated Settings/query fields.
        replacement = {**self.store.snapshot, ENVELOPE: copy.deepcopy(self.envelope)}
        self.store.commit(replacement, self.token)

    def _state(self, key):
        if not key:
            raise InvalidBudget("Live source work needs an explicit university identity")
        states = self.envelope["universities"]
        if key not in states:
            states[key] = {
                "calls": 0, "spent_ms": 0, "reserved_ms": 0,
                "opened_utc_ms": self.clock.utc_ms,
                "deadline_utc_ms": self.clock.utc_ms + MAX_MS,
                "last_checkpoint_utc_ms": self.clock.utc_ms,
                "last_remaining_ms": MAX_MS, "stop_reason": None,
            }
        return states[key]

    def _remaining_absolute(self, key, state):
        if self.clock.utc_ms < state["last_checkpoint_utc_ms"]:
            self.stop(key, "clock_unreliable")
        wall = state["deadline_utc_ms"] - self.clock.utc_ms
        if key not in self.local_deadlines:
            self.local_deadlines[key] = self.clock.monotonic_ms + min(wall, state["last_remaining_ms"])
        return min(wall, self.local_deadlines[key] - self.clock.monotonic_ms)

    def remaining(self):
        active = self.current.get()
        if active is None:
            raise InvalidBudget("Unscoped live read is blocked")
        key, began_ms, prior_spent_ms = active
        state = self._state(key)
        if state["stop_reason"]:
            raise BudgetStopped(state["stop_reason"])
        if self.policy == "absolute":
            left = self._remaining_absolute(key, state)
        else:
            left = MAX_MS - prior_spent_ms - math.ceil(self.clock.monotonic_ms - began_ms)
        if left <= 0:
            self.stop(key, "time_cap")
        return left

    def stop(self, key, reason):
        self._state(key)["stop_reason"] = reason
        self.persist()
        raise BudgetStopped(reason)

    @contextmanager
    def scope(self, key):
        active = self.current.get()
        if active is not None:
            if active[0] != key:
                raise InvalidBudget("Nested different university scope")
            yield  # Same-key nested helper: never recharge/reserve/restart timer.
            return
        self.store.check_cancelled()
        state = self._state(key)
        # A crash/reclaim cannot refund an unfinished focused reservation.
        if self.policy == "focused" and state["reserved_ms"]:
            state["spent_ms"] += state["reserved_ms"]
            state["reserved_ms"] = 0
            if state["spent_ms"] >= MAX_MS:
                state["stop_reason"] = "time_cap_unsettled_scope"
            self.persist()
        prior = state["spent_ms"]
        started = self.clock.monotonic_ms
        context = self.current.set((key, started, prior))
        try:
            left = self.remaining()
            if self.policy == "focused":
                state["reserved_ms"] = left  # All remaining allowance, durably.
            self.persist()  # Fence/time reservation before any possible I/O.
            self.remaining()  # Persistence time spends the same allowance.
            yield
            self.remaining()  # Detect synchronous CPU overrun on return.
        finally:
            if self.policy == "focused":
                # A live, owned, clean unwind may settle. A crash does not execute
                # this finally; a lost lease cannot commit a refund.
                elapsed = max(0, math.ceil(self.clock.monotonic_ms - started))
                state["spent_ms"] = min(MAX_MS, prior + elapsed)
                state["reserved_ms"] = 0
            try:
                self.persist()
            finally:
                self.current.reset(context)

    async def run(self, key, operation):
        with self.scope(key):
            timer = asyncio.timeout(self.remaining() / 1000)
            try:
                async with timer:
                    return await operation()
            except TimeoutError:
                if timer.expired():
                    self.stop(key, "time_cap")
                raise  # An unrelated operation timeout keeps its real meaning.

    async def get(self, original_get, url, **kwargs):
        self.store.check_cancelled()
        left = self.remaining()
        key = self.current.get()[0]
        state = self._state(key)
        if state["calls"] >= MAX_CALLS:
            self.stop(key, "read_cap")
        state["calls"] += 1  # Charge attempts, cache, refusal and failures alike.
        state["last_remaining_ms"] = min(state["last_remaining_ms"], math.ceil(left))
        state["last_checkpoint_utc_ms"] = self.clock.utc_ms
        self.persist()  # Crash after this point still consumes the reservation.
        self.store.check_cancelled()
        self.remaining()
        return await original_get(url, **kwargs)


def preserve_envelope_when_recording_settings(old_snapshot, settings_fields):
    prior = copy.deepcopy(old_snapshot.get(ENVELOPE))
    replacement = dict(settings_fields)
    if prior is not None:
        replacement[ENVELOPE] = prior
    return replacement
