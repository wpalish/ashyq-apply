"""PERF-1: kb-mode runtime budgets, and the two hotspots the measurement found.

The numbers behind the budgets are in ``docs/process/PERF_2026-10-22.md``. On
the measuring machine the whole 501-row catalogue with the knowledge block per
row (six pages at the route's cap of 100) reads in ~0.2 s and the committed KB
loads in ~17 ms; the budgets below (1.0 s and 0.5 s) leave room for a slow CI
runner under ``-n 4`` and still fail on a real regression, such as the KB
parsed per request or a query per row. A budget that fails on CI is reported
with its number, not loosened.

The hotspots: the route read the ``University`` table twice per request (once
for its counts, once in ``retrieve``), and ``KnowledgeBase.by_domain`` scanned
every KB entry for each of the ~500 rows. Both now answer from what is already
in memory; the old scan is kept here as the oracle.
"""

from __future__ import annotations

import statistics
import time
from datetime import date
from typing import Any

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.catalogue.importer import import_catalogue
from app.catalogue.retrieval import retrieve
from app.db import create_all_for_tests
from app.knowledge import (
    IMPORTED_FILE,
    KB_FILE,
    KnowledgeBase,
    KnowledgeEntry,
    load_knowledge_base,
)
from app.models import University

#: Generous on CI; the measured values are ~0.2 s and ~0.02 s.
CATALOGUE_WALK_BUDGET_SECONDS = 1.0
KB_LOAD_BUDGET_SECONDS = 0.5
#: The route's own cap on ``limit``.
PAGE = 100


def _scan_by_domain(kb: KnowledgeBase, host: str | None) -> KnowledgeEntry | None:
    """``by_domain`` before PERF-1, verbatim apart from the name."""
    host = (host or "").lower().removeprefix("www.")
    if not host:
        return None
    for entry in kb.entries.values():
        if any(host == d or host.endswith("." + d) for d in entry.official_domains):
            return entry
    return None


@pytest.fixture(scope="module")
def catalogue() -> list[University]:
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as session:
        import_catalogue(session)
        session.commit()
        rows = list(session.scalars(select(University)))
        session.expunge_all()
    engine.dispose()
    return rows


def _entry(seed_id: str, *domains: str) -> KnowledgeEntry:
    return KnowledgeEntry(
        seed_id=seed_id,
        university=seed_id,
        country="X",
        official_domains=domains,
        review_status="",
        verified_on=None,
        programme={},
        facts={},
        unknown=[],
        not_applicable=[],
        origin="test",
    )


def test_by_domain_finds_what_the_scan_found_for_every_catalogue_host(catalogue) -> None:
    kb = load_knowledge_base()
    hosts = {u.domain for u in catalogue} | {
        f"{prefix}{d}"
        for entry in kb.entries.values()
        for d in entry.official_domains
        for prefix in ("", "www.", "cs.", "WWW.Admissions.", "x")
    }
    hosts |= {None, "", "www.", ".", "edu", "ac.uk", "nothing.invalid"}
    assert len(hosts) > 500
    for host in hosts:
        assert kb.by_domain(host) is _scan_by_domain(kb, host), host


def test_by_domain_keeps_the_first_entry_in_order_when_two_could_answer() -> None:
    kb = KnowledgeBase(
        version="t",
        built_at=None,
        entries={
            "parent": _entry("parent", "uni.edu"),
            "child": _entry("child", "cs.uni.edu", "uni.edu"),
            "odd": _entry("odd", "", "Upper.EDU"),
        },
    )
    hosts = ["cs.uni.edu", "uni.edu", "a.cs.uni.edu", "upper.edu", "x.", "Upper.EDU", "other.edu"]
    for host in hosts:
        assert kb.by_domain(host) is _scan_by_domain(kb, host), host
    assert kb.by_domain("cs.uni.edu") is kb.entries["parent"]
    # The index follows the entries when they change.
    kb.entries["first"] = _entry("first", "new.edu")
    assert kb.by_domain("www.new.edu") is kb.entries["first"]
    kb.entries = {"only": _entry("only", "cs.uni.edu")}
    assert kb.by_domain("cs.uni.edu") is kb.entries["only"]
    assert kb.by_domain("uni.edu") is None


def test_retrieve_from_preloaded_rows_reads_as_from_the_table(catalogue) -> None:
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as session:
        import_catalogue(session)
        session.commit()
        loaded = list(session.scalars(select(University)))
        cases: list[dict[str, Any]] = [
            {},
            {"query": "university"},
            {"query": "Columbia University"},
            {"country": "europe", "preferred": ["Germany"]},
            {"excluded": ["United States"], "preferred": ["Canada", "Netherlands"]},
            {"university_ids": [u.id for u in loaded[::7]]},
        ]
        for kwargs in cases:
            expected = [u.id for u in retrieve(session, **kwargs)]
            got = retrieve(session, catalogue=list(reversed(loaded)), **kwargs)
            assert [u.id for u in got] == expected, kwargs
    engine.dispose()


@pytest.fixture
def kb_catalogue(paid_client, monkeypatch):
    """The 501-row catalogue in kb mode on the committed knowledge base."""
    import app.api.routes_universities as routes
    from app.config import get_settings

    settings = get_settings().model_copy(
        update={
            "demo_mode": False,
            "knowledge_mode": "kb",
            "knowledge_base_path": KB_FILE,
            "knowledge_imported_path": IMPORTED_FILE,
        }
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr("app.knowledge.claims.kb_today", lambda: date(2026, 10, 22))
    return paid_client


def _walk(client, extra: str = "") -> tuple[float, int]:
    started = time.perf_counter()
    seen = 0
    offset = 0
    while True:
        body = client.get(f"/api/universities?limit={PAGE}&offset={offset}{extra}").json()
        assert all(item["knowledge"] is not None for item in body["items"])
        seen += len(body["items"])
        offset += PAGE
        if offset >= body["total"]:
            break
    return time.perf_counter() - started, seen


def test_the_whole_kb_catalogue_reads_within_its_budget(kb_catalogue) -> None:
    client = kb_catalogue
    first = client.get("/api/universities?limit=1").json()
    assert first["catalogue_total"] == 501 and first["kb_total"] >= 90
    _walk(client)  # warm: the KB read once per process, imports
    times = {}
    for label, extra in (("all", ""), ("verified", "&verified=true")):
        runs = [_walk(client, extra) for _ in range(5)]
        seen = {n for _, n in runs}
        assert seen == ({first["catalogue_total"]} if label == "all" else {first["kb_total"]})
        times[label] = statistics.median(t for t, _ in runs)
    for label, median in times.items():
        assert median < CATALOGUE_WALK_BUDGET_SECONDS, (
            f"the kb catalogue ({label}) took a median {median:.2f} s per walk "
            f"(budget {CATALOGUE_WALK_BUDGET_SECONDS} s)"
        )


def test_a_catalogue_page_costs_a_fixed_number_of_queries(kb_catalogue) -> None:
    """No query per row: a page of 100 issues as many statements as a page of 1."""
    import app.db as db_module

    statements: list[str] = []

    def count(_conn, _cursor, statement, *_args) -> None:
        statements.append(statement)

    event.listen(db_module.engine, "before_cursor_execute", count)
    try:
        counts = []
        for limit in (1, PAGE):
            statements.clear()
            kb_catalogue.get(f"/api/universities?limit={limit}")
            counts.append(sum(s.lstrip().upper().startswith("SELECT") for s in statements))
    finally:
        event.remove(db_module.engine, "before_cursor_execute", count)
    assert counts[0] == counts[1], counts
    # One read of the catalogue table; the rest is the principal's lookup.
    universities = [s for s in statements if "FROM universities" in s]
    assert len(universities) == 1, universities


def test_the_knowledge_base_loads_within_its_budget() -> None:
    times = []
    for _ in range(3):
        started = time.perf_counter()
        kb = load_knowledge_base()
        times.append(time.perf_counter() - started)
    assert sum(e.has_verified_data for e in kb.entries.values()) >= 90
    median = statistics.median(times)
    assert median < KB_LOAD_BUDGET_SECONDS, (
        f"load_knowledge_base took a median {median:.3f} s (budget {KB_LOAD_BUDGET_SECONDS} s)"
    )
