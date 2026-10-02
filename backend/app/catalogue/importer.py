"""Deterministic import of identity hints and immutable seed observations."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.dedupe import normalize
from app.domain.site_identity import registrable_domain
from app.models import University, UniversityObservation

SEED_PATH = Path(__file__).with_name("unimatch_top500_seed.json")
REGISTRY_PATH = Path(__file__).parents[1] / "adapters/discovery/institution_registry.json"
COUNTRY_ALIASES = {
    "united states of america": "United States",
    "usa": "United States",
    "us": "United States",
    "uk": "United Kingdom",
    "china mainland": "China",
    "republic of korea": "South Korea",
    "korea": "South Korea",
    "hong kong sar china": "Hong Kong",
    "macao sar china": "Macao",
    "russian federation": "Russia",
    "turkiye": "Turkey",
    "czech republic": "Czechia",
}
NAME_ALIASES = {
    "nanyang technological university singapore": "Nanyang Technological University",
}


def country_name(value: str) -> str:
    return COUNTRY_ALIASES.get(normalize(value), value.strip())


def canonical_name(value: str) -> str:
    base = re.sub(r"\s*\([^()]+\)\s*$", "", value).strip()
    return NAME_ALIASES.get(normalize(base), base)


def identity_key(name: str, country: str) -> str:
    return f"{normalize(country_name(country))}::{normalize(canonical_name(name))}"


def stable_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def public_domain(value: object) -> str | None:
    if not value:
        return None
    if not isinstance(value, str):
        raise ValueError("Domain must be a hostname or null")
    value = value.lower().removeprefix("www.").rstrip(".")
    if (
        len(value) > 253
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value)
        or "." not in value
    ):
        raise ValueError(f"Invalid university domain: {value}")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ValueError("University domain must not be an IP address")
    if value.endswith((".local", ".localhost", ".internal", ".test", ".invalid")):
        raise ValueError("University domain must be public")
    return value


def validate_snapshot(document: dict) -> list[dict]:
    if document.get("schema_version") != "1.0":
        raise ValueError("Unsupported university seed schema")
    date.fromisoformat(document["generated_on"])
    rows = document.get("universities")
    if not isinstance(rows, list) or len(rows) != document.get("count") or not rows:
        raise ValueError("University count does not match the snapshot")
    keys: set[str] = set()
    ids: set[str] = set()
    domains: set[str] = set()
    for row in rows:
        for field, maximum in (("name", 300), ("country", 100), ("seed_id", 80)):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                raise ValueError(f"Invalid {field}")
        if row.get("city") is not None and (
            not isinstance(row["city"], str) or len(row["city"]) > 200
        ):
            raise ValueError("Invalid city")
        for source in (row.get("sources") or {}).values():
            parsed = urlsplit(source)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Invalid source URL")
        key = identity_key(row["name"], row["country"])
        if key in keys or row["seed_id"] in ids:
            raise ValueError("Duplicate university identity or seed identifier")
        keys.add(key)
        ids.add(row["seed_id"])
        domain = public_domain(row.get("official_domain"))
        if domain:
            if domain in domains:
                raise ValueError("Ambiguous shared university domain")
            domains.add(domain)
        if row.get("official_site"):
            site = urlsplit(row["official_site"])
            if site.scheme not in {"http", "https"} or site.username or site.password or site.port:
                raise ValueError("Invalid seed website")
            public_domain(site.hostname)
        if row.get("needs_live_refresh") is not True:
            raise ValueError("Seed facts must require live verification")
        cost = row.get("tuition_usd_estimate")
        if cost is not None:
            if (
                not isinstance(cost, dict)
                or not isinstance(cost.get("min"), int | float)
                or not isinstance(cost.get("max"), int | float)
            ):
                raise ValueError("Invalid seed tuition range")
            if not 0 <= cost["min"] <= cost["max"] < 10_000_000:
                raise ValueError("Invalid seed tuition range")
    return rows


def seed_domain(row: dict) -> str | None:
    domain = public_domain(row.get("official_domain"))
    site = public_domain(urlsplit(row.get("official_site") or "").hostname)
    if domain and site and registrable_domain(domain) != registrable_domain(site):
        return None  # Conflicting hints are preserved in the snapshot, not resolved by guessing.
    return registrable_domain(domain) if domain else None


def import_catalogue(session: Session, document: dict | None = None) -> dict[str, int]:
    document = document if document is not None else json.loads(SEED_PATH.read_text())
    rows = validate_snapshot(document)  # Validate everything before touching the database.
    version = f"{document['generated_on']}/{document['schema_version']}"
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(829004500)"))
    elif not session.in_transaction():
        session.execute(text("BEGIN IMMEDIATE"))
    existing = {u.identity_key: u for u in session.scalars(select(University))}
    registry = json.loads(REGISTRY_PATH.read_text())
    for entry in registry:
        key = identity_key(entry["name"], entry["country"])
        uni = existing.get(key)
        if uni is None:
            uni = University(
                id=stable_id(key),
                identity_key=key,
                name=entry["name"],
                country=country_name(entry["country"]),
                city=entry.get("city", ""),
                aliases=[],
            )
            session.add(uni)
            existing[key] = uni
        uni.registry_entry = entry
        uni.domain = public_domain(urlsplit(entry["homepage"]).hostname)
        uni.domain_status = "curated"
    known = {
        (o.university_id, o.fingerprint) for o in session.scalars(select(UniversityObservation))
    }
    observations = 0
    pending: list[UniversityObservation] = []
    for row in rows:
        key = identity_key(row["name"], row["country"])
        uni = existing.get(key)
        if uni is None:
            domain = seed_domain(row)
            uni = University(
                id=stable_id(key),
                identity_key=key,
                name=canonical_name(row["name"]),
                country=country_name(row["country"]),
                city=row.get("city") or "",
                aliases=[],
                domain=domain,
                domain_status="seed" if domain else "unknown",
            )
            session.add(uni)
            existing[key] = uni
        aliases = {uni.name, row["name"], *(uni.aliases or [])}
        suffix = re.search(r"\(([^()]+)\)$", row["name"])
        if suffix:
            aliases.add(suffix[1])
        uni.aliases = sorted(aliases)
        payload = {
            "record": row,
            "generated_on": document["generated_on"],
            "schema_version": document["schema_version"],
            "ranking_basis": document.get("ranking_basis"),
            "verification_status": "unverified_seed",
            "observed_at": None,
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if (uni.id, fingerprint) not in known:
            pending.append(
                UniversityObservation(
                    id=stable_id(f"{uni.id}/{fingerprint}"),
                    university_id=uni.id,
                    fingerprint=fingerprint,
                    seed_version=version,
                    payload=payload,
                )
            )
            observations += 1
        # Older imports remain history, never roll current seed pointers backwards.
        if not uni.seed_version or version >= uni.seed_version:
            uni.seed_snapshot = payload
            uni.seed_version = version
            if not uni.registry_entry and uni.domain_status in {"seed", "unknown"}:
                uni.domain = seed_domain(row)
                uni.domain_status = "seed" if uni.domain else "unknown"
    session.flush()
    session.add_all(pending)
    session.flush()
    return {
        "seed_records": len(rows),
        "universities": len(existing),
        "new_observations": observations,
    }


if __name__ == "__main__":
    from app.db import session_scope

    with session_scope() as db:
        print(json.dumps(import_catalogue(db), sort_keys=True))
