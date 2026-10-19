"""Explicit bounded capture of the unmodified pipeline; never reads ground truth.

Run from backend: python -m evaluation.research.live --live --out <directory>
Each institution runs in its own process with a hard wall-clock budget.

``--strict-expert-budget`` adds evaluation wrappers around the unchanged app:
60 cumulative cold Fetcher.get calls and six configured Exa queries across
all stages, with no further provider call after HTTP 429. Active time starts
at capture_one entry and lasts the requested 120 seconds by default, including
canary setup, discovery, verification, and funding. The parent adds a separate
15-second process reserve for startup and cancellation/output cleanup; this
reserve never authorizes more tool calls. Legacy mode retains its five-second
child reserve and cache-free page accounting.

``--finalization-reserve-ms 1000`` is an optional strict evaluation setting.
Source/work stops at 119000ms of the same 120000ms case clock; cancellation
cleanup and final output/checkpoint work remain measured, without clamping an
overrun. The final metering-envelope write is audit persistence after that work.

``--knockout-gold DATASET`` (G-07, measurement only) is the one exception to
"never reads ground truth": it reads the case's gold programme URLs from a
development dataset so the read wrapper can answer them with a counted
synthetic 404 (:class:`GoldKnockout`). Off the arm nothing is read or changed.

``--max-search-queries N`` (free-search ticket 02) is the run's hard cap on
provider queries, required for every provider that sends a query anywhere
(all but ``none``, ``fake`` and ``recorded``). The run refuses to start when
its plan (6 per case) exceeds what the cap leaves; each query reserves one
unit of a ledger file shared by every capture of the run (``--search-ledger``)
before it is sent, and the (N+1)th is refused locally with no request sent:
the capture records ``search_budget_exhausted`` and attempts no further case.
"""

import argparse
import asyncio
import functools
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from contextlib import ExitStack, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import urlsplit

from pydantic import HttpUrl

from .identities import IdentityMap
from .mapping import evidence_scope, normalize_subject_claims
from .schema import (
    Capture,
    Evidence,
    Observation,
    PageOutcome,
    Prediction,
    SiteIdentity,
    Telemetry,
)
from .search_cap import (
    RUN_CAP_STOP_REASON,
    SearchCapError,
    SearchQueryLedger,
    needs_cap,
    planned_queries,
)

# Evaluation cohort IDs, not expected URLs/values. Registry remains production's input.
COHORT = {
    "groningen": "rug.nl",
    "delft": "tudelft.nl",
    "aalto": "aalto.fi",
    "vienna": "univie.ac.at",
    "warsaw": "uw.edu.pl",
    "ubc": "ubc.ca",
    "toronto": "utoronto.ca",
    "hku": "hku.hk",
    "ntu": "ntu.edu.sg",
    "kaist": "kaist.ac.kr",
}

#: Registry institutions outside the certified ten. They have no signed
#: labels: a capture of one is scored by process measures and by hand, never
#: by the corpus. They exist so that a rule tuned on the ten is tested
#: somewhere it was not tuned (expert recovery protocol, 2026-09-27).
HELDOUT = {
    "nu": "nu.edu.kz",
    "metu": "metu.edu.tr",
    "sabanci": "sabanciuniv.edu",
    "charles": "cuni.cz",
    "masaryk": "muni.cz",
    "tum": "tum.de",
    "tartu": "ut.ee",
    "polimi": "polimi.it",
    "vilnius": "vu.lt",
}

#: Development cohort dev2 (discovery analysis 2026-10-17, §3): ten top-500
#: seed universities with NO curated registry entry. A capture of one runs the
#: production no-seed path - the entry ``CatalogueDiscoveryAdapter._identify_site``
#: would return, then ``_discover_one`` with empty seeds. Case -> seed_id.
DEV2 = {
    "ethz": "qs2027-008",
    "psaclay": "qs2027-076",
    "uppsala": "qs2027-089",
    "tcd": "qs2027-075",
    "tsinghua": "qs2027-014",
    "tec": "qs2027-188",
    "uba": "qs2027-084",
    "kaznu": "qs2027-177",
    "uct": "qs2027-184",
    "khalifa": "qs2027-147",
    # dev3 (2026-10-18): fifteen more no-seed universities, same path.
    "imperial": "qs2027-002",
    "unsw": "qs2027-019",
    "utokyo": "qs2027-039",
    "ntutw": "qs2027-054",
    "um": "qs2027-056",
    "kuleuven": "qs2027-059",
    "auckland": "qs2027-067",
    "ucph": "qs2027-091",
    "msu": "qs2027-116",
    "iitd": "qs2027-118",
    "puc": "qs2027-120",
    "uio": "qs2027-131",
    "usp": "qs2027-133",
    "ub": "qs2027-165",
    "chula": "qs2027-212",
}
#: The dev3 ids among DEV2: a separate development split file, same capture path.
DEV3_IDS = frozenset(
    "imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula".split()
)

#: The official domain per dev2 case. It overrides the seed file's: Khalifa's
#: seed still says ``kustar.ac.ae``, which redirects off-site.
DEV2_DOMAINS = {
    "ethz": "ethz.ch",
    "psaclay": "universite-paris-saclay.fr",
    "uppsala": "uu.se",
    "tcd": "tcd.ie",
    "tsinghua": "tsinghua.edu.cn",
    "tec": "tec.mx",
    "uba": "uba.ar",
    "kaznu": "kaznu.kz",
    "uct": "uct.ac.za",
    "khalifa": "ku.ac.ae",
    "imperial": "imperial.ac.uk",
    "unsw": "unsw.edu.au",
    "utokyo": "u-tokyo.ac.jp",
    "ntutw": "ntu.edu.tw",
    "um": "um.edu.my",
    "kuleuven": "kuleuven.be",
    "auckland": "auckland.ac.nz",
    "ucph": "ku.dk",
    "msu": "msu.ru",
    "iitd": "iitd.ac.in",
    "puc": "uc.cl",
    "uio": "uio.no",
    "usp": "usp.br",
    "ub": "ub.edu",
    "chula": "chula.ac.th",
}

#: Homepage hosts that are not ``www.<domain>``. ``_identify_site`` probes
#: ``https://<domain>/`` first and keeps the host it lands on: ETH's ``www``
#: redirects to the bare host, and UBA/UCT answer on the bare host (observed
#: 2026-10-17). Every other case lands on, or only answers at, ``www``.
DEV2_HOSTS = {"ethz": "ethz.ch", "uba": "uba.ar", "uct": "uct.ac.za"}

#: Development cohort dev4 (wayfinder programme-discovery, ticket 15,
#: 2026-10-18): country proxies for the heldout nine - other universities in
#: Czechia, Germany, Italy, Estonia, Lithuania and Türkiye, none sharing a
#: registrable domain or a parent with them. Same no-seed capture path as dev2.
#: Kazakhstan has no proxy: KBTU and Satbayev both refuse TLS (ticket 15).
#: Case -> official domain.
DEV4_DOMAINS = {
    "ctu": "cvut.cz",
    "vut": "vut.cz",
    "rwth": "rwth-aachen.de",
    "kit": "kit.edu",
    "unibo": "unibo.it",
    "taltech": "taltech.ee",
    "ktu": "ktu.edu",
    "boun": "bogazici.edu.tr",
    "itu": "itu.edu.tr",
}

#: dev4 case -> top-500 seed row. Three dev4 universities are not in the seed
#: (so the product never reaches them); their identity is given here instead,
#: as ``(name, country, city)``, and only the capture's throwaway database
#: gets a row for them.
DEV4_SEEDS = {
    "ctu": "qs2027-434",
    "rwth": "qs2027-105",
    "kit": "qs2027-111",
    "unibo": "qs2027-123",
    "boun": "qs2027-345",
    "itu": "qs2027-279",
}
DEV4_OFF_SEED = {
    "vut": ("Brno University of Technology", "Czechia", "Brno"),
    "taltech": ("Tallinn University of Technology", "Estonia", "Tallinn"),
    "ktu": ("Kaunas University of Technology", "Lithuania", "Kaunas"),
}

#: dev4 homepage hosts that are not ``www.<domain>``: the bare host answers
#: and is kept (observed 2026-10-18; ``https://cvut.cz/`` does not answer).
DEV4_HOSTS = {
    "taltech": "taltech.ee",
    "ktu": "ktu.edu",
    "boun": "bogazici.edu.tr",
    "itu": "itu.edu.tr",
}

#: Development cohort dev5 (2026-10-19): thirteen more country proxies for the
#: heldout nine - Kazakhstan (KBTU, Satbayev, AITU), Türkiye, Czechia, Germany,
#: Italy and Lithuania - none sharing a registrable domain or a parent with them.
#: Same no-seed capture path as dev4. KBTU and Satbayev are access cases: both
#: serve a TLS chain without its intermediate, so robots.txt cannot be read.
#: Case -> official domain.
DEV5_DOMAINS = {
    "kbtu": "kbtu.edu.kz",
    "satbayev": "satbayev.university",
    "aitu": "astanait.edu.kz",
    "hacettepe": "hacettepe.edu.tr",
    "bilkent": "bilkent.edu.tr",
    "ytu": "yildiz.edu.tr",
    "upol": "upol.cz",
    "zcu": "zcu.cz",
    "tud": "tu-dresden.de",
    "lmu": "lmu.de",
    "unipd": "unipd.it",
    "sapienza": "uniroma1.it",
    "vilniustech": "vilniustech.lt",
}

#: dev5 case -> top-500 seed row; the seven others are off-seed, as in dev4.
DEV5_SEEDS = {
    "satbayev": "qs2027-351",
    "bilkent": "qs2027-455",
    "tud": "qs2027-185",
    "lmu": "qs2027-061",
    "unipd": "qs2027-204",
    "sapienza": "qs2027-112",
}
DEV5_OFF_SEED = {
    "kbtu": ("Kazakh-British Technical University", "Kazakhstan", "Almaty"),
    "aitu": ("Astana IT University", "Kazakhstan", "Astana"),
    "hacettepe": ("Hacettepe University", "Türkiye", "Ankara"),
    "ytu": ("Yildiz Technical University", "Türkiye", "Istanbul"),
    "upol": ("Palacký University Olomouc", "Czechia", "Olomouc"),
    "zcu": ("University of West Bohemia", "Czechia", "Plzeň"),
    "vilniustech": ("Vilnius Gediminas Technical University", "Lithuania", "Vilnius"),
}

#: dev5 homepage hosts that are not ``www.<domain>``: ``https://<domain>/``
#: answers and is kept (observed 2026-10-19; AITU redirects to ``/en`` on the
#: bare host, ``www.tu-dresden.de`` and ``www.vilniustech.lt`` redirect to it).
#: KBTU and Satbayev answer neither from a container; the bare host is the one
#: their own pages use.
DEV5_HOSTS = {
    "kbtu": "kbtu.edu.kz",
    "satbayev": "satbayev.university",
    "aitu": "astanait.edu.kz",
    "hacettepe": "hacettepe.edu.tr",
    "ytu": "yildiz.edu.tr",
    "tud": "tu-dresden.de",
    "vilniustech": "vilniustech.lt",
}

#: The country-proxy sets (dev4, dev5): homepage entries built from these tables.
PROXY_DOMAINS = {**DEV4_DOMAINS, **DEV5_DOMAINS}
PROXY_SEEDS = {**DEV4_SEEDS, **DEV5_SEEDS}
PROXY_OFF_SEED = {**DEV4_OFF_SEED, **DEV5_OFF_SEED}
PROXY_HOSTS = {**DEV4_HOSTS, **DEV5_HOSTS}

#: Case -> official domain for every case id ``--case`` accepts.
CASE_DOMAINS = {**COHORT, **HELDOUT, **DEV2_DOMAINS, **PROXY_DOMAINS}

#: Every case captured from a homepage entry rather than a registry selector.
NO_REGISTRY_CASES = frozenset({*DEV2, *PROXY_DOMAINS})


def dev2_entry(case_id: str) -> dict[str, str]:
    """The ``{"name","country","city","homepage"}`` entry ``_identify_site`` returns."""
    from app.catalogue.importer import SEED_PATH, canonical_name, country_name

    if case_id in PROXY_OFF_SEED:
        name, country, city = PROXY_OFF_SEED[case_id]
        host = PROXY_HOSTS.get(case_id, f"www.{PROXY_DOMAINS[case_id]}")
        return {
            "name": name,
            "country": country_name(country),
            "city": city,
            "homepage": f"https://{host}/",
        }
    seed_id = PROXY_SEEDS[case_id] if case_id in PROXY_DOMAINS else DEV2[case_id]
    document = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    row = next(r for r in document["universities"] if r.get("seed_id") == seed_id)
    if case_id in PROXY_DOMAINS:
        host = PROXY_HOSTS.get(case_id, f"www.{PROXY_DOMAINS[case_id]}")
    else:
        host = DEV2_HOSTS.get(case_id, f"www.{DEV2_DOMAINS[case_id]}")
    return {
        # The University row's name, as _identify_site returns it, so the
        # canary's per-institution row finds its candidate and trace.
        "name": canonical_name(row["name"]),
        "country": country_name(row["country"]),
        "city": row.get("city") or "",
        "homepage": f"https://{host}/",
    }


def seed_entry(case_id: str) -> dict[str, str]:
    """v3-M3: the case's entry as its seed row alone gives it (``--through-identity-gate``).

    Name, country and city as ``dev2_entry`` gives them, so the canary finds
    the same catalogue row; the homepage is the row's own ``official_site``
    (else ``https://<official_domain>/``), with no ``DEV2_DOMAINS`` /
    ``DEV2_HOSTS`` correction. Nothing reads it as verified: production's
    ``_identify_site`` probes the catalogue row and decides, and the canary
    uses the homepage only to label its fetch audit until the gate has
    established a domain. A row with neither field (utokyo, ntutw, auckland)
    keeps ``dev2_entry``'s homepage as that label; the row still has no domain.

    G-06: a cohort case's entry is ``cohort_entry`` corrected the same way from
    its ``COHORT_SEEDS`` row (vienna, ntu, kaist have neither field).
    """
    from app.catalogue.importer import SEED_PATH

    seed_id = COHORT_SEEDS[case_id] if case_id in COHORT else DEV2[case_id]
    document = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    row = next(r for r in document["universities"] if r.get("seed_id") == seed_id)
    entry = cohort_entry(case_id) if case_id in COHORT else dev2_entry(case_id)
    if row.get("official_site"):
        entry["homepage"] = row["official_site"]
    elif row.get("official_domain"):
        entry["homepage"] = f"https://{row['official_domain']}/"
    return entry


# --- G-06: the cohort through the no-seed and identity-gate paths -------------

#: G-06: the cohort's top-500 seed rows (same identity key as the registry
#: row, so the canary binds the same University). Case -> seed_id.
COHORT_SEEDS = {
    "groningen": "qs2027-157",
    "delft": "qs2027-048",
    "aalto": "qs2027-126",
    "vienna": "qs2027-141",
    "warsaw": "qs2027-290",
    "ubc": "qs2027-046",
    "toronto": "qs2027-032",
    "hku": "qs2027-011",
    "ntu": "qs2027-012",
    "kaist": "qs2027-065",
}

#: v3-M3 / G-06: the cases ``--through-identity-gate`` sends through the gate.
GATED_CASES = frozenset({*DEV2, *COHORT})


def cohort_entry(case_id: str) -> dict[str, str]:
    """G-06 ``--no-registry-seeds``: a cohort case's registry row *without its seeds*.

    The same ``{"name","country","city","homepage"}`` shape as ``dev2_entry``:
    the registry row's name and country (so the canary binds the row the
    importer created), its city and its curated homepage, and nothing else -
    no ``seeds``, no ``seeds_verified_on``, no ``campuses``.
    """
    from app.catalogue.importer import REGISTRY_PATH, country_name

    domain = COHORT[case_id]
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    hosts = {domain, f"www.{domain}", f"en.{domain}"}
    row = next(r for r in registry if urlsplit(r["homepage"]).hostname in hosts)
    return {
        "name": row["name"],
        "country": country_name(row["country"]),
        "city": row.get("city") or "",
        "homepage": row["homepage"],
    }


def with_off_seed_rows(install: Callable[..., None]) -> Callable[..., None]:
    """``canary._install_identified_sites``, after adding a row for an off-seed dev4/dev5 entry.

    The canary binds an entry to its catalogue row and stops when there is
    none. A dev4 university outside the top-500 seed has no row, so one is
    added - to the canary's throwaway database only - before the original
    runs. Every other entry is left to the original, which still refuses a
    name it cannot match.
    """

    def installed(session: Any, entries: list[dict], **kwargs: Any) -> None:
        from app.catalogue.importer import country_name, identity_key, stable_id
        from app.models.university import University

        off_seed = {(name, country_name(country)) for name, country, _ in PROXY_OFF_SEED.values()}
        for entry in entries:
            if (entry["name"], entry["country"]) not in off_seed:
                continue
            key = identity_key(entry["name"], entry["country"])
            if session.get(University, stable_id(key)) is None:
                session.add(
                    University(
                        id=stable_id(key),
                        identity_key=key,
                        name=entry["name"],
                        country=entry["country"],
                        city=entry["city"],
                        aliases=[entry["name"]],
                    )
                )
        session.flush()
        install(session, entries, **kwargs)

    return installed


STRICT_MAX_FETCHER_CALLS = 60
STRICT_MAX_SEARCH_QUERIES = 6
STRICT_MAX_SECONDS = 120
STRICT_PROCESS_RESERVE_SECONDS = 15
STRICT_PROVIDERS = frozenset({"exa", "exa_mcp"})

#: Recorded-search replay (owner, 2026-10-19: paid search frozen): the store
#: ``--search-provider recorded`` answers from when ``--recorded-store`` and
#: ``UNIMATCH_RECORDED_SEARCH_STORE`` are both unset. Built by
#: ``evaluation.research.recorded_search`` from the base3 captures.
DEFAULT_RECORDED_STORE = Path(__file__).parent / "data" / "recorded_search.base3.json"
#: The paid providers' keys. A recorded capture's child gets every one of them
#: empty (an environment value outranks a ``.env`` file), so nothing it runs
#: could reach a paid provider even if the factory were changed to try.
PAID_SEARCH_KEYS = (
    "UNIMATCH_EXA_API_KEY",
    "UNIMATCH_TAVILY_API_KEY",
    "UNIMATCH_BRAVE_API_KEY",
    "UNIMATCH_SERPER_API_KEY",
)


#: H-1 (replay plan 2026-10-19 §5.4): the methods through which each kind of
#: search reaches the provider, as (module, owner or None, attribute, kind).
#: ``discover_candidates`` is imported where it is called, so patching the
#: module attribute reaches every discovery call site.
SEARCH_KIND_STAGES = (
    ("app.adapters.search.retrieval", None, "discover_candidates", "discovery"),
    (
        "app.adapters.requirements.web_requirements",
        "WebRequirementsAdapter",
        "_find_topic_pages",
        "topic",
    ),
    (
        "app.adapters.scholarship.web_scholarships",
        "WebScholarshipAdapter",
        "_search_awards",
        "scholarship",
    ),
    ("app.catalogue.discovery", "CatalogueDiscoveryAdapter", "_identify_site", "identity"),
)


def search_kind_patches() -> list[Any]:
    """Patches that mark every recorded request with the stage that sent it.

    Measurement only: each stage's own coroutine runs unchanged inside
    :func:`app.adapters.search.recorded.search_kind`, which changes no answer.
    Built from the attributes as they stand when called, so a stage another
    harness patch already observes (``_identify_site``) keeps that observer.
    """
    import importlib

    from app.adapters.search import recorded

    def marked(original: Callable[..., Any], kind: str) -> Callable[..., Any]:
        @functools.wraps(original)
        async def run(*args: Any, **kwargs: Any) -> Any:
            with recorded.search_kind(kind):
                return await original(*args, **kwargs)

        return run

    patches = []
    for module_name, owner_name, attribute, kind in SEARCH_KIND_STAGES:
        module = importlib.import_module(module_name)
        owner = getattr(module, owner_name) if owner_name else module
        patches.append(patch.object(owner, attribute, marked(getattr(owner, attribute), kind)))
    return patches


def recorded_kind_telemetry(telemetry: Telemetry, counters: Any) -> None:
    """Copy the recorded provider's counters, total and per kind, into ``telemetry``."""
    telemetry.recorded_search_hits = counters.hits
    telemetry.recorded_search_misses = counters.misses
    for kind, count in counters.misses_by_kind.items():
        setattr(telemetry, f"recorded_search_misses_{kind}", count)


#: Search log (MISS_STAGES 2026-10-19 §0.1): every provider request a live
#: capture sends, beside its case as ``<case>.search.json``, so the next
#: recorded-search store can replay titles and snippets, not URL words alone.
SEARCH_LOG_SCHEMA = "search-log/1"
#: Requests kept per case; a strict capture sends at most six discovery queries.
SEARCH_LOG_CAP = 200
#: Bounds on what one result keeps of the provider's text.
SEARCH_LOG_TITLE_CHARS = 300
SEARCH_LOG_SNIPPET_CHARS = 600


class SearchLog:
    """Per request: the full query text, its parameters and every result in rank order.

    Measurement only, written by the capture harness and read by
    ``evaluation.research.recorded_search``. The query text is public words
    (institution, domain, field, level, country): V2-11 keeps applicant data
    out of every provider request, so none can reach this file. A replayed
    request (the ``recorded`` provider) is never logged, and a case that sent
    no query writes no file, so a capture without one is unchanged.
    A snippet is the provider's ranking hint, never evidence.
    """

    def __init__(self, path: Path, case_id: str) -> None:
        self.path = path
        self.case_id = case_id
        self.requests: list[dict[str, Any]] = []

    def record(
        self,
        provider: str,
        method: str,
        request: dict[str, Any],
        response: Any,
        kind: str | None,
    ) -> None:
        """Keep one answered request and rewrite the file (a killed case keeps it)."""
        if len(self.requests) >= SEARCH_LOG_CAP:
            return
        results = [
            {
                "rank": result.rank,
                "url": result.url,
                "title": (result.title or "")[:SEARCH_LOG_TITLE_CHARS],
                "snippet": (result.snippet or "")[:SEARCH_LOG_SNIPPET_CHARS],
            }
            for result in getattr(response, "results", ())
        ]
        self.requests.append(
            {
                "provider": provider,
                "method": method,
                "kind": kind,
                "query": str(request.get("query", "")),
                "domains": [str(d) for d in request.get("domains") or ()],
                "hl": request.get("hl"),
                "gl": request.get("gl"),
                "max_results": request.get("max_results", 10),
                "results": results,
            }
        )
        self.write()

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SEARCH_LOG_SCHEMA, "case": self.case_id, "requests": self.requests}

    def write(self) -> None:
        temporary = self.path.with_suffix(".pending-search")
        temporary.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        temporary.replace(self.path)


def search_environment(search_provider: str, recorded_store: Path | None) -> dict[str, str]:
    """The environment a capture child is given for its search layer and mode.

    ``UNIMATCH_KNOWLEDGE_MODE=live`` always: since 2026-10-19 the product
    answers from the knowledge base by default, with an offline fetcher and
    no discovery, and a benchmark capture measures the web pipeline. In
    recorded mode the store path is passed and every paid key is blanked.
    """
    environment = {"UNIMATCH_KNOWLEDGE_MODE": "live"}
    if search_provider == "recorded":
        if recorded_store is None:
            raise ValueError("recorded search needs a store")
        environment["UNIMATCH_RECORDED_SEARCH_STORE"] = str(recorded_store)
        environment.update(dict.fromkeys(PAID_SEARCH_KEYS, ""))
    return environment


def resolve_recorded_store(argument: Path | None) -> Path:
    """``--recorded-store``, else ``UNIMATCH_RECORDED_SEARCH_STORE``, else the default."""
    configured = os.environ.get("UNIMATCH_RECORDED_SEARCH_STORE", "").strip()
    chosen = argument or (Path(configured) if configured else DEFAULT_RECORDED_STORE)
    return chosen.resolve()


def proxied_fetcher(fetcher_class: type) -> type:
    """``Fetcher`` sending through the environment's HTTPS proxy (``--trust-env-proxy``).

    For a capture run from an agent sandbox only, where the proxy is the one
    way out: robots, rate limits, the PII guard and TLS verification are the
    production fetcher's own (``Fetcher(trust_env_proxy=True)``).
    """

    class ProxiedFetcher(fetcher_class):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["trust_env_proxy"] = True
            super().__init__(*args, **kwargs)

    return ProxiedFetcher


@dataclass
class _ExpertBudget:
    """One case ledger shared by every Fetcher/provider instance and stage."""

    max_fetcher_calls: int
    seconds: float
    provider_name: str
    started: float
    max_search_queries: int = STRICT_MAX_SEARCH_QUERIES
    clock: Callable[[], float] = time.monotonic
    finalization_reserve_ms: int = 0
    fetcher_calls: int = 0
    search_queries: int = 0
    blocked_search_queries: int = 0
    network_http_requests: int = 0
    stop_reason: str | None = None
    provider_failure: dict[str, Any] | None = None

    @property
    def source_work_deadline_ms(self) -> int:
        return int(self.seconds * 1000) - self.finalization_reserve_ms

    @property
    def active_time_basis(self) -> str:
        basis = "capture_one entry; includes canary setup and all pipeline stages"
        if self.finalization_reserve_ms:
            basis += (
                ", cancellation cleanup, output/raw persistence and final checkpoint work; "
                "final metering-envelope persistence is audit only"
            )
        return basis

    def remaining(self) -> float:
        remaining = (
            self.seconds - self.finalization_reserve_ms / 1000 - (self.clock() - self.started)
        )
        if remaining <= 0:
            self.stop_reason = self.stop_reason or (
                "source_work_deadline_exhausted"
                if self.finalization_reserve_ms
                else "wall_clock_budget_exhausted"
            )
            raise TimeoutError("BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED")
        return remaining

    def before_fetch(self) -> None:
        self.remaining()
        if self.fetcher_calls >= self.max_fetcher_calls:
            self.stop_reason = self.stop_reason or "page_budget_exhausted"
            raise RuntimeError("BENCHMARK_PAGE_BUDGET_EXHAUSTED")
        self.fetcher_calls += 1

    def before_search(self, provider_name: str) -> None:
        from app.adapters.search.base import SearchUnavailable

        self.remaining()
        if provider_name != self.provider_name or provider_name not in STRICT_PROVIDERS:
            raise SearchUnavailable("Strict capture refused a different provider identity")
        if self.provider_failure and self.provider_failure.get("http_status") == 429:
            self.blocked_search_queries += 1
            raise SearchUnavailable(
                "Strict capture stopped provider calls after HTTP 429", http_status=429
            )
        if self.search_queries >= self.max_search_queries:
            self.blocked_search_queries += 1
            self.stop_reason = self.stop_reason or "search_budget_exhausted"
            raise SearchUnavailable("Strict capture search query budget exhausted")
        self.search_queries += 1

    def failed_search(self, exc: Exception) -> Exception:
        """Keep a fixed diagnostic/status, never vendor exception text or keys."""
        from app.adapters.search.base import (
            SearchFailureReason,
            SearchUnavailable,
            search_failure_diagnostic,
        )

        status = getattr(exc, "http_status", None)
        if type(status) is not int or not 100 <= status <= 599:
            status = getattr(getattr(exc, "response", None), "status_code", None)
        if type(status) is not int or not 100 <= status <= 599:
            status = None
        reason = getattr(exc, "reason", None)
        reason = reason if isinstance(reason, SearchFailureReason) else None
        sanitized = SearchUnavailable(
            "Configured search provider unavailable", http_status=status, reason=reason
        )
        self.provider_failure = {
            "http_status": status,
            "reason": reason.value if reason else None,
            "error": search_failure_diagnostic(self.provider_name, sanitized),
        }
        if status == 429:
            self.stop_reason = "http_429"
        return sanitized

    def snapshot(self) -> dict[str, Any]:
        return {
            "strict_expert_budget": True,
            "provider": self.provider_name,
            "max_fetcher_calls": self.max_fetcher_calls,
            "max_search_queries": self.max_search_queries,
            "max_active_seconds": self.seconds,
            "finalization_reserve_ms": self.finalization_reserve_ms,
            "source_work_deadline_ms": self.source_work_deadline_ms,
            "fetcher_calls": self.fetcher_calls,
            "search_queries": self.search_queries,
            "blocked_search_queries": self.blocked_search_queries,
            "network_http_requests": self.network_http_requests,
            "elapsed_ms": max(0, int((self.clock() - self.started) * 1000)),
            "stop_reason": self.stop_reason,
            "provider_failure": self.provider_failure,
            "active_time_basis": self.active_time_basis,
        }


#: Award and document identities the owner approved on 2026-09-23. Scoring
#: live with them is what lets a scholarship or document claim land on its
#: certified key; without them every such claim stays ``unmapped.*``.
REVIEWED_BINDINGS = Path(__file__).parent / "data" / "identity_bindings.reviewed.json"


def load_identities(extra_bindings: Sequence[Path] = ()) -> IdentityMap:
    """The reviewed bindings, then each extra file's bindings that add an identity.

    Measurement only (M-1): an unsigned draft binding file lets a claim on an
    award nobody has signed yet land on its corpus key instead of
    ``unmapped.*``. A reviewed binding is never overridden: an extra binding for
    an identity (kind, source URL, subject) already bound is skipped, and an
    earlier extra file wins over a later one the same way.
    """
    from .metrics import canonical_url

    reviewed = IdentityMap.model_validate_json(REVIEWED_BINDINGS.read_text(encoding="utf-8"))
    if not extra_bindings:
        return reviewed
    bindings = list(reviewed.bindings)
    seen = {(b.kind, canonical_url(b.source_url), b.subject) for b in bindings}
    versions = [reviewed.version]
    for path in extra_bindings:
        extra = IdentityMap.model_validate_json(Path(path).read_text(encoding="utf-8"))
        versions.append(extra.version)
        for binding in extra.bindings:
            identity = (binding.kind, canonical_url(binding.source_url), binding.subject)
            if identity in seen:
                continue
            seen.add(identity)
            bindings.append(binding)
    return IdentityMap(version="+".join(versions), bindings=bindings)


def _binding_label(path: Path) -> str:
    """A binding file as the capture config records it: relative to backend/ when inside it."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path(__file__).resolve().parents[2]).as_posix()
    except ValueError:
        return str(path)


def timeout_programme_urls(
    runners: Sequence[Any],
    predictions: Sequence[Prediction],
    confirmed: Sequence[str] = (),
) -> list[str]:
    """The programme pages a case had confirmed when its wall clock ran out.

    The normal path takes them from the canary report's ``programs``, i.e. the
    runner's candidates' programmes; a killed case never gets that report, and
    until QB-1b's analysis (Groningen, 2026-10-17) its ``programme_urls`` stayed
    empty although the page had already produced six claims. The same rows are
    read from the runner when it is reachable; otherwise the pages discovery
    had confirmed at its confirm/walker checkpoint (``confirmed``; UBC, killed
    in search after reading its programme page, 2026-10-18); otherwise the
    evidence URLs of the ``programme.exists`` claims already filed.
    """
    urls: list[str] = []
    for runner in runners[-1:]:
        for candidate in getattr(runner, "_candidates", None) or []:
            urls.extend(str(program.url) for program in candidate.programs if program.url)
    if not urls:
        urls = list(confirmed)
    if not urls:
        urls = [
            str(prediction.evidence.url)
            for prediction in predictions
            if prediction.key == "programme.exists"
            and prediction.value is True
            and prediction.evidence is not None
        ]
    return list(dict.fromkeys(urls))


def trace_stage_telemetry(trace: Any) -> dict[str, Any]:
    """The per-stage clock a discovery trace records, as telemetry fields.

    The trace may carry ``stage_seconds`` (stage -> seconds), ``stage_reads``
    (stage -> page reads) and ``t_first_query``; each is copied only when it
    is present and well formed, and a missing one stays unset rather than
    estimated (structural analysis 2026-10-18, section 4; the log-parsing
    prototype is what this replaces).
    """
    if not isinstance(trace, dict):
        return {}

    def number(value: Any) -> bool:
        return isinstance(value, int | float) and not isinstance(value, bool) and value >= 0

    out: dict[str, Any] = {}
    seconds = trace.get("stage_seconds")
    if (
        isinstance(seconds, dict)
        and seconds
        and all(isinstance(k, str) and number(v) for k, v in seconds.items())
    ):
        out["stage_seconds"] = {k: round(float(v), 1) for k, v in seconds.items()}
    reads = trace.get("stage_reads")
    if (
        isinstance(reads, dict)
        and reads
        and all(
            isinstance(k, str) and number(v) and float(v).is_integer() for k, v in reads.items()
        )
    ):
        out["stage_reads"] = {k: int(v) for k, v in reads.items()}
    if number(trace.get("t_first_query")):
        out["t_first_query"] = round(float(trace["t_first_query"]), 1)
    return out


def programme_aliases(programme_urls: Sequence[str], trace: Any) -> dict[str, list[str]]:
    """The declared twins (WF-17) of each programme page, from a trace or its dict.

    Matched on the scorer's canonical URL, so a lead recorded with a trailing
    slash still finds its twins; pages without a declared twin are left out.
    """
    from .metrics import canonical_url

    recorded = (
        trace.get("programme_url_aliases")
        if isinstance(trace, dict)
        else getattr(trace, "programme_url_aliases", None)
    ) or {}
    by_canonical: dict[str, list[str]] = {}
    for url, twins in recorded.items():
        known = by_canonical.setdefault(canonical_url(url), [])
        known.extend(t for t in twins if t not in known)
    out: dict[str, list[str]] = {}
    for url in programme_urls:
        twins = by_canonical.get(canonical_url(url))
        if twins:
            out[str(url)] = list(twins)
    return out


#: G-07: the error a knocked-out read carries instead of the page (a synthetic 404).
KNOCKOUT_ERROR = "KNOCKOUT_GOLD; synthetic 404, not read"


def _knockout_forms(url: object) -> set[str]:
    """The forms of one URL the gold-knockout arm treats as the same page.

    ``metrics._page_forms`` (trailing ``/``, ``index.html``, ``.htm``/``.html``,
    an intake-year segment) plus every ``lang`` query parameter dropped, the
    scheme and a leading ``www.`` ignored: the arm refuses more of the gold's
    spellings than the scorer would match, never fewer.
    """
    from urllib.parse import urlsplit

    from .metrics import _page_forms

    written, yearless = _page_forms(url, None)
    out: set[str] = set()
    for form in written | yearless:
        parts = urlsplit(form)
        host = parts.netloc.removeprefix("www.")
        query = "&".join(
            piece for piece in parts.query.split("&") if piece and piece.partition("=")[0] != "lang"
        )
        out.add(f"{host}{parts.path.rstrip('/')}?{query}")
    return out


class GoldKnockout:
    """G-07, measurement only: the case's gold programme pages are unreachable.

    Built from a development dataset's ``programme_urls`` (every labelled URL,
    so a declared twin in the label is refused too). The benchmark's
    ``bounded()`` read wrapper asks :meth:`refuses` before a read and answers a
    match with a synthetic 404 without touching the network; it asks
    :meth:`screen` after a read, so a redirect onto the gold or a page that
    declares a gold page as its ``hreflang`` alternate (a twin the label does
    not list) is replaced by the same 404. ``Fetcher`` is never changed.
    """

    def __init__(self, gold_urls: Sequence[str], domain: str) -> None:
        self.gold_urls = [str(u) for u in gold_urls]
        self.domain = domain
        self.forms: set[str] = set().union(*(_knockout_forms(u) for u in self.gold_urls))
        #: Reads answered with the synthetic 404 (count only; no URL is kept).
        self.refused = 0

    @classmethod
    def from_dataset(cls, path: Path, case_id: str) -> "GoldKnockout":
        from .schema import Dataset

        if case_id in HELDOUT:
            raise ValueError("The gold-knockout arm never runs on a heldout case")
        dataset = Dataset.model_validate_json(Path(path).read_text(encoding="utf-8"))
        if dataset.split != "development":
            raise ValueError("The gold-knockout arm reads a development dataset only")
        case = next((c for c in dataset.cases if c.id == case_id), None)
        if case is None:
            raise ValueError(f"Case {case_id} is not in the knockout dataset")
        return cls([str(u) for u in case.programme_urls], case.domain)

    def matches(self, url: object) -> bool:
        return bool(self.forms) and bool(_knockout_forms(url) & self.forms)

    def refusal(self, url: str) -> Any:
        from app.adapters.fetching import FetchResult
        from app.domain.enums import FetchOutcome

        self.refused += 1
        return FetchResult(
            url=url,
            outcome=FetchOutcome.HTTP_ERROR,
            status_code=404,
            error=KNOCKOUT_ERROR,
            final_url=url,
        )

    def screen(self, url: str, result: Any) -> Any:
        """``result``, or the synthetic 404 when the read landed on a gold page or its twin."""
        if not self.forms or result is None:
            return result
        if self.matches(getattr(result, "final_url", "") or url):
            return self.refusal(url)
        if getattr(result, "ok", False) and not getattr(result, "is_pdf", False):
            from app.adapters.discovery.live_discovery import declared_alternates

            text = getattr(result, "text", "") or ""
            twins = declared_alternates(getattr(result, "final_url", "") or url, text, self.domain)
            if any(self.matches(twin) for twin in twins):
                return self.refusal(url)
        return result

    def trace_line(self) -> str:
        if not self.forms:
            return "knockout: no-op (no gold programme label)"
        return f"knockout: {self.refused} urls refused"


def related_programmes(trace: Any) -> list[str]:
    """v3-M2: the URLs discovery recorded as a related programme (ticket 16 Q6).

    Read from the trace's ``related_programmes`` (a dict or its object; each
    entry a URL, a ``{"url", "title"}`` row or a ``(url, title)`` pair). A
    trace that records none gives none.
    """
    recorded = (
        trace.get("related_programmes")
        if isinstance(trace, dict)
        else getattr(trace, "related_programmes", None)
    ) or []
    out: list[str] = []
    for entry in recorded:
        if isinstance(entry, dict):
            url = entry.get("url")
        elif isinstance(entry, list | tuple) and entry:
            url = entry[0]
        else:
            url = entry
        if isinstance(url, str) and url.startswith(("http://", "https://")) and url not in out:
            out.append(url)
    return out


def apply_stage_telemetry(telemetry: Telemetry, trace: Any) -> None:
    """Fill the stage fields from ``trace``; the harness's own first-query clock wins."""
    for name, value in trace_stage_telemetry(trace).items():
        if name == "t_first_query" and telemetry.t_first_query is not None:
            continue
        setattr(telemetry, name, value)


async def _jev_shadow(case_id: str, queued: list[str], profile: Any) -> None:
    """Shadow only: where a decision model would rank the certified programme page.

    Nothing the run reads changes. The line it prints is the Phase 4 experiment's
    evidence: the gold page's rank in the heuristic queue beside its rank after the
    model reorders the same candidates (analysis/v2/07, Experiment 2).
    """
    from app.adapters.decisions import get_decision_model
    from app.adapters.decisions.link_ranker import LinkCandidate, rank_links

    model = get_decision_model()
    if model is None or not queued:
        return
    from .metrics import canonical_url
    from .schema import Dataset

    dataset = Dataset.model_validate_json(
        (Path(__file__).parent / "data" / "ground_truth.reviewed.json").read_text(encoding="utf-8")
    )
    case = next((c for c in dataset.cases if c.id == case_id), None)
    gold = {canonical_url(u) for u in (case.programme_urls if case else [])}
    context = profile.context
    ranked, model_id = await rank_links(
        model,
        [LinkCandidate(u) for u in queued[:48]],
        field=", ".join(context.intended_fields),
        degree=str(context.level),
        target="programme page",
    )

    def rank(urls: list[str]) -> int | None:
        return next((i + 1 for i, u in enumerate(urls) if canonical_url(u) in gold), None)

    print(
        f"jev shadow: gold programme rank heuristic={rank(queued[:48])} "
        f"model={rank([r.url for r in ranked])} of {len(ranked)} ({model_id or 'unavailable'})",
        flush=True,
    )


#: D7: seconds the documents stage gets after the decision stage; 0 skips it.
DOCUMENT_SECONDS = 0.0


async def capture_one(
    case_id: str,
    output: Path,
    max_pages: int,
    seconds: float | None = None,
    *,
    strict_expert_budget: bool = False,
    finalization_reserve_ms: int = 0,
    extra_bindings: Sequence[Path] = (),
    through_identity_gate: bool = False,
    knockout_gold: Path | None = None,
    no_registry_seeds: bool = False,
    trust_env_proxy: bool = False,
    search_ledger: SearchQueryLedger | None = None,
) -> None:
    entered = time.monotonic()
    if type(finalization_reserve_ms) is not int or finalization_reserve_ms < 0:
        raise ValueError("Finalization reserve must be a nonnegative integer in milliseconds")
    if finalization_reserve_ms and not strict_expert_budget:
        raise ValueError("Finalization reserve requires strict expert budget mode")
    # Delayed imports keep ordinary offline evaluation entirely independent of I/O.
    from app.adapters import fetching
    from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter, PageCategory
    from app.adapters.search import recorded as recorded_search
    from app.adapters.search.exa import ExaSearchProvider
    from app.catalogue.discovery import CatalogueDiscoveryAdapter
    from app.config import get_settings as current_settings
    from app.domain.enums import FetchOutcome, UserDecision
    from app.models.research import ClaimRow, ProgramResultRow
    from app.pipeline import runner as runner_module
    from scripts import canary_discovery as canary

    #: Recorded-search replay (2026-10-19): the store's hits and misses become
    #: this case's telemetry, so a rule that changes the queries reads as
    #: unmeasurable on the replay instead of as a pipeline loss.
    recorded_mode = current_settings().search_provider == "recorded"
    recorded_search.COUNTERS.reset()
    misses_printed = 0
    search_log = SearchLog(output.with_suffix(".search.json"), case_id)

    budget = None
    if strict_expert_budget:
        from app.config import get_settings

        seconds = STRICT_MAX_SECONDS if seconds is None else seconds
        if (
            type(max_pages) is not int
            or not 1 <= max_pages <= STRICT_MAX_FETCHER_CALLS
            or not 0 < seconds <= STRICT_MAX_SECONDS
        ):
            raise ValueError(
                "Strict capture budget must be at most 60 Fetcher calls and 120 active seconds"
            )
        if finalization_reserve_ms >= seconds * 1000:
            raise ValueError("Finalization reserve must be less than the full case clock")
        settings = get_settings()
        if settings.search_provider not in STRICT_PROVIDERS:
            raise ValueError("Strict live capture requires configured exa or exa_mcp")
        if settings.enable_browser_tier or not settings.respect_robots:
            raise ValueError("Strict live capture requires browser tier off and robots respected")
        budget = _ExpertBudget(
            max_pages,
            seconds,
            settings.search_provider,
            entered,
            clock=time.monotonic,
            finalization_reserve_ms=finalization_reserve_ms,
        )

    predictions: list[Prediction] = []
    raw_claims: list[dict[str, Any]] = []
    identities = load_identities(extra_bindings)
    started = entered if budget else time.monotonic()
    observation = Observation(
        case_id=case_id,
        error="CAPTURE_IN_PROGRESS",
        telemetry=Telemetry(
            http_fetches=0,
            browser_fetches=0,
            pdf_fetches=0,
            search_calls=0,
            model_input_tokens=0,
            jev_input_tokens=0,
        ),
    )
    #: v3-M3: only a seed-only (dev2/dev3) case - or, since G-06, a cohort case
    #: whose registry entry is dropped - has a gate to go through; it counts as
    #: not established until production's gate says otherwise.
    gated = through_identity_gate and case_id in GATED_CASES
    #: G-06: a cohort case captured from its registry row without the seeds.
    seedless = no_registry_seeds and case_id in COHORT and not gated
    gate_options: dict[str, Any] = {"drop_registry_entry": True} if case_id in COHORT else {}
    if gated:
        observation.site_identity = SiteIdentity()
    #: G-07: the gold-knockout arm (measurement only; never in ``Fetcher``).
    knockout = GoldKnockout.from_dataset(knockout_gold, case_id) if knockout_gold else None
    if knockout is not None:
        observation.telemetry.knockout_gold_urls = len(knockout.gold_urls)
        observation.telemetry.knockout_refused = 0
        print(knockout.trace_line(), flush=True)

    fetchers: list[Any] = []
    #: D7: the runner, kept for the documents stage that follows the decision.
    runners: list[Any] = []
    recorded_claims: set[str] = set()
    documents_phase = False

    def budget_checkpoint() -> None:
        assert budget is not None
        budget_output = output.with_suffix(".budget.json")
        budget_temporary = budget_output.with_suffix(".pending")
        budget_temporary.write_text(json.dumps(budget.snapshot(), indent=2), encoding="utf-8")
        budget_temporary.replace(budget_output)

    def checkpoint() -> None:
        nonlocal misses_printed
        observation.telemetry.latency_seconds = time.monotonic() - started
        if recorded_mode:
            counters = recorded_search.COUNTERS
            recorded_kind_telemetry(observation.telemetry, counters)
            for digest in counters.missed[misses_printed:]:
                # A digest, never the query text (WF-17 keeps no query text).
                print(f"recorded search miss key={digest}", flush=True)
            misses_printed = len(counters.missed)
        # Counted from the fetcher's own tier tally, never assumed: a zero
        # that nothing increments is a counter invented after the fact.
        observation.telemetry.browser_fetches = sum(
            f.tier_counts.get("browser", 0) for f in fetchers if hasattr(f, "tier_counts")
        )
        temporary = output.with_suffix(".pending")
        temporary.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(output)
        if budget:
            budget_checkpoint()

    def final_checkpoint() -> None:
        checkpoint()
        if budget and budget.finalization_reserve_ms:
            # Record the completed first checkpoint's own work from the same
            # clock. This final metering envelope never opens a new work budget.
            budget_checkpoint()

    checkpoint()
    original_request = fetching._pinned_request
    # Every provider's search is counted, not only Exa's: runs 80-93 used
    # Serper and recorded search_calls=0 while six queries ran per case.
    from app.adapters.search.brave import BraveSearchProvider
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider
    from app.adapters.search.recorded import RecordedSearchProvider
    from app.adapters.search.serper import SerperSearchProvider
    from app.adapters.search.tavily import TavilySearchProvider

    provider_classes = (
        ExaSearchProvider,
        ExaMcpSearchProvider,
        TavilySearchProvider,
        BraveSearchProvider,
        SerperSearchProvider,
        RecordedSearchProvider,
    )
    #: Both ways a query reaches a provider. R5's local-language family goes
    #: through ``search_localized`` (Serper, recorded), which calls the
    #: provider's private request path, not ``search``: counting ``search``
    #: alone left every such case one query short of the 6-query budget.
    search_methods = ("search", "search_localized")
    originals = {
        (cls, method): getattr(cls, method)
        for cls in provider_classes
        for method in search_methods
        if hasattr(cls, method)
    }

    def counted_for(cls, method="search"):
        async def counted(provider, *args, **kwargs):
            return await counted_search(
                originals[(cls, method)],
                provider,
                *args,
                localized=method == "search_localized",
                **kwargs,
            )

        return counted

    async def counted_search(original_search, provider, *args, localized=False, **kwargs):
        # Each search call is counted and timed into this case's own log: a
        # case that runs out of wall clock after two fetches spent the time
        # somewhere, and search is the first place to look.
        if budget:
            budget.before_search(getattr(provider, "name", ""))
        if search_ledger is not None and not search_ledger.reserve():
            # Ticket 02: the run's cap is spent. Refused here, before the
            # provider is asked anything, so the (N+1)th query costs nothing.
            from app.adapters.search.base import SearchUnavailable

            if budget:
                budget.search_queries -= 1
                budget.blocked_search_queries += 1
                budget.stop_reason = budget.stop_reason or RUN_CAP_STOP_REASON
            observation.telemetry.search_cap_refusals = (
                observation.telemetry.search_cap_refusals or 0
            ) + 1
            print("search refused: the run's query cap is reached; no request sent", flush=True)
            checkpoint()
            raise SearchUnavailable("Run search query cap reached; no request was sent")
        if budget:
            observation.telemetry.search_calls = budget.search_queries
        else:
            observation.telemetry.search_calls = (observation.telemetry.search_calls or 0) + 1
        if localized:
            # Already inside search_calls; kept apart so a scorecard can tell
            # the local-language query from the rest.
            observation.telemetry.search_localized_calls = (
                observation.telemetry.search_localized_calls or 0
            ) + 1
        began = time.monotonic()
        if observation.telemetry.t_first_query is None:
            # On the case clock, like latency_seconds: how long the case ran
            # before discovery asked the provider anything.
            observation.telemetry.t_first_query = round(began - started, 1)
        if budget:
            checkpoint()
            if budget.finalization_reserve_ms:
                budget.remaining()
        try:
            response = await original_search(provider, *args, **kwargs)
            name = getattr(provider, "name", "")
            if name != recorded_search.RECORDED_PROVIDER_NAME:
                search_log.record(
                    name,
                    "search_localized" if localized else "search",
                    kwargs,
                    response,
                    recorded_search.current_search_kind(),
                )
            return response
        except Exception as exc:
            reason = getattr(getattr(exc, "reason", None), "value", None)
            # The adapter's capped, key-masked excerpt of the provider's error
            # body: "http 400" alone read as a pipeline result for a night.
            body = getattr(exc, "body_excerpt", None)
            print(
                f"search failed after {time.monotonic() - began:.1f}s: {type(exc).__name__}"
                f" ({reason or 'no reason'}, http {getattr(exc, 'http_status', None)}"
                + (f", body {body!r}" if isinstance(body, str) and body else "")
                + ")"
            )
            if budget:
                raise budget.failed_search(exc) from None
            raise
        finally:
            print(
                f"search #{observation.telemetry.search_calls} took "
                f"{time.monotonic() - began:.1f}s (t={time.monotonic() - started:.0f}s)",
                flush=True,
            )
            checkpoint()

    original_confirm = LiveDiscoveryAdapter._confirm_programs
    original_walk = LiveDiscoveryAdapter._walk_catalogs
    #: What discovery had confirmed at its last checkpoint, and its trace, so a
    #: case killed later still reports them (structural analysis 2026-10-18 §4.2).
    discovery: dict[str, Any] = {"trace": None, "confirmed": []}
    trace_output = output.with_suffix(".trace.json")

    def write_partial_trace(stage: str) -> None:
        as_dict = getattr(discovery["trace"], "as_dict", None)
        if as_dict is None:
            return
        snapshot = {
            "partial": True,
            "checkpoint": stage,
            "programme_urls": discovery["confirmed"],
            "discovery_trace": as_dict(),
        }
        temporary = trace_output.with_suffix(".pending-trace")
        temporary.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        temporary.replace(trace_output)

    def discovery_checkpoint(stage: str, selected: dict[str, list[str]], trace: Any) -> None:
        discovery["trace"] = trace
        discovery["confirmed"] = list(selected.get(PageCategory.PROGRAM_PAGE) or [])
        if discovery["confirmed"]:
            observation.programme_urls = [HttpUrl(url) for url in discovery["confirmed"]]
            observation.programme_url_aliases = programme_aliases(discovery["confirmed"], trace)
        observation.related_programme_urls = related_programmes(trace)
        write_partial_trace(stage)
        checkpoint()

    def counted_request(*args, **kwargs):
        if budget:
            budget.network_http_requests += 1
        else:
            observation.telemetry.http_fetches = (observation.telemetry.http_fetches or 0) + 1
        checkpoint()
        return original_request(*args, **kwargs)

    async def observed_confirm(adapter, selected, ranked, trace, profile):
        queued = list(selected[PageCategory.PROGRAM_PAGE])
        for _score, url in sorted(ranked[PageCategory.PROGRAM_PAGE], reverse=True):
            if url not in queued:
                queued.append(url)
        observation.ranked_urls = [HttpUrl(url) for url in queued]
        checkpoint()
        if budget is None:
            await _jev_shadow(case_id, queued, profile)
        result = await original_confirm(adapter, selected, ranked, trace, profile)
        discovery_checkpoint("confirm", selected, trace)
        return result

    async def observed_walk(adapter, entry, selected, trace, profile):
        result = await original_walk(adapter, entry, selected, trace, profile)
        # The walker confirms its own catalogue candidates (T29), so its
        # programme pages are as confirmed as the confirm stage's.
        discovery_checkpoint("walker", selected, trace)
        return result

    original_identify = CatalogueDiscoveryAdapter._identify_site

    async def observed_identify(adapter, uni, trace):
        # v3-M3: production's own gate, unchanged; its answer is recorded.
        entry = await original_identify(adapter, uni, trace)
        proofs = getattr(adapter, "site_identity_proofs", {})
        observation.site_identity = SiteIdentity(
            established=entry is not None,
            homepage=(entry or {}).get("homepage"),
            proof=proofs.get(uni.id) if entry is not None else None,
        )
        checkpoint()
        return entry

    class ObservedRunner(canary.CanaryRunner):
        def _make_fetcher(self):
            fetcher = super()._make_fetcher()
            fetchers.append(fetcher)
            original = fetcher.get
            requests = 0
            network_reads = 0

            async def bounded(url, **kwargs):
                nonlocal requests, network_reads
                # The budget bounds reads that reach a server. A page two
                # stages both need is served from the cache the second time,
                # and until 2026-09-23 that repeat still spent the budget: run
                # 20 ended Delft, Vienna and UBC in the funding stage with up
                # to a fifth of their 60 calls being cache hits.
                if documents_phase:
                    # The documents stage has its own clock (D7); its reads
                    # never spend the decision stage's budget.
                    pass
                elif budget:
                    budget.before_fetch()
                    observation.telemetry.http_fetches = budget.fetcher_calls
                    kwargs["use_cache"] = False
                elif network_reads >= max_pages:
                    if fetching.CASE_READ_LEDGER:
                        # RL-1: the case stops reading where the ledger would,
                        # gracefully: the read is refused, the claims stand.
                        print(f"get refused (page cap {max_pages}) {url[:120]}", flush=True)
                        return fetching.FetchResult(
                            url=url,
                            outcome=FetchOutcome.BLOCKED,
                            error="BENCHMARK_PAGE_BUDGET_EXHAUSTED; not read",
                            final_url=url,
                        )
                    raise RuntimeError("BENCHMARK_PAGE_BUDGET_EXHAUSTED")
                requests += 1
                if knockout is not None and knockout.matches(url):
                    # G-07: counted like a network read, answered without one.
                    if not documents_phase and not budget:
                        network_reads += 1
                    refused = knockout.refusal(url)
                    observation.telemetry.knockout_refused = knockout.refused
                    print(f"get #{requests} {knockout.trace_line()}", flush=True)
                    checkpoint()
                    return refused
                began = time.monotonic()
                # Written before the read, so a read that never returns still
                # names itself in the log.
                print(f"get #{requests} start t={began - started:.0f}s {url[:120]}", flush=True)
                if budget and not documents_phase:
                    checkpoint()
                    if budget.finalization_reserve_ms:
                        budget.remaining()
                result = await original(url, **kwargs)
                if knockout is not None:
                    result = knockout.screen(url, result)
                    observation.telemetry.knockout_refused = knockout.refused
                # One line per page read, so a case that runs out of wall
                # clock shows which reads took it: its own log is printed by
                # the benchmark when the budget ends the case.
                print(
                    f"get #{requests} took {time.monotonic() - began:.1f}s "
                    f"{getattr(result, 'outcome', '?')}",
                    flush=True,
                )
                if documents_phase:
                    observation.telemetry.document_reads = (
                        observation.telemetry.document_reads or 0
                    ) + 1
                    return result
                if not getattr(result, "from_cache", False):
                    network_reads += 1
                if result.ok and result.is_pdf and not result.from_cache:
                    observation.telemetry.pdf_fetches = (observation.telemetry.pdf_fetches or 0) + 1
                checkpoint()
                return result

            fetcher.get = bounded
            return fetcher

        async def run_to_decision(self):
            try:
                return await super().run_to_decision()
            finally:
                # Why a page produced nothing, in the runner's own vocabulary.
                # Read here rather than after the run, so a case killed by its
                # budget still records what it managed to read — which is
                # exactly the case whose zero needs explaining.
                observation.page_outcomes = [
                    PageOutcome(
                        category=record["category"],
                        url=record["url"],
                        page_type=record.get("page_type") or "",
                        detail=record.get("detail") or "",
                        characters=int(record["characters"]) if record.get("characters") else None,
                    )
                    for record in canary.page_outcomes(self.run)
                ]
                runners.append(self)
                self.record_claims()

        def record_claims(self) -> None:
            for row in self.session.query(ClaimRow).filter(ClaimRow.run_id == self.run.id):
                if row.id in recorded_claims:
                    continue
                recorded_claims.add(row.id)
                raw = row.payload
                raw_claims.append(raw)
                # With the owner-approved identity bindings (2026-09-23),
                # the same split the offline mapper makes: an award or a
                # document claim becomes the fields of the identity it is
                # bound to, and an unbound one stays under its raw key.
                mapped = normalize_subject_claims(row.claim_type, raw, identities)
                excerpt = raw.get("original_text_excerpt")
                for key, value, programme, degree in mapped:
                    evidence = None
                    if excerpt and str(row.source_url).startswith(("http://", "https://")):
                        evidence = Evidence(
                            url=row.source_url,
                            excerpt=excerpt,
                            scope=evidence_scope(
                                raw,
                                university=next(iter(self._candidates)).name
                                if self._candidates
                                else case_id,
                                programme=programme,
                                degree=degree,
                            ),
                            accessed_on=row.accessed_at.date(),
                            source_type="official" if raw.get("official_domain") else "unknown",
                        )
                    predictions.append(Prediction(key=key, value=value, evidence=evidence))

    async def documents_stage() -> None:
        nonlocal documents_phase
        if not (DOCUMENT_SECONDS and runners):
            return
        # D7: the documents stage, after the decision stage is measured and on
        # its own clock, so the decision metrics stay comparable with runs
        # that never collected documents. Every row is approved, as an
        # applicant approving the whole shortlist would.
        documents_phase = True
        began = time.monotonic()
        runner = runners[-1]
        for row in runner.session.query(ProgramResultRow).filter(
            ProgramResultRow.run_id == runner.run.id
        ):
            row.user_decision = UserDecision.APPROVED.value
        runner.session.flush()
        try:
            await asyncio.wait_for(runner.collect_documents(), DOCUMENT_SECONDS)
            observation.telemetry.document_stop = "completed"
        except TimeoutError:
            observation.telemetry.document_stop = "document_seconds_exhausted"
        except Exception as exc:  # recorded, never raised: the decision stage stands
            observation.telemetry.document_stop = f"{type(exc).__name__}: {exc}"[:200]
        runner.record_claims()
        observation.telemetry.document_seconds = time.monotonic() - began
        print(
            f"documents stage {observation.telemetry.document_stop} in "
            f"{observation.telemetry.document_seconds:.1f}s, "
            f"{observation.telemetry.document_reads or 0} reads",
            flush=True,
        )

    with (
        patch.object(canary, "CanaryRunner", ObservedRunner),
        patch.object(
            canary,
            "_install_identified_sites",
            with_off_seed_rows(canary._install_identified_sites),
        ),
        patch.object(fetching, "_pinned_request", counted_request),
        ExitStack() as search_patches,
        patch.object(runner_module, "Fetcher", proxied_fetcher(runner_module.Fetcher))
        if trust_env_proxy
        else nullcontext(),
        patch.object(LiveDiscoveryAdapter, "_confirm_programs", observed_confirm),
        patch.object(LiveDiscoveryAdapter, "_walk_catalogs", observed_walk),
        patch.object(CatalogueDiscoveryAdapter, "_identify_site", observed_identify),
    ):
        for cls, method in originals:
            search_patches.enter_context(patch.object(cls, method, counted_for(cls, method)))
        # H-1: entered last, so the identity stage keeps its observer. Every
        # mode: a replay counts its misses per kind, a live capture's search
        # log names the stage that sent each request.
        for kind_patch in search_kind_patches():
            search_patches.enter_context(kind_patch)
        try:
            active_seconds = budget.remaining() if budget else seconds
            # A dev2/dev4/dev5 case has no registry entry to select: it is handed the
            # homepage entry the production site-identity step would build -
            # or, on the identity-gate arm (v3-M3), a dev2 seed row goes through
            # that step itself. G-06: a cohort case's registry entry is dropped
            # first on the gate arm, and on the no-seed arm it is replaced by the
            # same row without its seeds.
            canary_run = (
                canary.run_canary(
                    None,
                    False,
                    entries=[seed_entry(case_id)],
                    through_identity_gate=True,
                    **gate_options,
                )
                if gated
                else canary.run_canary(
                    None, False, entries=[cohort_entry(case_id)], drop_registry_entry=True
                )
                if seedless
                else canary.run_canary(None, False, entries=[dev2_entry(case_id)])
                if case_id in NO_REGISTRY_CASES
                else canary.run_canary(CASE_DOMAINS[case_id], False)
            )
            report = await asyncio.wait_for(canary_run, active_seconds)
        except TimeoutError:
            # The child stops itself just short of the parent's kill, so the
            # claims already filed are kept: run_to_decision's finally reads
            # them on cancellation, which a killed process never reaches.
            # Runs 59-62: UBC filed nothing because the kill came mid-funding.
            observation.predictions = predictions
            observation.programme_urls = [
                HttpUrl(url)
                for url in timeout_programme_urls(runners, predictions, discovery["confirmed"])
            ]
            if discovery["trace"] is not None:
                observation.programme_url_aliases = programme_aliases(
                    [str(u) for u in observation.programme_urls], discovery["trace"]
                )
                observation.related_programme_urls = related_programmes(discovery["trace"])
                # The trace as it stood at the kill, beside the observation:
                # the canary report that normally carries it never arrives.
                write_partial_trace("timeout")
                apply_stage_telemetry(observation.telemetry, discovery["trace"].as_dict())
            observation.error = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
            if budget:
                budget.stop_reason = budget.stop_reason or (
                    "source_work_deadline_exhausted"
                    if budget.finalization_reserve_ms
                    else "wall_clock_budget_exhausted"
                )
            final_checkpoint()
            # D7: a decision stage that ran out of clock still filed rows; the
            # documents stage has its own clock and reads them. Run 37351314325:
            # Groningen's documents were measured in one repetition of two.
            if DOCUMENT_SECONDS and runners:
                await documents_stage()
                output.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
            return
    rows = report["institutions"]
    observation.programme_urls = [HttpUrl(url) for r in rows for url in r["programs"]]
    traces = [r.get("discovery_trace") for r in rows if r.get("discovery_trace")]
    if traces:
        apply_stage_telemetry(observation.telemetry, traces[0])
        observation.programme_url_aliases = programme_aliases(
            [str(u) for u in observation.programme_urls], traces[0]
        )
        observation.related_programme_urls = related_programmes(traces[0])
    observation.predictions = predictions
    observation.error = report["run_error"] or None
    if budget is None or not budget.finalization_reserve_ms:
        checkpoint()
    await documents_stage()
    # Preserve raw output for mapping/adjudication; do not invent unsupported counters.
    output.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
    output.with_suffix(".raw.json").write_text(
        json.dumps({"canary": report, "claims": raw_claims}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # The raw report carries the full trace; the checkpoint copy is superseded.
    trace_output.unlink(missing_ok=True)
    if budget and budget.finalization_reserve_ms:
        final_checkpoint()


# --- negative forms of the default-on rules (seen-site ledger, 2026-10-19) ----

#: Every default-on rule the harness can switch off, as ``--no-<stem>``: stem ->
#: the module constants the off arm sets False. The fifteen seen-site rules of
#: SEEN_SITE_LEDGER_2026-10-19.md come first, in its re-measure order. A stem
#: with an on-form (``--<stem>``, store_true) cannot be combined with it.
#: ``--recover-search-candidates``, ``--search-funding-fallback`` and
#: ``--target-award-search`` already have their own BooleanOptionalAction form.
#: A flag-off rule whose ticket asks for its off-form ahead of a default change
#: (``DEFAULT_OFF_NEGATABLE``) is listed too: ``--no-<stem>`` keeps it off.
NEGATABLE_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    # The fifteen seen-site rules (ledger re-measure order).
    "local-language-queries": (("app.adapters.search.intent", "LOCAL_LANGUAGE_QUERIES"),),
    "site-identity-v2": (("app.catalogue.discovery", "SITE_IDENTITY_V2"),),
    "alias-aware-program-match": (("app.adapters.matching", "ALIAS_AWARE_PROGRAM_MATCH"),),
    "stage-budgets": (("app.adapters.discovery.live_discovery", "STAGE_BUDGETS"),),
    "question-routing": (
        ("app.adapters.requirements.web_requirements", "QUESTION_ROUTED_EVIDENCE"),
    ),
    "coordinated-degree-scope": (
        ("app.adapters.requirements.web_requirements", "COORDINATED_DEGREE_SCOPE"),
    ),
    "international-round-deadline": (("app.adapters.extraction", "INTERNATIONAL_ROUND_DEADLINE"),),
    "english-readers-v2": (("app.adapters.extraction", "ENGLISH_READERS_V2"),),
    "fee-readers-v2": (("app.adapters.extraction", "FEE_READERS_V2"),),
    "intake-section-deadline": (("app.adapters.extraction", "INTAKE_SECTION_DEADLINE"),),
    "parent-degree-link": (("app.adapters.requirements.web_requirements", "PARENT_DEGREE_LINK"),),
    "question-page-order": (("app.adapters.requirements.web_requirements", "QUESTION_PAGE_ORDER"),),
    "award-page-evidence": (("app.adapters.page_classifier", "AWARD_PAGE_EVIDENCE"),),
    "award-name-qualifier": (("app.adapters.page_classifier", "AWARD_NAME_QUALIFIER"),),
    "scholarship-index-query": (
        ("app.adapters.scholarship.web_scholarships", "SCHOLARSHIP_INDEX_QUERY"),
    ),
    # Every other default-on rule with a harness on-form.
    "applicant-academic-year": (("app.pipeline.runner", "APPLICANT_ACADEMIC_YEAR"),),
    "shared-query-budget": (("app.adapters.search.intent", "SHARED_QUERY_BUDGET"),),
    "deadline-v2": (("app.adapters.extraction", "DEADLINE_V2"),),
    "route-leads": (("app.adapters.requirements.web_requirements", "ROUTE_LEADS"),),
    "localized-page-identity": (("app.adapters.page_classifier", "LOCALIZED_PAGE_IDENTITY"),),
    "subject-title-shapes": (("app.adapters.discovery.live_discovery", "SUBJECT_TITLE_SHAPES"),),
    "scholarship-level-scope": (
        ("app.adapters.scholarship.web_scholarships", "SCHOLARSHIP_LEVEL_SCOPE"),
    ),
    "nav-link-level-guard": (
        ("app.adapters.scholarship.web_scholarships", "NAV_LINK_LEVEL_GUARD"),
    ),
    "front-page-not-programme": (
        ("app.adapters.discovery.live_discovery", "FRONT_PAGE_NOT_PROGRAMME"),
    ),
    "quoted-href-guard": (("app.adapters.scholarship.web_scholarships", "QUOTED_HREF_GUARD"),),
    "award-coordinated-degree-scope": (
        ("app.adapters.scholarship.web_scholarships", "AWARD_COORDINATED_DEGREE_SCOPE"),
    ),
    "fee-subpage-exclusion": (("app.adapters.discovery.live_discovery", "FEE_SUBPAGE_EXCLUSION"),),
    "local-twin-on-identity-refusal": (
        ("app.adapters.discovery.live_discovery", "LOCAL_TWIN_ON_IDENTITY_REFUSAL"),
    ),
    "case-read-ledger": (("app.adapters.fetching", "CASE_READ_LEDGER"),),
    "case-time-budget": (("app.adapters.fetching", "CASE_TIME_BUDGET"),),
    "redirect-memory": (("app.adapters.fetching", "REDIRECT_MEMORY"),),
    "url-variant-dedupe": (("app.adapters.fetching", "URL_VARIANT_DEDUPE"),),
    "topic-faculty-scope": (("app.adapters.requirements.web_requirements", "TOPIC_FACULTY_SCOPE"),),
    "topic-programme-scope": (
        ("app.adapters.requirements.web_requirements", "TOPIC_PROGRAMME_SCOPE"),
    ),
    "discovery-query-reserve": (("app.adapters.search.intent", "DISCOVERY_QUERY_RESERVE"),),
    "programme-page-guard": (("app.adapters.page_classifier", "PROGRAMME_PAGE_GUARD"),),
    "catalog-heading-scope": (("app.adapters.page_classifier", "CATALOG_HEADING_SCOPE"),),
    "funding-identity-scope": (("app.adapters.page_classifier", "FUNDING_IDENTITY_SCOPE"),),
    "campus-guard": (("app.adapters.discovery.live_discovery", "CAMPUS_GUARD"),),
    "localized-identity": (("app.adapters.discovery.live_discovery", "LOCALIZED_IDENTITY"),),
    "sitemap-trim": (("app.adapters.discovery.live_discovery", "SITEMAP_TRIM"),),
    "deadline-award-condition": (("app.adapters.extraction", "DEADLINE_AWARD_CONDITION"),),
    "canonical-http-https": (("app.adapters.discovery.live_discovery", "CANONICAL_HTTP_HTTPS"),),
    "fee-year-columns": (("app.adapters.extraction", "FEE_YEAR_COLUMNS"),),
    "search-rate-limit-retry": (("app.adapters.search.exa_mcp", "RATE_LIMIT_RETRY"),),
    "document-leads": (("app.adapters.documents.web_documents", "DOCUMENT_LEADS"),),
    "document-rules-v2": (
        ("app.adapters.documents.web_documents", "DOCUMENT_RULES_V2"),
        ("app.adapters.document_ir", "FORM_LABEL_HEADINGS"),
    ),
    "tuition-row-year": (("app.adapters.extraction", "TUITION_ROW_YEAR"),),
    "navigation-field-leads": (
        ("app.adapters.discovery.live_discovery", "NAVIGATION_FIELD_LEADS"),
    ),
    "topic-search": (("app.adapters.requirements.web_requirements", "TOPIC_SEARCH"),),
    # Default-on with no on-form (IM-1, unmeasured in the ledger).
    "integrated-masters-level": (
        ("app.adapters.discovery.live_discovery", "INTEGRATED_MASTERS_LEVEL"),
    ),
    # Default-off rules entered ahead of a default-on decision (replay plan
    # 2026-10-19 §5): the off arm is ready when the rule turns on.
    "abstain-on-unreadable-entry": (
        ("app.adapters.discovery.live_discovery", "ABSTAIN_ON_UNREADABLE_ENTRY"),
    ),
    # On by default since the rp-bundle2 replay of 2026-10-19 (CH-1, SP-1, CQ-1).
    "confirm-head-identity": (
        ("app.adapters.discovery.live_discovery", "CONFIRM_REQUIRES_HEAD_IDENTITY"),
    ),
    "reject-subpage-head": (
        ("app.adapters.discovery.live_discovery", "CONFIRM_REJECTS_SUBPAGE_HEAD"),
    ),
    "reject-combination-head": (
        ("app.adapters.discovery.live_discovery", "CONFIRM_REJECTS_COMBINATION_HEAD"),
    ),
    # On by default since replay rp-cl2 of 2026-10-19 (CL-2).
    "classify-head-and-slug-identity": (
        ("app.adapters.page_classifier", "CLASSIFY_HEAD_AND_SLUG_IDENTITY"),
    ),
    # On by default since the CC-1 replay of 2026-10-19.
    "course-lead-guard": (("app.adapters.discovery.live_discovery", "COURSE_LEAD_GUARD"),),
    # On by default since replay rp-qt1c of 2026-10-19 (QT-1).
    "read-qualifier-twin": (
        ("app.adapters.discovery.live_discovery", "CONFIRM_READS_QUALIFIER_TWIN"),
    ),
    # Default-off (MISS_STAGES_2026-10-19 §3, candidate 6, LL-1).
    "listing-follows-local-aliases": (
        ("app.adapters.discovery.live_discovery", "LISTING_FOLLOWS_LOCAL_ALIASES"),
    ),
}
#: The ``NEGATABLE_RULES`` stems that are still off by default: their off-form
#: is ready for the day a replay turns them on, and changes nothing until then.
DEFAULT_OFF_NEGATABLE: frozenset[str] = frozenset({"listing-follows-local-aliases"})


def _negation_dest(stem: str) -> str:
    return "no_" + stem.replace("-", "_")


def add_rule_negations(parser: argparse.ArgumentParser) -> None:
    """Add ``--no-<stem>`` for every ``NEGATABLE_RULES`` entry."""
    for stem, targets in NEGATABLE_RULES.items():
        parser.add_argument(
            f"--no-{stem}",
            action="store_true",
            dest=_negation_dest(stem),
            help="off arm: set " + ", ".join(name for _, name in targets) + " False",
        )


def check_rule_negations(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """A rule cannot be switched on and off in the same capture."""
    for stem in NEGATABLE_RULES:
        if getattr(args, _negation_dest(stem)) and getattr(args, stem.replace("-", "_"), False):
            parser.error(f"--{stem} and --no-{stem} cannot be combined")


def rule_negation_arguments(args: argparse.Namespace) -> list[str]:
    """The ``--no-<stem>`` flags set on ``args``, as the parent forwards them."""
    return [f"--no-{stem}" for stem in NEGATABLE_RULES if getattr(args, _negation_dest(stem))]


def apply_rule_negations(args: argparse.Namespace) -> None:
    """In the child: set each negated rule's module constants False."""
    import importlib

    for stem, targets in NEGATABLE_RULES.items():
        if getattr(args, _negation_dest(stem)):
            for module, name in targets:
                setattr(importlib.import_module(module), name, False)


def recorded_store_config(store: Path | None) -> dict[str, Any]:
    """The capture config's record of the replayed store: file, schema, digest, size, sources.

    The schema tells the scorecard a v2 replay (titles, snippets and the topic
    and scholarship searches recorded) from a URL-only v1 one (W4).
    """
    if store is None:
        return {}
    document = json.loads(store.read_text(encoding="utf-8"))
    sources = (document.get("provenance") or {}).get("sources") or []
    return {
        "recorded_search_store": {
            "file": store.name,
            "schema": str(document.get("schema") or ""),
            "sha256": hashlib.sha256(store.read_bytes()).hexdigest(),
            "entries": len(document.get("entries") or []),
            "source_runs": [str(s.get("run_id")) for s in sources if isinstance(s, dict)],
        }
    }


def cap_config(
    ledger: SearchQueryLedger,
    planned: int,
    planned_cases: Sequence[str],
    case_index: int,
    batch_stop_reason: str | None,
) -> dict[str, Any]:
    """Ticket 02: the run's query ledger as this capture saw it, for ``capture.json``."""
    stopped = batch_stop_reason == RUN_CAP_STOP_REASON
    return {
        **ledger.state(),
        "planned_this_capture": planned,
        "ledger": ledger.path.name,
        "stop_reason": RUN_CAP_STOP_REASON if stopped else None,
        "remaining_case_ids": list(planned_cases[case_index + 1 :]) if stopped else [],
    }


def entry_path_config(args: argparse.Namespace) -> dict[str, str]:
    """G-06: the capture's ``entry_path`` when an arm changes it (absent = default)."""
    if args.no_registry_seeds:
        return {"entry_path": "no_seed"}
    if args.through_identity_gate:
        return {"entry_path": "identity_gate"}
    return {}


def main() -> None:
    from app.adapters.discovery import live_discovery
    from app.adapters.scholarship import web_scholarships
    from app.adapters.search import KNOWN_SEARCH_PROVIDERS
    from app.config import Settings, get_settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", choices=[*COHORT, *HELDOUT, *DEV2, *PROXY_DOMAINS])
    parser.add_argument("--seconds-per-case", type=int, default=120)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument(
        "--strict-expert-budget",
        action="store_true",
        help="evaluation only: cold 60 get / 6 provider query / 120 active second caps; stop batch on 429",
    )
    parser.add_argument(
        "--finalization-reserve-ms",
        type=int,
        default=None,
        help="strict evaluation only: reserve case-clock milliseconds for cancellation/output cleanup (V4:1000)",
    )
    parser.add_argument(
        "--search-provider",
        choices=sorted(KNOWN_SEARCH_PROVIDERS),
        help="search provider for this capture (default: configured provider)",
    )
    parser.add_argument(
        "--recorded-store",
        type=Path,
        default=None,
        metavar="PATH",
        help="with --search-provider recorded: the recorded-search store to replay "
        "(default: UNIMATCH_RECORDED_SEARCH_STORE, else data/recorded_search.base3.json); "
        "a query it has no answer for returns nothing and is counted as a miss",
    )
    parser.add_argument(
        "--max-search-queries",
        type=int,
        default=None,
        metavar="N",
        help="the run's hard cap on provider queries, required for every provider but none, "
        "fake and recorded; the run refuses to start when 6 per case exceeds what it leaves, "
        "and the (N+1)th query is refused locally with no request sent",
    )
    parser.add_argument(
        "--search-ledger",
        type=Path,
        default=None,
        metavar="PATH",
        help="with --max-search-queries: the query ledger every capture of one run shares "
        "(default: search_ledger.json in this capture's directory)",
    )
    parser.add_argument(
        "--trust-env-proxy",
        action="store_true",
        help="agent sandbox only: the production Fetcher sends through the environment's "
        "HTTPS_PROXY (Fetcher(trust_env_proxy=True)); robots and TLS checks unchanged",
    )
    parser.add_argument(
        "--search-first",
        action="store_true",
        help="experiment: search before the navigation fallback (default off)",
    )
    parser.add_argument(
        "--skip-refused-hosts",
        action="store_true",
        help="experiment ER-04: search candidates on hosts that refused this run take no slot",
    )
    parser.add_argument(
        "--reject-archive-hosts",
        action="store_true",
        help="experiment ER-06: mirror/repository/journal/archive hosts are not programme pages",
    )
    parser.add_argument(
        "--admission-lexicon",
        action="store_true",
        help="experiment ER-05: links naming undergraduate admission become candidates",
    )
    parser.add_argument(
        "--applicant-academic-year",
        action="store_true",
        help="plan rule AY-1: read fee and requirement tables for the applicant's academic "
        "year (fall 2027 -> 2027/28) instead of the server default",
    )
    parser.add_argument(
        "--shared-query-budget",
        action="store_true",
        help="plan rule BL-1: every stage's provider queries count against one budget of six "
        "per institution; topic search leaves one for the scholarship search",
    )
    parser.add_argument(
        "--deadline-v2",
        action="store_true",
        help="plan rule DL-2: abbreviated months, date-first 'Applications due' rows, and a "
        "window table's catch-all qualification row",
    )
    parser.add_argument(
        "--euro-grouping",
        action="store_true",
        help="plan rule EU-1: continental euro amounts ('€ 20.563', '€ 18.750,00') read a "
        "dot as a thousands separator and a comma as the cents mark",
    )
    parser.add_argument(
        "--with-documents",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="D7: after the decision stage, approve every row and run the documents stage "
        "on its own clock of SECONDS; the decision stage's budget is untouched",
    )
    parser.add_argument(
        "--search-429-retry",
        action="store_true",
        help="plan rule SR-2: one retry, after 6 s, when the keyless Exa MCP answers 429",
    )
    parser.add_argument(
        "--search-pacing",
        action="store_true",
        help="plan rule SP-1: at least 1.5 s between two Exa MCP queries",
    )
    parser.add_argument(
        "--topic-search-continue",
        action="store_true",
        help="plan rule TS-2: a failed topic query no longer ends topic search",
    )
    parser.add_argument(
        "--hop-root-deadline",
        action="store_true",
        help="plan rule HP-1: a hop entry root gets an 8 s deadline",
    )
    parser.add_argument(
        "--canonical-http-https",
        action="store_true",
        help="plan rule CU-1: canonical_url treats http and https of one page as one URL",
    )
    parser.add_argument(
        "--route-leads",
        action="store_true",
        help="plan rule RL-1: follow official deadline and foreign-diploma route links "
        "below the admissions page",
    )
    parser.add_argument(
        "--english-readers-v2",
        action="store_true",
        help="plan change EN-2/TF-2: English tables attributed by column header or table "
        "label, the programme's row picked by its programme page (else abstain), "
        "Standard/Higher levels, and a TOEFL total past dates and section scores",
    )
    parser.add_argument(
        "--local-language-queries",
        action="store_true",
        help="plan v3 rule R5 (LQ-1, stage 3): for an institution whose country publishes "
        "in a language other than English, a local_language query family "
        '(site:<domain> "<ontology alias>" <R1 bachelor word>, Serper hl/gl of that '
        "language and country) takes the third first-pass slot; programmes moves to the "
        "reserve and admissions is dropped, so six families stay six",
    )
    parser.add_argument(
        "--localized-page-identity",
        action="store_true",
        help="plan v3 rule R1 (LI-2, stage 4(a)): bachelor and master degree words in page "
        "text for every language in languages.json (earliest wins; fr licence only under "
        '<html lang="fr">), LX-1\'s degree words and aliases, dictionary-grade localized '
        "computer science aliases, local related-not-equivalent forms refused by name, and a "
        "refused English page's twin in the institution's language read once",
    )
    parser.add_argument(
        "--provider-lead-floor",
        action="store_true",
        help="plan rule PL-1: links followed from a refused search result get their own "
        "identity-recovery checks instead of the provider results' ones, and past the "
        "discovery deadline the first search pass may read until it has made the SB-1b "
        "reserve's number of recovery reads in all",
    )
    parser.add_argument(
        "--retrieval-rank-v2",
        action="store_true",
        help="plan v3 change RK-2 (loss stages v3 #1): a URL returned by more query families "
        "of one pass ranks higher (+1 per further family, cap 3); while R5 has a language for "
        "the institution, R1's local degree words and R4's local listing roots count as "
        "degree and catalogue signals, and a local master's slug is another level; identity "
        "recovery's first pass reads each family's top result ahead of the ranked order "
        "(at most 2 ahead) before a confirmation can stop it",
    )
    parser.add_argument(
        "--subject-title-shapes",
        action="store_true",
        help="plan v3 rule R2 (ST-1, stage 4(b)): only a programme title's subject head is "
        "tested (the part before a ':' or spaced dash subtitle), a bracketed place, form words "
        "and award names are filler, and the field joined to a related field ('Business ...', "
        "'Mathematics and ...', '... and Economics') is refused as a related programme and "
        "recorded as related_programmes on the trace; '<field> and Engineering' is the field",
    )
    parser.add_argument(
        "--sitemap-keep-evidence-sum",
        action="store_true",
        help="plan v3 rule R3 (SK-1, stage 2(a)): the sitemap stage keeps a URL with no "
        "structural programme word when its slug names the subject and the level (or the "
        "subject as an exact field slug), at most 10 of the 40 programme slots and only those "
        "the structural picks leave free",
    )
    parser.add_argument(
        "--site-identity-v2",
        action="store_true",
        help="plan v3 rule R6 (IG-1, stage 0): production's site-identity gate also "
        "establishes a site on the seed row's own official_site host after redirects, a "
        "native-script name under the country's <html lang>, or the English name on the "
        "homepage's English alternate (one read); never on a third-party host, a parked "
        "domain or a homepage naming another institution (measure on --through-identity-gate)",
    )
    parser.add_argument(
        "--coordinated-degree-scope",
        action="store_true",
        help="plan rule SC-2: on a requirements page a degree word coordinated with a scoped "
        "one ('an undergraduate and postgraduate course') is read too, so a page naming two "
        "levels is silent on its degree instead of scoped to the second one alone",
    )
    parser.add_argument(
        "--local-catalogue-entry",
        action="store_true",
        help="plan v3 rule R4 (LC-1, stages 1, 2(b), 2(c)): a homepage link whose label is a "
        "study-section or catalogue word in a language of the institution's country is a "
        "catalogue lead whatever its URL says (at most two hops: homepage -> section -> "
        "catalogue; a page reached by its label is classified and dropped when it lists no "
        "programmes), local listing words are URL signals (/carreras/, /formation/, "
        "/studier/program/, /opleidingen/n/...), and a catalogue host on the same registrable "
        "domain has its own sitemap read (at most 3 documents, inside the sitemap allowance)",
    )
    parser.add_argument(
        "--award-route",
        action="store_true",
        help="plan rule AR-1: scholarships from the programme page's official funding links "
        "first, an index budget by shape, a filtered award query, and existence and "
        "international applicability from eligibility sentences only",
    )
    parser.add_argument(
        "--scholarship-index-query",
        action="store_true",
        help="plan rule SQ-1: when the funding walk found no award and no index linked one, "
        "one scholarship-index query ('<institution> scholarships for international "
        "bachelor's students') before the award query, inside the shared 6-query budget "
        "only; its top official result is read as the funding index",
    )
    parser.add_argument(
        "--scholarship-level-scope",
        action="store_true",
        help="plan rule SL-1: for a bachelor request, no funding page whose URL names another "
        "level (PhD, postgraduate, master's, studentship) or funding outside study/admissions "
        "paths is read, and deadline/route links get the URL degree-level guard",
    )
    parser.add_argument(
        "--award-page-evidence",
        action="store_true",
        help="plan rule AP-1: a page whose heading is a proper award name is that award "
        "however many hub links it carries, an index's own award-name sections are read as "
        "awards (existence and international applicability from their eligibility sentences "
        "only), the depth-0 index read is not charged to the index budget, and one "
        "navigation 'Scholarships' link of the programme/admissions page is followed",
    )
    parser.add_argument(
        "--nav-link-level-guard",
        action="store_true",
        help="plan rule AP-1c: AP-1's navigation 'Scholarships' link is never one whose URL "
        "names another degree level than the request's",
    )
    parser.add_argument(
        "--pdf-evidence-readers",
        action="store_true",
        help="plan rule PD-1: a fetched PDF is read as pages, classified by its own title and "
        "headings, read by the same deterministic readers, and each claim names its page",
    )
    parser.add_argument(
        "--cache-buster-canonical",
        action="store_true",
        help="plan rule PD-2: a purely numeric cache-buster query parameter (_t, v, ts, ... or a "
        "bare-number query) is dropped from an official-domain link before it is requested",
    )
    parser.add_argument(
        "--front-page-not-programme",
        action="store_true",
        help="plan rule FP-1: identity recovery never confirms a host's front page (path /, "
        "no query) as the programme page; it is refused like a listing and its matching "
        "links are read next",
    )
    parser.add_argument(
        "--exact-field-lead-first",
        action="store_true",
        help="plan rule EF-1: in a single-field run, identity recovery reads the search leads "
        "whose last path segment names the requested field and nothing else first (those "
        "more query families returned first); the predicate and the stop are unchanged",
    )
    parser.add_argument(
        "--abstain-on-unreadable-entry",
        action="store_true",
        help="replay plan UA-1: when no read of the institution's own entry points succeeded "
        "(robots.txt, sitemap probes, homepage, navigation fallback), identity recovery confirms "
        "no search lead as the programme page; an accepted lead is kept as unresolved_access",
    )
    parser.add_argument(
        "--quoted-href-guard",
        action="store_true",
        help="plan rule QH-1: a funding index's award link whose href opens with a quote or "
        "holds a double quote (broken markup) is not followed",
    )
    parser.add_argument(
        "--award-name-qualifier",
        action="store_true",
        help="plan rule AN-1: a proper award name may carry one capitalised 'for/at/in/of ...' "
        "qualifier after its award noun (no population or degree word in it)",
    )
    parser.add_argument(
        "--award-coordinated-degree-scope",
        action="store_true",
        help="plan rule AN-1b: an award page's and an award section's scope reads degree words "
        "coordinated in one phrase ('Bachelor's or Master's programme'), so naming two levels "
        "is silent on the degree and the section's degree falls back to the page's own",
    )
    parser.add_argument(
        "--question-routing",
        action="store_true",
        help="plan rule QR-1: question-routed evidence: programme/admissions links that name "
        "English, fees or deadlines first, one topic query per still-unanswered question, each "
        "page read for the question it was reached for, fee pages to the cost adapter, "
        "other-level scopes withheld, and all of it without a confirmed programme page",
    )
    parser.add_argument(
        "--question-page-order",
        action="store_true",
        help="plan rule QP-1: after the link sources, the next question page read is one for "
        "the unanswered question with the fewest pages read (one page per unanswered core "
        "question first); pages for answered questions keep their order after those",
    )
    parser.add_argument(
        "--parent-degree-link",
        action="store_true",
        help="plan rule QR-2: the confirmed programme page's link to its parent degree page "
        "('a major in the Bachelor of Science (BSc)') is read for the deadline and English "
        "and handed to the cost adapter as a fees page",
    )
    parser.add_argument(
        "--field-slug-scoring",
        action="store_true",
        help="plan rule SR-1: a programme URL earns the field bonus only for the field phrase "
        "or a strong alias as whole slug words, and fee/tuition pages are never programme pages",
    )
    parser.add_argument(
        "--fee-subpage-exclusion",
        action="store_true",
        help="plan v3 change #2(b): a URL with a fee, tuition, cost or scholarship segment or an "
        "entry-requirements segment (entry-requirements---2027, standard-requirement) is never a "
        "programme page or catalogue candidate, whatever SR-1 and R3 say",
    )
    parser.add_argument(
        "--local-twin-on-identity-refusal",
        action="store_true",
        help="plan v3 change #2(a): R1 reads a refused English page's twin in the "
        "institution's language only when the page was refused on its subject or degree "
        "level, not when it reads as another kind of page",
    )
    parser.add_argument(
        "--reject-subpage-head",
        action="store_true",
        help="plan rule SP-1: a page whose head (first h1 or the title's first part) names "
        "one study year or a process of a programme (application, admission, enrolment, "
        "fees, deadlines) before any programme title of its own is refused as a sub-page, "
        "and a lead whose path sits above it in the same candidate set is read next",
    )
    parser.add_argument(
        "--confirm-head-identity",
        action="store_true",
        help="plan rule CH-1: a programme page is confirmed only when its head (<title> or "
        "first h1) names the requested subject, the level is named in the head, the URL's "
        "degree slug or a labelled field, and the head names no organisational unit without a "
        "degree; identity recovery's listing acceptance asks the same",
    )
    parser.add_argument(
        "--reject-combination-head",
        action="store_true",
        help="plan rule CQ-1: a programme page whose head (first h1 or the title's first part) "
        "names a field combination (joint honours, JH, double/dual degree, second major, "
        "combined, a major/minor pair, or 'with'/'and' another field that is no alias of the "
        "requested subject) is refused as a related programme",
    )
    parser.add_argument(
        "--classify-head-and-slug-identity",
        action="store_true",
        help="plan rule CL-2: a page that reads unknown (no decisive signals) or irrelevant only "
        "on a heading below its own head is a programme page when its head (first h1 or the "
        "title's first part) names a field alias, the head or the URL's degree slug names one "
        "level, and it has no listing structure; never while CH-1 is off",
    )
    parser.add_argument(
        "--course-lead-guard",
        action="store_true",
        help="plan rule CC-1: a catalogue or listing link whose label or last slug starts with "
        "a course code (2-4 letters directly followed by 3-4 digits), or whose path has a "
        "course/courses segment followed by a course id or 'view', is never a programme lead",
    )
    parser.add_argument(
        "--read-qualifier-twin",
        action="store_true",
        help="plan rule QT-1: after identity recovery confirms a page, read once its qualifier "
        "twin among the unread leads (same host and parent path; the slug minus exactly one "
        "token, or one degree slug of the requested level swapped for another) before SB-1 "
        "stops; the twin is judged like any lead",
    )
    parser.add_argument(
        "--listing-follows-local-aliases",
        action="store_true",
        help="plan rule LL-1: identity recovery's listing follow-up also follows a link whose "
        "own heading (a card's name) matches the field through the ontology's aliases, and "
        "follows the links of a refused page whose head names only the requested level",
    )
    parser.add_argument(
        "--alias-aware-program-match",
        action="store_true",
        help="plan v3 change #3: verify's programme.exists match accepts a page whose subject "
        "names the requested field or one of its strong/localized aliases by discovery's own "
        "field predicate (so 'Informatics' is computer science, 'Business Informatics' is not)",
    )
    parser.add_argument(
        "--guessed-url-stall-exempt",
        action="store_true",
        help="plan rule HS-1: a timeout on a guessed URL (a conventional sitemap location) "
        "skips only that URL instead of stalling its host, and a guess waits at most 6 s",
    )
    parser.add_argument(
        "--case-read-ledger",
        action="store_true",
        help="plan rule RL-1 (read ledger, not --route-leads): a per-institution ledger "
        "charged per wire request, hard cap 60, 16 held for verify, refusals in the trace; "
        "the page cap refuses reads instead of ending the case",
    )
    parser.add_argument(
        "--case-time-budget",
        action="store_true",
        help="plan rule TB-1: a per-institution case clock shared by discovery, verify, costs "
        "and funding; a read predicted to leave less than its kind's floor is not started, "
        "Crawl-delay is waited in full or the read is refused, every read ends by 110 s",
    )
    parser.add_argument(
        "--redirect-memory",
        action="store_true",
        help="plan rule RS-1: a URL whose redirect chain reached a page is read from that "
        "final URL for the rest of the run, and the page is cached under it too",
    )
    parser.add_argument(
        "--url-variant-dedupe",
        action="store_true",
        help="plan rule RS-2: trailing-slash and http/https variants of a URL on one host "
        "share one cache key",
    )
    parser.add_argument(
        "--topic-faculty-scope",
        action="store_true",
        help="plan rule FS-1: a page reached by topic search (or a lead from one) that names "
        "another faculty than the programme's yields no requirement claims; on a page listing "
        "several faculties, IELTS is read only from the block naming the programme or its faculty",
    )
    parser.add_argument(
        "--topic-programme-scope",
        action="store_true",
        help="plan rule FS-2: a topic-search page that is another programme's own page "
        "claims no requirement for the requested programme",
    )
    parser.add_argument(
        "--hub-leads",
        action="store_true",
        help="plan rule HL-1: follow language, route, deadline, fee and scholarship links "
        "from every official page read, accepted or rejected, never naming another degree "
        "level; a fee or scholarship link fills a missing cost or scholarship page",
    )
    parser.add_argument(
        "--service-page-priority",
        action="store_true",
        help="plan rule UC-1: a URL whose last segment is a service word (fees, how-to-apply, "
        "scholarships, ...) is that service page even under /undergraduate/, and admissions, "
        "cost and scholarship pages naming another degree level are never selected",
    )
    parser.add_argument(
        "--catalog-heading-scope",
        action="store_true",
        help="plan rule CL-1: catalogue words are matched on the page's own h1 and title "
        "separately, not on every heading joined",
    )
    parser.add_argument(
        "--lexicon-v2",
        action="store_true",
        help="plan rule LX-1: B.Tech, licenciatura and local bachelor compounds are degree "
        "words, scholarship words count only on the page's h1 or title, localized computer "
        "science aliases (informatikk, datalogi, ...) and local publication paths and the "
        "lirias repository host for PG-1",
    )
    parser.add_argument(
        "--funding-identity-scope",
        action="store_true",
        help="plan rule FI-1: scholarship words count only on the page's h1 or title, "
        "not on every heading (the funding-gate part of LX-1 on its own)",
    )
    parser.add_argument(
        "--campus-guard",
        action="store_true",
        help="plan rule CG-1: a programme page whose title or URL names a branch campus "
        "abroad (Bengaluru, Malaysia campus, Dubai, ...) is not confirmed; a domestic "
        "second campus is",
    )
    parser.add_argument(
        "--discovery-query-reserve",
        action="store_true",
        help="plan rule QB-1: programme discovery sends three query families first and "
        "the other three only when no programme page is confirmed, leaving the unsent "
        "queries for topic and award search",
    )
    parser.add_argument(
        "--admissions-host-from-homepage",
        action="store_true",
        help="plan rule DI-1: one other registrable domain the homepage's admissions "
        "navigation links to is official for that institution for the run",
    )
    parser.add_argument(
        "--programme-page-guard",
        action="store_true",
        help="plan rule PG-1: search drops research-output and archive URLs, a "
        "publication or host root needs programme structure to be a programme page, "
        "and unread search leads are never promoted to programme pages",
    )
    parser.add_argument(
        "--localized-identity",
        action="store_true",
        help="plan rule LI-1: localized ontology aliases and certain local degree words in "
        "discovery, and one read of a local-language programme page's hreflang English twin",
    )
    parser.add_argument(
        "--sitemap-child-priority",
        action="store_true",
        help="plan rule SM-1: stop probing conventional sitemap locations after one "
        "answers, and read an index's programme sitemaps before its news sitemaps",
    )
    parser.add_argument(
        "--sitemap-trim",
        action="store_true",
        help="plan rule SM-2: stop probing conventional sitemap locations after one answers, "
        "and read no sitemap document named for news, events, galleries, media or press",
    )
    parser.add_argument(
        "--cost-aware-search-order",
        action="store_true",
        help=(
            "plan rule SO-1: search before navigation when sitemaps found no programme, "
            "and on a slow host (crawl delay or median read >= 5 s) also before confirm, "
            "with three sitemap documents and no walker"
        ),
    )
    parser.add_argument(
        "--stage-budgets",
        action="store_true",
        help=(
            "plan rule SB-1: discovery gets a 55 s deadline and 28 reads, stops once a "
            "programme page is confirmed, and searches right after the first sitemap "
            "document on a slow host; per-stage seconds and reads go into the trace"
        ),
    )
    parser.add_argument(
        "--alias-queries",
        action="store_true",
        help=(
            "plan rule QA-1: operator queries name the field as an OR-group of its strong "
            "ontology aliases, and Serper sends a single site: operator"
        ),
    )
    parser.add_argument(
        "--deadline-window-scope",
        action="store_true",
        help="plan rule EX-2: a study-period date range is not an application window, and "
        "a page with one section per intake is read for the requested intake only",
    )
    parser.add_argument(
        "--intake-section-deadline",
        action="store_true",
        help="plan rule DL-5 (absorbs EX-2): the deadline and the tuition are read from the "
        "requested intake's own section (Autumn 2027, Semester One 2027) or its row of a "
        "table of intakes, 'closing date(s)' labels a deadline, and a study period is never "
        "an application window",
    )
    parser.add_argument(
        "--international-round-deadline",
        action="store_true",
        help="plan rule DL-6: for an international applicant, the degree level's bare "
        "'Application' / 'How to apply' page is read for the international admission round, "
        "whose 'application period ... close <date>' window is the deadline (population "
        "international) only on a page naming that round; when the site names both an "
        "international and a national/EU round, no deadline naming no population is claimed",
    )
    parser.add_argument(
        "--deadline-award-condition",
        action="store_true",
        help="plan rule DL-3: a deadline its own sentence makes conditional on an award "
        "or scholarship application is not the admission deadline",
    )
    parser.add_argument(
        "--fee-year-columns",
        action="store_true",
        help="plan rule DF-1: fee tables with academic years as columns and named "
        "tariffs (statutory / institutional rate) as rows",
    )
    parser.add_argument(
        "--fee-readers-v2",
        action="store_true",
        help="plan rule FE-2: fee-status rows (Overseas / International / non-EU fee, Home "
        "fee) on a fee page for the requested programme or level, and the requested "
        "programme's row of a per-course fee table's international column",
    )
    parser.add_argument(
        "--search-rate-limit-retry",
        action="store_true",
        help="plan rule SR-1: one retry, after a short pause, when the keyless Exa MCP "
        "reports its rate limit",
    )
    parser.add_argument(
        "--document-leads",
        action="store_true",
        help="plan rule DOC-3: the documents stage also reads the institution's own "
        "application-documents page, at most two links from the programme page",
    )
    parser.add_argument(
        "--document-rules-v2",
        action="store_true",
        help="plan rule DOC-2: gpt-6-astra's PR #41 document rules (measured only with "
        "--with-documents)",
    )
    parser.add_argument(
        "--tuition-row-year",
        action="store_true",
        help="plan rule TY-1: a fee table row that prints its academic year records it "
        "in the claim's scope",
    )
    parser.add_argument(
        "--walker-subject-cap",
        action="store_true",
        help="experiment ER-10: a catalogue walk reads at most three leads that name none "
        "of the applicant's subjects, lists first",
    )
    parser.add_argument(
        "--navigation-field-leads",
        action="store_true",
        help="experiment ER-09: the navigation fallback keeps a programme lead only when "
        "its URL or link text names the applicant's subject",
    )
    parser.add_argument(
        "--topic-search",
        action="store_true",
        help="experiment ER-08: one public query per topic (English, fees, deadline) finds "
        "the official page that publishes it",
    )
    parser.add_argument(
        "--navigation-slot",
        action="store_true",
        help="experiment ER-07: one programme-page slot is kept for the navigation hop",
    )
    parser.add_argument(
        "--recover-search-candidates",
        action=argparse.BooleanOptionalAction,
        default=live_discovery.RECOVER_SEARCH_CANDIDATES,
        help="experiment: verify search identities and backfill rejected programme leads",
    )
    parser.add_argument(
        "--search-funding-fallback",
        action=argparse.BooleanOptionalAction,
        default=web_scholarships.SEARCH_FUNDING_FALLBACK,
        help="experiment: search official awards when index walking yields no scholarships",
    )
    parser.add_argument(
        "--target-award-search",
        action=argparse.BooleanOptionalAction,
        default=web_scholarships.TARGET_AWARD_SEARCH,
        help="experiment: target award policies instead of generic scholarship indices",
    )
    parser.add_argument(
        "--extra-bindings",
        action="append",
        type=Path,
        default=[],
        metavar="PATH",
        help="measurement M-1: also map claims with this identity-binding file (repeatable; "
        "loaded after the reviewed bindings, never overriding one)",
    )
    parser.add_argument(
        "--through-identity-gate",
        action="store_true",
        help="measurement v3-M3: a dev2/dev3 case's seed row goes through production's "
        "_identify_site instead of being handed a verified homepage; the scorecard reports "
        "identity established n/N",
    )
    parser.add_argument(
        "--knockout-gold",
        type=Path,
        default=None,
        metavar="DATASET",
        help="measurement G-07: the case's gold programme URLs in this development dataset "
        "(and their /, .html, ?lang= and declared hreflang twins) are answered with a counted "
        "synthetic 404 and never requested; a case without a programme label is a no-op",
    )
    parser.add_argument(
        "--no-registry-seeds",
        action="store_true",
        help="measurement G-06: a cohort case is captured from its registry row without the "
        "seeds (the no-seed path dev2-dev4 take); the capture records entry_path no_seed",
    )
    add_rule_negations(parser)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    check_rule_negations(parser, args)
    if args.no_registry_seeds and args.through_identity_gate:
        parser.error("--no-registry-seeds and --through-identity-gate are separate arms")
    if args.no_registry_seeds and args.case and args.case not in COHORT:
        parser.error("--no-registry-seeds applies to cohort cases only")
    if args.max_pages is None:
        args.max_pages = STRICT_MAX_FETCHER_CALLS if args.strict_expert_budget else 40
    if args.knockout_gold is not None and (
        not args.knockout_gold.is_file() or (args.case in HELDOUT)
    ):
        parser.error("--knockout-gold needs a development dataset file and a development case")
    if not 1 <= args.seconds_per_case <= 600 or not 1 <= args.max_pages <= 100:
        parser.error("Budget must be 1..600 seconds and 1..100 Fetcher.get calls per university")
    if args.strict_expert_budget and (
        args.seconds_per_case > STRICT_MAX_SECONDS or args.max_pages > STRICT_MAX_FETCHER_CALLS
    ):
        parser.error(
            "Strict expert budget cannot exceed 60 Fetcher.get calls and 120 active seconds"
        )
    if args.finalization_reserve_ms is not None:
        if not args.strict_expert_budget:
            parser.error("Finalization reserve requires --strict-expert-budget")
        if not 0 <= args.finalization_reserve_ms < args.seconds_per_case * 1000:
            parser.error("Finalization reserve must be 0..(full case clock minus 1) milliseconds")
    finalization_reserve_ms = args.finalization_reserve_ms or 0
    try:
        load_identities(args.extra_bindings)
    except (OSError, ValueError) as exc:
        parser.error(f"--extra-bindings: {exc}")
    recorded_store: Path | None = None
    if args.recorded_store is not None and args.search_provider != "recorded":
        parser.error("--recorded-store needs --search-provider recorded")
    if args.search_provider == "recorded":
        from app.adapters.search.recorded import RecordedSearchStore, RecordedStoreError

        recorded_store = resolve_recorded_store(args.recorded_store)
        try:
            RecordedSearchStore.from_file(recorded_store)
        except RecordedStoreError as exc:
            parser.error(f"--recorded-store: {exc}")
    settings = (
        Settings(search_provider=args.search_provider, recorded_search_store=recorded_store)
        if args.search_provider
        else Settings()
    )
    if args.search_provider or args.strict_expert_budget:
        try:
            settings._validate_search()
        except RuntimeError as exc:
            parser.error(str(exc))
    search_provider = settings.search_provider
    if args.strict_expert_budget and search_provider not in STRICT_PROVIDERS:
        parser.error("Strict expert budget requires configured exa or exa_mcp")
    print(f"search provider: {search_provider}", flush=True)
    cap = args.max_search_queries
    if cap is None and needs_cap(search_provider):
        parser.error(
            f"--search-provider {search_provider} sends queries that can spend an allowance or a "
            "paid key: pass --max-search-queries N, the run's hard cap (6 per case is planned)"
        )
    if cap is not None and cap < 1:
        parser.error("--max-search-queries must be a positive integer")
    if args.search_ledger is not None and cap is None:
        parser.error("--search-ledger needs --max-search-queries")
    planned_cases = [args.case] if args.case else list(COHORT)
    planned = planned_queries(len(planned_cases))
    search_ledger: SearchQueryLedger | None = None
    if cap is not None and (args.search_ledger is not None or args.child):
        if args.search_ledger is None:
            parser.error("--child with --max-search-queries needs the run's --search-ledger")
        try:
            search_ledger = SearchQueryLedger.open(args.search_ledger, cap)
            remaining = search_ledger.remaining()
        except SearchCapError as exc:
            parser.error(f"--search-ledger: {exc}")
    else:
        remaining = cap or 0
    if cap is not None and not args.child and planned > remaining:
        parser.error(
            f"the run plans {planned} provider queries ({len(planned_cases)} case(s) x 6) but "
            f"its cap leaves {remaining} of {cap}; no capture started"
        )
    if cap is not None:
        print(f"search query cap: {cap} (planned {planned}, left {remaining})", flush=True)
    if args.child:
        web_scholarships.SEARCH_FUNDING_FALLBACK = args.search_funding_fallback
        web_scholarships.TARGET_AWARD_SEARCH = args.target_award_search
        live_discovery.RECOVER_SEARCH_CANDIDATES = args.recover_search_candidates
        if args.search_first:
            from app.adapters.discovery import live_discovery

            live_discovery.SEARCH_BEFORE_NAVIGATION = True
        if args.skip_refused_hosts:
            from app.adapters.discovery import live_discovery

            live_discovery.SKIP_REFUSED_SEARCH_HOSTS = True
        if args.reject_archive_hosts:
            from app.adapters.search import retrieval

            retrieval.REJECT_ARCHIVE_HOSTS = True
        if args.admission_lexicon:
            from app.adapters.search import navigation

            navigation.ADMISSION_LEXICON = True
        if args.navigation_slot:
            from app.adapters.discovery import live_discovery

            live_discovery.NAVIGATION_SLOT = True
        if args.applicant_academic_year:
            from app.pipeline import runner as runner_module

            runner_module.APPLICANT_ACADEMIC_YEAR = True
        if args.shared_query_budget:
            from app.adapters.search import intent as intent_module

            intent_module.SHARED_QUERY_BUDGET = True
        if args.deadline_v2:
            from app.adapters import extraction as extraction_module

            extraction_module.DEADLINE_V2 = True
        if args.euro_grouping:
            from app.adapters import extraction as euro_module

            euro_module.EURO_GROUPING = True
        if args.with_documents:
            global DOCUMENT_SECONDS
            DOCUMENT_SECONDS = args.with_documents
        if args.search_429_retry or args.search_pacing:
            from app.adapters.search import exa_mcp as pacing_module

            if args.search_429_retry:
                pacing_module.RETRY_429_ONCE = True
            if args.search_pacing:
                pacing_module.MIN_QUERY_INTERVAL_SECONDS = 1.5
        if args.topic_search_continue:
            from app.adapters.requirements import web_requirements as ts2_module

            ts2_module.TOPIC_SEARCH_CONTINUE = True
        if args.route_leads:
            from app.adapters.requirements import web_requirements as rl1_module

            rl1_module.ROUTE_LEADS = True
        if args.english_readers_v2:
            from app.adapters import extraction as en2_module

            en2_module.ENGLISH_READERS_V2 = True
        if args.provider_lead_floor:
            from app.adapters.discovery import live_discovery as pl1_module

            pl1_module.PROVIDER_LEAD_FLOOR = True
        if args.retrieval_rank_v2:
            from app.adapters.search import retrieval as rk2_module

            rk2_module.RETRIEVAL_RANK_V2 = True
        if args.local_language_queries:
            from app.adapters.search import intent as r5_module

            r5_module.LOCAL_LANGUAGE_QUERIES = True
        if args.localized_page_identity:
            from app.adapters import page_classifier as r1_module

            r1_module.LOCALIZED_PAGE_IDENTITY = True
        if args.subject_title_shapes:
            from app.adapters.discovery import live_discovery as r2_module

            r2_module.SUBJECT_TITLE_SHAPES = True

        if args.sitemap_keep_evidence_sum:
            from app.adapters.discovery import live_discovery as r3_module

            r3_module.SITEMAP_KEEP_EVIDENCE_SUM = True
        if args.site_identity_v2:
            from app.catalogue import discovery as r6_module

            r6_module.SITE_IDENTITY_V2 = True
        if args.coordinated_degree_scope:
            from app.adapters.requirements import web_requirements as sc2_module

            sc2_module.COORDINATED_DEGREE_SCOPE = True
        if args.local_catalogue_entry:
            from app.adapters.discovery import live_discovery as r4_module

            r4_module.LOCAL_CATALOGUE_ENTRY = True
        if args.award_route:
            from app.adapters.scholarship import web_scholarships as ar1_module

            ar1_module.AWARD_ROUTE = True
        if args.scholarship_index_query:
            from app.adapters.scholarship import web_scholarships as sq1_module

            sq1_module.SCHOLARSHIP_INDEX_QUERY = True
        if args.scholarship_level_scope:
            from app.adapters.scholarship import web_scholarships as sl1_module

            sl1_module.SCHOLARSHIP_LEVEL_SCOPE = True
        if args.award_page_evidence:
            from app.adapters import page_classifier as ap1_module

            ap1_module.AWARD_PAGE_EVIDENCE = True
        if args.nav_link_level_guard:
            from app.adapters.scholarship import web_scholarships as ap1c_module

            ap1c_module.NAV_LINK_LEVEL_GUARD = True
        if args.pdf_evidence_readers:
            from app.adapters import pdf_evidence as pd1_module

            pd1_module.PDF_EVIDENCE_READERS = True
        if args.cache_buster_canonical:
            from app.adapters import url_canonical as pd2_module

            pd2_module.CACHE_BUSTER_CANONICAL = True
        if args.front_page_not_programme:
            from app.adapters.discovery import live_discovery as fp1_module

            fp1_module.FRONT_PAGE_NOT_PROGRAMME = True
        if args.exact_field_lead_first:
            from app.adapters.discovery import live_discovery as ef1_module

            ef1_module.EXACT_FIELD_LEAD_FIRST = True
        if args.abstain_on_unreadable_entry:
            from app.adapters.discovery import live_discovery as ua1_module

            ua1_module.ABSTAIN_ON_UNREADABLE_ENTRY = True
        if args.quoted_href_guard:
            from app.adapters.scholarship import web_scholarships as qh1_module

            qh1_module.QUOTED_HREF_GUARD = True
        if args.award_name_qualifier:
            from app.adapters import page_classifier as an1_module

            an1_module.AWARD_NAME_QUALIFIER = True
        if args.award_coordinated_degree_scope:
            from app.adapters.scholarship import web_scholarships as an1b_module

            an1b_module.AWARD_COORDINATED_DEGREE_SCOPE = True
        if args.question_routing:
            from app.adapters.requirements import web_requirements as qr1_module

            qr1_module.QUESTION_ROUTED_EVIDENCE = True
        if args.question_page_order:
            from app.adapters.requirements import web_requirements as qp1_module

            qp1_module.QUESTION_PAGE_ORDER = True
        if args.parent_degree_link:
            from app.adapters.requirements import web_requirements as qr2_module

            qr2_module.PARENT_DEGREE_LINK = True
        if args.field_slug_scoring:
            from app.adapters.discovery import live_discovery as sr1_module

            sr1_module.FIELD_SLUG_SCORING = True
        if args.fee_subpage_exclusion:
            from app.adapters.discovery import live_discovery as fx1_module

            fx1_module.FEE_SUBPAGE_EXCLUSION = True
        if args.local_twin_on_identity_refusal:
            from app.adapters.discovery import live_discovery as tw1_module

            tw1_module.LOCAL_TWIN_ON_IDENTITY_REFUSAL = True
        if args.confirm_head_identity:
            from app.adapters.discovery import live_discovery as ch1_module

            ch1_module.CONFIRM_REQUIRES_HEAD_IDENTITY = True
        if args.reject_subpage_head:
            from app.adapters.discovery import live_discovery as sp1_module

            sp1_module.CONFIRM_REJECTS_SUBPAGE_HEAD = True
        if args.reject_combination_head:
            from app.adapters.discovery import live_discovery as cq1_module

            cq1_module.CONFIRM_REJECTS_COMBINATION_HEAD = True
        if args.classify_head_and_slug_identity:
            from app.adapters import page_classifier as cl2_module

            cl2_module.CLASSIFY_HEAD_AND_SLUG_IDENTITY = True
        if args.course_lead_guard:
            from app.adapters.discovery import live_discovery as cc1_module

            cc1_module.COURSE_LEAD_GUARD = True
        if args.read_qualifier_twin:
            from app.adapters.discovery import live_discovery as qt1_module

            qt1_module.CONFIRM_READS_QUALIFIER_TWIN = True
        if args.listing_follows_local_aliases:
            from app.adapters.discovery import live_discovery as ll1_module

            ll1_module.LISTING_FOLLOWS_LOCAL_ALIASES = True
        if args.alias_aware_program_match:
            from app.adapters import matching as am1_module

            am1_module.ALIAS_AWARE_PROGRAM_MATCH = True
        if args.guessed_url_stall_exempt:
            from app.adapters import fetching as hs1_module

            hs1_module.GUESSED_URL_STALL_EXEMPT = True
        if args.case_read_ledger:
            from app.adapters import fetching as ledger_module

            ledger_module.CASE_READ_LEDGER = True
        if args.case_time_budget:
            from app.adapters import fetching as tb1_module

            tb1_module.CASE_TIME_BUDGET = True
        if args.redirect_memory:
            from app.adapters import fetching as rs1_module

            rs1_module.REDIRECT_MEMORY = True
        if args.url_variant_dedupe:
            from app.adapters import fetching as rs2_module

            rs2_module.URL_VARIANT_DEDUPE = True
        if args.topic_faculty_scope:
            from app.adapters.requirements import web_requirements as fs1_module

            fs1_module.TOPIC_FACULTY_SCOPE = True
        if args.topic_programme_scope:
            from app.adapters.requirements import web_requirements as fs2_module

            fs2_module.TOPIC_PROGRAMME_SCOPE = True
        if args.hub_leads:
            from app.adapters.requirements import web_requirements as hl1_module

            hl1_module.HUB_LEADS = True
        if args.service_page_priority:
            from app.adapters.discovery import live_discovery as uc1_module

            uc1_module.SERVICE_PAGE_PRIORITY = True
        if args.discovery_query_reserve:
            from app.adapters.search import intent as qb1_module

            qb1_module.DISCOVERY_QUERY_RESERVE = True
        if args.admissions_host_from_homepage:
            from app.adapters.discovery import live_discovery as di1_module

            di1_module.ADMISSIONS_HOST_FROM_HOMEPAGE = True
        if args.programme_page_guard:
            from app.adapters import page_classifier as pg1_module

            pg1_module.PROGRAMME_PAGE_GUARD = True
        if args.catalog_heading_scope:
            from app.adapters import page_classifier as cl1_module

            cl1_module.CATALOG_HEADING_SCOPE = True
        if args.lexicon_v2:
            from app.adapters import page_classifier as lx1_module

            lx1_module.LEXICON_V2 = True
        if args.funding_identity_scope:
            from app.adapters import page_classifier as fi1_module

            fi1_module.FUNDING_IDENTITY_SCOPE = True
        if args.campus_guard:
            from app.adapters.discovery import live_discovery as cg1_module

            cg1_module.CAMPUS_GUARD = True
        if args.deadline_window_scope:
            from app.adapters import extraction as ex2_module

            ex2_module.DEADLINE_WINDOW_SCOPE = True
        if args.intake_section_deadline:
            from app.adapters import extraction as dl5_module

            dl5_module.INTAKE_SECTION_DEADLINE = True
        if args.international_round_deadline:
            from app.adapters import extraction as dl6_module

            dl6_module.INTERNATIONAL_ROUND_DEADLINE = True
        if args.localized_identity:
            from app.adapters.discovery import live_discovery as li1_module

            li1_module.LOCALIZED_IDENTITY = True
        if args.sitemap_child_priority:
            from app.adapters.discovery import live_discovery as sm1_module

            sm1_module.SITEMAP_CHILD_PRIORITY = True
        if args.sitemap_trim:
            from app.adapters.discovery import live_discovery as sm2_module

            sm2_module.SITEMAP_TRIM = True
        if args.cost_aware_search_order:
            from app.adapters.discovery import live_discovery as so1_module

            so1_module.COST_AWARE_SEARCH_ORDER = True
        if args.stage_budgets:
            from app.adapters.discovery import live_discovery as sb1_module

            sb1_module.STAGE_BUDGETS = True
        if args.alias_queries:
            from app.adapters.search import intent as qa1_module

            qa1_module.ALIAS_QUERIES = True
        if args.deadline_award_condition:
            from app.adapters import extraction as dl3_module

            dl3_module.DEADLINE_AWARD_CONDITION = True
        if args.hop_root_deadline:
            from app.adapters.search import retrieval as hp1_module

            hp1_module.HOP_ROOT_DEADLINE = True
        if args.canonical_http_https:
            from app.adapters.discovery import live_discovery as cu1_module

            cu1_module.CANONICAL_HTTP_HTTPS = True
        if args.fee_year_columns:
            from app.adapters import extraction as fee_module

            fee_module.FEE_YEAR_COLUMNS = True
        if args.fee_readers_v2:
            from app.adapters import extraction as fe2_module

            fe2_module.FEE_READERS_V2 = True
        if args.search_rate_limit_retry:
            from app.adapters.search import exa_mcp as exa_mcp_module

            exa_mcp_module.RATE_LIMIT_RETRY = True
        if args.document_leads:
            from app.adapters.documents import web_documents as leads_module

            leads_module.DOCUMENT_LEADS = True
        if args.document_rules_v2:
            from app.adapters import document_ir
            from app.adapters.documents import web_documents

            web_documents.DOCUMENT_RULES_V2 = True
            document_ir.FORM_LABEL_HEADINGS = True
        if args.tuition_row_year:
            from app.adapters import extraction as year_module

            year_module.TUITION_ROW_YEAR = True
        if args.walker_subject_cap:
            from app.adapters.discovery import catalog_walker

            catalog_walker.WALKER_SIGNAL_LESS_CAP = 3
        if args.navigation_field_leads:
            from app.adapters.discovery import live_discovery as discovery_module

            discovery_module.NAVIGATION_FIELD_LEADS = True
        if args.topic_search:
            from app.adapters.requirements import web_requirements

            web_requirements.TOPIC_SEARCH = True
        apply_rule_negations(args)
        # A few seconds under the parent's timeout, so the child's own stop
        # comes first and writes what it has.
        soft = (
            args.seconds_per_case
            if args.strict_expert_budget
            else max(args.seconds_per_case - 5, 1)
        )
        # Apply the selection before the pipeline constructs Settings. Clearing
        # the cache also covers direct --child invocation in an existing process.
        child_configuration = {
            "UNIMATCH_SEARCH_PROVIDER": search_provider,
            **search_environment(search_provider, recorded_store),
        }
        if args.strict_expert_budget:
            child_configuration.update(
                UNIMATCH_ENABLE_BROWSER_TIER="false", UNIMATCH_RESPECT_ROBOTS="true"
            )
        with patch.dict(os.environ, child_configuration):
            get_settings.cache_clear()
            try:
                strict_arguments: dict[str, Any] = (
                    {"strict_expert_budget": True} if args.strict_expert_budget else {}
                )
                if args.finalization_reserve_ms is not None:
                    strict_arguments["finalization_reserve_ms"] = finalization_reserve_ms
                if args.extra_bindings:
                    strict_arguments["extra_bindings"] = args.extra_bindings
                if args.through_identity_gate:
                    strict_arguments["through_identity_gate"] = True
                if args.knockout_gold:
                    strict_arguments["knockout_gold"] = args.knockout_gold
                if args.no_registry_seeds:
                    strict_arguments["no_registry_seeds"] = True
                if args.trust_env_proxy:
                    strict_arguments["trust_env_proxy"] = True
                if search_ledger is not None:
                    strict_arguments["search_ledger"] = search_ledger
                asyncio.run(
                    capture_one(args.case, args.out, args.max_pages, soft, **strict_arguments)
                )
            finally:
                get_settings.cache_clear()
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = args.out / stamp
    directory.mkdir(parents=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    observations = []
    if cap is not None and search_ledger is None:
        search_ledger = SearchQueryLedger.open(directory / "search_ledger.json", cap)
    case_budgets: dict[str, Any] = {}
    batch_stop_reason = None
    for case_index, case_id in enumerate(planned_cases):
        output = directory / f"{case_id}.json"
        started = time.monotonic()
        environment = dict(
            os.environ,
            UNIMATCH_DEMO_MODE="false",
            UNIMATCH_ENABLE_BROWSER_TIER="false",
            UNIMATCH_FETCH_CONTACT="https://github.com/wpalish/ashyq-apply",
            UNIMATCH_SEARCH_PROVIDER=search_provider,
            PYTHONIOENCODING="utf-8",
            **search_environment(search_provider, recorded_store),
        )
        if args.strict_expert_budget:
            environment["UNIMATCH_RESPECT_ROBOTS"] = "true"
        with (directory / f"{case_id}.log").open("w", encoding="utf-8") as log:
            try:
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "evaluation.research.live",
                        "--live",
                        "--child",
                        "--case",
                        case_id,
                        "--out",
                        str(output),
                        "--max-pages",
                        str(args.max_pages),
                        "--seconds-per-case",
                        str(args.seconds_per_case),
                        *(["--strict-expert-budget"] if args.strict_expert_budget else []),
                        *(
                            ["--finalization-reserve-ms", str(finalization_reserve_ms)]
                            if args.finalization_reserve_ms is not None
                            else []
                        ),
                        *(["--search-provider", search_provider] if args.search_provider else []),
                        *(
                            [
                                "--max-search-queries",
                                str(cap),
                                "--search-ledger",
                                str(search_ledger.path),
                            ]
                            if search_ledger is not None
                            else []
                        ),
                        *(["--through-identity-gate"] if args.through_identity_gate else []),
                        *(["--no-registry-seeds"] if args.no_registry_seeds else []),
                        *(["--trust-env-proxy"] if args.trust_env_proxy else []),
                        *rule_negation_arguments(args),
                        *(
                            ["--knockout-gold", str(args.knockout_gold)]
                            if args.knockout_gold
                            else []
                        ),
                        *(
                            argument
                            for path in args.extra_bindings
                            for argument in ("--extra-bindings", str(path))
                        ),
                        *(["--search-first"] if args.search_first else []),
                        *(["--skip-refused-hosts"] if args.skip_refused_hosts else []),
                        *(["--reject-archive-hosts"] if args.reject_archive_hosts else []),
                        *(["--admission-lexicon"] if args.admission_lexicon else []),
                        *(["--navigation-slot"] if args.navigation_slot else []),
                        *(["--topic-search"] if args.topic_search else []),
                        *(["--navigation-field-leads"] if args.navigation_field_leads else []),
                        *(["--walker-subject-cap"] if args.walker_subject_cap else []),
                        *(["--deadline-v2"] if args.deadline_v2 else []),
                        *(["--euro-grouping"] if args.euro_grouping else []),
                        *(["--tuition-row-year"] if args.tuition_row_year else []),
                        *(["--document-rules-v2"] if args.document_rules_v2 else []),
                        *(["--document-leads"] if args.document_leads else []),
                        *(["--search-rate-limit-retry"] if args.search_rate_limit_retry else []),
                        *(["--fee-year-columns"] if args.fee_year_columns else []),
                        *(["--fee-readers-v2"] if args.fee_readers_v2 else []),
                        *(["--route-leads"] if args.route_leads else []),
                        *(["--english-readers-v2"] if args.english_readers_v2 else []),
                        *(["--provider-lead-floor"] if args.provider_lead_floor else []),
                        *(["--retrieval-rank-v2"] if args.retrieval_rank_v2 else []),
                        *(["--local-language-queries"] if args.local_language_queries else []),
                        *(["--localized-page-identity"] if args.localized_page_identity else []),
                        *(["--subject-title-shapes"] if args.subject_title_shapes else []),
                        *(["--site-identity-v2"] if args.site_identity_v2 else []),
                        *(["--coordinated-degree-scope"] if args.coordinated_degree_scope else []),
                        *(
                            ["--sitemap-keep-evidence-sum"]
                            if args.sitemap_keep_evidence_sum
                            else []
                        ),
                        *(["--local-catalogue-entry"] if args.local_catalogue_entry else []),
                        *(["--award-route"] if args.award_route else []),
                        *(["--scholarship-index-query"] if args.scholarship_index_query else []),
                        *(["--scholarship-level-scope"] if args.scholarship_level_scope else []),
                        *(["--award-page-evidence"] if args.award_page_evidence else []),
                        *(["--nav-link-level-guard"] if args.nav_link_level_guard else []),
                        *(["--pdf-evidence-readers"] if args.pdf_evidence_readers else []),
                        *(["--cache-buster-canonical"] if args.cache_buster_canonical else []),
                        *(["--front-page-not-programme"] if args.front_page_not_programme else []),
                        *(["--exact-field-lead-first"] if args.exact_field_lead_first else []),
                        *(
                            ["--abstain-on-unreadable-entry"]
                            if args.abstain_on_unreadable_entry
                            else []
                        ),
                        *(["--quoted-href-guard"] if args.quoted_href_guard else []),
                        *(["--award-name-qualifier"] if args.award_name_qualifier else []),
                        *(
                            ["--award-coordinated-degree-scope"]
                            if args.award_coordinated_degree_scope
                            else []
                        ),
                        *(["--question-routing"] if args.question_routing else []),
                        *(["--question-page-order"] if args.question_page_order else []),
                        *(["--parent-degree-link"] if args.parent_degree_link else []),
                        *(["--field-slug-scoring"] if args.field_slug_scoring else []),
                        *(["--fee-subpage-exclusion"] if args.fee_subpage_exclusion else []),
                        *(
                            ["--local-twin-on-identity-refusal"]
                            if args.local_twin_on_identity_refusal
                            else []
                        ),
                        *(["--confirm-head-identity"] if args.confirm_head_identity else []),
                        *(["--reject-subpage-head"] if args.reject_subpage_head else []),
                        *(["--reject-combination-head"] if args.reject_combination_head else []),
                        *(
                            ["--classify-head-and-slug-identity"]
                            if args.classify_head_and_slug_identity
                            else []
                        ),
                        *(["--course-lead-guard"] if args.course_lead_guard else []),
                        *(["--read-qualifier-twin"] if args.read_qualifier_twin else []),
                        *(
                            ["--listing-follows-local-aliases"]
                            if args.listing_follows_local_aliases
                            else []
                        ),
                        *(
                            ["--alias-aware-program-match"]
                            if args.alias_aware_program_match
                            else []
                        ),
                        *(["--guessed-url-stall-exempt"] if args.guessed_url_stall_exempt else []),
                        *(["--case-read-ledger"] if args.case_read_ledger else []),
                        *(["--case-time-budget"] if args.case_time_budget else []),
                        *(["--redirect-memory"] if args.redirect_memory else []),
                        *(["--url-variant-dedupe"] if args.url_variant_dedupe else []),
                        *(["--topic-faculty-scope"] if args.topic_faculty_scope else []),
                        *(["--topic-programme-scope"] if args.topic_programme_scope else []),
                        *(["--hub-leads"] if args.hub_leads else []),
                        *(["--service-page-priority"] if args.service_page_priority else []),
                        *(["--discovery-query-reserve"] if args.discovery_query_reserve else []),
                        *(
                            ["--admissions-host-from-homepage"]
                            if args.admissions_host_from_homepage
                            else []
                        ),
                        *(["--programme-page-guard"] if args.programme_page_guard else []),
                        *(["--catalog-heading-scope"] if args.catalog_heading_scope else []),
                        *(["--lexicon-v2"] if args.lexicon_v2 else []),
                        *(["--funding-identity-scope"] if args.funding_identity_scope else []),
                        *(["--campus-guard"] if args.campus_guard else []),
                        *(["--localized-identity"] if args.localized_identity else []),
                        *(["--alias-queries"] if args.alias_queries else []),
                        *(["--cost-aware-search-order"] if args.cost_aware_search_order else []),
                        *(["--stage-budgets"] if args.stage_budgets else []),
                        *(["--sitemap-child-priority"] if args.sitemap_child_priority else []),
                        *(["--sitemap-trim"] if args.sitemap_trim else []),
                        *(["--deadline-award-condition"] if args.deadline_award_condition else []),
                        *(["--deadline-window-scope"] if args.deadline_window_scope else []),
                        *(["--intake-section-deadline"] if args.intake_section_deadline else []),
                        *(
                            ["--international-round-deadline"]
                            if args.international_round_deadline
                            else []
                        ),
                        *(["--hop-root-deadline"] if args.hop_root_deadline else []),
                        *(["--canonical-http-https"] if args.canonical_http_https else []),
                        *(["--topic-search-continue"] if args.topic_search_continue else []),
                        *(["--search-429-retry"] if args.search_429_retry else []),
                        *(["--search-pacing"] if args.search_pacing else []),
                        *(
                            ["--with-documents", str(args.with_documents)]
                            if args.with_documents
                            else []
                        ),
                        *(["--shared-query-budget"] if args.shared_query_budget else []),
                        *(["--applicant-academic-year"] if args.applicant_academic_year else []),
                        "--search-funding-fallback"
                        if args.search_funding_fallback
                        else "--no-search-funding-fallback",
                        *(
                            ["--recover-search-candidates"]
                            if args.recover_search_candidates
                            else ["--no-recover-search-candidates"]
                        ),
                        "--target-award-search"
                        if args.target_award_search
                        else "--no-target-award-search",
                    ],
                    env=environment,
                    stdout=log,
                    stderr=log,
                    timeout=(
                        args.seconds_per_case + STRICT_PROCESS_RESERVE_SECONDS
                        if args.strict_expert_budget
                        else args.seconds_per_case
                    )
                    + args.with_documents,
                    check=False,
                )
                error = f"PROCESS_EXIT_{completed.returncode}" if completed.returncode else None
            except subprocess.TimeoutExpired:
                error = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
        process_elapsed_seconds = time.monotonic() - started
        if output.exists():
            observation = Observation.model_validate_json(output.read_text(encoding="utf-8"))
            if error:
                observation.error = error
                if not args.strict_expert_budget:
                    observation.telemetry.latency_seconds = process_elapsed_seconds
        else:
            observation = Observation(
                case_id=case_id,
                error=error or "MISSING_OUTPUT",
                telemetry=Telemetry(
                    latency_seconds=None if args.strict_expert_budget else process_elapsed_seconds
                ),
            )
        observations.append(observation)
        if args.strict_expert_budget:
            budget_output = output.with_suffix(".budget.json")
            if budget_output.exists():
                case_budgets[case_id] = json.loads(budget_output.read_text(encoding="utf-8"))
                if case_budgets[case_id].get("stop_reason") == "http_429":
                    batch_stop_reason = "http_429"
            case_budgets.setdefault(case_id, {}).update(
                parent_process_elapsed_seconds=process_elapsed_seconds,
                process_error=error,
                active_checkpoint_available=budget_output.exists(),
            )
        # Ticket 02: the run's cap is spent, so no further case could search.
        if search_ledger is not None and search_ledger.exhausted():
            batch_stop_reason = batch_stop_reason or RUN_CAP_STOP_REASON
        strict_config = (
            {
                "strict_expert_budget": True,
                "max_search_queries_per_case": STRICT_MAX_SEARCH_QUERIES,
                "page_budget_counts": "every Fetcher.get invocation; cache hits consume a call",
                "cold_fetcher_reads": True,
                "child_active_seconds": args.seconds_per_case,
                "finalization_reserve_ms": finalization_reserve_ms,
                "source_work_deadline_ms": args.seconds_per_case * 1000 - finalization_reserve_ms,
                "active_time_basis": _ExpertBudget(
                    args.max_pages,
                    args.seconds_per_case,
                    search_provider,
                    0.0,
                    finalization_reserve_ms=finalization_reserve_ms,
                ).active_time_basis,
                "parent_process_reserve_seconds": STRICT_PROCESS_RESERVE_SECONDS,
                "parent_process_timeout_seconds": args.seconds_per_case
                + STRICT_PROCESS_RESERVE_SECONDS,
                "case_budgets": case_budgets,
                "batch_stop_reason": batch_stop_reason,
                "batch_completed_case_ids": planned_cases[: case_index + 1],
                "batch_remaining_case_ids": planned_cases[case_index + 1 :],
            }
            if args.strict_expert_budget
            else {}
        )
        capture = Capture(
            pipeline_sha=sha,
            captured_at=stamp,
            mode="live",
            config={
                "search_provider": search_provider,
                "seconds_per_case": args.seconds_per_case,
                "max_fetcher_calls_per_case": args.max_pages,
                "page_budget_counts": "network reads; cache hits are free (since 2026-09-23)",
                "search_before_navigation": args.search_first,
                "recover_search_candidates": args.recover_search_candidates,
                "search_funding_fallback": args.search_funding_fallback,
                "target_award_search": args.target_award_search,
                "skip_refused_search_hosts": args.skip_refused_hosts,
                "reject_archive_hosts": args.reject_archive_hosts,
                "admission_lexicon": args.admission_lexicon,
                "navigation_slot": args.navigation_slot,
                "identity_bindings": [
                    _binding_label(path) for path in (REVIEWED_BINDINGS, *args.extra_bindings)
                ],
                "browser_enabled": False,
                "cohort": list(COHORT),
                "scope": "current production pipeline; HTTP-only bounded cold run",
                "rank_stage": "programme confirmation queue before catalogue walking",
                "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "mapping_sha256": hashlib.sha256(
                    Path(__file__).with_name("mapping.py").read_bytes()
                ).hexdigest(),
                **strict_config,
                **({"through_identity_gate": True} if args.through_identity_gate else {}),
                **(
                    {"knockout_gold": True, "knockout_dataset": args.knockout_gold.name}
                    if args.knockout_gold
                    else {}
                ),
                **entry_path_config(args),
                **recorded_store_config(recorded_store),
                **({"trust_env_proxy": True} if args.trust_env_proxy else {}),
                **(
                    {
                        "search_query_cap": cap_config(
                            search_ledger, planned, planned_cases, case_index, batch_stop_reason
                        )
                    }
                    if search_ledger is not None
                    else {}
                ),
                **(
                    {"rules_off": rule_negation_arguments(args)}
                    if rule_negation_arguments(args)
                    else {}
                ),
            },
            observations=observations,
        )
        (directory / "capture.json").write_text(capture.model_dump_json(indent=2), encoding="utf-8")
        print(f"{case_id}: {observation.error or 'complete'}", flush=True)
        if batch_stop_reason:
            print(
                "Capture stopped: the run's search query cap is reached; remaining cases were "
                "not attempted."
                if batch_stop_reason == RUN_CAP_STOP_REASON
                else "Capture stopped after provider HTTP 429; remaining cases were not attempted.",
                flush=True,
            )
            break
    print(directory / "capture.json", flush=True)


if __name__ == "__main__":
    main()
