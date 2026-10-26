"""Build the recorded-search store from paired-run captures of the development sets.

``python -m evaluation.research.recorded_search --source SET RUN_ID CREATED_AT HEAD_SHA DIR
[--source ...] --out evaluation/research/data/recorded_search.<name>.json``

``make_v2_store`` (W4), after a single-column record run (``expert_paired``,
``columns=1``): ``python -m evaluation.research.recorded_search --record-run RUN_ID
CREATED_AT HEAD_SHA DIR --cases ID [ID ...] --out recorded_search.<tag>.json`` reads
the one artifact for every development set the case list touches, and writes
nothing unless the result is ``recorded-search/2``.

Owner decision 2026-10-19: no scraping, paid search frozen; the work after
search continues offline by replaying the lists Serper already returned.
Every capture's discovery trace keeps, per query family, the URLs the provider
returned (WF-17 ``search_results``) — but not the query text. The text is
deterministic from public words (``queries_for(DiscoveryIntent)``), so it is
rebuilt here from what the trace records (institution, domain) and the
institution's country, and the exact request discovery sends — text, domain
filter, ``hl``/``gl`` — is read off ``discover_candidates`` itself through a
provider that only records what it is asked. A family the rebuilt plan does not
contain stops the build: a store whose keys were guessed would replay nothing.

Only the development sets are read: cohort, dev2, dev3, dev4. A case outside
them is never opened — directories are globbed per allowed case id, so a
heldout or design-blind case's files are not even listed. A repetition whose
trace records a failed search (``search_failures``) is left out. Where the
repetitions of one request disagree, the most frequent list is kept (ties:
the earliest repetition), and the entry says how many agreed.

Titles and snippets (store v2, 2026-10-19): a capture made since
``live.SearchLog`` landed keeps ``<case>.search.json`` beside the trace, with
every request's full text and parameters and each result's URL, title,
snippet and rank. Where a repetition has one, its entries carry ``results``
(the title and snippet beside each URL), and a request the log holds but the
trace does not (past the trace's cap, or a topic, scholarship or identity
search) becomes an entry of its own, keyed by the logged request itself. A
build that reads no log writes the URL-only ``recorded-search/1`` document
it always did.

Record wide (SR-WIDE, 2026-10-26): a capture run with ``--record-wide`` logs
the provider's whole paid page per request (Exa 25, Tavily 20) beside a
``page`` record (asked, returned, consumed, parameters, cost). Its entries
then hold every returned URL (not the trace's ten), each result with its
``rank``, and the ``page`` record; replay hands a caller the top
``max_results`` of them, which is what the live adapter handed it.

Evaluation tooling only: nothing under ``app/`` may import it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .live import COHORT, DEV2, DEV3_IDS, DEV4_DOMAINS, DEV5_DOMAINS, HELDOUT

#: The development sets a store may be built from (LOOP_PROTOCOL case lists).
DEV_SETS: dict[str, tuple[str, ...]] = {
    "cohort": tuple(COHORT),
    "dev2": tuple(c for c in DEV2 if c not in DEV3_IDS),
    "dev3": tuple(c for c in DEV2 if c in DEV3_IDS),
    "dev4": tuple(DEV4_DOMAINS),
}
#: Never read: the heldout nine and the design-blind dev5.
FORBIDDEN_CASES = frozenset({*HELDOUT, *DEV5_DOMAINS})

#: The request discovery's single-field search asks about (canary profile).
FIELD = "computer science"


#: Each logged result's title and snippet, in the order of its URLs.
Texts = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Request:
    """What reached the provider for one query family ("" for a request outside the plan)."""

    family: str
    query: str
    domains: tuple[str, ...]
    hl: str | None
    gl: str | None


class _Recorder:
    """A provider that answers nothing and remembers what it was asked."""

    name = "recorder"

    def __init__(self) -> None:
        self.asked: list[tuple[str, tuple[str, ...], str | None, str | None]] = []

    async def search(self, *, query: str, domains: Sequence[str] = (), max_results: int = 10):
        return self._empty(query, domains, None, None)

    async def search_localized(
        self,
        *,
        query: str,
        hl: str,
        gl: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ):
        return self._empty(query, domains, hl, gl)

    def _empty(self, query: str, domains: Sequence[str], hl: str | None, gl: str | None):
        from app.adapters.search.base import SearchResponse

        self.asked.append((query, tuple(domains), hl, gl))
        return SearchResponse(query=query, provider=self.name, retrieved_at=datetime.now(UTC))


def discovery_requests(institution: str, domain: str, country: str) -> dict[str, Request]:
    """Family -> the request discovery sends for it, rebuilt from public words.

    Mirrors ``LiveDiscoveryAdapter._send_search``: the intent names the
    institution, its registrable domain, the bachelor's level, the canary's
    field and (R5) the institution's own country; the request is whatever
    ``discover_candidates`` hands a provider that has ``search_localized``, as
    Serper does.
    """
    from app.adapters.discovery.live_discovery import registrable_domain
    from app.adapters.search import intent as intent_module
    from app.adapters.search.intent import DiscoveryIntent, queries_for
    from app.adapters.search.retrieval import discover_candidates
    from app.domain.enums import DegreeLevel

    intent = DiscoveryIntent(
        institution=institution,
        domain=registrable_domain(domain) or domain,
        degree=DegreeLevel.BACHELOR,
        field=FIELD,
        institution_country=country if intent_module.LOCAL_LANGUAGE_QUERIES else "",
    )
    requests: dict[str, Request] = {}
    for planned in queries_for(intent, budget=99):
        recorder = _Recorder()
        asyncio.run(
            discover_candidates(
                recorder,  # type: ignore[arg-type]
                intent,
                only_families=(planned.family,),
                hop_entry_points=0,
            )
        )
        (query, domains, hl, gl) = recorder.asked[0]
        requests[planned.family] = Request(planned.family, query, domains, hl, gl)
    return requests


def _trace_and_country(rep_dir: Path, case_id: str) -> tuple[dict[str, Any], str] | None:
    """The discovery trace of one repetition and the institution's country."""
    raw = rep_dir / f"{case_id}.raw.json"
    if raw.is_file():
        report = json.loads(raw.read_text(encoding="utf-8"))
        rows = report.get("canary", {}).get("institutions") or []
        if rows and rows[0].get("discovery_trace"):
            return rows[0]["discovery_trace"], str(rows[0].get("country") or "")
    partial = rep_dir / f"{case_id}.trace.json"
    if partial.is_file():
        snapshot = json.loads(partial.read_text(encoding="utf-8"))
        if snapshot.get("discovery_trace"):
            return snapshot["discovery_trace"], ""
    return None


def _search_log(rep_dir: Path, case_id: str) -> list[dict[str, Any]] | None:
    """The repetition's logged requests (``live.SearchLog``), or None when it kept none."""
    path = rep_dir / f"{case_id}.search.json"
    if not path.is_file():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    from .live import SEARCH_LOG_SCHEMA

    if document.get("schema") != SEARCH_LOG_SCHEMA:
        raise ValueError(f"{path}: not a {SEARCH_LOG_SCHEMA!r} document")
    return [row for row in document.get("requests") or [] if isinstance(row, dict)]


def _logged_key(row: dict[str, Any]) -> str:
    from app.adapters.search.recorded import request_key

    return request_key(
        str(row.get("query") or ""), row.get("domains") or [], row.get("hl"), row.get("gl")
    )


def _logged_urls(answer: dict[str, Any]) -> tuple[str, ...]:
    """Every public http(s) result URL of one logged request, in the provider's order."""
    urls = (str(r.get("url") or "") for r in answer.get("results") or [] if isinstance(r, dict))
    return tuple(
        u for u in urls if urlsplit(u).scheme in {"http", "https"} and urlsplit(u).hostname
    )


#: What a wide (SR-WIDE) log row's ``page`` may carry into the store entry.
PAGE_FIELDS = ("requested", "returned", "consumed", "parameters", "cost", "cost_unit")


def _wide_page(answer: dict[str, Any] | None) -> dict[str, Any] | None:
    """SR-WIDE: the logged request's page record (asked, returned, consumed, cost), if wide."""
    page = (answer or {}).get("page")
    if not isinstance(page, dict):
        return None
    return {name: page[name] for name in PAGE_FIELDS if name in page}


def _texts_for(urls: Sequence[str], results: Sequence[dict[str, Any]]) -> Texts:
    """``(title, snippet)`` per URL, matched on the URL; "" where the log has none."""
    by_url: dict[str, tuple[str, str]] = {}
    for result in results:
        url = str(result.get("url") or "")
        if url and url not in by_url:
            by_url[url] = (str(result.get("title") or ""), str(result.get("snippet") or ""))
    return tuple(by_url.get(url, ("", "")) for url in urls)


def _case_country(case_id: str) -> str:
    """The institution's country as the capture's entry gives it (a partial trace has none)."""
    from . import live

    entry = live.cohort_entry(case_id) if case_id in COHORT else live.dev2_entry(case_id)
    return entry["country"]


def collect(
    set_name: str, run_id: str, created_at: str, head_sha: str, directory: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Every recorded discovery request of one set's paired run, with its provenance."""
    from app.adapters.search.recorded import request_key

    if set_name not in DEV_SETS:
        raise ValueError(f"{set_name!r} is not a development set ({sorted(DEV_SETS)})")
    observed: list[dict[str, Any]] = []
    read: list[str] = []
    excluded: list[dict[str, str]] = []
    logged: list[str] = []
    for case_id in DEV_SETS[set_name]:
        if case_id in FORBIDDEN_CASES:  # pragma: no cover - the tables are disjoint
            raise ValueError(f"{case_id} is not a development case")
        plans: dict[tuple[str, str, str], dict[str, Request]] = {}
        rep_dirs = [
            p for arm in ("off", "on") for p in directory.glob(f"{case_id}-{arm}/*") if p.is_dir()
        ]
        for rep_dir in sorted(rep_dirs, key=lambda p: p.name):
            label = f"{rep_dir.parent.name}/{rep_dir.name}"
            found = _trace_and_country(rep_dir, case_id)
            if found is None:
                excluded.append({"repetition": label, "reason": "no discovery trace"})
                continue
            trace, country = found
            if trace.get("search_failures"):
                excluded.append({"repetition": label, "reason": "search_failures recorded"})
                continue
            read.append(label)
            identity = (
                str(trace.get("institution") or ""),
                str(trace.get("domain") or ""),
                country or _case_country(case_id),
            )
            if identity not in plans:
                plans[identity] = discovery_requests(*identity)
            plan = plans[identity]
            log = _search_log(rep_dir, case_id)
            #: The log's answer per request key (the first time it was asked).
            answers: dict[str, dict[str, Any]] = {}
            for logged_row in log or []:
                answers.setdefault(_logged_key(logged_row), logged_row)
            if log is not None:
                logged.append(label)
            traced: set[str] = set()
            for row in trace.get("search_results") or []:
                family = str(row.get("family") or "")
                if family not in plan:
                    raise ValueError(
                        f"{label}: family {family!r} is not in the rebuilt query plan; "
                        "the store would not replay it"
                    )
                request = plan[family]
                key = request_key(request.query, request.domains, request.hl, request.gl)
                traced.add(key)
                urls = tuple(str(u) for u in row.get("urls") or [])
                answer = answers.get(key)
                page = _wide_page(answer)
                if page is not None and answer is not None:
                    # SR-WIDE: the trace keeps the ten discovery ranked; the
                    # log keeps the whole page the request paid for.
                    urls = _logged_urls(answer)
                observed.append(
                    {
                        "set": set_name,
                        "case": case_id,
                        "request": request,
                        "intent": identity,
                        "urls": urls,
                        "texts": None
                        if answer is None
                        else _texts_for(urls, answer.get("results") or []),
                        "kind": None if answer is None else answer.get("kind"),
                        "provider": None if answer is None else answer.get("provider"),
                        "page": page,
                        "repetition": label,
                    }
                )
            # Requests the log holds and the trace does not: keyed by what was
            # sent, under the plan's family when discovery's plan has the key.
            planned = {request_key(r.query, r.domains, r.hl, r.gl): r for r in plan.values()}
            for key, answer in answers.items():
                if key in traced or not str(answer.get("query") or "").strip():
                    continue
                results = [r for r in answer.get("results") or [] if isinstance(r, dict)]
                urls = _logged_urls(answer)
                observed.append(
                    {
                        "set": set_name,
                        "case": case_id,
                        "request": planned.get(key)
                        or Request(
                            "",
                            str(answer["query"]),
                            tuple(str(d) for d in answer.get("domains") or []),
                            answer.get("hl"),
                            answer.get("gl"),
                        ),
                        "intent": identity,
                        "urls": urls,
                        "texts": _texts_for(urls, results),
                        "kind": answer.get("kind"),
                        "provider": answer.get("provider"),
                        "page": _wide_page(answer),
                        "repetition": label,
                    }
                )
    provenance = {
        "set": set_name,
        "run_id": run_id,
        "run_created_at": created_at,
        "head_sha": head_sha,
        "workflow": "benchmark-capture.yml mode expert_paired",
        "artifact": f"expert-recovery-{run_id}",
        "repetitions_read": len(read),
        "repetitions_excluded": excluded,
    }
    if logged:
        provenance["repetitions_with_search_log"] = len(logged)
    return observed, provenance


def build_store(sources: list[tuple[str, str, str, str, Path]]) -> dict[str, Any]:
    """The store document: one entry per distinct request, the modal list kept."""
    from app.adapters.search.recorded import request_key

    groups: dict[tuple[str, str, Request], list[dict[str, Any]]] = {}
    provenance: list[dict[str, Any]] = []
    for set_name, run_id, created_at, head_sha, directory in sources:
        observed, source = collect(set_name, run_id, created_at, head_sha, directory)
        provenance.append(source)
        for row in observed:
            groups.setdefault((row["set"], row["case"], row["request"]), []).append(row)
    entries: list[dict[str, Any]] = []
    for (set_name, case_id, request), rows in groups.items():
        rows.sort(key=lambda r: r["repetition"].split("/", 1)[1])
        tally = Counter(r["urls"] for r in rows)
        best = max(tally.values())
        modal = [r for r in rows if tally[r["urls"]] == best]
        # The earliest modal repetition, preferring one whose log kept the titles.
        chosen = next((r for r in modal if r["texts"] is not None), modal[0])
        institution, host, country = chosen["intent"]
        entry: dict[str, Any] = {
            "set": set_name,
            "case": case_id,
            # What the request was rebuilt from (the trace's institution and
            # host, the institution's country), so the keys can be re-checked.
            "institution": institution,
            "host": host,
            "country": country,
            "family": request.family,
            "query": request.query,
            "domains": list(request.domains),
            "hl": request.hl,
            "gl": request.gl,
            "urls": list(chosen["urls"]),
            "agreement": f"{best}/{len(rows)}",
            "source_repetition": chosen["repetition"],
        }
        if chosen["texts"] is not None:
            entry["results"] = [
                {"url": url, "title": title, "snippet": snippet}
                for url, (title, snippet) in zip(chosen["urls"], chosen["texts"], strict=True)
            ]
            for name in ("kind", "provider"):
                if chosen[name]:
                    entry[name] = chosen[name]
            if chosen.get("page") is not None:
                # SR-WIDE: the whole paid page, ranked; ``page.consumed`` says
                # how many of them the live caller ranked (the head).
                for rank, result in enumerate(entry["results"], start=1):
                    result["rank"] = rank
                entry["page"] = chosen["page"]
        entries.append(entry)
    order = {s: i for i, s in enumerate(DEV_SETS)}
    entries.sort(
        key=lambda e: (
            order[e["set"]],
            DEV_SETS[e["set"]].index(e["case"]),
            e["family"],
            e["query"],
        )
    )
    if any("results" in e for e in entries):
        # A logged request outside discovery's plan (a topic search, say) may
        # repeat across cases; the store keys by request, so the first stays.
        seen: set[str] = set()
        unique = []
        for entry in entries:
            key = request_key(entry["query"], entry["domains"], entry["hl"], entry["gl"])
            if key not in seen:
                seen.add(key)
                unique.append(entry)
        entries = unique
        providers = sorted({e["provider"] for e in entries if e.get("provider")})
        wide = [e for e in entries if "page" in e]
        record_wide: dict[str, Any] = (
            {
                "record_wide": {
                    "entries": len(wide),
                    "results": sum(len(e["urls"]) for e in wide),
                    "rule": "every result the provider returned per request, best first; "
                    "replay hands a caller the top max_results, as the live adapter did",
                }
            }
            if wide
            else {}
        )
        return {
            "schema": "recorded-search/2",
            "provenance": {
                "description": (
                    "Result lists recorded by WF-17 (search_results) in paired-run captures of "
                    "the development sets, with each result's title and snippet where the "
                    "capture's search log (<case>.search.json) kept them, and every logged "
                    "request the trace did not record; replayed by RecordedSearchProvider. "
                    "Snippets are ranking hints, never evidence."
                ),
                "provider_recorded": ", ".join(providers) or "serper",
                "key": "normalised query text, domain filter, hl, gl (max_results truncates)",
                "query_rules": "today's defaults (LOCAL_LANGUAGE_QUERIES on, ALIAS_QUERIES off)",
                "sources": provenance,
                **record_wide,
            },
            "entries": entries,
        }
    return {
        "schema": "recorded-search/1",
        "provenance": {
            "description": (
                "Serper result lists recorded by WF-17 (search_results) in paired-run captures "
                "of the development sets, replayed by RecordedSearchProvider. Discovery queries "
                "only: the scholarship, topic and identity searches were never recorded and "
                "always miss. URLs only (no title, no snippet)."
            ),
            "provider_recorded": "serper",
            "key": "normalised query text, domain filter, hl, gl (max_results truncates)",
            "query_rules": "today's defaults (LOCAL_LANGUAGE_QUERIES on, ALIAS_QUERIES off)",
            "sources": provenance,
        },
        "entries": entries,
    }


def coverage(document: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Set -> cases and requests the store answers."""
    out: dict[str, dict[str, int]] = {}
    for entry in document["entries"]:
        row = out.setdefault(entry["set"], {"cases": 0, "requests": 0})
        row["requests"] += 1
    for set_name, row in out.items():
        row["cases"] = len({e["case"] for e in document["entries"] if e["set"] == set_name})
    return out


def record_run_sources(
    run_id: str, created_at: str, head_sha: str, directory: Path, cases: Sequence[str]
) -> list[tuple[str, str, str, str, Path]]:
    """W4 ``make_v2_store``: one source per development set a record run's case list touches.

    A single-column record run captures every listed case once into one
    artifact, so every set it covers reads the same directory. A case outside
    the development sets is refused before anything is read.
    """
    known = {case for members in DEV_SETS.values() for case in members}
    outside = [case for case in cases if case not in known]
    if outside:
        raise ValueError(f"not development cases: {' '.join(outside)}")
    return [
        (set_name, run_id, created_at, head_sha, directory)
        for set_name, members in DEV_SETS.items()
        if any(case in members for case in cases)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--source",
        nargs=5,
        action="append",
        default=[],
        metavar=("SET", "RUN_ID", "CREATED_AT", "HEAD_SHA", "DIR"),
        help="one unpacked expert_paired artifact of a development set",
    )
    parser.add_argument(
        "--record-run",
        nargs=4,
        default=None,
        metavar=("RUN_ID", "CREATED_AT", "HEAD_SHA", "DIR"),
        help="make_v2_store (W4): one single-column record run's artifact, read for every "
        "development set --cases touches; the store must come out recorded-search/2",
    )
    parser.add_argument(
        "--cases", nargs="+", default=None, help="with --record-run: the run's case ids"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if bool(args.source) == bool(args.record_run):
        parser.error("pass --source (one per set) or --record-run, not both and not neither")
    if (args.cases is None) != (args.record_run is None):
        parser.error("--cases goes with --record-run")
    if args.record_run:
        run_id, created_at, head_sha, directory = args.record_run
        try:
            sources = record_run_sources(run_id, created_at, head_sha, Path(directory), args.cases)
        except ValueError as exc:
            parser.error(str(exc))
    else:
        sources = [(s, r, c, h, Path(d)) for s, r, c, h, d in args.source]
    for set_name, *_rest in sources:
        if set_name not in DEV_SETS:
            parser.error(f"{set_name!r} is not a development set ({', '.join(DEV_SETS)})")
    document = build_store(sources)
    if args.record_run and document["schema"] != "recorded-search/2":
        print(
            f"make_v2_store: no capture kept a search log, so the store would be "
            f"{document['schema']}; nothing written",
            file=sys.stderr,
        )
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for set_name, row in coverage(document).items():
        print(f"{set_name}: {row['cases']} cases, {row['requests']} requests", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
