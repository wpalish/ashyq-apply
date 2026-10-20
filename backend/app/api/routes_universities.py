"""A usable local catalogue even before a research run or during an outage."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.knowledge.claims as kb_claims
from app.api.tenancy import owned_profile
from app.catalogue.retrieval import retrieve
from app.config import Settings, get_settings
from app.db import get_session
from app.domain.message_keys import CAVEATS, match, stale_reason_message
from app.knowledge import (
    CORE_QUESTIONS,
    DOCUMENTS,
    KnowledgeBase,
    KnowledgeEntry,
    carried_stale_reasons,
    fact_caveat,
    load_knowledge_base,
    review_label,
    stale_reasons,
)
from app.knowledge.claims import covers, entry_for, tuition_value
from app.models import University
from app.schemas.profile import ApplicantProfileIn
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/universities", tags=["universities"])


@router.get("")
def universities(
    q: str = Query(default="", max_length=200),
    country: str = Query(default="", max_length=100),
    profile_id: str | None = None,
    verified: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> dict:
    preferred: list[str] = []
    excluded: list[str] = []
    profile: ApplicantProfileIn | None = None
    if profile_id:
        row = owned_profile(session, profile_id, principal)
        profile = ApplicantProfileIn.model_validate(row.payload)
        preferred = profile.preferences.preferred_countries
        excluded = profile.preferences.excluded_countries
    all_rows = list(session.scalars(select(University)))
    rows = retrieve(session, query=q, country=country, preferred=preferred, excluded=excluded)
    # None in live and demo mode: the response then reads exactly as before,
    # with ``knowledge`` and ``kb_total`` null and ``verified`` ignored.
    coverage = KnowledgeCoverage.for_request(get_settings(), profile)
    kb_total: int | None = None
    if coverage is not None:
        kb_total = sum(coverage.in_kb(u) for u in all_rows)
        if verified:
            rows = [u for u in rows if coverage.in_kb(u)]
    return {
        "total": len(rows),
        "catalogue_total": len(all_rows),
        "kb_total": kb_total,
        "seed_count": sum(u.seed_snapshot is not None for u in all_rows),
        "countries": sorted({u.country for u in all_rows}),
        "items": [
            {**view(u), "knowledge": coverage.block(u) if coverage is not None else None}
            for u in rows[offset : offset + limit]
        ],
    }


def view(u: University) -> dict:
    snapshot = u.seed_snapshot or {}
    record = snapshot.get("record") or {}
    return {
        "id": u.id,
        "name": u.name,
        "country": u.country,
        "city": u.city,
        "aliases": u.aliases,
        "domain": u.domain,
        "domain_status": u.domain_status,
        "identity_status": "curated" if u.registry_entry else "seed",
        "programme_status": "needs_research",
        "admissions_status": "unknown",
        "tuition_status": "needs_verification",
        "funding_status": "needs_research",
        "seed_tuition_usd": record.get("tuition_usd_estimate"),
        "seed_ranking": {"year": 2027, "rank": record.get("qs_rank_2027"), "status": "seed"}
        if record
        else None,
        "seed_version": u.seed_version,
        "observed_at": None,
        "sources": record.get("sources", {}),
    }


@lru_cache(maxsize=4)
def _knowledge_base(path: Path | None, imported: Path | None) -> KnowledgeBase:
    """The verified knowledge base, read once per process (two files, never the web)."""
    return load_knowledge_base(path, imported)


#: What the KB says about the CS programme page (``types.ts``: ``KbProgrammePage``).
PROGRAMME_PAGES = ("known", "related_only", "not_offered", "unknown")


def programme_page(entry: KnowledgeEntry) -> str:
    """``known`` / ``related_only`` / ``not_offered`` / ``unknown`` for the CS programme page.

    ``not_offered`` needs the build's explicit ``programme.offered: false``;
    ``related_only`` a related official route and no CS page. Nothing else
    says a programme is absent: a page nobody read is ``unknown``.
    """
    if entry.programme_known:
        return "known"
    if entry.programme.get("offered") is False:
        return "not_offered"
    if entry.programme.get("related_programme_urls"):
        return "related_only"
    return "unknown"


def fact_stale_reasons(fact: dict[str, Any], today: date, intake: str | None) -> list[str]:
    """Why a fact is not current: the rule ``claims.fact_claim`` applies in the run."""
    return list(
        dict.fromkeys([*stale_reasons(fact, today, intake), *carried_stale_reasons(fact, intake)])
    )


#: The block of a university the KB holds no verified data for.
NO_KNOWLEDGE: dict[str, Any] = {
    "in_kb": False,
    "programme_page": "unknown",
    "core_answered": 0,
    "documents": 0,
    "verified_on": None,
    "stale_count": 0,
    "review_label": None,
    "tuition": None,
}


class KnowledgeCoverage:
    """Per-university verified-data coverage for the catalogue cards (kb mode only)."""

    def __init__(
        self, kb: KnowledgeBase, *, applies: bool, intake: str | None, today: date
    ) -> None:
        self.kb = kb
        self.applies = applies
        self.intake = intake
        self.today = today
        self._entries: dict[str, KnowledgeEntry | None] = {}

    @classmethod
    def for_request(
        cls, settings: Settings, profile: ApplicantProfileIn | None
    ) -> KnowledgeCoverage | None:
        """None in live and demo mode (demo ignores the knowledge mode, as the runner does)."""
        if settings.demo_mode or settings.knowledge_mode != "kb":
            return None
        kb = _knowledge_base(settings.knowledge_base_path, settings.knowledge_imported_path)
        intake = f"{profile.context.intake_term} {profile.context.intake_year}" if profile else None
        # The KB answers a CS bachelor's only; for any other request the run
        # shows "no verified data yet", so the card says the same.
        applies = profile is None or covers(profile)
        return cls(kb, applies=applies, intake=intake, today=kb_claims.kb_today())

    def entry(self, u: University) -> KnowledgeEntry | None:
        """The entry the run would answer from (``KnowledgeDiscovery``), or None."""
        if not self.applies:
            return None
        if u.id not in self._entries:
            found = entry_for(self.kb, u)
            self._entries[u.id] = found if found is not None and found.has_verified_data else None
        return self._entries[u.id]

    def in_kb(self, u: University) -> bool:
        return self.entry(u) is not None

    def block(self, u: University) -> dict[str, Any]:
        entry = self.entry(u)
        if entry is None:
            return dict(NO_KNOWLEDGE)
        not_applicable = {str(n.get("question") or "") for n in entry.not_applicable}
        answered = sum(bool(entry.facts.get(q)) or q in not_applicable for q in CORE_QUESTIONS)
        stale = sum(
            bool(fact_stale_reasons(fact, self.today, self.intake))
            for _question, fact in entry.all_facts()
        )
        return {
            "in_kb": True,
            "programme_page": programme_page(entry),
            "core_answered": answered,
            "documents": len(entry.facts.get(DOCUMENTS) or []),
            "verified_on": entry.verified_on,
            "stale_count": stale,
            "review_label": review_label(entry.review_status),
            "tuition": self.tuition(entry),
        }

    def tuition(self, entry: KnowledgeEntry) -> dict[str, Any] | None:
        """The first KB fee with a figure, as published, under the run's stale and caveat rules."""
        for fact in entry.facts.get("tuition") or []:
            value = tuition_value(fact.get("value"))
            if value is None or not fact.get("source_url"):
                continue
            reasons = fact_stale_reasons(fact, self.today, self.intake)
            caveat = fact_caveat(fact)
            # Keyed beside the English, as on a served claim
            # (``message_keys.annotate_claim``), so ru and kk can say them.
            stale_messages = [stale_reason_message(r) for r in reasons]
            caveat_message = match(CAVEATS, caveat) if caveat else None
            return {
                "amount": value["amount"],
                "currency": value["currency"],
                "range_low": value.get("range_low"),
                "range_high": value.get("range_high"),
                "period": fact.get("period") or None,
                "academic_year": fact.get("academic_year") or None,
                "stale": bool(reasons),
                "stale_reasons": reasons,
                "stale_messages": [m.model_dump() if m else None for m in stale_messages],
                "caveat": caveat,
                "caveat_message": caveat_message.model_dump() if caveat_message else None,
                "source_url": str(fact["source_url"]),
            }
        return None
