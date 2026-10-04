"""Offline public catalogue projection and a reproducible expert evaluation split.

The production importer runs only against a new in-memory SQLite database. No
configured database, reviewed corpus, identity bindings, or admission facts are
used as inputs to the public projection or to allocation of the cohort.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Table, create_engine, select
from sqlalchemy.orm import Session

from app.catalogue.importer import (
    REGISTRY_PATH,
    SEED_PATH,
    identity_key,
    import_catalogue,
    stable_id,
)
from app.models import Base, University, UniversityObservation

from .packet import build_packet, digest

DEFAULT_SPLIT_SEED = "unimatch-expert500-2026-10-04-v1"
SPLIT_VERSION = "unimatch-expert500-split.1"
PROFILE_VERSION = "kz-bachelor-cs-fall-2027.1"
PUBLIC_PROFILE: dict[str, Any] = {
    "level": "bachelor",
    "intended_fields": ["computer science"],
    "intake_term": "fall",
    "intake_year": 2027,
    "citizenship": "Kazakhstan",
    "country_of_residence": "Kazakhstan",
    "education_country": "Kazakhstan",
    "education_system": "KZ national secondary",
}

# Only public names/countries of the already used development universities.
# These are deliberately independent of the reviewed corpus and its answers.
PILOT_IDENTITIES = (
    ("groningen", "University of Groningen", "Netherlands"),
    ("delft", "Delft University of Technology", "Netherlands"),
    ("aalto", "Aalto University", "Finland"),
    ("vienna", "University of Vienna", "Austria"),
    ("warsaw", "University of Warsaw", "Poland"),
    ("ubc", "University of British Columbia", "Canada"),
    ("toronto", "University of Toronto", "Canada"),
    ("hku", "The University of Hong Kong", "Hong Kong"),
    ("ntu", "Nanyang Technological University", "Singapore"),
    ("kaist", "KAIST", "South Korea"),
)


@dataclass(frozen=True)
class CatalogueIdentity:
    """Explicit allowlist, with no seed record or curated research routes."""

    id: str
    name: str
    country: str
    city: str
    aliases: tuple[str, ...]
    domain: str | None


@dataclass(frozen=True)
class PublicCatalogue:
    identities: tuple[CatalogueIdentity, ...]
    seed_case_ids: tuple[str, ...]
    seed_version: str
    seed_sha256: str
    registry_sha256: str
    importer_sha256: str
    source_sha: str

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(sorted(identity.id for identity in self.identities))

    @property
    def extra_curated_case_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.case_ids) - set(self.seed_case_ids)))

    def provenance(self) -> dict[str, Any]:
        """Identify sealed catalogue inputs without revealing their contents."""
        return {
            "seed_version": self.seed_version,
            "seed_sha256": self.seed_sha256,
            "registry_sha256": self.registry_sha256,
            "importer_sha256": self.importer_sha256,
            "source_sha": self.source_sha,
            "identity_sha256": digest(
                [asdict(identity) for identity in sorted(self.identities, key=lambda item: item.id)]
            ),
            "catalogue_ids_sha256": digest(list(self.case_ids)),
            "seed_ids_sha256": digest(sorted(self.seed_case_ids)),
            "extra_curated_ids_sha256": digest(list(self.extra_curated_case_ids)),
        }


def _source_sha() -> str:
    """Read the local checkout revision; this command has no network operation."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _catalogue_index(catalogue: PublicCatalogue) -> dict[str, CatalogueIdentity]:
    index = {identity.id: identity for identity in catalogue.identities}
    if len(index) != len(catalogue.identities):
        raise ValueError("Duplicate catalogue identity ID")
    if len(catalogue.seed_case_ids) != len(set(catalogue.seed_case_ids)):
        raise ValueError("Duplicate seed catalogue identity ID")
    if set(catalogue.seed_case_ids) - index.keys():
        raise ValueError("Unknown seed catalogue identity ID")
    return index


def load_catalogue(
    seed_path: Path = SEED_PATH, *, source_sha: str | None = None
) -> PublicCatalogue:
    """Project the real importer into public identities in an isolated database.

    This never imports ``app.db`` or opens its configured engine. It creates only
    the two catalogue tables, closes the session, and disposes the memory engine.
    """
    seed_bytes = seed_path.read_bytes()
    document = json.loads(seed_bytes)
    revision = source_sha if source_sha is not None else _source_sha()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise ValueError("Catalogue source SHA must be a full Git revision")
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                cast(Table, University.__table__),
                cast(Table, UniversityObservation.__table__),
            ],
        )
        with Session(engine) as session:
            counts = import_catalogue(session, document)
            if counts["seed_records"] != 500 or counts["universities"] != 501:
                raise ValueError("Expected 500 seed identities and 501 imported identities")
            identities = tuple(
                CatalogueIdentity(
                    id=university.id,
                    name=university.name,
                    country=university.country,
                    city=university.city,
                    aliases=tuple(sorted(university.aliases or [])),
                    domain=university.domain,
                )
                for university in session.scalars(select(University).order_by(University.id))
            )
    finally:
        engine.dispose()
    catalogue = PublicCatalogue(
        identities=identities,
        seed_case_ids=tuple(
            sorted(
                stable_id(identity_key(row["name"], row["country"]))
                for row in document["universities"]
            )
        ),
        seed_version=f"{document['generated_on']}/{document['schema_version']}",
        seed_sha256=hashlib.sha256(seed_bytes).hexdigest(),
        registry_sha256=hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest(),
        importer_sha256=hashlib.sha256(SEED_PATH.with_name("importer.py").read_bytes()).hexdigest(),
        source_sha=revision,
    )
    _catalogue_index(catalogue)
    if len(catalogue.extra_curated_case_ids) != 1:
        raise ValueError("Expected one curated identity outside the seed cohort")
    return catalogue


def public_request(identity: CatalogueIdentity) -> dict[str, Any]:
    """Use the same public request as the ten-case bounded canary.

    A nationality in the profile does not imply a published population or
    qualification scope. Those, the academic year, and programme name stay null.
    """
    return {
        "university": identity.name,
        "programme": None,
        "degree": "bachelor",
        "field": "computer science",
        "intake": "fall 2027",
        "population": None,
        "qualification": None,
        "academic_year": None,
    }


def _validate_baseline(capture: dict[str, Any], known_ids: set[str]) -> None:
    """Refuse ambiguous identities and structured payloads in allowed fields."""
    config = capture.get("config")
    if not isinstance(config, dict):
        raise ValueError("Baseline must contain its bounded run configuration")
    calls = config.get("max_fetcher_calls_per_case")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 1:
        raise ValueError("Baseline Fetcher budget must be a positive integer")
    seconds = config.get("seconds_per_case")
    if (
        isinstance(seconds, bool)
        or not isinstance(seconds, int | float)
        or not 0 < seconds < float("inf")
    ):
        raise ValueError("Baseline elapsed budget must be a positive finite number")
    if not isinstance(config.get("browser_enabled"), bool):
        raise ValueError("Baseline browser policy must be explicit")
    queries = config.get("max_search_queries_per_case", 6)
    if isinstance(queries, bool) or not isinstance(queries, int) or queries < 1:
        raise ValueError("Baseline search query budget must be a positive integer")
    if not isinstance(capture.get("pipeline_sha"), str) or not capture["pipeline_sha"]:
        raise ValueError("Baseline must identify the captured pipeline")
    if not isinstance(capture.get("captured_at"), str) or not capture["captured_at"]:
        raise ValueError("Baseline must identify its capture time")
    observations = capture.get("observations")
    if not isinstance(observations, list):
        raise ValueError("Baseline must contain observations")
    seen: set[str] = set()
    for observation in observations:
        if not isinstance(observation, dict) or not isinstance(observation.get("case_id"), str):
            raise ValueError("Baseline observation must have a catalogue case ID")
        case_id = observation["case_id"]
        if case_id in seen:
            raise ValueError("Duplicate baseline observation")
        if case_id not in known_ids:
            raise ValueError(f"Unknown baseline catalogue ID: {case_id}")
        seen.add(case_id)
        for field in ("ranked_urls", "programme_urls"):
            urls = observation.get(field)
            if urls is None and field == "ranked_urls":
                continue
            if urls is None and field not in observation:
                continue
            if not isinstance(urls, list) or any(not isinstance(url, str) for url in urls):
                raise ValueError(f"Baseline {field} must contain only URL strings")
        if not isinstance(observation.get("predictions", []), list):
            raise ValueError("Baseline predictions must be a list")
        if observation.get("error") is not None and not isinstance(observation["error"], str):
            raise ValueError("Baseline error must be a string or null")
        telemetry = observation.get("telemetry", {})
        if not isinstance(telemetry, dict):
            raise ValueError("Baseline telemetry must be an object")
        for field in ("http_fetches", "pdf_fetches", "browser_fetches", "latency_seconds"):
            value = telemetry.get(field)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not 0 <= value < float("inf")
            ):
                raise ValueError(f"Invalid baseline telemetry: {field}")
    profile = config.get("public_profile")
    if profile is not None and profile != PUBLIC_PROFILE:
        raise ValueError("Baseline public profile differs from the catalogue request")


def build_catalogue_packet(
    catalogue: PublicCatalogue, capture: dict[str, Any], case_ids: Sequence[str]
) -> dict[str, Any]:
    """Prepare any catalogue identities with same-ID independent baselines.

    ``build_packet`` continues to own the existing packet allowlist. Its dataset
    input here is newly constructed from public identities, never a gold case.
    """
    index = _catalogue_index(catalogue)
    wanted = list(case_ids)
    if not wanted or len(wanted) != len(set(wanted)):
        raise ValueError("Choose at least one unique catalogue case ID")
    unknown = set(wanted) - index.keys()
    if unknown:
        raise ValueError(f"Unknown catalogue case ID: {sorted(unknown)}")
    _validate_baseline(capture, set(index))
    dataset = {
        "version": f"catalogue-public/{catalogue.seed_version}/{PROFILE_VERSION}",
        "cases": [
            {
                "id": identity.id,
                "university": identity.name,
                "domain": identity.domain,
                "request": public_request(identity),
            }
            for identity in sorted(catalogue.identities, key=lambda item: item.id)
        ],
    }
    packet = build_packet(dataset, capture, wanted)
    packet["public_profile"] = deepcopy(PUBLIC_PROFILE)
    packet["profile_version"] = PROFILE_VERSION
    packet["catalogue"] = catalogue.provenance()
    packet["comparison_mode"] = "independent_full_budget"
    packet["baseline_budget"]["max_search_queries"] = capture["config"].get(
        "max_search_queries_per_case", 6
    )
    return packet


def build_catalogue_split(
    catalogue: PublicCatalogue, split_seed: str = DEFAULT_SPLIT_SEED
) -> dict[str, Any]:
    """Allocate 350 DEV/150 HELDOUT from seed IDs, reserving all ten pilots.

    Rank IDs by SHA-256 of compact canonical JSON ``[split_seed, case_id]``.
    Reserve the known development identities before taking the first 340 other
    ranked identities. Input file order and admission facts cannot affect this.
    """
    index = _catalogue_index(catalogue)
    if len(catalogue.seed_case_ids) != 500:
        raise ValueError("The DEV/HELDOUT split requires exactly 500 seed identities")
    if not isinstance(split_seed, str) or not split_seed.strip():
        raise ValueError("Split seed must be a nonempty string")
    pilot_reservations = []
    seed_ids = set(catalogue.seed_case_ids)
    for pilot_id, name, country in PILOT_IDENTITIES:
        case_id = stable_id(identity_key(name, country))
        if case_id not in index or case_id not in seed_ids:
            raise ValueError(f"Pilot identity missing from the seed cohort: {name}")
        pilot_reservations.append(
            {
                "pilot_case_id": pilot_id,
                "university": name,
                "country": country,
                "catalogue_case_id": case_id,
            }
        )
    reserved = {item["catalogue_case_id"] for item in pilot_reservations}
    if len(reserved) != 10:
        raise ValueError("The ten pilot identities must be distinct")
    ranked = sorted(seed_ids, key=lambda case_id: (digest([split_seed, case_id]), case_id))
    natural_dev = set(ranked[:350])
    dev = reserved | set([case_id for case_id in ranked if case_id not in reserved][:340])
    heldout = seed_ids - dev
    return {
        "schema_version": "1",
        "manifest_version": SPLIT_VERSION,
        "catalogue": catalogue.provenance(),
        "split_seed": split_seed,
        "split_seed_sha256": hashlib.sha256(split_seed.encode("utf-8")).hexdigest(),
        "ranking_algorithm": "sha256(compact canonical JSON [split_seed, catalogue_case_id]); ascending; ID tiebreak",
        "DEV": sorted(dev),
        "HELDOUT": sorted(heldout),
        "excluded_curated_ids": list(catalogue.extra_curated_case_ids),
        "id_hashes": {
            "DEV": digest(sorted(dev)),
            "HELDOUT": digest(sorted(heldout)),
            "excluded_curated": digest(list(catalogue.extra_curated_case_ids)),
        },
        "pilot_reservations": pilot_reservations,
        "allocation_deviation": {
            "policy": "reserve_all_ten_previously_used_pilots_in_DEV",
            "reason": "Keep prior pilot source facts and routes out of HELDOUT; allocation uses public identities only.",
            "moved_from_seeded_HELDOUT_to_DEV": sorted(reserved - natural_dev),
            "moved_from_seeded_DEV_to_HELDOUT": sorted(natural_dev - dev),
            "heldout_source_facts_used": False,
        },
    }
