"""Ranking adapter over the bundled snapshot.

Rankings are discovery input only. Every claim produced here is stamped
AGGREGATOR specificity, which ``enforce_source_hierarchy`` uses to make sure a
ranking can never end up backing a requirement or a price.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.adapters.fetching import Fetcher
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity
from app.schemas.claim import Claim
from app.schemas.result import RankingEntry


class FixtureRankingAdapter:
    name = "fixture-rankings"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher
        self._cache: dict[str, list[dict]] | None = None

    async def _load(self) -> list[dict]:
        if self._cache is None:
            res = await self.fetcher.get("fixture://rankings.json")
            self._cache = {"rows": json.loads(res.text) if res.ok else []}
        return self._cache["rows"]

    async def for_university(self, name: str) -> tuple[list[RankingEntry], list[Claim]]:
        rows = await self._load()
        entries, claims = [], []
        for row in rows:
            if row["university"] != name:
                continue
            entries.append(
                RankingEntry(
                    source=row["source"],
                    year=row["year"],
                    position=str(row["position"]),
                    url="fixture://rankings.json",
                )
            )
            claims.append(
                Claim(
                    claim_type=ClaimType.RANKING_POSITION,
                    normalized_value={
                        "source": row["source"],
                        "year": row["year"],
                        "position": row["position"],
                    },
                    original_text_excerpt=f"{row['university']} — {row['source']} {row['year']}: {row['position']}",
                    source_url="fixture://rankings.json",
                    page_title="Ranking snapshot (demo fixture)",
                    official_domain=False,
                    accessed_at=datetime.now(UTC),
                    source_specificity=SourceSpecificity.AGGREGATOR,
                    status=ClaimStatus.UNVERIFIED,
                    confidence=0.5,
                    extraction_method="fixture",
                    notes="Ranking data is used for discovery and sorting only, never as proof of a requirement.",
                )
            )
        return entries, claims
