"""IG-2: production's identity gate (R6) on every development homepage, from outside the pipeline.

IG bundle, ``docs/process/NEXT_CYCLES_2026-10-20.md`` §6. For every case of the
four development sets and dev5 the probe builds the entry the benchmark builds
(``live.seed_entry`` for the cohort, dev2 and dev3 - the seed row alone, the
cohort's registry entry dropped as the gate arm drops it; ``live.dev2_entry``
for the dev4/dev5 country proxies), binds the catalogue row the importer gives
it (an off-seed proxy gets a bare row, as ``live.with_off_seed_rows`` adds),
reads the homepage through the production ``Fetcher`` (our user agent,
robots.txt, its limits; nothing retried around a refusal) and runs
``CatalogueDiscoveryAdapter._identity_branch`` on it. The identity fallback
search is never sent: no search provider is configured or called.

Per case it records the branch that fired (``official_site``, ``native_name``,
``title_name``, ``english_alternate``) or the refusal (``fetch:<outcome>``,
``redirect_off_site``, ``third_party_host``, ``names_other_institution``,
``parked``, ``no_branch``). The cohort and dev2-dev4 are written per case;
dev5 is design-blind (13-Q1): it is written as counts only, and the rendered
text is checked for its case ids, names, domains and hosts before anything is
emitted (as ``stage_summary.leak_check``). Held-out cases are refused.

``--fold-letters`` turns ``discovery.IDENTITY_FOLD_MARKS`` on (NN-1b).
``--native-names FILE`` reads a native-name proposals file (NN-1a) and puts
each usable row's names on the probe's own copy of the record - measurement
only: rows a reviewer rejected are skipped, and an unreviewed row counts only
at high or medium match confidence. Production reads only the signed overlay.

Run from ``backend``::

    python -m evaluation.research.identity_gate_probe --out <report.json> --markdown <tables.md>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import tempfile
from collections import Counter
from collections.abc import Iterable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.fetching import Fetcher, same_source_site
from app.catalogue import discovery
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.catalogue.importer import (
    identity_key,
    import_catalogue,
    public_domain,
    seed_domain,
    stable_id,
)
from app.db import create_all_for_tests
from app.domain.site_identity import canonical_host
from app.models import University
from evaluation.research import live

#: The case sets, in LOOP_PROTOCOL order.
SETS: dict[str, tuple[str, ...]] = {
    "cohort": tuple(live.COHORT),
    "dev2": tuple(case for case in live.DEV2 if case not in live.DEV3_IDS),
    "dev3": tuple(case for case in live.DEV2 if case in live.DEV3_IDS),
    "dev4": tuple(live.DEV4_DOMAINS),
    "dev5": tuple(live.DEV5_DOMAINS),
}
#: Design-blind sets: counts only, never a row (13-Q1).
BLIND_SETS = frozenset({"dev5"})
#: Never probed, whatever the set tables say.
HELDOUT_CASES = frozenset(live.HELDOUT)
#: A proposal without a reviewer's decision counts at these confidences only.
USABLE_CONFIDENCE = frozenset({"high", "medium"})

PASS_RESULTS = ("official_site", "native_name", "title_name", "english_alternate")


@dataclass(frozen=True)
class Case:
    set_name: str
    case_id: str
    entry: dict[str, str]


def cases_for(sets: Iterable[str]) -> list[Case]:
    out: list[Case] = []
    for set_name in sets:
        for case_id in SETS[set_name]:
            if case_id in HELDOUT_CASES:
                raise ValueError("a held-out case is never probed")
            entry = (
                live.seed_entry(case_id)
                if case_id in live.GATED_CASES
                else live.dev2_entry(case_id)
            )
            out.append(Case(set_name, case_id, entry))
    return out


def catalogue_session() -> Session:
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    session = Session(engine)
    import_catalogue(session)
    session.flush()
    return session


def bind_university(session: Session, entry: dict[str, str]) -> University:
    """The row the gate would see: the importer's, registry entry dropped, or a bare off-seed one."""
    key = identity_key(entry["name"], entry["country"])
    uni = session.get(University, stable_id(key))
    if uni is None:
        return University(
            id=stable_id(key),
            identity_key=key,
            name=entry["name"],
            country=entry["country"],
            city=entry.get("city") or "",
            aliases=[entry["name"]],
        )
    if uni.registry_entry is not None:
        # As canary._install_identified_sites(drop_registry_entry=True).
        record = (uni.seed_snapshot or {}).get("record") or {}
        uni.registry_entry = None
        uni.domain = seed_domain(record) if record else None
        uni.domain_status = "seed" if uni.domain else "unknown"
    return uni


def usable_native_names(document: dict[str, Any]) -> dict[str, list[str]]:
    """Seed id and identity key -> the names a measurement may use (see the module doc)."""
    usable: dict[str, list[str]] = {}
    for row in document.get("proposals") or []:
        decision = (row.get("review") or {}).get("decision")
        names = [n for n in row.get("proposed_native_names") or [] if isinstance(n, str) and n]
        if not names or decision == "reject":
            continue
        if decision != "accept" and row.get("match_confidence") not in USABLE_CONFIDENCE:
            continue
        for key in (row.get("seed_id"), row.get("identity_key")):
            if isinstance(key, str) and key:
                usable[key] = names
    return usable


def with_native_names(uni: University, native: dict[str, list[str]]) -> bool:
    """Put the usable names on this probe's copy of the record; True when it had any."""
    snapshot = deepcopy(uni.seed_snapshot or {})
    record = snapshot.setdefault("record", {})
    names = native.get(str(record.get("seed_id") or "")) or native.get(uni.identity_key)
    if not names:
        return False
    record["native_name"] = list(names)
    uni.seed_snapshot = snapshot
    return True


def refusal(uni: University, soup: BeautifulSoup) -> str:
    """Why ``_identity_branch`` found nothing, in the gate's own terms."""
    names = [discovery._fold(name) for name in discovery._english_names(uni)]
    _, identity_text = discovery._identity_parts(soup)
    identity_text = discovery._fold(identity_text)
    if discovery._names_other_institution(names, identity_text):
        return "names_other_institution"
    if discovery._refused_page(names, soup, identity_text):
        return "parked"
    return "no_branch"


async def probe_case(fetcher: Any, uni: University, homepage: str) -> dict[str, Any]:
    """The gate's verdict on one homepage, as ``_probe_site`` reaches it, without the query."""
    host = urlsplit(homepage).hostname or ""
    try:
        public_domain(host)
    except ValueError:
        return {"result": "invalid_host", "final_host": ""}
    if discovery._third_party_host(host):
        return {"result": "third_party_host", "final_host": ""}
    url = f"https://{host}/"
    page = await fetcher.get(url)
    final = page.final_url or url
    if not page.ok:
        return {"result": f"fetch:{page.outcome.value}", "final_host": ""}
    final_host = canonical_host(final)
    if not same_source_site(url, final):
        return {"result": "redirect_off_site", "final_host": final_host}
    soup = BeautifulSoup(page.content or page.text, "html.parser")
    gate = CatalogueDiscoveryAdapter(
        fetcher, session=cast(Session, None), university_ids=None, live_limit=0
    )
    evidence: dict[str, Any] = {}
    branch = await gate._identity_branch(uni, host, soup, final, evidence)
    return {"result": branch or refusal(uni, soup), "final_host": final_host}


async def measure(
    fetcher: Any,
    cases: Sequence[Case],
    native: dict[str, list[str]] | None = None,
    concurrency: int = 4,
) -> list[dict[str, Any]]:
    """One record per case, in case order."""
    session = catalogue_session()
    try:
        bound = [(case, bind_university(session, case.entry)) for case in cases]
        flags = [with_native_names(uni, native) if native else False for _, uni in bound]
        gate = asyncio.Semaphore(concurrency)

        async def one(case: Case, uni: University, has_native: bool) -> dict[str, Any]:
            async with gate:
                verdict = await probe_case(fetcher, uni, case.entry["homepage"])
            return {
                "set": case.set_name,
                "case": case.case_id,
                "homepage": case.entry["homepage"],
                "native_name_given": has_native,
                "passed": verdict["result"] in PASS_RESULTS,
                **verdict,
            }

        return list(
            await asyncio.gather(
                *(one(case, uni, has) for (case, uni), has in zip(bound, flags, strict=True))
            )
        )
    finally:
        session.close()


def summarize(records: Sequence[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    """Per set: counts always; the per-case rows only outside the blind sets."""
    sets: dict[str, Any] = {}
    for set_name in dict.fromkeys(r["set"] for r in records):
        mine = [r for r in records if r["set"] == set_name]
        block: dict[str, Any] = {
            "cases": len(mine),
            "passed": sum(1 for r in mine if r["passed"]),
            "native_name_given": sum(1 for r in mine if r["native_name_given"]),
            "by_result": dict(sorted(Counter(r["result"] for r in mine).items())),
        }
        if set_name not in BLIND_SETS:
            block["rows"] = [
                {k: r[k] for k in ("case", "result", "final_host", "native_name_given")}
                for r in mine
            ]
        sets[set_name] = block
    return {"schema": "identity_gate_probe/1", "config": config, "sets": sets}


def render(summary: dict[str, Any]) -> str:
    config = summary["config"]
    lines = [
        "# Identity gate probe (R6, no fallback query)",
        "",
        f"fold letters: {'on' if config['fold_letters'] else 'off'}; "
        f"native names: {config['native_names'] or 'none'}",
        "",
        "| set | passed / cases | native name given | results |",
        "|---|---|---|---|",
    ]
    for set_name, block in summary["sets"].items():
        results = ", ".join(f"{k} {v}" for k, v in block["by_result"].items())
        lines.append(
            f"| {set_name} | {block['passed']}/{block['cases']} | "
            f"{block['native_name_given']} | {results} |"
        )
    for set_name, block in summary["sets"].items():
        if "rows" not in block:
            continue
        lines += ["", f"## {set_name}", "", "| case | result | final host | native name |"]
        lines.append("|---|---|---|---|")
        lines += [
            f"| {r['case']} | {r['result']} | {r['final_host']} | "
            f"{'yes' if r['native_name_given'] else 'no'} |"
            for r in block["rows"]
        ]
    return "\n".join(lines) + "\n"


def blind_tokens(cases: Iterable[Case]) -> list[str]:
    """What must never appear in the output for a blind set's cases."""
    tokens: list[str] = []
    for case in cases:
        if case.set_name not in BLIND_SETS:
            continue
        host = urlsplit(case.entry["homepage"]).hostname or ""
        domain = live.CASE_DOMAINS.get(case.case_id, "")
        tokens += [case.case_id, case.entry["name"], host.removeprefix("www."), domain]
    return [t for t in tokens if t]


def leak_check(text: str, cases: Iterable[Case]) -> list[str]:
    """The kinds of blind-set material ``text`` holds; empty when clean (tokens never returned)."""
    folded = text.casefold()
    found: set[str] = set()
    for token in blind_tokens(cases):
        pattern = rf"(?<![a-z0-9]){re.escape(token.casefold())}(?![a-z0-9])"
        if re.search(pattern, folded):
            found.add("blind_case")
    return sorted(found)


class LeakError(RuntimeError):
    """The output names a blind-set case; nothing was written."""


async def run(args: argparse.Namespace) -> tuple[dict[str, Any], list[Case]]:
    cases = cases_for(args.sets)
    native = None
    if args.native_names:
        document = json.loads(Path(args.native_names).read_text(encoding="utf-8"))
        native = usable_native_names(document)
    discovery.IDENTITY_FOLD_MARKS = bool(args.fold_letters)
    with tempfile.TemporaryDirectory() as cache:
        fetcher = Fetcher(Path(cache), timeout=args.timeout, trust_env_proxy=args.trust_env_proxy)
        async with fetcher:
            records = await measure(fetcher, cases, native, concurrency=args.concurrency)
    config = {
        "fold_letters": bool(args.fold_letters),
        "native_names": Path(args.native_names).name if args.native_names else "",
        "site_identity_v2": discovery.SITE_IDENTITY_V2,
        "fallback_query": False,
    }
    return summarize(records, config), cases


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--sets", nargs="*", default=list(SETS), choices=list(SETS))
    parser.add_argument("--fold-letters", action="store_true", help="NN-1b on")
    parser.add_argument("--native-names", help="a native-name proposals or signed file (NN-1a)")
    parser.add_argument("--out", type=Path, help="the JSON report")
    parser.add_argument("--markdown", type=Path, help="the tables, as Markdown")
    parser.add_argument("--trust-env-proxy", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    # The fetcher's own log lines name hosts; a blind case's must not reach the job log.
    logging.getLogger("unimatch").setLevel(logging.CRITICAL)
    summary, cases = asyncio.run(run(args))
    report = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    tables = render(summary)
    if leak_check(report + tables, cases):
        raise LeakError("refusing to emit: the output names a design-blind case")
    if args.out:
        args.out.write_text(report, encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(tables, encoding="utf-8")
    print(tables, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
