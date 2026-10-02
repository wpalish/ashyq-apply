"""Pure local candidate selection; seed tuition and tests never exclude anyone."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogue.importer import country_name
from app.domain.dedupe import normalize
from app.models import University

REGIONS = {
    "europe": {
        "Russia",
        "Turkey",
        "United Kingdom",
        "Germany",
        "Italy",
        "Spain",
        "France",
        "Netherlands",
        "Switzerland",
        "Sweden",
        "Belgium",
        "Ireland",
        "Finland",
        "Austria",
        "Denmark",
        "Portugal",
        "Norway",
        "Poland",
        "Greece",
        "Czechia",
        "Estonia",
        "Luxembourg",
        "Lithuania",
    },
    "asia": {
        "Russia",
        "Turkey",
        "China",
        "South Korea",
        "Japan",
        "India",
        "Malaysia",
        "Taiwan",
        "Hong Kong",
        "Indonesia",
        "Saudi Arabia",
        "United Arab Emirates",
        "Singapore",
        "Kazakhstan",
        "Israel",
        "Iran",
        "Qatar",
        "Thailand",
        "Lebanon",
        "Macao",
        "Jordan",
        "Pakistan",
        "Oman",
        "Brunei Darussalam",
        "Philippines",
        "Uzbekistan",
    },
    "north america": {"United States", "Canada", "Mexico", "Costa Rica"},
    "south america": {"Brazil", "Colombia", "Argentina", "Chile", "Peru"},
    "oceania": {"Australia", "New Zealand"},
    "africa": {"South Africa", "Egypt"},
}


def in_country(country: str, constraint: str) -> bool:
    return normalize(country) in {
        normalize(c) for c in REGIONS.get(normalize(constraint), {country_name(constraint)})
    }


def retrieve(
    session: Session,
    *,
    query: str = "",
    country: str = "",
    preferred: list[str] | None = None,
    excluded: list[str] | None = None,
    university_ids: list[str] | None = None,
) -> list[University]:
    rows = list(session.scalars(select(University)))
    tokens = normalize(query).split()
    selected = set(university_ids or [])
    rows = [
        u
        for u in rows
        if (not selected or u.id in selected)
        and (not country or in_country(u.country, country))
        and not any(in_country(u.country, c) for c in excluded or [])
        and all(
            t in normalize(" ".join([u.name, u.country, u.city, *(u.aliases or [])]))
            for t in tokens
        )
    ]
    # Known research routes help select useful first reads. QS prestige and
    # unscoped prices/tests do not determine applicant fit or exclude rows.
    return sorted(
        rows,
        key=lambda u: (
            0 if any(in_country(u.country, c) for c in preferred or []) else 1,
            0 if u.registry_entry else 1,
            normalize(u.name),
            u.id,
        ),
    )
