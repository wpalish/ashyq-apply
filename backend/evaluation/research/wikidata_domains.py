"""Wikidata ``P856`` (official website) as a domain proposal source, in evaluation only.

Issue 06 of the free-search wayfinder: 147 of the 500 catalogue rows have no
``official_domain`` and so cannot enter discovery at all. Wikidata lists an
official website for most universities, under CC0, through a free query
service. This module asks it, by name and country, and writes **proposals**
for the owner to confirm row by row. It never writes the catalogue.

It also checks the KB top-100 list's domains against the same property and
lists where the two disagree: a disagreement is a question for a reviewer,
not evidence that either side is wrong (Wikidata often lists the main site
of a university whose admissions live on a sibling domain).

Network: plain HTTPS to ``query.wikidata.org`` through the container's proxy,
like ``search_probe.read_page``. Wikidata is not a university site and not a
search provider; nothing here crawls a page. Politeness follows the query
service's user-agent policy: a descriptive ``User-Agent`` naming the project,
at most one request a second, one request at a time, and ``429``/``503``
answered by waiting the server's ``Retry-After`` before one retry at a time.
Name lookups are batched so the whole run is a few dozen requests. This
direct read is a recorded exception to the ``Fetcher``-only rule (AGENTS.md
§6, owner, 2026-10-19): one fixed endpoint, no redirects, a capped body
(``MAX_RESPONSE_BYTES``) and no applicant data in any query.

Held-out institutions are skipped by seed id before any query is built: they
are listed as excluded and nothing about them is looked up.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.domain.site_identity import registrable_domain

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = (
    "ashyq-apply-evaluation/0.1 "
    "(https://github.com/wpalish/ashyq-apply; catalogue official-domain proposals) "
    "httpx"
)
MIN_INTERVAL_S = 1.0
MAX_ATTEMPTS = 4
MAX_RETRY_AFTER_S = 120.0
#: SR-06: a body larger than this is refused rather than parsed. A full label
#: batch answers in well under 1 MiB; the cap only stops a runaway response.
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
LABEL_BATCH = 20
SEARCHES_PER_ROW = 4

BACKEND = Path(__file__).resolve().parents[2]
SEED_PATH = BACKEND / "app" / "catalogue" / "unimatch_top500_seed.json"
KB_LIST_PATH = BACKEND / "evaluation" / "research" / "data" / "kb_top100_list.json"
OUT_PATH = BACKEND / "evaluation" / "research" / "data" / "catalogue_official_domains.proposed.json"

#: Held-out institutions (nu metu sabanci charles masaryk tum tartu polimi
#: vilnius), by catalogue seed id. Nazarbayev University is not in the seed.
#: Nothing is looked up for these rows.
HELDOUT_SEED_IDS: dict[str, str] = {
    "qs2027-025": "tum",
    "qs2027-087": "polimi",
    "qs2027-273": "charles",
    "qs2027-305": "metu",
    "qs2027-358": "sabanci",
    "qs2027-369": "tartu",
    "qs2027-456": "masaryk",
    "qs2027-468": "vilnius",
}

#: Wikidata ``higher education institution``; the label query requires an
#: instance of it or of one of its subclasses.
HIGHER_EDUCATION = "Q38723"

#: Catalogue country name -> the English labels of the Wikidata country (P17)
#: values that count as the same country. Hong Kong and Macao rows are carried
#: by the People's Republic of China on most items.
COUNTRY_LABELS: dict[str, frozenset[str]] = {
    "United States of America": frozenset({"United States", "United States of America"}),
    "Republic of Korea": frozenset({"South Korea", "Republic of Korea"}),
    "China (Mainland)": frozenset({"People's Republic of China", "China"}),
    "Hong Kong SAR, China": frozenset({"Hong Kong", "People's Republic of China", "China"}),
    "Macao SAR, China": frozenset({"Macau", "Macao", "People's Republic of China", "China"}),
    "Brunei Darussalam": frozenset({"Brunei", "Brunei Darussalam"}),
    "Russian Federation": frozenset({"Russia", "Russian Federation"}),
    "Türkiye": frozenset({"Turkey", "Türkiye"}),
    "Czechia": frozenset({"Czech Republic", "Czechia"}),
    "Netherlands": frozenset({"Netherlands", "Kingdom of the Netherlands"}),
    "Taiwan": frozenset({"Taiwan", "Republic of China"}),
}

Sleep = Callable[[float], None]
Clock = Callable[[], float]


def country_matches(catalogue_country: str, wikidata_country: str) -> bool:
    accepted = COUNTRY_LABELS.get(catalogue_country, frozenset({catalogue_country}))
    return wikidata_country in accepted


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    stripped = stripped.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", stripped).strip().casefold()


_ACRONYM = re.compile(r"[A-Z][A-Z&-]{1,7}")
#: ``Universitaet`` in the catalogue is ``Universität`` on Wikidata.
_UMLAUTS = {"Universitaet": "Universität", "universitaet": "universität"}
_UMLAUT = re.compile("|".join(_UMLAUTS))


def name_variants(name: str, places: Iterable[str] = ()) -> dict[str, int]:
    """The catalogue name and the shapes Wikidata usually labels it by, with a tier.

    Tier 0 is the name itself (also without its parenthesis or a leading
    ``The``). Tier 1 is a reshaping that keeps the institution: the parenthesis
    alone (``NTU Singapore``), the name before a trailing place
    (``Nanyang Technological University, Singapore``), ``Essex, University of``
    turned round. Tier 2 is any other piece of a split name, which can name a
    different body (``Birkbeck, University of London`` -> ``University of
    London``); a match only on tier 2 is never better than low confidence.
    """
    found: dict[str, int] = {}
    folded_places = {_fold(p) for p in places if p}

    def add(text: str, tier: int) -> None:
        text = re.sub(r"\s+", " ", text).strip(" ,-\u2013")
        if len(text) >= 2 and found.get(text, 99) > tier:
            found[text] = tier

    add(name, 0)
    inside = re.findall(r"\(([^)]*)\)", name)
    bare = re.sub(r"\([^)]*\)", " ", name).strip()
    add(bare, 0)
    parts = [p.strip() for p in re.split(r",| [-\u2013] ", bare) if p.strip()]
    if (
        len(parts) == 2
        and parts[1].lower().startswith("university of")
        and parts[1].lower().endswith(" of")
    ):
        add(f"{parts[1]} {parts[0]}", 1)
    if len(parts) > 1 and _fold(parts[-1]) in folded_places:
        add(", ".join(parts[:-1]), 1)
    acronyms = [p for p in parts if _ACRONYM.fullmatch(p)]
    if len(parts) == 2 and len(acronyms) == 1:
        # ``KIT, Karlsruhe Institute of Technology``: an acronym and its name.
        for part in parts:
            add(part, 1)
    for part in parts:
        if _fold(part) not in folded_places:
            add(part, 2)
    for text, tier in list(found.items()):
        if text.lower().startswith("the "):
            add(text[4:], tier)
        unquoted = re.sub(r"[\"\u201c\u201d]", "", text)
        add(unquoted, tier)
        add(_UMLAUT.sub(lambda m: _UMLAUTS[m.group(0)], unquoted), tier)
    for text in inside:
        if _fold(text) not in folded_places:
            add(text, 1)
    return found


def _row_variants(row: dict[str, Any]) -> dict[str, int]:
    places = [row.get("city") or "", row.get("country") or ""]
    places += sorted(COUNTRY_LABELS.get(row.get("country") or "", frozenset()))
    return name_variants(row["name"], places)


#: SPARQL ``ECHAR`` escapes for a double-quoted literal. The backslash goes
#: first so the escapes added after it are not doubled; CR and LF may not
#: appear raw inside a literal at all.
_LITERAL_ESCAPES = (
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("'", "\\'"),
    ("\n", "\\n"),
    ("\r", "\\r"),
)


def _literal(text: str) -> str:
    for raw, escaped in _LITERAL_ESCAPES:
        text = text.replace(raw, escaped)
    return '"' + text + '"'


def label_query(variants: Iterable[str], languages: Sequence[str] = ("en", "mul")) -> str:
    values = " ".join(f"{_literal(v)}@{lang}" for v in variants for lang in languages)
    return f"""SELECT ?name ?item ?itemLabel ?site ?countryLabel ?isLabel ?dissolved WHERE {{
  VALUES ?name {{ {values} }}
  ?item rdfs:label|skos:altLabel ?name .
  ?item wdt:P31/wdt:P279* wd:{HIGHER_EDUCATION} .
  BIND(EXISTS {{ ?item rdfs:label ?name }} AS ?isLabel)
  BIND(EXISTS {{ ?item wdt:P576 ?end }} AS ?dissolved)
  OPTIONAL {{ ?item wdt:P856 ?site }}
  OPTIONAL {{ ?item wdt:P17 ?country }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
}}"""


def search_query(text: str, limit: int = 7) -> str:
    """Wikidata's own entity search, run inside the query service."""
    return f"""SELECT ?item ?itemLabel ?site ?countryLabel ?ord ?dissolved WHERE {{
  SERVICE wikibase:mwapi {{
    bd:serviceParam wikibase:endpoint "www.wikidata.org"; wikibase:api "EntitySearch";
      mwapi:search {_literal(text)}; mwapi:language "en"; mwapi:limit "{limit}" .
    ?item wikibase:apiOutputItem mwapi:item .
    ?ord wikibase:apiOrdinal true .
  }}
  ?item wdt:P31/wdt:P279* wd:{HIGHER_EDUCATION} .
  BIND(EXISTS {{ ?item wdt:P576 ?end }} AS ?dissolved)
  OPTIONAL {{ ?item wdt:P856 ?site }}
  OPTIONAL {{ ?item wdt:P17 ?country }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
}}"""


class WikidataUnavailable(RuntimeError):
    """The query service kept refusing after the retries the policy allows."""


class WikidataResponseTooLarge(RuntimeError):
    """The query service answered with more than the client's byte cap."""


def _read_capped(response: httpx.Response, limit: int) -> bytes:
    declared = response.headers.get("Content-Length", "")
    if declared.isdigit() and int(declared) > limit:
        raise WikidataResponseTooLarge(f"declared {declared} bytes, cap is {limit}")
    body = bytearray()
    for chunk in response.iter_bytes():
        body += chunk
        if len(body) > limit:
            raise WikidataResponseTooLarge(f"body passed the {limit}-byte cap")
    return bytes(body)


@dataclass
class PoliteClient:
    """One request at a time, ≥ 1 s apart, ``Retry-After`` honoured."""

    client: httpx.Client
    sleep: Sleep = time.sleep
    clock: Clock = time.monotonic
    min_interval_s: float = MIN_INTERVAL_S
    max_response_bytes: int = MAX_RESPONSE_BYTES
    requests: int = 0
    throttled: int = 0
    _last: float | None = None

    def _wait_turn(self) -> None:
        if self._last is not None:
            gap = self.min_interval_s - (self.clock() - self._last)
            if gap > 0:
                self.sleep(gap)

    def sparql(self, query: str) -> list[dict[str, str]]:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._wait_turn()
            self._last = self.clock()
            self.requests += 1
            # Streamed so the body is read under a cap, never parsed whole first.
            with self.client.stream(
                "POST",
                SPARQL_ENDPOINT,
                data={"query": query},
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/sparql-results+json",
                },
            ) as response:
                if response.status_code not in (429, 503):
                    response.raise_for_status()
                    body = _read_capped(response, self.max_response_bytes)
                    bindings = json.loads(body)["results"]["bindings"]
                    return [{k: str(v["value"]) for k, v in b.items()} for b in bindings]
                self.throttled += 1
                wait = _retry_after(response, attempt)
            if attempt == MAX_ATTEMPTS:
                break
            self.sleep(wait)
            self._last = self.clock()
        raise WikidataUnavailable(f"query service refused {MAX_ATTEMPTS} times")


def _retry_after(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("Retry-After", "")
    try:
        seconds = float(raw)
    except ValueError:
        seconds = 5.0 * 2 ** (attempt - 1)
    return max(1.0, min(seconds, MAX_RETRY_AFTER_S))


@dataclass
class Candidate:
    item: str
    label: str
    country: str
    sites: list[str] = field(default_factory=list)
    matched_names: set[str] = field(default_factory=set)
    label_match: bool = False
    dissolved: bool = False
    search_rank: int | None = None

    @property
    def domains(self) -> list[str]:
        out: list[str] = []
        for site in self.sites:
            domain = registrable_domain(site)
            if domain and domain not in out:
                out.append(domain)
        return out


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _true(value: str | None) -> bool:
    return value in ("true", "1")


def collect(bindings: Iterable[dict[str, str]]) -> dict[str, Candidate]:
    """Fold SPARQL rows (one per site × country × name) into one candidate per item."""
    found: dict[str, Candidate] = {}
    for row in bindings:
        qid = _qid(row["item"])
        cand = found.get(qid)
        if cand is None:
            cand = found[qid] = Candidate(
                item=qid, label=row.get("itemLabel", qid), country=row.get("countryLabel", "")
            )
        if row.get("countryLabel") and not cand.country:
            cand.country = row["countryLabel"]
        site = row.get("site")
        if site and site not in cand.sites:
            cand.sites.append(site)
        if row.get("name"):
            cand.matched_names.add(row["name"])
        cand.label_match = cand.label_match or _true(row.get("isLabel"))
        cand.dissolved = cand.dissolved or _true(row.get("dissolved"))
        if row.get("ord") is not None:
            rank = int(row["ord"])
            cand.search_rank = rank if cand.search_rank is None else min(cand.search_rank, rank)
    return found


def _countries(rows: Iterable[dict[str, str]]) -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {}
    for row in rows:
        if row.get("countryLabel"):
            seen.setdefault(_qid(row["item"]), set()).add(row["countryLabel"])
    return seen


@dataclass(frozen=True)
class Match:
    item: str | None
    label: str
    sites: tuple[str, ...]
    domains: tuple[str, ...]
    confidence: str  # high | medium | low | none
    reason: str
    method: str  # label | search | none
    alternatives: tuple[str, ...] = ()


def judge(
    variants: dict[str, int],
    country: str,
    candidates: Sequence[Candidate],
    countries: dict[str, set[str]],
    method: str,
) -> Match:
    """Name + country decide the confidence; it is never a probability."""
    tiers = {_fold(v): t for v, t in variants.items()}
    live = [c for c in candidates if not c.dissolved]
    in_country = [
        c for c in live if any(country_matches(country, k) for k in countries.get(c.item, set()))
    ]
    if not in_country:
        if live:
            seen = sorted({k for c in live for k in countries.get(c.item, set())})
            return Match(
                None,
                "",
                (),
                (),
                "none",
                f"{len(live)} {method} hit(s), none in {country} (countries seen: "
                f"{', '.join(seen) or 'none'})",
                method,
                tuple(c.item for c in live),
            )
        return Match(None, "", (), (), "none", f"no {method} hit for any name variant", method)

    def tier(c: Candidate) -> int:
        names = [tiers.get(_fold(n), 3) for n in c.matched_names]
        return min([*names, tiers.get(_fold(c.label), 3)])

    def exact(c: Candidate) -> bool:
        return c.label_match or _fold(c.label) in tiers

    def strength(c: Candidate) -> tuple[int, int, int, int]:
        rank = c.search_rank if c.search_rank is not None else 0
        return (-tier(c), int(exact(c)), int(bool(c.sites)), -rank)

    ranked = sorted(in_country, key=strength, reverse=True)
    best = ranked[0]
    others = tuple(c.item for c in ranked[1:])
    domains = best.domains
    if not best.sites:
        return Match(
            best.item,
            best.label,
            (),
            (),
            "none",
            f"{best.item} ({best.label}) matches name and country but has no P856",
            method,
            others,
        )
    rivals = [c for c in ranked[1:] if strength(c)[:3] == strength(best)[:3]]
    matched = ", ".join(repr(n) for n in sorted(best.matched_names)) or repr(best.label)
    reasons = [
        f"{'label' if exact(best) else 'alias'} match on {matched} (name tier {tier(best)})"
        if method == "label"
        else f"entity search rank {best.search_rank}, label {best.label!r} "
        f"({'equals' if exact(best) else 'differs from'} the catalogue name)",
        f"country {best.country or country}",
    ]
    if len(domains) > 1:
        reasons.append(f"P856 spans {len(domains)} registrable domains")
    if tier(best) == 2:
        reasons.append("matched only a piece of a split name")
    if rivals:
        rival_ids = ", ".join(c.item for c in rivals)
        reasons.append(f"{len(rivals)} equally strong rival item(s): {rival_ids}")
    if rivals or tier(best) == 2:
        confidence = "low"
    elif exact(best) and tier(best) <= 1 and len(domains) == 1:
        confidence = "high"
    else:
        confidence = "medium"
    return Match(
        best.item,
        best.label,
        tuple(best.sites),
        tuple(domains),
        confidence,
        "; ".join(reasons),
        method,
        others,
    )


def search_texts(variants: dict[str, int], limit: int = SEARCHES_PER_ROW) -> list[tuple[str, bool]]:
    """What entity search is asked, best first, and whether the text was cut short.

    Wikidata's entity search matches a label from its start, so a hyphenated
    name is also tried spaced out, and a long one cut to its first three words;
    a hit found only by a cut name is never better than low confidence.
    """
    ordered = sorted(
        (v for v, t in variants.items() if t <= 1), key=lambda v: (variants[v], len(v))
    )
    full: list[tuple[str, bool]] = []
    short: list[tuple[str, bool]] = []
    for text in ordered:
        spaced = text.replace("-", " ")
        for form in (text, spaced):
            if (form, False) not in full:
                full.append((form, False))
        cut = " ".join(spaced.split()[:3])
        if cut != spaced and len(cut) >= 3 and (cut, True) not in short:
            short.append((cut, True))
    return (full + short)[:limit]


def lookup(
    client: PoliteClient, rows: Sequence[dict[str, Any]], batch: int = LABEL_BATCH
) -> dict[str, Match]:
    """Label query in batches; one entity search per row the labels leave unmatched."""
    out: dict[str, Match] = {}
    for start in range(0, len(rows), batch):
        chunk = rows[start : start + batch]
        variants = sorted({v for row in chunk for v in _row_variants(row)})
        bindings = client.sparql(label_query(variants))
        countries = _countries(bindings)
        for row in chunk:
            mine = _row_variants(row)
            folded = {_fold(v) for v in mine}
            hits = [b for b in bindings if _fold(b.get("name", "")) in folded]
            out[row["seed_id"]] = judge(
                mine, row["country"], list(collect(hits).values()), countries, "label"
            )
    for row in rows:
        previous = out[row["seed_id"]]
        if previous.confidence != "none":
            continue
        mine = _row_variants(row)
        found = previous
        for query_text, cut in search_texts(mine):
            bindings = client.sparql(search_query(query_text))
            found = judge(
                mine,
                row["country"],
                list(collect(bindings).values()),
                _countries(bindings),
                "search",
            )
            if found.confidence == "medium" and cut:
                found = replace(
                    found,
                    confidence="low",
                    reason=f"{found.reason}; found only by the shortened name {query_text!r}",
                )
            if found.confidence != "none":
                break
        if found.confidence == "none":
            found = Match(
                previous.item,
                previous.label,
                (),
                (),
                "none",
                previous.reason
                if found.reason == previous.reason
                else f"{previous.reason}; {found.reason}",
                "none",
                previous.alternatives + found.alternatives,
            )
        out[row["seed_id"]] = found
    return out


def _proposal(row: dict[str, Any], match: Match) -> dict[str, Any]:
    return {
        "seed_id": row["seed_id"],
        "name": row["name"],
        "country": row["country"],
        "wikidata_item": match.item,
        "wikidata_label": match.label or None,
        "p856": list(match.sites),
        "proposed_official_domain": match.domains[0] if match.domains else None,
        "match_confidence": match.confidence,
        "match_method": match.method,
        "reason": match.reason,
        "alternatives": list(match.alternatives),
        "review": {"decision": None, "reviewer": None, "note": None},
    }


def _kb_domains(row: dict[str, Any]) -> list[str]:
    raw = [row.get("official_domain") or "", *(row.get("extra_domains") or [])]
    return [d for d in (registrable_domain(x) for x in raw if x) if d]


def kb_check(row: dict[str, Any], match: Match) -> dict[str, Any]:
    ours = _kb_domains(row)
    theirs = list(match.domains)
    if match.item is None or not theirs:
        verdict = "unresolved"
    elif set(ours) & set(theirs):
        verdict = "agree"
    else:
        verdict = "disagree"
    return {
        "seed_id": row["seed_id"],
        "name": row["name"],
        "kb_official_domain": row.get("official_domain"),
        "kb_extra_domains": list(row.get("extra_domains") or []),
        "wikidata_item": match.item,
        "wikidata_label": match.label or None,
        "p856": list(match.sites),
        "wikidata_domains": theirs,
        "match_confidence": match.confidence,
        "verdict": verdict,
        "reason": match.reason,
    }


def build_report(
    client: PoliteClient,
    seed: Sequence[dict[str, Any]],
    kb_rows: Sequence[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    missing = [r for r in seed if not r.get("official_domain")]
    excluded = [r for r in missing if r["seed_id"] in HELDOUT_SEED_IDS]
    to_query = [r for r in missing if r["seed_id"] not in HELDOUT_SEED_IDS]
    kb_to_check = [
        r
        for r in kb_rows
        if r.get("official_domain")
        and r["seed_id"] not in HELDOUT_SEED_IDS
        and r.get("status") != "excluded_heldout"
    ]
    matches = lookup(client, to_query)
    kb_matches = lookup(client, kb_to_check)
    proposals = [_proposal(r, matches[r["seed_id"]]) for r in to_query]
    checks = [kb_check(r, kb_matches[r["seed_id"]]) for r in kb_to_check]

    def count(items: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
        tally: dict[str, int] = {}
        for item in items:
            tally[item[key]] = tally.get(item[key], 0) + 1
        return dict(sorted(tally.items()))

    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": "catalogue_official_domains.proposed/1",
        "generated_at": stamp,
        "source": "Wikidata P856 via query.wikidata.org (CC0)",
        "status": "proposals only - the catalogue is never written from this file; "
        "the owner confirms row by row in each proposal's `review` block",
        "confidence_rule": "high = one live item in the row's country whose label (or alias, "
        "for the label query) equals a name variant, with one P856 registrable domain; "
        "medium = the same without an exact label, or P856 spanning several domains; "
        "low = an equally strong rival item; none = no item in the country with P856",
        "counts": {
            "catalogue_rows": len(seed),
            "missing_official_domain": len(missing),
            "excluded_heldout": len(excluded),
            "queried": len(to_query),
            "proposed": sum(1 for p in proposals if p["proposed_official_domain"]),
            "by_confidence": count(proposals, "match_confidence"),
            "kb_rows_checked": len(checks),
            "kb_by_verdict": count(checks, "verdict"),
            "requests": client.requests,
            "throttled_responses": client.throttled,
        },
        "excluded_heldout": [
            {"seed_id": r["seed_id"], "case": HELDOUT_SEED_IDS[r["seed_id"]]} for r in excluded
        ],
        "proposals": proposals,
        "kb_check": checks,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))["universities"]
    kb_rows = json.loads(KB_LIST_PATH.read_text(encoding="utf-8"))["rows"]
    with httpx.Client(timeout=90, follow_redirects=False) as http:
        report = build_report(PoliteClient(http), seed, kb_rows)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
