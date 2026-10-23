"""Bounded decision-episode Fetcher.get reservations; no clock or HTTP-count claim."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from contextvars import ContextVar
from copy import deepcopy
from typing import Any

from app.adapters.base import Candidate
from app.adapters.fetching import Fetcher, FetchResult
from app.pipeline.control import UniversityReadStopped

UNIVERSITY_READ_BUDGET = False
READ_LIMIT = 60
LEDGER_KEY = "university_research_budget_v1"
ACTIVE_UNIVERSITY: ContextVar[str | None] = ContextVar("research_read_university", default=None)


def university_key(candidate: Candidate) -> str:
    """An imported row's id wins; curated identity retains qualifiers and punctuation."""
    if candidate.catalogue_id is not None:
        if not isinstance(candidate.catalogue_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9:._-]{0,127}", candidate.catalogue_id
        ):
            raise UniversityReadStopped("invalid_catalogue_identity")
        return "catalogue:" + candidate.catalogue_id
    values = []
    for value in (candidate.name, candidate.country):
        if not isinstance(value, str):
            raise UniversityReadStopped("missing_curated_identity")
        normalized = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
        if not normalized:
            raise UniversityReadStopped("missing_curated_identity")
        values.append(normalized)
    digest = hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()
    return "curated:" + digest


def validate_ledger(value: Any) -> dict:
    """Reject corrupt/incompatible known fields; preserve opaque future fields."""
    if (
        not isinstance(value, dict)
        or type(value.get("version")) is not int
        or value["version"] != 1
    ):
        raise UniversityReadStopped("invalid_ledger")
    if type(value.get("read_limit")) is not int or value["read_limit"] != READ_LIMIT:
        raise UniversityReadStopped("invalid_ledger")
    episodes = value.get("episodes")
    if not isinstance(episodes, dict):
        raise UniversityReadStopped("invalid_ledger")
    active = value.get("active_episode")
    if not isinstance(active, str) or active not in episodes:
        raise UniversityReadStopped("invalid_ledger")
    for episode_id, episode in episodes.items():
        if (
            not isinstance(episode_id, str)
            or not re.fullmatch(r"decision:[A-Za-z0-9][A-Za-z0-9:._-]{0,127}", episode_id)
            or not isinstance(episode, dict)
        ):
            raise UniversityReadStopped("invalid_ledger")
        counts = episode.get("read_counts")
        if not isinstance(counts, dict):
            raise UniversityReadStopped("invalid_ledger")
        for key, count in counts.items():
            valid_key = isinstance(key, str) and re.fullmatch(
                r"catalogue:[A-Za-z0-9][A-Za-z0-9:._-]{0,127}|curated:[0-9a-f]{64}", key
            )
            if not valid_key or type(count) is not int or not 0 <= count <= READ_LIMIT:
                raise UniversityReadStopped("invalid_ledger")
    return deepcopy(value)


def new_ledger() -> dict:
    return {"version": 1, "read_limit": READ_LIMIT, "active_episode": None, "episodes": {}}


def copy_snapshot_with_ledger(snapshot: dict, durable_snapshot: dict) -> dict:
    """Whole JSON replacement, preserving the durable envelope without nested mutation."""
    replacement = deepcopy(snapshot)
    if LEDGER_KEY in durable_snapshot:
        replacement[LEDGER_KEY] = deepcopy(durable_snapshot[LEDGER_KEY])
    else:
        replacement.pop(LEDGER_KEY, None)
    return replacement


class BudgetedFetcher(Fetcher):
    """The original Fetcher.get is entered only after the caller's durable fence."""

    def __init__(self, *args, before_get: Callable[[], None], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.before_get = before_get

    async def get(
        self,
        url: str,
        *,
        use_cache: bool = True,
        etag: str | None = None,
        if_modified_since: str | None = None,
    ) -> FetchResult:
        self.before_get()
        return await super().get(
            url, use_cache=use_cache, etag=etag, if_modified_since=if_modified_since
        )
