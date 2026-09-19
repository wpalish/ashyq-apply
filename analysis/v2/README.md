# ASHYQ Apply v2 — START HERE

**Purpose:** execution pack for an AI coding agent (Claude Code / Codex or equivalent) implementing the next architecture of ASHYQ Apply.

**Snapshot used to prepare this pack:** 2026-09-20  
**Repository:** `wpalish/ashyq-apply`

This pack does **not** replace the repository's existing engineering constitution. The agent must obey, in this order:

1. `AGENTS.md`
2. `docs/process/HANDOFF.md`
3. accepted ADRs under `docs/adr/`
4. current owner-approved decisions/invariants in `analysis/AI_TASK_BRIEF.md` and `analysis/SPEC_matching_v2.md`
5. this pack

If this pack conflicts with an already accepted repository decision, **do not silently override the repository**. Record the conflict in `HANDOFF.md` and continue with all non-conflicting work.

## Mission

Evolve ASHYQ Apply from a small evidence-backed shortlisting prototype into a reliable, scalable university and scholarship research platform.

The core product promise is:

> Important admissions facts must be traceable to evidence, scoped to the correct programme/intake/population, and allowed to remain UNKNOWN rather than invented.

The implementation priority is:

```text
MEASURE
  ↓
IMPROVE DISCOVERY
  ↓
IMPROVE SCOPE / CLAIM RELIABILITY
  ↓
PERSIST AND REUSE EVIDENCE
  ↓
SCHOLARSHIP INTELLIGENCE
  ↓
BENCHMARK JEV / OTHER MODELS
  ↓
DEPLOY ONLY WHAT BEATS BASELINES
```

Do **not** start by replacing the system with an LLM agent or with Jev.

## First session — mandatory

Before changing code:

```bash
git fetch --all --prune
python scripts/handoff_check.py
```

Then:

1. Read `AGENTS.md` and `docs/process/HANDOFF.md` in full.
2. Verify the actual current `main`. Do not trust dated numbers in README/HANDOFF without checking git/tests.
3. Inspect all open PRs that can affect this programme of work.
4. Reconcile the current state before creating a new branch.
5. Run the repository's required fast/full gates appropriate to the task.
6. Write the exact next step into `HANDOFF.md` **before code**, as required by `AGENTS.md`.

At the 2026-09-20 research snapshot, relevant open PRs included:
- PR #13: event-loop blocking/offloading in crawler paths
- PR #11: security/paywall hardening
- PR #10: frontend redesign
- PR #1: older production-hardening branch

These are only a historical snapshot. **Re-check GitHub before acting. Do not merge them automatically.**

## Rules that must survive every phase

- `UNKNOWN`, `NOT_FOUND`, `NEEDS_OFFICIAL_CLARIFICATION` are legitimate results.
- Never manufacture a value because the user would prefer a complete answer.
- Aggregators may discover sources; they do not silently become authoritative evidence.
- The search/discovery stage should not contain applicant PII unless technically necessary and explicitly authorized.
- Keep final eligibility arithmetic, funding arithmetic, provenance, freshness and ranking deterministic.
- No model output may bypass source/provenance checks.
- No AI model is allowed to turn an unsupported statement into a verified Claim.
- Do not describe fit/ranking as admission probability.
- Do not bypass robots.txt, CAPTCHAs, authentication, paywalls or access controls.
- Tests must not depend on live internet or live AI providers.
- Live canaries/benchmarks are separate, explicit, bounded commands.
- Do not commit secrets, applicant data, raw private documents, `.env` files or provider keys.

## Definition of success

The system is not successful because it “uses AI”.

It is successful when measurable product quality improves:

- exact programme-page recall rises;
- exact programme-page precision remains very high;
- wrong-scope claims fall;
- unsupported claims stay near zero;
- scholarship applicability becomes evidence-backed;
- latency and marginal cost fall due to reuse/caching;
- every important answer remains auditable;
- human-review rate declines without sacrificing correctness.

Start with `01_MASTER_IMPLEMENTATION_PROMPT.md`.
