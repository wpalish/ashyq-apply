"""Independent offline regression sketch. Passing tests do not validate production."""
import asyncio
import copy
import unittest
from unittest.mock import patch

from draft_guard import (
    BudgetStopped, Clock, DraftGuard, ENVELOPE, InvalidBudget, LeaseLost,
    MemoryStore, UserCancelled, preserve_envelope_when_recording_settings,
)


class DraftGuardTests(unittest.IsolatedAsyncioTestCase):
    def setup_guard(self, policy="focused", store=None, clock=None):
        self.store = store or MemoryStore({"target_currency": "USD"})
        self.clock = clock or Clock()
        self.guard = DraftGuard(self.store, self.clock, policy=policy)
        self.calls = []

    async def original(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return {"ok": True, "from_cache": kwargs.get("cached", False)}

    def state(self, key="catalogue:1"):
        return self.store.snapshot[ENVELOPE]["universities"][key]

    async def test_sixty_successes_sixty_first_blocked(self):
        self.setup_guard()
        with self.assertRaisesRegex(BudgetStopped, "read_cap"):
            with self.guard.scope("catalogue:1"):
                for _ in range(60):
                    await self.guard.get(self.original, "https://uni.invalid/page")
                await self.guard.get(self.original, "https://uni.invalid/unread")
        self.assertEqual(len(self.calls), 60)
        self.assertEqual(self.state()["calls"], 60)

    async def test_multiple_programmes_and_stages_share_identity(self):
        self.setup_guard()
        for stage, count in [("discovery", 11), ("CS verification", 25), ("Physics funding", 24)]:
            with self.guard.scope("catalogue:1"):
                for _ in range(count):
                    await self.guard.get(self.original, "https://uni.invalid/" + stage)
        with self.assertRaises(BudgetStopped):
            with self.guard.scope("catalogue:1"):
                await self.guard.get(self.original, "https://uni.invalid/other-programme")
        self.assertEqual(self.state()["calls"], 60)

    async def test_cache_hit_is_charged_without_forcing_cache_off(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            result = await self.guard.get(self.original, "https://uni.invalid/page", cached=True, use_cache=True)
        self.assertTrue(result["from_cache"])
        self.assertTrue(self.calls[0][1]["use_cache"])
        self.assertEqual(self.state()["calls"], 1)

    async def test_cross_domain_government_charged_to_active_uni(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            await self.guard.get(self.original, "https://government.invalid/public-policy")
        self.assertEqual(set(self.store.snapshot[ENVELOPE]["universities"]), {"catalogue:1"})
        self.assertEqual(self.state()["calls"], 1)

    async def test_adapter_memo_no_fetcher_invocation_no_charge(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            memo = await self.guard.get(self.original, "https://government.invalid/page")
        with self.guard.scope("catalogue:2"):
            self.assertTrue(memo["ok"])  # Existing gov_cache/pure claim reuse.
        self.assertEqual(self.state("catalogue:2")["calls"], 0)

    async def test_internal_robots_retry_redirect_mock_exchanges_not_extra_gets(self):
        self.setup_guard()
        async def internal(url, **kwargs):
            for kind in ["robots", "DNS", "attempt-1", "redirect", "attempt-2", "render-wait"]:
                self.clock.advance(1000)
            return {"ok": True}
        with self.guard.scope("catalogue:1"):
            await self.guard.get(internal, "https://uni.invalid/page")
        self.assertEqual(self.state()["calls"], 1)
        self.assertEqual(self.state()["spent_ms"], 6000)

    async def test_all_focused_waits_cpu_and_serialization_spend_clock(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            for kind in ["robots", "pacing", "retry", "render", "CPU", "result serialization"]:
                self.clock.advance(10_000)
            await self.guard.get(self.original, "https://uni.invalid/page")
        self.assertEqual(self.state()["spent_ms"], 60_000)

    async def test_A_early_uni_expires_while_other_uni_work_runs(self):
        self.setup_guard("absolute")
        with self.guard.scope("catalogue:1"):
            self.clock.advance(20_000)
        with self.guard.scope("catalogue:2"):
            self.clock.advance(101_000)
        with self.assertRaises(BudgetStopped):
            with self.guard.scope("catalogue:1"):
                await self.guard.get(self.original, "https://uni.invalid/verification")
        self.assertEqual(len(self.calls), 0)

    async def test_B_other_uni_gap_excluded_focused_work_carried(self):
        self.setup_guard("focused")
        with self.guard.scope("catalogue:1"):
            self.clock.advance(20_000)
        with self.guard.scope("catalogue:2"):
            self.clock.advance(101_000)
        with self.guard.scope("catalogue:1"):
            self.clock.advance(99_000)
            await self.guard.get(self.original, "https://uni.invalid/verification")
        self.assertEqual(self.state()["spent_ms"], 119_000)
        self.assertEqual(len(self.calls), 1)

    async def test_deadline_no_new_read_at_120(self):
        for policy in ["absolute", "focused"]:
            self.setup_guard(policy)
            with self.assertRaises(BudgetStopped):
                with self.guard.scope("catalogue:1"):
                    self.clock.advance(120_000)
                    await self.guard.get(self.original, "https://uni.invalid/unread")
            self.assertEqual(len(self.calls), 0)

    async def test_restart_read_reservation_not_refunded(self):
        self.setup_guard("absolute")
        async def crashes(url, **kwargs):
            self.assertEqual(self.state()["calls"], 1)  # Committed before I/O.
            raise RuntimeError("simulated transport crash")
        with self.assertRaises(RuntimeError):
            with self.guard.scope("catalogue:1"):
                await self.guard.get(crashes, "https://uni.invalid/page")
        self.guard = DraftGuard(self.store, self.clock, policy="absolute")
        with self.guard.scope("catalogue:1"):
            await self.guard.get(self.original, "https://uni.invalid/new")
        self.assertEqual(self.state()["calls"], 2)

    async def test_B_hard_crash_consumes_unsettled_full_reservation(self):
        self.setup_guard()
        # Snapshot DURING a scope: emulate a process death with no finally.
        with self.guard.scope("catalogue:1"):
            await self.guard.get(self.original, "https://uni.invalid/page")
            frozen_at_crash = copy.deepcopy(self.store.snapshot)
        resumed_store = MemoryStore(frozen_at_crash)
        resumed = DraftGuard(resumed_store, self.clock, policy="focused")
        with self.assertRaisesRegex(BudgetStopped, "unsettled"):
            with resumed.scope("catalogue:1"):
                await resumed.get(self.original, "https://uni.invalid/forbidden")
        self.assertEqual(resumed_store.snapshot[ENVELOPE]["universities"]["catalogue:1"]["spent_ms"], 120_000)
        self.assertEqual(len(self.calls), 1)

    async def test_A_restart_downtime_spends_absolute_deadline(self):
        self.setup_guard("absolute")
        with self.guard.scope("catalogue:1"):
            await self.guard.get(self.original, "https://uni.invalid/page")
        self.clock.advance(120_000)
        resumed = DraftGuard(self.store, self.clock, policy="absolute")
        with self.assertRaises(BudgetStopped):
            with resumed.scope("catalogue:1"):
                await resumed.get(self.original, "https://uni.invalid/unread")
        self.assertEqual(len(self.calls), 1)

    async def test_A_backwards_utc_on_resume_fails_closed(self):
        self.setup_guard("absolute")
        with self.guard.scope("catalogue:1"):
            await self.guard.get(self.original, "https://uni.invalid/page")
        self.clock.utc_ms -= 1
        resumed = DraftGuard(self.store, self.clock, policy="absolute")
        with self.assertRaisesRegex(BudgetStopped, "clock_unreliable"):
            with resumed.scope("catalogue:1"):
                pass

    async def test_lost_fence_before_reservation_no_io(self):
        self.setup_guard()
        self.store.owner_token = 2
        with self.assertRaises(LeaseLost):
            with self.guard.scope("catalogue:1"):
                await self.guard.get(self.original, "https://uni.invalid/page")
        self.assertEqual(len(self.calls), 0)

    async def test_lost_fence_cannot_refund_active_reservation(self):
        self.setup_guard()
        with self.assertRaises(LeaseLost):
            with self.guard.scope("catalogue:1"):
                self.store.owner_token = 2
        self.assertEqual(self.state()["reserved_ms"], 120_000)

    async def test_cancel_flag_checked_before_io(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            self.store.cancelled = True
            with self.assertRaises(UserCancelled):
                await self.guard.get(self.original, "https://uni.invalid/page")
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(self.state()["calls"], 0)

    async def test_foreign_task_cancel_propagates(self):
        self.setup_guard()
        async def cancelled():
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.guard.run("catalogue:1", cancelled)
        self.assertIsNone(self.state()["stop_reason"])

    async def test_scope_timer_cancels_an_inflight_wait_without_new_io(self):
        self.setup_guard()
        loop = asyncio.get_running_loop()
        loop_started = loop.time()
        cleaned = []
        async def waits():
            try:
                self.clock.advance(120_001)
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                await asyncio.sleep(0)
            finally:
                cleaned.append(True)
        prior_debug = loop.get_debug()
        loop.set_debug(False)  # Avoid a debug warning reporting virtual 120s as latency.
        try:
            with patch.object(loop, "time", lambda: loop_started + self.clock.monotonic_ms / 1000):
                with self.assertRaises(BudgetStopped):
                    await self.guard.run("catalogue:1", waits)
        finally:
            loop.set_debug(prior_debug)
        self.assertEqual(cleaned, [True])

    async def test_unscoped_read_rejected_and_nested_same_key_not_restarted(self):
        self.setup_guard()
        with self.assertRaises(InvalidBudget):
            await self.guard.get(self.original, "https://uni.invalid/unscoped")
        with self.guard.scope("catalogue:1"):
            self.clock.advance(5000)
            with self.guard.scope("catalogue:1"):
                self.clock.advance(5000)
            with self.assertRaises(InvalidBudget):
                with self.guard.scope("catalogue:2"):
                    pass
        self.assertEqual(self.state()["spent_ms"], 10_000)

    async def test_settings_replacement_preserves_envelope_and_opaque_query_state(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            await self.guard.get(self.original, "https://uni.invalid/page")
        self.store.snapshot[ENVELOPE]["universities"]["catalogue:1"]["queries_used"] = 5
        replacement = preserve_envelope_when_recording_settings(self.store.snapshot, {"academic_year": "2027/28"})
        self.assertEqual(replacement[ENVELOPE]["universities"]["catalogue:1"]["calls"], 1)
        self.assertEqual(replacement[ENVELOPE]["universities"]["catalogue:1"]["queries_used"], 5)
        self.assertEqual(replacement["academic_year"], "2027/28")

    async def test_bad_state_and_silent_new_episode_rejected(self):
        self.setup_guard()
        with self.guard.scope("catalogue:1"):
            pass
        with self.assertRaises(InvalidBudget):
            DraftGuard(self.store, self.clock, policy="focused", episode="job-2")
        self.store.snapshot[ENVELOPE]["universities"]["catalogue:1"]["calls"] = -1
        with self.assertRaises(InvalidBudget):
            DraftGuard(self.store, self.clock, policy="focused")

    async def test_known_limitation_sync_cpu_is_detected_after_it_returns(self):
        self.setup_guard()
        self.completed_cpu = False
        async def CPU():
            self.clock.advance(180_000)  # Represents synchronous work: no await.
            self.completed_cpu = True
        with self.assertRaises(BudgetStopped):
            await self.guard.run("catalogue:1", CPU)
        self.assertTrue(self.completed_cpu)
        self.assertEqual(self.clock.monotonic_ms, 180_000)

    async def test_completed_adapter_evidence_survives_later_budget_stop_sketch(self):
        self.setup_guard()
        workspace = {"requirements": None, "costs": None, "unresolved": []}
        async def research():
            workspace["requirements"] = {"claims": ["mock official language claim"]}
            self.clock.advance(120_000)
            workspace["costs"] = await self.guard.get(self.original, "https://uni.invalid/costs")
        try:
            await self.guard.run("catalogue:1", research)
        except BudgetStopped:
            workspace["unresolved"].append("Remaining research remains unknown: university budget exhausted.")
        self.assertEqual(workspace["requirements"]["claims"], ["mock official language claim"])
        self.assertIsNone(workspace["costs"])
        self.assertEqual(len(workspace["unresolved"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
