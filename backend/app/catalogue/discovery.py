"""Bounded live enrichment of local identities through the existing discovery adapter."""

from __future__ import annotations

import asyncio
import hashlib
import re
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
from app.schemas.profile import ApplicantProfileIn


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
        self.walker_outcomes = []
        candidates: list[Candidate] = []
        for index, uni in enumerate(rows):
            trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
            candidate = Candidate(
                name=uni.name,
                country=uni.country,
                city=uni.city,
                discovery_source=f"local-catalogue:{uni.id}",
                notes="Institution candidate; programme, cost and requirements need research.",
            )
            if index < self.live_limit:
                try:
                    candidate, trace = await asyncio.wait_for(
                        self._enrich(uni, profile, candidate, trace), timeout=300
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
        entry = uni.registry_entry
        if entry is None:
            entry = await self._identify_site(uni, trace)
        if entry is None:
            trace.search_limitations.append(
                f"Official website identity not established for {uni.name}; candidate retained without verified programme facts."
            )
            return candidate, trace
        enriched, discovered = await self._discover_one(entry, profile)
        discovered.search_failures[:0] = trace.search_failures
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
        try:
            provider = get_search_provider()
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
        if not long_match and not acronym_match:
            return None
        domain = registrable_domain(urlsplit(final).hostname or "")
        proof = {
            "kind": "site_identity",
            "source_url": final,
            "accessed_at": page.fetched_at.isoformat(),
            "excerpt": f"{title} {headings}".strip(),
            "name": uni.name,
            "domain": domain,
            "verification_status": "site_identity_checked",
        }
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
