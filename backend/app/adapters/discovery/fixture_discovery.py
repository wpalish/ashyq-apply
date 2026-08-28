"""Candidate discovery over the bundled catalogue."""

from __future__ import annotations

import json

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.ranking.fixture_rankings import FixtureRankingAdapter
from app.schemas.profile import ApplicantProfileIn


def _matches_field(program_field: str, wanted: list[str]) -> bool:
    if not wanted:
        return True
    pf = program_field.lower()
    return any(w.lower() in pf or pf in w.lower() for w in wanted)


class FixtureDiscoveryAdapter:
    name = "fixture-catalog"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher
        self.rankings = FixtureRankingAdapter(fetcher)

    async def discover(self, profile: ApplicantProfileIn, limit: int = 50) -> list[Candidate]:
        res = await self.fetcher.get("fixture://catalog.json")
        if not res.ok:
            return []
        rows = json.loads(res.text)
        prefs = profile.preferences
        excluded = {c.lower() for c in prefs.excluded_countries}
        preferred = {c.lower() for c in prefs.preferred_countries}
        wanted = profile.context.intended_fields

        out: list[Candidate] = []
        for row in rows:
            country = row["country"].lower()
            if country in excluded:
                continue

            programs = [
                CandidateProgram(name=p["name"], field=p["field"], degree=p["degree"], url=p["url"])
                for p in row.get("programs", [])
                if _matches_field(p["field"], wanted) and p["degree"] == profile.context.level
            ]
            # A catalogue entry with no programme detail is still a real lead;
            # it is carried through and reported as unverifiable rather than dropped.
            if row.get("programs") and not programs:
                continue

            entries, _ = await self.rankings.for_university(row["name"])
            out.append(
                Candidate(
                    name=row["name"],
                    country=row["country"],
                    city=row["city"],
                    domain=row.get("domain", ""),
                    programs=programs,
                    rankings=entries,
                    admissions_url=row.get("admissions_url"),
                    costs_url=row.get("costs_url"),
                    scholarships_url=row.get("scholarships_url"),
                    attributes={
                        k: row.get(k, "unknown")
                        for k in ("city_size", "climate", "size", "campus", "workload")
                    },
                    discovery_source="Bundled demo catalogue (synthetic)",
                    notes=row.get("exercises", ""),
                )
            )

        # Preferred countries first, then better-ranked, then verifiable ones.
        def sort_key(c: Candidate) -> tuple:
            pref = 0 if c.country.lower() in preferred else 1
            best = 9999
            for r in c.rankings:
                digits = "".join(ch for ch in r.position.split("-")[0] if ch.isdigit())
                if digits:
                    best = min(best, int(digits))
            return (pref, 0 if c.verifiable else 1, best, c.name)

        out.sort(key=sort_key)
        return out[:limit]
