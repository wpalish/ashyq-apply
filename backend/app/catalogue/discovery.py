"""Bounded live enrichment of local identities through the existing discovery adapter."""

from __future__ import annotations

import asyncio
import hashlib
import re
from contextlib import nullcontext
from dataclasses import fields
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import same_source_site
from app.adapters.search import SearchError, get_search_provider
from app.adapters.search.base import search_failure_diagnostic
from app.catalogue.importer import canonical_name, public_domain, stable_id
from app.catalogue.retrieval import retrieve
from app.domain.dedupe import normalize
from app.domain.site_identity import registrable_domain
from app.models import University, UniversityObservation
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.schemas.profile import ApplicantProfileIn

# SI-1: additional first-party homepage branding. Off until measured and approved.
SITE_BRANDING_IDENTITY = False


def _branding_name(value: str) -> str:
    """Keep ordered name words; only the optional article is insignificant."""
    return " ".join(word for word in normalize(value).split() if word != "the")


def _site_branding(
    soup: BeautifulSoup, names: list[str], localities: tuple[str, ...] = ()
) -> tuple[str, str] | None:
    """Read site names and explicit copyright owners, never incidental mentions."""
    full_names = [name for n in names if len(n) >= 8 and (name := _branding_name(n))]
    known_localities = {normalize(place) for place in localities if place}
    for meta in soup.select('meta[property="og:site_name"]'):
        value = str(meta.get("content") or "").strip()
        if value and _branding_name(value) in full_names:
            return value, "homepage_og_site_name"
    for node in soup.select("footer p, footer small"):
        value = node.get_text(" ", strip=True)
        if len(value) > 300:
            continue
        owner = re.match(
            r"^\s*(?:copyright\s*(?:©|\(c\))?|©)\s*"
            r"(?:\d{4}(?:\s*[-–]\s*\d{4})?\s*[-–—|,:.]?\s*)?(.*)$",
            value,
            re.IGNORECASE,
        )
        if owner is None:
            continue
        # A comma may introduce a known city/country, never an arbitrary legal
        # entity suffix ("Example University, Foundation" is another owner).
        owner_parts = re.split(r"[,|;]", owner.group(1))
        if any(normalize(part) not in known_localities for part in owner_parts[1:]):
            continue
        owner_name = _branding_name(owner_parts[0])
        if owner_name and owner_name in full_names:
            return value, "homepage_copyright_owner"
    return None


class CatalogueDiscoveryAdapter(LiveDiscoveryAdapter):
    name = "local-catalogue-with-live-enrichment"

    def __init__(
        self,
        fetcher,
        *,
        session: Session,
        university_ids: list[str] | None,
        live_limit: int,
        **kwargs,
    ):
        super().__init__(fetcher, **kwargs)
        self.session = session
        self.university_ids = university_ids
        self.live_limit = live_limit

    async def discover(self, profile: ApplicantProfileIn, limit: int = 50) -> list[Candidate]:
        rows = retrieve(
            self.session,
            preferred=profile.preferences.preferred_countries,
            excluded=profile.preferences.excluded_countries,
            university_ids=self.university_ids,
        )[:limit]
        if not rows and not self.university_ids:
            # Older isolated evaluation harnesses intentionally have no catalogue.
            return await super().discover(profile, limit)
        self.traces = []
        self.interrupted_traces = []
        self.walker_outcomes = []
        candidates: list[Candidate] = []
        for index, uni in enumerate(rows):
            trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
            candidate = Candidate(
                name=uni.name,
                catalogue_id=uni.id,
                country=uni.country,
                city=uni.city,
                discovery_source=f"local-catalogue:{uni.id}",
                notes="Institution candidate; programme, cost and requirements need research.",
            )
            if index < self.live_limit:
                try:
                    with self.research_scope(candidate) if self.research_scope else nullcontext():
                        candidate, trace = await asyncio.wait_for(
                            self._enrich(uni, profile, candidate, trace), timeout=300
                        )
                except (asyncio.CancelledError, RunCancelled, LeaseLost):
                    self.interrupted_traces.append(trace)
                    raise
                except UniversityReadStopped as stopped:
                    if stopped.reason == "checkpoint_busy":
                        raise
                    candidate.search_queries_used = trace.search_queries_sent
                    trace.search_limitations.append(
                        f"Remaining research remains unknown: university read allowance unavailable ({stopped.reason})."
                    )
                except TimeoutError:
                    trace.errors.append(
                        "Live discovery time limit reached; local university candidate retained."
                    )
                    trace.search_limitations.append(
                        "Live discovery time limit reached; local university candidate retained."
                    )
            self.traces.append(trace)
            candidates.append(candidate)
        return candidates

    async def _enrich(
        self,
        uni: University,
        profile: ApplicantProfileIn,
        candidate: Candidate,
        trace: DiscoveryTrace,
    ) -> tuple[Candidate, DiscoveryTrace]:
        trace.search_queries_sent = max(trace.search_queries_sent, candidate.search_queries_used)
        entry = uni.registry_entry
        if entry is None:
            entry = await self._identify_site(uni, trace)
        if entry is None:
            trace.search_limitations.append(
                f"Official website identity not established for {uni.name}; candidate retained without verified programme facts."
            )
            candidate.search_queries_used = trace.search_queries_sent
            return candidate, trace
        inner = DiscoveryTrace(
            institution=entry["name"],
            domain=trace.domain,
            search_queries_sent=trace.search_queries_sent,
        )
        try:
            enriched, discovered = await self._discover_one(
                entry, profile, search_queries_used=trace.search_queries_sent, trace=inner
            )
        except (asyncio.CancelledError, RunCancelled, LeaseLost):
            inner.search_failures[:0] = trace.search_failures
            inner.search_limitations[:0] = trace.search_limitations
            for observed in fields(trace):
                if observed.name != "institution":
                    setattr(trace, observed.name, getattr(inner, observed.name))
            raise
        except UniversityReadStopped as stopped:
            if stopped.reason != "checkpoint_busy":
                inner.search_failures[:0] = trace.search_failures
                inner.search_limitations[:0] = trace.search_limitations
                for observed in fields(trace):
                    # The stopped seed owns the exported report's institution key.
                    if observed.name != "institution":
                        setattr(trace, observed.name, getattr(inner, observed.name))
            raise
        discovered.search_failures[:0] = trace.search_failures
        discovered.search_limitations[:0] = trace.search_limitations
        enriched.catalogue_id = uni.id
        enriched.discovery_source = f"local-catalogue:{uni.id}; {enriched.discovery_source}"
        return enriched, discovered

    async def _identify_site(self, uni: University, trace: DiscoveryTrace) -> dict | None:
        record = (uni.seed_snapshot or {}).get("record", {})
        hints = [f"https://{uni.domain}/" if uni.domain else None, record.get("official_site")]
        urls = list(dict.fromkeys(url for url in hints if url))
        for hint in urls[:2]:
            entry = await self._probe_site(uni, hint)
            if entry:
                return entry
        # Missing or stale seed websites use the same explicitly configured
        # search provider. Only institution identity enters this query.
        from app.adapters.search import intent as intent_module

        if (
            intent_module.SHARED_QUERY_BUDGET
            and trace.search_queries_sent >= intent_module.DEFAULT_QUERY_BUDGET
        ):
            trace.search_limitations.append(
                "Identity search not run: earlier searches used the "
                f"{intent_module.DEFAULT_QUERY_BUDGET}-query budget."
            )
            return None
        try:
            provider = get_search_provider()
            # Charge the seam attempt, including local wrapper refusal. This
            # ledger is a budget, not proof of a vendor HTTP request.
            trace.charge_search_query_attempt()
            response = await provider.search(
                query=f'"{uni.name}" "{uni.country}" official university website', max_results=3
            )
            discovered = list(
                dict.fromkeys(
                    f"https://{urlsplit(r.url).hostname}/"
                    for r in response.results
                    if urlsplit(r.url).hostname
                )
            )
        except SearchError as exc:
            trace.search_failures.append(
                search_failure_diagnostic("configured search provider", exc)
            )
            return None
        for hint in discovered[:3]:
            if hint not in urls:
                entry = await self._probe_site(uni, hint)
                if entry:
                    return entry
        return None

    async def _probe_site(self, uni: University, hint: str) -> dict | None:
        parts = urlsplit(hint)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return None
        try:
            public_domain(parts.hostname)
        except ValueError:
            return None
        # Verify the site's own homepage, not an aggregator's profile page.
        url = f"https://{parts.hostname}/"
        page = await self.fetcher.get(url)
        final = page.final_url or url
        if not page.ok or not same_source_site(url, final):
            return None
        soup = BeautifulSoup(page.content or page.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        headings = " ".join(h.get_text(" ", strip=True) for h in soup.find_all("h1"))
        identity_text = normalize(f"{title} {headings}")
        names = [normalize(canonical_name(n)) for n in [uni.name, *(uni.aliases or [])]]
        long_match = any(len(n) >= 8 and n in identity_text for n in names)
        # Some institutions are publicly named by an acronym (e.g. UCL).
        # Require the same whole token in both the hostname and page identity,
        # together with an institutional word; a substring such as "us" is not enough.
        host_label = normalize((parts.hostname or "").removeprefix("www.").split(".")[0])
        acronym_match = any(
            3 <= len(n) < 8
            and " " not in n
            and n == host_label
            and re.search(rf"\b{re.escape(n)}\b", identity_text)
            for n in names
        ) and any(word in identity_text.split() for word in ("university", "college", "institute"))
        excerpt = f"{title} {headings}".strip()
        identity_basis = None
        if not long_match and not acronym_match:
            # Additional branding can corroborate an existing domain hint. It
            # cannot authorize an unrelated host returned by a search provider.
            branding = (
                _site_branding(
                    soup,
                    [normalize(n) for n in [uni.name, *(uni.aliases or [])]],
                    (uni.city or "", uni.country or ""),
                )
                if SITE_BRANDING_IDENTITY
                and uni.domain
                and registrable_domain(parts.hostname) == uni.domain
                else None
            )
            if branding is None:
                return None
            excerpt, identity_basis = branding
        domain = registrable_domain(urlsplit(final).hostname or "")
        proof = {
            "kind": "site_identity",
            "source_url": final,
            "accessed_at": page.fetched_at.isoformat(),
            "excerpt": excerpt,
            "name": uni.name,
            "domain": domain,
            "verification_status": "site_identity_checked",
        }
        if identity_basis is not None:
            proof["identity_basis"] = identity_basis
        digest = hashlib.sha256(str(proof).encode()).hexdigest()
        observation_id = stable_id(f"{uni.id}/{digest}")
        if self.session.get(UniversityObservation, observation_id) is None:
            self.session.add(
                UniversityObservation(
                    id=observation_id,
                    university_id=uni.id,
                    fingerprint=digest,
                    seed_version="live-site-identity",
                    payload=proof,
                )
            )
        uni.domain = domain
        uni.domain_status = "site_identity_checked"
        self.session.flush()
        return {"name": uni.name, "country": uni.country, "city": uni.city, "homepage": final}
