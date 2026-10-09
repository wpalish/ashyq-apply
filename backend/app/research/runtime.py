"""Strict JSON persistence for the staged runtime (no implicit ledger resets)."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from app.research.staging import LEDGER_KEY, StagedResearch

PROCESS_SESSION = str(uuid4())
INTENT_KEY = "research_intent"


def clock() -> dict:
    return {
        "session_id": PROCESS_SESSION,
        "monotonic_ms": time.monotonic_ns() // 1000000,
        "wall_at": datetime.now(UTC),
    }


def load(snapshot: dict) -> StagedResearch | None:
    if LEDGER_KEY not in snapshot:
        return None
    # JSON-mode validation is intentional: durable timestamps are strings.
    ledger = StagedResearch.model_validate_json(json.dumps(snapshot[LEDGER_KEY]))
    intent = snapshot.get(INTENT_KEY)
    if not isinstance(intent, dict) or intent.get("enabled") is not True:
        raise ValueError("staged ledger lacks durable enabled intent")
    if intent.get("mode") != ledger.research_mode or intent.get("deep_tier") != ledger.deep_tier:
        raise ValueError("staged intent/ledger mismatch")
    return ledger


def replace(snapshot: dict, ledger: StagedResearch) -> dict:
    result = deepcopy(snapshot)
    result[LEDGER_KEY] = json.loads(ledger.model_dump_json())
    return result


def enabled(snapshot: dict) -> bool:
    intent = snapshot.get(INTENT_KEY)
    return isinstance(intent, dict) and intent.get("enabled") is True
