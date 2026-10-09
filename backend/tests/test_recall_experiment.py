"""Experimental integrity checks, not a synthetic live-quality benchmark."""

import pytest
from pydantic import ValidationError

from evaluation.research.recall_experiment import (
    MATRIX,
    TIERS,
    Freeze,
    Manifest,
    Request,
    RunReceipt,
    Variant,
    audit_receipt,
    schedule,
)


def manifest(split="development", offset=0, development=()):
    count = 30 if split == "development" else 60
    return Manifest(
        experiment_id="test-only",
        split=split,
        custodian="synthetic-test-custodian",
        sampling_receipt_sha256="a" * 64,
        gold_commitment_sha256="b" * 64,
        development_university_ids=frozenset(development),
        freeze=Freeze(
            code_sha="a" * 40,
            provider="fake",
            model="fake",
            prompts_sha256="c" * 64,
            config_sha256="d" * 64,
            catalogue_sha256="e" * 64,
        ),
        requests=tuple(
            Request(
                id=f"{index}-{subject}-{route}",
                university_id=f"u{index}",
                subject=subject,
                route=route,
                requested_programme=subject,
                cycle="2027",
            )
            for index in range(offset, offset + count)
            for subject, route in sorted(MATRIX)
        ),
    )


def test_preregistered_requests_include_all_directions_and_routes():
    value = manifest()
    assert len(value.requests) == 180
    with pytest.raises(ValidationError, match="every subject"):
        Manifest.model_validate({**value.model_dump(), "requests": value.requests[:-1]})


def test_validation_must_be_disjoint_from_frozen_development():
    dev = {f"u{i}" for i in range(30)}
    with pytest.raises(ValidationError, match="overlap"):
        manifest("validation", 0, dev)
    assert len(manifest("validation", 30, dev).requests) == 360


def test_abba_order_and_cache_isolation_are_reproducible():
    value = manifest()
    runs = schedule(value, TIERS[0])
    assert runs == schedule(value, TIERS[0])
    assert len(runs) == 30 * 3 * 4
    assert len({r.cache_namespace for r in runs}) == len(runs)
    for index in range(0, len(runs), 4):
        group = runs[index : index + 4]
        assert [r.variant for r in group] == [
            Variant.BASELINE,
            group[0].comparator,
            group[0].comparator,
            Variant.BASELINE,
        ]
        assert len({r.tier.model_dump_json() for r in group}) == 1
        assert len({r.request_ids for r in group}) == 1


def test_missing_telemetry_cannot_be_assumed_zero():
    value = manifest()
    run = schedule(value, TIERS[0])[0]
    receipt = RunReceipt(
        run_id=run.id,
        manifest_sha256=value.digest(),
        code_sha=value.freeze.code_sha,
        observed_freeze=value.freeze,
        request_ids=run.request_ids,
        outcome="complete",
        capture_sha256="f" * 64,
    )
    failures = audit_receipt(run, receipt, value)
    assert "missing_queries_telemetry" in failures
    assert receipt.cold_cost_usd is None and receipt.warm_cost_usd is None


def test_over_budget_and_failed_run_cannot_pass_receipt():
    value = manifest()
    run = schedule(value, TIERS[0])[0]
    receipt = RunReceipt(
        run_id=run.id,
        manifest_sha256=value.digest(),
        code_sha=value.freeze.code_sha,
        observed_freeze=value.freeze,
        request_ids=run.request_ids,
        outcome="refused",
        queries=7,
        reads=0,
        elapsed_seconds=2,
        model_calls=0,
        input_tokens=0,
        output_tokens=0,
        capture_sha256="f" * 64,
    )
    assert audit_receipt(run, receipt, value) == ["queries_cap_exceeded", "incomplete_run"]
