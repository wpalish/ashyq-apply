"""Experiment: does the current matching react to the applicant's profile?"""
from __future__ import annotations

import asyncio
import copy

from app.adapters.discovery.fixture_discovery import FixtureDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.config import get_settings
from app.corpus.demo_profile import DEMO_PROFILE
from app.domain.scoring import score_result
from app.db import init_db, session_scope
from app.models import ProgramResultRow
from app.schemas.result import ProgramResult


def variant(**changes):
    p = DEMO_PROFILE.model_copy(deep=True)
    for path, value in changes.items():
        section, field = path.split(".")
        setattr(getattr(p, section), field, value)
    return p


async def discover(profile, label):
    settings = get_settings().model_copy(update={"demo_mode": True})
    fetcher = Fetcher(settings.cache_dir, offline=True, corpus_dir=settings.corpus_dir)
    try:
        cands = await FixtureDiscoveryAdapter(fetcher).discover(profile, 40)
    finally:
        pass
    print(f"\n=== DISCOVERY: {label} ===")
    print(f"candidates: {len(cands)}  verifiable: {sum(1 for c in cands if c.verifiable)}")
    print("top-10:", [c.name[:22] for c in cands[:10]])
    return cands


def rescore(profile, label):
    with session_scope() as s:
        rows = s.query(ProgramResultRow).all()
        results = [ProgramResult.model_validate(r.payload) for r in rows]
    scored = []
    for r in results:
        sc = score_result(r, profile)
        scored.append((sc.total, r.university, r.climate_fit, r.country))
    scored.sort(reverse=True)
    print(f"\n=== RESCORE: {label} ===")
    for total, uni, clim, country in scored[:8]:
        print(f"  {total:5.2f}  {uni[:32]:33} {country[:14]:15} climate_fit={clim}")
    return scored


async def main():
    init_db()
    base = DEMO_PROFILE
    await discover(base, "baseline (CS, bachelor, temperate, NL/DE/CA/FI/BE)")
    await discover(variant(**{"context.intended_fields": ["medicine"]}), "field = medicine")
    await discover(variant(**{"context.intended_fields": ["mechanical engineering"]}), "field = mechanical engineering")
    await discover(variant(**{"context.intended_fields": ["cs"]}), "field = 'cs' (abbreviation)")
    await discover(variant(**{"context.intended_fields": ["Computer Science"]}), "field = 'Computer Science' (caps)")
    await discover(variant(**{"context.intended_fields": ["informatics"]}), "field = 'informatics' (synonym)")
    await discover(variant(**{"context.level": "master"}), "level = master")
    await discover(variant(**{"preferences.climate": "warm", "preferences.preferred_countries": ["Japan", "Australia", "Singapore"]}), "climate=warm, prefer JP/AU/SG")
    await discover(variant(**{"preferences.excluded_countries": ["Netherlands", "Canada", "Finland", "Belgium", "Germany"], "preferences.preferred_countries": []}), "exclude all baseline-preferred")

    base_scores = rescore(base, "baseline")
    warm = rescore(variant(**{"preferences.climate": "warm"}), "climate = warm")
    cold = rescore(variant(**{"preferences.climate": "cold"}), "climate = cold")
    # How much does climate move the top score?
    b = {u: t for t, u, _, _ in base_scores}
    w = {u: t for t, u, _, _ in warm}
    c = {u: t for t, u, _, _ in cold}
    deltas = sorted(((abs(w[u] - b[u]), u) for u in b), reverse=True)[:5]
    print("\nLargest |delta| when climate temperate->warm:", [(round(d, 2), u[:20]) for d, u in deltas])
    print("Rank order baseline == warm ?", [u for _, u, _, _ in base_scores] == [u for _, u, _, _ in warm])
    print("Rank order baseline == cold ?", [u for _, u, _, _ in base_scores] == [u for _, u, _, _ in cold])

    # Weight extremes
    hot = variant(**{"preferences.climate": "warm"})
    hot.weights.climate_fit = 3.0
    hot.weights.funding_fit = 0.0
    hot.weights.academic_fit = 0.0
    rescore(hot, "climate=warm with climate weight 3.0, funding & academic weight 0")


asyncio.run(main())
