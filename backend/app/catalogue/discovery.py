"""Bounded live enrichment of local identities through the existing discovery adapter."""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.adapters import fetching
from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import same_source_site
from app.adapters.search import SearchError, get_search_provider
from app.adapters.search.base import search_failure_diagnostic
from app.catalogue.importer import canonical_name, public_domain, stable_id
from app.catalogue.retrieval import retrieve
from app.domain.dedupe import normalize
from app.domain.site_identity import canonical_host, registrable_domain
from app.models import University, UniversityObservation
from app.schemas.profile import ApplicantProfileIn

#: Plan v3 rule R6 (stage 0 "Site identity", IG-1; wayfinder programme-discovery
#: tickets 05 Q2 and 16-Q8, owner 2026-10-18). Off: ``_probe_site`` keeps
#: today's rule only (the seed name in the homepage's title/h1, or an acronym
#: equal to the host label). On: identity is established when any of
#: (i) ``official_site`` - the homepage, after redirects, is on the seed row's
#: own ``official_site`` / ``official_domain`` host (``www.`` aside);
#: (ii) ``native_name`` - ``<html lang>`` is a language of the row's country and
#: the title holds the row's native-script name (fires only where a seed record
#: carries ``native_name``; none does today, 16-Q8);
#: (iii) ``english_alternate`` - the English name is on the homepage's English
#: alternate (``hreflang="en"``, else its language link), read once, on the same
#: registrable domain; (iv) ``title_name`` - today's rule. Whatever the branch,
#: no identity on a third-party host (never read), a parked domain, or a
#: homepage that names another institution or a unit of ours. The branch that
#: fired is the proof's ``proof`` field. On since paired runs 39113842507 /
#: 39113844090 (identity 8/10 dev2, 12/15 dev3; 0 losses) and the 6-query fix;
#: False turns it off.
SITE_IDENTITY_V2 = True

#: R6: registrable domains that are never an institution's own site: the
#: encyclopaedias, rankings, study portals and social hosts the identity
#: fallback search returns (dev2/dev3 gate run, 2026-10-18). ``google.*`` is
#: matched by its first label, ``studyin*`` national portals by their prefix.
_THIRD_PARTY_SITES = frozenset(
    {
        "wikipedia.org",
        "wikimedia.org",
        "wikidata.org",
        "wikiwand.com",
        "britannica.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "youtube.com",
        "tiktok.com",
        "bit.ly",
        "topuniversities.com",
        "timeshighereducation.com",
        "usnews.com",
        "shanghairanking.com",
        "cwur.org",
        "webometrics.info",
        "4icu.org",
        "unirank.org",
        "niche.com",
        "study.eu",
        "studyportals.com",
        "mastersportal.com",
        "bachelorsportal.com",
        "educations.com",
        "unipage.net",
        "hotcoursesabroad.com",
        "shiksha.com",
        "collegedunia.com",
        "academicstudies.com",
        "igminresearch.com",
        "ucas.com",
        "commonapp.org",
        "uni-assist.de",
    }
)
#: R6: words that make a title name an institution, for the "names another
#: institution" check. English only: a local word ("universitet") is how a
#: local-language homepage names its own university.
_INSTITUTION_WORDS = frozenset({"university", "college", "institute", "polytechnic"})
#: R6: name words that do not tell one institution from another.
_GENERIC_NAME_WORDS = frozenset(
    {
        "the",
        "of",
        "at",
        "for",
        "and",
        "in",
        "de",
        "del",
        "la",
        "di",
        "du",
        "des",
        "university",
        "universiti",
        "universitat",
        "universite",
        "universidad",
        "universidade",
        "universita",
        "universiteit",
        "college",
        "institute",
        "school",
        "polytechnic",
        "technology",
        "technological",
        "technical",
        "science",
        "sciences",
        "national",
        "state",
        "federal",
        "royal",
        "international",
    }
)
#: R6: a word right after our name that makes the page a unit's or a campus's
#: site, not the institution's ("... State University Business School").
_UNIT_WORDS = frozenset(
    {
        "business",
        "school",
        "faculty",
        "campus",
        "hospital",
        "press",
        "library",
        "alumni",
        "foundation",
        "museum",
    }
)
#: R6: the text of a parked or for-sale domain.
_PARKED_DOMAIN = re.compile(
    r"\bdomain\s+(?:name\s+)?(?:is\s+|may\s+be\s+)?for\s+sale\b|\bbuy\s+this\s+domain\b"
    r"|\bthis\s+domain\s+(?:is|has\s+been)\s+(?:parked|registered)\b|\bparked\s+(?:free|domain)\b"
    r"|\bdomain\s+parking\b|\bsedoparking\b|\bparkingcrew\b|\bbodis\.com\b|\bafternic\b"
    r"|\bhugedomains\b|\bdan\.com\b",
    re.IGNORECASE,
)
#: R6 (iii): the label of a homepage's language link to its English version.
_ENGLISH_LINK_LABELS = frozenset({"english", "en", "eng", "english version"})
#: R6 (ii): the ``<html lang>`` primary subtags of each catalogue country's
#: languages (official and main teaching languages; dictionary facts).
_COUNTRY_LANGUAGES: dict[str, frozenset[str]] = {
    country: frozenset(codes.split())
    for country, codes in {
        "Argentina": "es",
        "Australia": "en",
        "Austria": "de",
        "Belgium": "nl fr de",
        "Brazil": "pt",
        "Brunei Darussalam": "ms en",
        "Canada": "en fr",
        "Chile": "es",
        "China": "zh",
        "Colombia": "es",
        "Costa Rica": "es",
        "Czechia": "cs",
        "Denmark": "da",
        "Egypt": "ar",
        "Estonia": "et",
        "Finland": "fi sv",
        "France": "fr",
        "Germany": "de",
        "Greece": "el",
        "Hong Kong": "zh en",
        "India": "hi en",
        "Indonesia": "id",
        "Iran": "fa",
        "Ireland": "en ga",
        "Israel": "he",
        "Italy": "it",
        "Japan": "ja",
        "Jordan": "ar",
        "Kazakhstan": "kk ru",
        "Lebanon": "ar fr",
        "Lithuania": "lt",
        "Luxembourg": "lb fr de",
        "Macao": "zh pt",
        "Malaysia": "ms",
        "Mexico": "es",
        "Netherlands": "nl",
        "New Zealand": "en mi",
        "Norway": "no nb nn",
        "Oman": "ar",
        "Pakistan": "ur en",
        "Peru": "es",
        "Philippines": "fil tl en",
        "Poland": "pl",
        "Portugal": "pt",
        "Qatar": "ar",
        "Russia": "ru",
        "Saudi Arabia": "ar",
        "Singapore": "en zh ms ta",
        "South Africa": "en af zu xh",
        "South Korea": "ko",
        "Spain": "es ca eu gl",
        "Sweden": "sv",
        "Switzerland": "de fr it rm",
        "Taiwan": "zh",
        "Thailand": "th",
        "Turkey": "tr",
        "United Arab Emirates": "ar",
        "United Kingdom": "en cy",
        "United States": "en",
        "Uzbekistan": "uz ru",
    }.items()
}


def _third_party_host(host: str) -> bool:
    """R6: an aggregator, registry, portal or social host - never a university's site."""
    site = registrable_domain(host)
    first = site.split(".")[0]
    return site in _THIRD_PARTY_SITES or first == "google" or first.startswith("studyin")


def _identity_parts(soup: BeautifulSoup) -> tuple[str, str]:
    """R6: the page's declared name - title, every h1, ``og:site_name`` - raw and normalized."""
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    headings = " ".join(h.get_text(" ", strip=True) for h in soup.find_all("h1"))
    site_names = " ".join(
        str(m.get("content") or "")
        for m in soup.find_all("meta")
        if m.get("property") == "og:site_name"
    )
    raw = " ".join(part for part in (title, headings, site_names) if part)
    return raw, normalize(raw)


def _english_names(uni: University) -> list[str]:
    """R6: the row's normalized English names, each also without a leading "the"."""
    names = [normalize(canonical_name(n)) for n in [uni.name, *(uni.aliases or [])]]
    names += [n.removeprefix("the ") for n in names if n.startswith("the ")]
    return list(dict.fromkeys(n for n in names if n))


def _names_us(names: list[str], host: str, identity_text: str) -> bool:
    """R6 (iii)/(iv): today's name test, on whole words, refusing a unit's site.

    A long name (>= 8 characters) must occur as whole words and not run on
    into a unit word; an acronym (3-7 characters) must equal the host label and
    stand with an institutional word, as today.
    """
    padded = f" {identity_text} "
    for name in names:
        if len(name) < 8:
            continue
        for match in re.finditer(rf"(?<=\s){re.escape(name)}(?=\s)", padded):
            following = padded[match.end() :].split()[:1]
            if not following or following[0] not in _UNIT_WORDS:
                return True
    host_label = normalize(host.removeprefix("www.").split(".")[0])
    words = identity_text.split()
    return any(
        3 <= len(n) < 8 and " " not in n and n == host_label and n in words for n in names
    ) and any(word in words for word in ("university", "college", "institute"))


def _names_other_institution(names: list[str], identity_text: str) -> bool:
    """R6: the page names an institution in English and shares no distinctive word with us."""
    words = set(identity_text.split())
    if not words & _INSTITUTION_WORDS:
        return False
    ours = {
        token
        for name in names
        for token in name.split()
        if len(token) >= 3 and token not in _GENERIC_NAME_WORDS
    } | {name for name in names if " " not in name and 2 <= len(name) <= 7}
    return not ours & words


def _refused_page(names: list[str], soup: BeautifulSoup, identity_text: str) -> bool:
    """R6: a parked domain, or a page that names another institution, proves nothing."""
    text = f"{identity_text} {soup.get_text(' ', strip=True)[:20000]}"
    return bool(_PARKED_DOMAIN.search(text)) or _names_other_institution(names, identity_text)


def _row_hosts(uni: University) -> frozenset[str]:
    """R6 (i): the seed row's own hosts (``www.`` aside); none when its two hints disagree."""
    record = (uni.seed_snapshot or {}).get("record", {})
    hints = [record.get("official_domain"), urlsplit(record.get("official_site") or "").hostname]
    hosts = {canonical_host(h).removeprefix("www.") for h in hints if h}
    hosts.discard("")
    if len({registrable_domain(h) for h in hosts}) > 1:
        return frozenset()  # Conflicting hints are not resolved by guessing (importer).
    return frozenset(hosts)


def _native_name_match(uni: University, soup: BeautifulSoup) -> bool:
    """R6 (ii): ``<html lang>`` names a language of the country and the title holds the native name."""
    record = (uni.seed_snapshot or {}).get("record", {})
    native = record.get("native_name")
    natives = [native] if isinstance(native, str) else list(native or [])
    lang = str(soup.html.get("lang") or "") if soup.html else ""
    if lang.split("-")[0].lower() not in _COUNTRY_LANGUAGES.get(uni.country, frozenset()):
        return False
    title = normalize(soup.title.get_text(" ", strip=True) if soup.title else "")
    return any(len(n) >= 3 and n in title for n in (normalize(str(v)) for v in natives))


def _english_alternate(soup: BeautifulSoup, final: str) -> tuple[str, str] | None:
    """R6 (iii): the homepage's English version on its own registrable domain, and how it was found.

    A declared ``<link rel="alternate" hreflang="en">`` first; else a link that
    declares ``hreflang="en"`` or whose whole label is "English"/"EN" (the
    language switcher). The homepage itself is not its own alternate.
    """
    site = registrable_domain(final)
    here = final.split("#")[0].rstrip("/")
    links: list[tuple[str, str]] = [
        (str(link.get("href") or ""), "hreflang")
        for link in soup.find_all("link")
        if "alternate" in (link.get("rel") or [])
        and str(link.get("hreflang") or "").lower().split("-")[0] == "en"
    ]
    links += [
        (str(a.get("href") or ""), "language_link")
        for a in soup.find_all("a", href=True)
        if str(a.get("hreflang") or "").lower().split("-")[0] == "en"
        or normalize(a.get_text(" ", strip=True)) in _ENGLISH_LINK_LABELS
    ]
    for href, via in links:
        url = urljoin(final, href.strip()).split("#")[0]
        if urlsplit(url).scheme not in {"http", "https"} or url.rstrip("/") == here:
            continue
        if registrable_domain(url) == site:
            return url, via
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
        #: R6: university id -> the identity branch that fired (``SITE_IDENTITY_V2`` only).
        self.site_identity_proofs: dict[str, str] = {}

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
            # RL-1: the site-identity probes are this institution's reads too.
            with fetching.charging(self.fetcher, uni.domain or "", "discovery"):
                entry = await self._identify_site(uni, trace)
        if entry is None:
            trace.search_limitations.append(
                f"Official website identity not established for {uni.name}; candidate retained without verified programme facts."
            )
            candidate.search_queries_used = trace.search_queries_sent
            return candidate, trace
        # The identity fallback query is this institution's too: it counts in
        # the shared per-institution budget, so discovery sends one fewer.
        self._queries_before_discovery = trace.search_queries_sent
        try:
            enriched, discovered = await self._discover_one(entry, profile)
        finally:
            self._queries_before_discovery = 0
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
            # Charged before it is sent: a query that fails still cost one.
            trace.search_queries_sent += 1
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
        if SITE_IDENTITY_V2 and _third_party_host(parts.hostname):
            # R6: an aggregator, registry or social host is never read for identity.
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
        evidence: dict[str, Any] = {}
        if SITE_IDENTITY_V2:
            branch = await self._identity_branch(uni, parts.hostname, soup, final, evidence)
            if branch is None:
                return None
            evidence["proof"] = branch
            self.site_identity_proofs[uni.id] = branch
        else:
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
            ) and any(
                word in identity_text.split() for word in ("university", "college", "institute")
            )
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
            **evidence,
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

    async def _identity_branch(
        self,
        uni: University,
        host: str,
        soup: BeautifulSoup,
        final: str,
        evidence: dict[str, Any],
    ) -> str | None:
        """R6: the first identity branch that holds for this homepage, or None.

        The free branches come first - (i) the row's own host, (ii) the native
        name, (iv) today's title rule - then (iii), which costs the one read of
        the English alternate. A parked page, or one that names another
        institution, establishes nothing whatever the branch.
        """
        names = _english_names(uni)
        _, identity_text = _identity_parts(soup)
        if _refused_page(names, soup, identity_text):
            return None
        final_host = canonical_host(final).removeprefix("www.")
        if final_host and final_host in _row_hosts(uni):
            return "official_site"
        if _native_name_match(uni, soup):
            return "native_name"
        if _names_us(names, host, identity_text):
            return "title_name"
        alternate = _english_alternate(soup, final)
        if alternate is None:
            return None
        url, via = alternate
        page = await self.fetcher.get(url)
        landed = page.final_url or url
        if not page.ok or not same_source_site(url, landed):
            return None
        if registrable_domain(landed) != registrable_domain(final):
            return None
        english = BeautifulSoup(page.content or page.text, "html.parser")
        raw, english_text = _identity_parts(english)
        if _refused_page(names, english, english_text) or not _names_us(names, host, english_text):
            return None
        evidence["english_alternate"] = {"url": landed, "via": via, "excerpt": raw}
        return "english_alternate"
