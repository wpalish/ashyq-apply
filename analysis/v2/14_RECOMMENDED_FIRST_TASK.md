# RECOMMENDED FIRST TASK FOR THE CODING AGENT

## Do this first

Do **not** begin with Jev.

The first new v2 task should be:

> **V2-01 — Create a reproducible university-research benchmark harness and capture the current baseline.**

# Prompt to the coding agent

You are implementing V2-01 inside `wpalish/ashyq-apply`.

First obey `AGENTS.md` and reconcile `docs/process/HANDOFF.md`.

Your goal is to create a benchmark framework that scores the existing pipeline before any discovery-model rewrite.

## Required outputs

1. A versioned benchmark schema for:
   - university;
   - exact programme;
   - degree;
   - field;
   - intake;
   - country-specific rule;
   - IELTS;
   - SAT;
   - deadline;
   - tuition/fees;
   - scholarships and applicability;
   - required documents.

2. A repository location for manually verified benchmark cases.

3. At least 10 initial cases chosen to exercise different site architectures.

4. An offline benchmark runner that reports:
   - programme-page recall/precision;
   - claim precision/recall where labelled;
   - unsupported claim rate;
   - wrong-scope claim rate;
   - scholarship applicability precision/recall;
   - coverage separately from precision;
   - page/fetch counts;
   - latency/cost fields when available.

5. Fixtures/snapshots sufficient for CI to run without internet.

6. A separate explicit live-canary command that does not run in normal CI.

7. Documentation explaining how a human reviewer adds/updates a benchmark row.

## Non-goals

Do not:
- add Jev;
- add a paid search provider;
- rewrite discovery;
- change ranking;
- expand community;
- change payments;
- deploy anything;
- lower test coverage.

## Critical integrity rule

The benchmark data must not be imported by production discovery or extraction code.

Production must never be able to “look up the answer” from benchmark ground truth.

Add a guard/test if needed to enforce this separation.

## Acceptance

The task is complete only when:
- current pipeline can be scored reproducibly;
- precision and coverage are separate;
- UNKNOWN is not rewarded as correct coverage;
- at least 10 manually verified cases exist;
- existing repo gates remain green;
- a baseline artifact is produced and committed if repository policy permits benchmark artifacts;
- HANDOFF contains the exact next task: V2 discovery-provider abstraction.

If a live site changed while labeling, record the new evidence and dataset version. Do not modify a label merely to make the pipeline score better.
