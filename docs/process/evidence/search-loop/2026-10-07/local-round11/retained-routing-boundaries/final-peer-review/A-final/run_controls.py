from __future__ import annotations

import asyncio
import json
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import control_support as c
from app.adapters import page_classifier as pc
from app.adapters.discovery import catalog_walker as aw
from app.adapters.search.base import SearchFailureReason, SearchUnavailable
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped

ROWS = []


def record(name, expected, okay, **values):
    ROWS.append({"case": name, "expected": expected, "status": "PASS" if okay else "RED", **values})


async def wrapper(module, flag, pages, fields, *, cat=c.CAT, kind="live", search=None,
                  scope=None, precharge=0):
    external = module is c.live or module is c.catalogue
    if external:
        c.live.RETAIN_CONFIRMED_DISCOVERY_PARTIAL = flag
    fetcher = c.MockFetcher(pages)
    entry = c.entry(cat)
    if kind == "live":
        adapter = module.LiveDiscoveryAdapter(fetcher, research_scope=scope)
        adapter.registry = lambda: [entry]
    else:
        adapter = module.CatalogueDiscoveryAdapter(fetcher, session=None,
            university_ids=["u-one"], live_limit=1, research_scope=scope)
    adapter.sitemaps.collect = c.no_sitemaps
    adapter._navigation_fallback = c.no_navigation
    adapter._add_search_results = search or c.no_search
    if precharge:
        async def identify(uni, trace):
            for _ in range(precharge):
                trace.charge_search_query_attempt()
            return entry
        adapter._identify_site = identify
    uni = SimpleNamespace(id="u-one", name=entry["name"], country=entry["country"], city="City",
        domain=cat.split('/')[2], registry_entry=None if precharge else entry)
    applies = []
    original_apply = adapter._apply

    def apply(*args, **kwargs):
        applies.append({"exception_active": sys.exc_info()[0] is not None, "gets": list(fetcher.calls)})
        return original_apply(*args, **kwargs)

    adapter._apply = apply
    with patch.object(aw, "CatalogWalker", c.walker.CatalogWalker if external else c.actual_walker.CatalogWalker), patch.object(
        module, "retrieve", lambda *args, **kwargs: [uni], create=True
    ):
        escaped = None
        try:
            candidates = await adapter.discover(c.profile(fields), limit=1)
        except BaseException as exc:
            candidates = []
            escaped = exc
    return {"candidates": [asdict(x) for x in candidates], "traces": [asdict(x) for x in adapter.traces],
        "gets": fetcher.calls, "applies": applies, "error": c.error(escaped) if escaped else None,
        "error_object": escaped}


def safe(value):
    return {k: v for k, v in value.items() if k != "error_object"}


def urls(value):
    return [p["url"] for candidate in value["candidates"] for p in candidate["programs"]]


async def normal(name, pages, fields, cat=c.CAT):
    for kind, native, proposed in [("live", c.actual_live, c.live), ("catalogue", c.actual_catalogue, c.catalogue)]:
        old = await wrapper(native, False, pages, fields, cat=cat, kind=kind)
        off = await wrapper(proposed, False, pages, fields, cat=cat, kind=kind)
        on = await wrapper(proposed, True, pages, fields, cat=cat, kind=kind)
        # Apply instrumentation is intentionally extra in ON but observable outputs/native reads stay equal.
        comparable = lambda x: {key: safe(x)[key] for key in ["candidates", "traces", "gets", "error"]}
        record(name + "." + kind + ".OFF", "Whole native output and exact read sequence unchanged", comparable(old) == comparable(off), native=safe(old), off=safe(off))
        record(name + "." + kind + ".ON", "Complete output/capped routing/native read sequence unchanged", comparable(old) == comparable(on) and not any(x["exception_active"] for x in on["applies"]), native=safe(old), on=safe(on))


async def partial(name, pages, fields, expected_urls, *, cat=c.CAT, search=None, precharge=0):
    for kind, proposed in [("live", c.live), ("catalogue", c.catalogue)]:
        if precharge and kind == "live":
            continue
        off = await wrapper(proposed, False, pages, fields, cat=cat, kind=kind, search=search, precharge=precharge)
        on = await wrapper(proposed, True, pages, fields, cat=cat, kind=kind, search=search, precharge=precharge)
        record(name + "." + kind, "Typed read_cap retains only strict previously read native-cap routing; no extra reads/_apply on unwind", on["error"] is None and urls(on) == expected_urls and on["gets"] == off["gets"] and not any(x["exception_active"] for x in on["applies"]) and all("unknown" in x["notes"].lower() for x in on["candidates"]) and all(not x["applies"] for x in [off]), off=safe(off), on=safe(on))
        return_value = on
    return return_value


async def main():
    good = c.programme()
    entries = [(c.PREFIX + "a", "BSc Computer Science", good), (c.PREFIX + "b", "BSc Computer Science", good)]
    await normal("complete_two", c.catalog(entries), ["computer science"])
    gr = {url: item for url, item in c.retained.items() if ".rug.nl/" in url}
    from app.adapters.fetching import FetchResult
    from app.domain.enums import FetchOutcome
    refused = "https://test.ucms.rug.nl/bachelors/pedagogical-sciences"
    gr[refused] = FetchResult(url=refused, outcome=FetchOutcome.ROBOTS_DISALLOWED, error="Saved refusal")
    await normal("saved_groningen_all5", gr, ["computer science"], c.GRCAT)
    au = {url: item for url, item in c.retained.items() if "aut.ac.nz/" in url}
    autcat = "https://www.aut.ac.nz/study/synthetic-catalogue"
    autentries = [(url, pc.classify_page(url=url, html=raw.decode(meta["encoding"])).title, (raw, meta)) for url, (raw, meta) in au.items()]
    await normal("saved_aut_data_then_cs", c.catalog(autentries, autcat), ["computer science"], autcat)
    for name, fields in [("multifield", ["computer science", "mathematics"]), ("aliases", ["computer science", "computing science"]), ("unknown", ["Geology"]), ("empty", [])]:
        await normal(name, c.catalog(entries + [(c.PREFIX + "math", "BSc Mathematics", c.programme("BSc Mathematics"))]), fields)
    late = c.PREFIX + "z"
    cap = UniversityReadStopped("read_cap")
    p = c.catalog(entries + [(late, "BSc Computer Science", cap)])
    await partial("read_cap_after_two", p, ["computer science"], [c.PREFIX + "a", c.PREFIX + "b"])
    for name, sentence in [("year", "Available only for academic year 2026/27."), ("domestic", "Available only for domestic applicants."), ("nondegree", "This is a non-degree visiting study course and does not award a Bachelor degree.")]:
        old_url, new_url = c.PREFIX + "a", c.PREFIX + "b"
        p = c.catalog([(old_url, "BSc Computer Science", c.programme(extra="<p>" + sentence + "</p>")), (new_url, "BSc Computer Science", c.programme(extra="<p>International applicants can apply for 2027/28.</p>")), (late, "BSc Computer Science", cap)])
        await normal("complete_late_" + name, {**p, late: good}, ["computer science"])
        await partial("partial_late_" + name, p, ["computer science"], [old_url, new_url] if name != "nondegree" else [new_url])
    p = c.catalog([(c.PREFIX + "a", "BSc Computer Science", good), (c.PREFIX + "math", "BSc Mathematics", c.programme("BSc Mathematics")), (late, "BSc Computer Science", cap)])
    await partial("partial_multifield", p, ["computer science", "mathematics"], [c.PREFIX + "a", c.PREFIX + "math"])
    await partial("partial_unknown_field", p, ["Geology"], [])
    # Saved AUT Data Science cannot be published as Computer Science. Conservative local academic proof also abstains on saved AUT CS.
    autp = c.catalog(autentries + [("https://www.aut.ac.nz/study/z", "BSc Computer Science", cap)], autcat)
    await partial("saved_aut_no_false_permission", autp, ["computer science"], [], cat=autcat)
    # Native programme cap3: strict fourth route is never admitted to the partial snapshot.
    four = [(c.PREFIX + k, "BSc Computer Science", good) for k in "abcd"] + [(late, "BSc Computer Science", cap)]
    await partial("native_cap_three", c.catalog(four), ["computer science"], [c.PREFIX + k for k in "abc"])
    # Latest counters must survive a snapshot taken before five optional native search attempts.
    async def later_queries(entry, domain, selected, trace, profile):
        for _ in range(5):
            trace.charge_search_query_attempt()
        raise cap
    counted = await partial("upstream1_plus_later5", c.catalog(entries[:1]), ["computer science"], [c.PREFIX + "a"], search=later_queries, precharge=1)
    record("latest_query_ledger", "Retained candidate and trace carry all six attempted queries", counted["candidates"][0]["search_queries_used"] == 6 and counted["traces"][0]["search_queries_sent"] == 6, result=safe(counted))
    # No publication exists when the real scope itself refuses entry.
    @contextmanager
    def refuse_scope(candidate):
        raise cap
        yield
    for kind, proposed in [("live", c.live), ("catalogue", c.catalogue)]:
        out = await wrapper(proposed, True, c.catalog(entries), ["computer science"], kind=kind, scope=refuse_scope)
        record("entry_scope_read_cap." + kind, "No source publication: bare explicitly unknown candidate and zero source I/O", out["error"] is None and not urls(out) and not out["gets"], result=safe(out))
    # Boundaries after genuine confirmation: only read_cap may become routing partial.
    for i, signal in enumerate([UniversityReadStopped("checkpoint_busy"), UniversityReadStopped("invalid_snapshot"), UniversityReadStopped("deadline"), RunCancelled("saved-control"), LeaseLost("saved-control"), asyncio.CancelledError("saved-control"), SearchUnavailable("saved-refusal", reason=SearchFailureReason.RATE_LIMITED)]):
        async def stop(*args, signal=signal, **kwargs):
            raise signal
        for kind, proposed in [("live", c.live), ("catalogue", c.catalogue)]:
            out = await wrapper(proposed, True, c.catalog(entries[:1]), ["computer science"], kind=kind, search=stop)
            record("propagation_" + str(i) + "." + kind, "Original control exception propagates after read confirmation, no returned success/partial", out["error_object"] is signal and not out["candidates"], result=safe(out))
    # Reach the genuine provider seam rather than replacing _add_search_results with a raising stub.
    signal = SearchUnavailable("synthetic vendor refusal", reason=SearchFailureReason.RATE_LIMITED)
    class Provider:
        name = "fake"
        async def search(self, *args, **kwargs):
            raise signal
    from app.adapters.search import retrieval
    async def actual_provider_search(entry, domain, selected, trace, profile):
        adapter = c.live.LiveDiscoveryAdapter(fetcher)
        adapter._search_provider = Provider()
        adapter._search_provider_resolved = True
        await adapter._add_search_results(entry, domain, selected, trace, profile)
        # Deliberately attempt next source read exactly as native recovery might, after refusal diagnostics.
        await fetcher.get(late)
    fetcher = c.MockFetcher({late: cap})
    out = await wrapper(c.live, True, c.catalog(entries[:1]), ["computer science"], search=actual_provider_search)
    record("native_provider_refusal_then_read_cap", "An actual provider refusal must not be returned as a retained partial routing success", out["error_object"] is signal and not out["candidates"], result=safe(out), note="Native retrieval converts refusal to report.failure_diagnostics; Live degrades rather than propagates. This is a material boundary gap, not proof of a real vendor call.")
    report = {"counts": {"PASS": sum(x["status"] == "PASS" for x in ROWS), "RED": sum(x["status"] == "RED" for x in ROWS), "total": len(ROWS)}, "checks": ROWS,
        "normal_dependencies": "Actual app dependency imports; three explicit external proposal class seams. Source not applied.",
        "network_provider_model_real_calls": 0, "claim_or_coverage_gain": False, "historical_async_cancelled_groningen_fixed": False}
    target = c.B / (sys.argv[1] if len(sys.argv) > 1 else "controls.attempt1.json")
    assert not target.exists(), "Raw results are append-only by fresh name"
    target.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report["counts"]))
    for row in ROWS:
        if row["status"] == "RED":
            print(row["case"])


if __name__ == "__main__":
    asyncio.run(main())
