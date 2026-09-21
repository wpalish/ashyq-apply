"""The institution registry, read as identities rather than as seed lists.

`app.domain.entity_resolution` deliberately knows nothing about files: it
resolves against identities a caller hands it. This is the one place that
builds those identities, from the registry the owner maintains — the same
human-verified data `is_seed_host` already trusts, read a second way.

The key is the institution's **registrable domain**, not its name. A name is
how a page spells something and changes with the language it is written in; a
domain is what serves the pages, and two registry entries sharing one would be
a data error rather than two universities (a test says so).

Aliases and former names are read from the registry if it records them, and
that is all. Nothing here derives an alias from a name: the registry's
`seeds_verified_on` exists because this data is asserted by a person, and a
generated alias would wear that signature without having earned it.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from app.domain.claim_verifier import registrable_domain
from app.domain.entity_resolution import InstitutionIdentity

from .live_discovery import REGISTRY_PATH


def _identities(entries: list[dict]) -> list[InstitutionIdentity]:
    out: list[InstitutionIdentity] = []
    for entry in entries:
        urls = [entry.get("homepage") or ""]
        urls += [u for u in (entry.get("seeds") or {}).values() if u]
        hosts = [h for h in (urlparse(u).hostname or "" for u in urls) if h]
        domains = tuple(dict.fromkeys(registrable_domain(h) for h in hosts if h))
        if not domains:
            # An entry with no URL at all identifies nothing; it is a registry
            # bug, and inventing a key from its name would hide it.
            continue
        out.append(
            InstitutionIdentity(
                key=domains[0],
                name=str(entry.get("name") or ""),
                country=str(entry.get("country") or ""),
                domains=domains,
                aliases=tuple(entry.get("aliases") or ()),
                former_names=tuple(entry.get("former_names") or ()),
                source_urls=tuple(u for u in urls if u),
            )
        )
    return out


@lru_cache(maxsize=1)
def institution_identities() -> tuple[InstitutionIdentity, ...]:
    """Every institution the registry knows, as resolvable identities."""
    try:
        entries = json.loads(Path(REGISTRY_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - a broken registry is a deploy problem
        return ()
    return tuple(_identities(entries))
