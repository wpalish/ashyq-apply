"""Preregistered recall experiments; scheduling/auditing never makes live calls."""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUBJECTS = frozenset({"computer_science", "business_administration", "mechanical_engineering"})
ROUTES = frozenset({"nis", "kazakhstan_school_certificate"})
MATRIX = {(subject, route) for subject in SUBJECTS for route in ROUTES}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Variant(StrEnum):
    BASELINE = "A_strict_baseline"
    FRONTIER = "B_question_frontier"
    SHARED = "C_shared_evidence"
    SEMANTIC = "D_semantic_fallback"


class Tier(Strict):
    seconds: int
    queries: int
    reads: int
    model_calls: int = 12
    input_tokens: int = 200000
    output_tokens: int = 20000


TIERS = (
    Tier(seconds=120, queries=6, reads=60),
    Tier(seconds=300, queries=12, reads=120),
    Tier(seconds=900, queries=24, reads=240),
    Tier(seconds=1800, queries=24, reads=240),
)


class Request(Strict):
    id: str = Field(min_length=1)
    university_id: str = Field(min_length=1)
    subject: Literal["computer_science", "business_administration", "mechanical_engineering"]
    route: Literal["nis", "kazakhstan_school_certificate"]
    # Missing programmes are preregistered questions too, not sampling failures.
    requested_programme: str = Field(min_length=1)
    cycle: str = Field(min_length=1)


class Freeze(Strict):
    code_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompts_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    catalogue_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    cache_policy: Literal["isolated_cold_then_warm"] = "isolated_cold_then_warm"


class Manifest(Strict):
    version: Literal[1] = 1
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    split: Literal["development", "validation"]
    custodian: str = Field(min_length=1)
    # A declaration is not verified automatically. Keep its receipt for review.
    sampling_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    gold_commitment_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    development_university_ids: frozenset[str] = frozenset()
    requests: tuple[Request, ...]
    freeze: Freeze
    seed: int = 90

    @model_validator(mode="after")
    def cohort(self) -> Manifest:
        if not self.custodian.strip():
            raise ValueError("custodian identity is required")
        if len({r.id for r in self.requests}) != len(self.requests):
            raise ValueError("duplicate request identity")
        grouped: dict[str, list[Request]] = defaultdict(list)
        for request in self.requests:
            grouped[request.university_id].append(request)
        expected = 30 if self.split == "development" else 60
        if len(grouped) != expected:
            raise ValueError(f"{self.split} requires exactly {expected} universities")
        for rows in grouped.values():
            if len(rows) != 6 or {(r.subject, r.route) for r in rows} != MATRIX:
                raise ValueError("each university requires every subject and qualification route")
            if len({r.cycle for r in rows}) != 1:
                raise ValueError("university requests must share one cycle")
        if self.split == "validation":
            if len(self.development_university_ids) != 30:
                raise ValueError("validation requires frozen development university identities")
            if set(grouped) & self.development_university_ids:
                raise ValueError("development and validation universities overlap")
        return self

    def digest(self) -> str:
        # Sort sets explicitly so the receipt is stable across Python processes.
        payload = self.model_dump(mode="json")
        payload["development_university_ids"] = sorted(self.development_university_ids)
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class ScheduledRun(Strict):
    id: str
    manifest_sha256: str
    university_id: str
    request_ids: tuple[str, ...]
    variant: Variant
    comparator: Variant
    tier: Tier
    position: int
    cache_namespace: str


def schedule(manifest: Manifest, tier: Tier) -> list[ScheduledRun]:
    if tier not in TIERS:
        raise ValueError("budget tier was not preregistered")
    universities = sorted({r.university_id for r in manifest.requests})
    random.Random(manifest.seed).shuffle(universities)
    digest = manifest.digest()
    result = []
    for university in universities:
        requests = tuple(sorted(r.id for r in manifest.requests if r.university_id == university))
        for comparator in (Variant.FRONTIER, Variant.SHARED, Variant.SEMANTIC):
            for position, variant in enumerate(
                (Variant.BASELINE, comparator, comparator, Variant.BASELINE)
            ):
                identity = hashlib.sha256(
                    json.dumps(
                        [
                            digest,
                            university,
                            comparator,
                            tier.model_dump(),
                            position,
                        ],
                        sort_keys=True,
                    ).encode()
                ).hexdigest()
                result.append(
                    ScheduledRun(
                        id=identity,
                        manifest_sha256=digest,
                        university_id=university,
                        request_ids=requests,
                        variant=variant,
                        comparator=comparator,
                        tier=tier,
                        position=position,
                        cache_namespace=f"{manifest.experiment_id}/{identity}",
                    )
                )
    return result


class RunReceipt(Strict):
    run_id: str
    manifest_sha256: str
    code_sha: str
    observed_freeze: Freeze
    request_ids: tuple[str, ...]
    outcome: Literal["complete", "partial", "unavailable", "refused"]
    queries: int | None = Field(default=None, ge=0)
    reads: int | None = Field(default=None, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0)
    model_calls: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cold_cost_usd: float | None = Field(default=None, ge=0)
    warm_cost_usd: float | None = Field(default=None, ge=0)
    capture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def audit_receipt(run: ScheduledRun, receipt: RunReceipt, manifest: Manifest) -> list[str]:
    failures = []
    if (
        receipt.run_id != run.id
        or receipt.manifest_sha256 != manifest.digest()
        or run.manifest_sha256 != manifest.digest()
    ):
        failures.append("experiment_identity_mismatch")
    if receipt.code_sha != manifest.freeze.code_sha:
        failures.append("code_changed_after_freeze")
    if receipt.observed_freeze != manifest.freeze:
        failures.append("configuration_changed_after_freeze")
    if set(receipt.request_ids) != set(run.request_ids) or len(receipt.request_ids) != 6:
        failures.append("missing_or_foreign_requests")
    for name, cap in (
        ("queries", run.tier.queries),
        ("reads", run.tier.reads),
        ("elapsed_seconds", run.tier.seconds),
        ("model_calls", run.tier.model_calls),
        ("input_tokens", run.tier.input_tokens),
        ("output_tokens", run.tier.output_tokens),
    ):
        value = getattr(receipt, name)
        if value is None:
            failures.append(f"missing_{name}_telemetry")
        elif value > cap:
            failures.append(f"{name}_cap_exceeded")
    # Failed/unavailable requests remain observations, but cannot pass a run gate.
    if receipt.outcome != "complete":
        failures.append("incomplete_run")
    return failures


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--tier", type=int, choices=range(4), default=0)
    args = parser.parse_args()
    manifest = Manifest.model_validate_json(args.manifest.read_bytes())
    print(
        json.dumps(
            [r.model_dump(mode="json") for r in schedule(manifest, TIERS[args.tier])], indent=2
        )
    )


if __name__ == "__main__":
    main()
