# Expert Recovery Implementation Plan

> **For agentic workers:** Execute the tasks below in order in an isolated branch. A separate implementation agent is optional; this session proceeds inline under the owner's standing authorization.

**Goal:** Publish a reproducible, blinded expert-recovery protocol and an evidence-ranked hypothesis registry ready for the separate run agent.

**Architecture:** Keep teacher data and diagnostics in evaluation tooling. Export only public task inputs, capture real intervention events in a strict schema, and adjudicate against sealed ground truth after trace submission. No production rule is changed by this plan.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, JSON, existing research benchmark artifacts.

## Global constraints

- Keep signed `ground_truth.reviewed.json` and frozen baseline captures immutable.
- Never call a real provider or university website from tests.
- Search results are navigation hints; only official fetched sources can support facts.
- No applicant PII in provider inputs; no secrets or raw applicant records in Git.
- Keep rule status and evidence level explicit. A saved expert path is not a validated product improvement.

## Task 1 — Blinded work packet and trace contract

**Files:** `backend/evaluation/research/expert/{models,packet,__main__}.py`, `backend/tests/test_expert_recovery.py`, `backend/evaluation/research/expert/README.md`.

**Interfaces:** `build_packet(dataset: dict, capture: dict, case_ids: Sequence[str]) -> dict`; `validate_trace(trace: dict, packet: dict) -> ExpertTrace`.

- [x] Test that a packet for KAIST includes its request and baseline observations, but copies no signed URL, value, excerpt, or label key from the gold case. A baseline-produced URL may coincidentally equal a signed URL.
- [x] Implement explicit allowlist serialization and SHA-256 provenance. Reject unknown case IDs.
- [x] Test that each trace action has a prior observation, source/tool, timestamp, outcome, budget and stage; proposals cannot self-declare human verification.
- [x] Implement strict Pydantic models and the `prepare`/`validate` CLI commands. Test with a synthetic complete trace.
- [x] Document exact run commands, artifact locations, and the isolation boundary.

## Task 2 — First-failure analysis and hypothesis registry

**Files:** `backend/evaluation/research/expert/{diagnose,hypotheses}.py`, `backend/evaluation/research/expert/data/hypotheses.json`, `backend/tests/test_expert_diagnosis.py`.

**Interfaces:** `diagnose(dataset, capture, probe) -> list[FailureRecord]`; `validate_hypotheses(hypotheses, failure_records) -> None`.

- [x] Test the three pilot failure shapes against the committed capture and probe: absence in the old queue, low position in the later probe, and unproved top identity.
- [x] Implement stage classification using only measured fields. Emit `unmeasured` when the capture lacks a rank list; never infer a fetch from a candidate rank.
- [x] Record KAIST, Toronto and Aalto hypotheses with source artifact, expected gain, guard, counterexample, and falsification test. Mark them `candidate`, not `tested`.
- [x] Run deterministic offline diagnosis and compare its output to the curated registry.

## Task 3 — Adversarial review and downstream handoff

**Files:** `backend/evaluation/research/expert/HANDOFF_TO_RUNNER.md`, `docs/process/HANDOFF.md`, this plan.

- [x] Review packet construction for gold leakage and trace validation for fabricated evidence.
- [x] Review each hypothesis against counterexamples: unavailable page, wrong campus, wrong intake, provider drift, and budget expansion.
- [x] Write copy-ready commands, artifact contract, owner boundaries, stop conditions, and acceptance gates for the separate run agent.
- [ ] Run focused pytest, Ruff, mypy and repository gates appropriate to the changed evaluation code; record actual outcomes.
- [ ] Commit and push the branch; open a PR with the real verification record, and leave a precise next step in the relay.

## Completion check

The packet must contain no gold data, all three hypotheses must have honest candidate status, and the run agent must be able to start from `HANDOFF_TO_RUNNER.md` without chat history. A live blind expert trace and 62/62 claim recovery are separate measured follow-on work; do not report them as achieved by documentation or offline replay.
