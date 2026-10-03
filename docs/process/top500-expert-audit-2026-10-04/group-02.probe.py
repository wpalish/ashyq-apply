"""Offline, non-blind catalogue and synthetic identity audit; run from repo root.

backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-02.probe.py
Only group-02.rows.json is written. No provider or network calls are permitted.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import os
from pathlib import Path
import re
import socket
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
os.environ["UNIMATCH_DATABASE_URL"] = "sqlite://"
os.environ["UNIMATCH_DEMO_MODE"] = "true"
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import FetchOutcome, FetchResult
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.catalogue.importer import SEED_PATH, canonical_name, identity_key, import_catalogue, seed_domain
from app.catalogue.retrieval import retrieve
from app.domain.dedupe import normalize
from app.domain.site_identity import registrable_domain
from app.models import University
from app.models.base import Base

PACKET = Path(__file__).with_name("group-02.packet.json")
OUTPUT = Path(__file__).with_name("group-02.rows.json")


async def probe_identity(session, uni, hint, markup, final=None):
    """Actual production method, synthetic FetchResult and rolled-back writes."""
    tx = session.begin_nested()
    fetcher = SimpleNamespace(get=AsyncMock(return_value=FetchResult(
        url=hint, outcome=FetchOutcome.OK, content=markup.encode(), final_url=final or ""
    )))
    adapter = CatalogueDiscoveryAdapter(fetcher, session=session, university_ids=[uni.id], live_limit=1)
    result = await adapter._probe_site(uni, hint)
    evidence = {"accepted": result is not None, "requested": fetcher.get.call_args.args[0],
                "final": final or hint, "synthetic": True}
    tx.rollback()
    return evidence


async def main():
    packet = json.loads(PACKET.read_text())
    assert hashlib.sha256(SEED_PATH.read_bytes()).hexdigest() == packet["seed_sha256"]
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    output = []
    with Session(engine) as session:
        imported = import_catalogue(session)
        session.commit()
        again = import_catalogue(session)
        assert again["new_observations"] == 0
        all_rows = list(session.scalars(select(University)))
        by_key = {u.identity_key: u for u in all_rows}
        for row in packet["universities"]:
            uni = by_key[identity_key(row["name"], row["country"])]
            queries = [("exact_seed_name", row["name"]), ("canonical_name", canonical_name(row["name"])),
                       ("normalized_name", normalize(row["name"]))]
            queries += [("imported_alias", alias) for alias in uni.aliases]
            # Exploratory query variants, not claims that these are official aliases.
            if row.get("official_domain"):
                queries += [("exploratory_host_label", row["official_domain"].split(".")[0])]
            acronym_tokens = re.findall(r"\b[A-Z][A-Z0-9]{2,7}\b", row["name"])
            queries += [("supplied_name_acronym_token", a) for a in acronym_tokens]
            retrieval = []
            for kind, query in dict.fromkeys(queries):
                result = retrieve(session, query=query)
                ids = [u.id for u in result]
                retrieval.append({"kind": kind, "query": query, "target_found": uni.id in ids,
                                  "target_position": ids.index(uni.id)+1 if uni.id in ids else None,
                                  "result_count": len(result), "result_names": [u.name for u in result]})
            domain = uni.domain
            site = row.get("official_site")
            hint = f"https://{domain or 'audit-university.edu'}/"
            title = html.escape(uni.name)
            tests = {
                "retrieval": retrieval,
                "country_filter_target_found": uni.id in [u.id for u in retrieve(session, query=uni.name, country=row["country"])],
                "id_selection_exact": [u.id for u in retrieve(session, university_ids=[uni.id])] == [uni.id],
                "synthetic_identity": {},
            }
            scenarios = {
                "full_name_title": (f"<title>{title}</title>", None),
                "full_name_h1": (f"<h1>{title}</h1>", None),
                "full_name_h2_only": (f"<title>Welcome</title><h2>{title}</h2>", None),
                "third_party_guide_title": (f"<title>Unofficial guide to {title} fees</title>", None),
                "unrelated_title": ("<title>Independent directory</title>", None),
                "same_site_www_redirect": (f"<title>{title}</title>", f"https://www.{domain or 'audit-university.edu'}/en/"),
                "cross_site_redirect": (f"<title>{title}</title>", "https://unrelated-college.edu/"),
            }
            for name, (markup, final) in scenarios.items():
                tests["synthetic_identity"][name] = await probe_identity(session, uni, hint, markup, final)
            # Long names are also accepted on an unrelated host if present in its title.
            tests["synthetic_identity"]["third_party_host_full_name"] = await probe_identity(
                session, uni, "https://unrelated-college.edu/", f"<title>{title}</title>")
            acronym_probes = []
            for alias in uni.aliases:
                n = normalize(canonical_name(alias))
                if 3 <= len(n) < 8 and " " not in n:
                    acronym_probes.append({"alias": alias, "probe": await probe_identity(
                        session, uni, hint, f"<title>{html.escape(alias)} University</title>")})
            tests["synthetic_identity"]["supplied_short_aliases"] = acronym_probes
            for token in dict.fromkeys(acronym_tokens):
                tests["synthetic_identity"][f"acronym_token_{token}"] = await probe_identity(
                    session, uni, hint, f"<title>{token} University</title>")
            domain_hint = row.get("official_domain")
            site_host = urlsplit(site or "").hostname
            conflict = bool(domain_hint and site_host and registrable_domain(domain_hint) != registrable_domain(site_host))
            hints = list(dict.fromkeys(x for x in [f"https://{domain}/" if domain else None, site] if x))
            observations = [f"Imported as {uni.name}; route={'curated' if uni.registry_entry else 'generic'}; domain_status={uni.domain_status}."]
            if not hints:
                observations.append("No seed/curated identity hints; identity provider path required under present code. Missing hints are not proof of a defective or missing official site.")
            if row["name"] != uni.name:
                observations.append("Canonical/curated name differs from seed; exact seed remains in aliases.")
            if domain_hint and domain_hint != domain:
                observations.append(f"Stored domain differs from raw seed domain: {domain_hint} -> {domain}; curated authority or registrable-domain normalization applies.")
            failed = [q["query"] for q in retrieval if not q["target_found"]]
            if failed:
                observations.append("Exploratory variants did not retrieve target: " + ", ".join(failed))
            observations.append("Synthetic full-name title was accepted even on unrelated host; this is a reproduced rule limitation, not an observed live identity mistake.")
            output.append({"seed_id": row["seed_id"], "name": row["name"], "live_checked": False,
                           "tests": tests, "observations": observations,
                           "risk": {"identity_false_positive": "synthetically demonstrated; exposure to provider results depends on generic route",
                                    "query_variants": "exploratory gaps" if failed else "all tested variants include target",
                                    "route": "curated" if uni.registry_entry else "generic"},
                           "imported": {"name": uni.name, "country": uni.country, "aliases": uni.aliases,
                                        "domain": domain, "domain_status": uni.domain_status,
                                        "registry_seed_categories": sorted((uni.registry_entry or {}).get("seeds", {}))},
                           "hints": {"official_domain": domain_hint, "official_site": site, "conflict": conflict,
                                     "ordered_probe_hints": hints, "seed_domain_result": seed_domain(row)}})
        # Contradictory hints: actual _identify_site does not probe original official_domain.
        uni = by_key[identity_key(packet["universities"][0]["name"], packet["universities"][0]["country"])]
        tx = session.begin_nested()
        uni.domain = None
        uni.seed_snapshot = {"record": {"official_domain": "first-college.edu", "official_site": "https://second-college.edu/"}}
        fetcher = SimpleNamespace(get=AsyncMock(return_value=FetchResult(
            url="https://second-college.edu/", outcome=FetchOutcome.OK,
            content=f"<title>{html.escape(uni.name)}</title>".encode())))
        adapter = CatalogueDiscoveryAdapter(fetcher, session=session, university_ids=[uni.id], live_limit=1)
        identified = await adapter._identify_site(uni, DiscoveryTrace(institution=uni.name, domain=""))
        conflict_probe = {"synthetic": True, "seed_domain_result": seed_domain(uni.seed_snapshot["record"]),
                          "requests": [c.args[0] for c in fetcher.get.call_args_list],
                          "accepted_homepage": identified["homepage"] if identified else None}
        tx.rollback()
    engine.dispose()
    summary = {
        "audited": len(output), "import": imported, "second_import_new_observations": again["new_observations"],
        "exact_name_found": sum(r["tests"]["retrieval"][0]["target_found"] for r in output),
        "canonical_name_found": sum(r["tests"]["retrieval"][1]["target_found"] for r in output),
        "curated": sum(r["risk"]["route"] == "curated" for r in output),
        "missing_hints": sum(not r["hints"]["ordered_probe_hints"] for r in output),
        "domain_site_conflicts": sum(r["hints"]["conflict"] for r in output),
        "retrieval_queries": sum(len(r["tests"]["retrieval"]) for r in output),
        "failed_queries": [dict(seed_id=r["seed_id"], **q) for r in output for q in r["tests"]["retrieval"] if not q["target_found"]],
        "synthetic_conflicting_hints": conflict_probe,
    }
    assert len(output) == 50 and len({r["seed_id"] for r in output}) == 50
    OUTPUT.write_text(json.dumps({"group": 2, "source_sha": packet["source_sha"], "seed_sha256": packet["seed_sha256"],
                                  "scope": "Non-blind offline engineering audit; all HTML/Fetcher responses synthetic; no official fact certification.",
                                  "summary": summary, "rows": output}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    def forbid_network(*args, **kwargs):
        raise AssertionError("Network/provider use forbidden in group-02 audit")
    with patch.object(socket.socket, "connect", forbid_network), patch.object(socket, "create_connection", forbid_network), patch(
        "app.catalogue.discovery.get_search_provider", side_effect=forbid_network
    ):
        asyncio.run(main())
