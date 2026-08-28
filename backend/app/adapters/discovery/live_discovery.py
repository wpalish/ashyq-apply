"""Live candidate discovery against real university websites.

Discovery starts from a curated registry of institution homepages rather than a
search engine, for two reasons: search queries would carry applicant context
off-machine, and a homepage is a stable, robots-respecting entry point. From
there the adapter follows the site's own navigation to find the admissions,
fees and scholarship pages, using link-text heuristics.

Anything it cannot find is left as ``None``. The downstream adapters then
report NOT_FOUND honestly instead of substituting a guess.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RankingEntry

REGISTRY_PATH = Path(__file__).parent / "institution_registry.json"

_HINTS: dict[str, tuple[str, ...]] = {
    "admissions": ("international admission", "admission requirements", "entry requirements",
                   "how to apply", "admissions", "apply"),
    "costs": ("tuition", "fees", "cost of attendance", "costs", "tuition and fees"),
    "scholarships": ("scholarship", "financial aid", "funding", "grants", "bursar"),
    "programs": ("bachelor", "undergraduate", "master", "programmes", "programs", "study programmes"),
}
_MAX_LINKS_SCANNED = 400


class LiveDiscoveryAdapter:
    """Discovers real pages by walking a university's own navigation."""

    name = "live-institution-registry"

    def __init__(self, fetcher: Fetcher, registry_path: Path | None = None) -> None:
        self.fetcher = fetcher
        self.registry_path = registry_path or REGISTRY_PATH

    def _registry(self) -> list[dict]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text())

    async def discover(self, profile: ApplicantProfileIn, limit: int = 50) -> list[Candidate]:
        prefs = profile.preferences
        excluded = {c.lower() for c in prefs.excluded_countries}
        preferred = {c.lower() for c in prefs.preferred_countries}

        entries = [e for e in self._registry() if e["country"].lower() not in excluded]
        if preferred:
            entries.sort(key=lambda e: 0 if e["country"].lower() in preferred else 1)
        entries = entries[:limit]

        out: list[Candidate] = []
        for entry in entries:
            candidate = Candidate(
                name=entry["name"],
                country=entry["country"],
                city=entry.get("city", ""),
                domain=urlparse(entry["homepage"]).netloc,
                attributes=entry.get("attributes", {}),
                rankings=[
                    RankingEntry(**r) for r in entry.get("rankings", [])
                ],
                discovery_source=f"Institution registry -> {entry['homepage']}",
            )
            await self._locate_pages(candidate, entry, profile)
            out.append(candidate)
        return out

    async def _locate_pages(
        self, candidate: Candidate, entry: dict, profile: ApplicantProfileIn
    ) -> None:
        # Explicit URLs in the registry win; crawling is the fallback.
        candidate.admissions_url = entry.get("admissions_url")
        candidate.costs_url = entry.get("costs_url")
        candidate.scholarships_url = entry.get("scholarships_url")
        for p in entry.get("programs", []):
            candidate.programs.append(
                CandidateProgram(
                    name=p["name"], field=p.get("field", ""),
                    degree=p.get("degree", profile.context.level), url=p.get("url"),
                )
            )

        if all([candidate.admissions_url, candidate.costs_url, candidate.scholarships_url]):
            return

        res = await self.fetcher.get(entry["homepage"])
        if not res.ok:
            candidate.notes = f"Homepage unreachable ({res.outcome.value}); no pages located."
            return

        links = _harvest_links(res.text, res.final_url or entry["homepage"])
        if candidate.admissions_url is None:
            candidate.admissions_url = _best_match(links, _HINTS["admissions"])
        if candidate.costs_url is None:
            candidate.costs_url = _best_match(links, _HINTS["costs"])
        if candidate.scholarships_url is None:
            candidate.scholarships_url = _best_match(links, _HINTS["scholarships"])

        if not candidate.programs:
            wanted = [f.lower() for f in profile.context.intended_fields]
            for url, label in links:
                if wanted and not any(w in label.lower() for w in wanted):
                    continue
                if any(h in label.lower() for h in _HINTS["programs"]) or wanted:
                    candidate.programs.append(
                        CandidateProgram(
                            name=label[:120], field=wanted[0] if wanted else "",
                            degree=profile.context.level, url=url,
                        )
                    )
                if len(candidate.programs) >= 3:
                    break

        found = [n for n, v in (("admissions", candidate.admissions_url),
                                ("fees", candidate.costs_url),
                                ("scholarships", candidate.scholarships_url)) if v]
        candidate.notes = (
            f"Located from homepage navigation: {', '.join(found) or 'nothing'}."
            + ("" if len(found) == 3 else " Missing sections will be reported as not found.")
        )


def _harvest_links(html: str, base: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    base_host = urlparse(base).netloc
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True)[:_MAX_LINKS_SCANNED]:
        url = urljoin(base, a["href"])
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        # Stay on the institution's own domain: an off-site link is not an
        # official source for that institution.
        if base_host.split(".")[-2:] != parsed.netloc.split(".")[-2:]:
            continue
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:160]
        if label:
            out.append((url.split("#")[0], label))
    return out


def _best_match(links: list[tuple[str, str]], hints: tuple[str, ...]) -> str | None:
    """Prefer the earliest hint in the list — hints are ordered by specificity."""
    for hint in hints:
        for url, label in links:
            if hint in label.lower() or hint.replace(" ", "-") in url.lower():
                return url
    return None
