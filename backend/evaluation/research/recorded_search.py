"""Build the recorded-search store from paired-run captures of the development sets.

``python -m evaluation.research.recorded_search --source SET RUN_ID CREATED_AT HEAD_SHA DIR
[--source ...] --out evaluation/research/data/recorded_search.<name>.json``

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


@dataclass(frozen=True)
class Request:
    """What reached the provider for one query family."""

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


def _case_country(case_id: str) -> str:
    """The institution's country as the capture's entry gives it (a partial trace has none)."""
    from . import live

    entry = live.cohort_entry(case_id) if case_id in COHORT else live.dev2_entry(case_id)
    return entry["country"]


def collect(
    set_name: str, run_id: str, created_at: str, head_sha: str, directory: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Every recorded discovery request of one set's paired run, with its provenance."""
    if set_name not in DEV_SETS:
        raise ValueError(f"{set_name!r} is not a development set ({sorted(DEV_SETS)})")
    observed: list[dict[str, Any]] = []
    read: list[str] = []
    excluded: list[dict[str, str]] = []
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
            for row in trace.get("search_results") or []:
                family = str(row.get("family") or "")
                if family not in plan:
                    raise ValueError(
                        f"{label}: family {family!r} is not in the rebuilt query plan; "
                        "the store would not replay it"
                    )
                observed.append(
                    {
                        "set": set_name,
                        "case": case_id,
                        "request": plan[family],
                        "intent": identity,
                        "urls": tuple(str(u) for u in row.get("urls") or []),
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
    return observed, provenance


def build_store(sources: list[tuple[str, str, str, str, Path]]) -> dict[str, Any]:
    """The store document: one entry per distinct request, the modal list kept."""
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
        chosen = next(r for r in rows if tally[r["urls"]] == best)
        institution, host, country = chosen["intent"]
        entries.append(
            {
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
        )
    order = {s: i for i, s in enumerate(DEV_SETS)}
    entries.sort(key=lambda e: (order[e["set"]], DEV_SETS[e["set"]].index(e["case"]), e["family"]))
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--source",
        nargs=5,
        action="append",
        required=True,
        metavar=("SET", "RUN_ID", "CREATED_AT", "HEAD_SHA", "DIR"),
        help="one unpacked expert_paired artifact of a development set",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    sources = [(s, r, c, h, Path(d)) for s, r, c, h, d in args.source]
    for set_name, *_rest in sources:
        if set_name not in DEV_SETS:
            parser.error(f"{set_name!r} is not a development set ({', '.join(DEV_SETS)})")
    document = build_store(sources)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for set_name, row in coverage(document).items():
        print(f"{set_name}: {row['cases']} cases, {row['requests']} requests", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
