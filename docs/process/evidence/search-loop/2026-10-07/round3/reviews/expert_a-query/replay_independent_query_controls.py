"""Actual external-proposal control replay; outputs raw synthetic vendor records."""
import asyncio
import copy
import hashlib
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import conftest  # imports the pinned external modules only
from pytest import MonkeyPatch
from test_independent_query_controls import (
    ENTRY, Candidate, DiscoveryTrace, IndependentVendor, PageCategory,
    adapter, intent, profile, reset_search_throttle,
)


def forbid(*args, **kwargs):
    raise AssertionError("Offline-only review")


async def main():
    cases = []
    for multi in [False, True]:
        with MonkeyPatch.context() as mp:
            reset_search_throttle()
            mp.setattr(socket, "getaddrinfo", forbid)
            mp.setattr(socket, "create_connection", forbid)
            mp.setattr(socket.socket, "connect", forbid)
            mp.setattr(intent, "SHARED_QUERY_BUDGET", True)
            vendor = IndependentVendor()
            instance, factories = adapter(mp, vendor)
            uni = SimpleNamespace(id="audit", name=ENTRY["name"], country=ENTRY["country"], city=ENTRY["city"], domain="example.edu", registry_entry=None, seed_snapshot={})
            candidate, trace = await instance._enrich(uni, profile(multi), Candidate(uni.name, uni.country, uni.city), DiscoveryTrace(uni.name, uni.domain))
            cases.append({"case": "identity_then_programmes", "multi": multi, "vendor_search_calls": len(vendor.calls), "identity_calls": sum("official university website" in q for q in vendor.calls), "candidate_count": candidate.search_queries_used, "trace_attempts": trace.search_queries_sent, "trace_raw": trace.as_dict(), "vendor_queries": vendor.calls})
    for multi in [False, True]:
        with MonkeyPatch.context() as mp:
            reset_search_throttle()
            mp.setattr(socket, "getaddrinfo", forbid)
            mp.setattr(socket, "create_connection", forbid)
            mp.setattr(socket.socket, "connect", forbid)
            mp.setattr(intent, "SHARED_QUERY_BUDGET", True)
            vendor = IndependentVendor(fail_at=2)
            instance, _ = adapter(mp, vendor)
            trace = DiscoveryTrace(ENTRY["name"], "example.edu", search_queries_sent=1)
            selected = {category: [] for category in PageCategory.ALL}
            await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
            before = {"vendor_search_calls": len(vendor.calls), "trace_attempts": trace.search_queries_sent, "trace_raw": copy.deepcopy(trace.as_dict())}
            vendor.fail_at = None
            await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
            cases.append({"case": "ordinary_SearchError_second_query_then_reentry", "multi": multi, "upstream_precharge": 1, "before_reentry": before, "final_vendor_search_calls": len(vendor.calls), "final_trace_attempts": trace.search_queries_sent, "final_trace_raw": trace.as_dict(), "vendor_queries": vendor.calls})
    root = Path(__file__).resolve().parent
    payload = {"status": "unreviewed independent mock replay", "created_at_utc": datetime.now(UTC).isoformat(), "real_network_calls": 0, "real_provider_calls": 0, "source_used": "hash-pinned proposal-source; external loader conftest", "reproducer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": cases}
    target = root / "independent-query-replay.offline.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(target), "cases": [{"case": c["case"], "multi": c["multi"], "count": c.get("vendor_search_calls", c.get("final_vendor_search_calls")), "trace": c.get("trace_attempts", c.get("final_trace_attempts"))} for c in cases]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
