# Expert recovery traces for ASHYQ research

## Purpose

Use an expert AI to diagnose where the existing research pipeline loses official evidence. Preserve the observed state and actual tool actions so another AI can reproduce the failure and test a general repair. A successful expert search is a candidate hypothesis, not a verified production rule or a new ground-truth label.

## Boundaries

- Evaluation tooling only under `backend/evaluation/research/expert/`; no production discovery, claim, or eligibility behavior changes in this slice.
- The certified ten-case corpus supplies public task requests and later adjudication. Preparation exports only case identity, institution, domain, and request. It never exports gold URLs, labels, values, excerpts, review notes, or programme evidence.
- The expert's executable workspace must contain the exported pack and curated algorithm context, but not the repository's gold corpus. A prompt prohibition alone is insufficient isolation.
- Official pages must be acquired under the same robots, egress, privacy, and fetch rules as the pipeline for an action to count as transferable. Any action using a different tool is recorded as `outside_policy` and cannot promote a rule.
- Preserve failed actions as well as successful ones. Log actions and observations, not hidden model reasoning or a retrospective story.
- A discovered fact remains a proposal until its exact source, excerpt, access date, programme identity, population, and year are independently checked. Do not change signed labels to improve scores.

## Data flow

1. `prepare` creates a blinded task pack from an explicit allowlist and records dataset/capture hashes and baseline observations. The pack excludes ground truth and scores.
2. An expert starts from the algorithm's recorded state and appends a structured trace: pre-action observation, action/tool, result, URL, budget, failure stage, and proposed evidence.
3. `validate` rejects missing provenance, post-hoc actions without observations, contradictory timestamps, leaked gold fields, and unreviewed claims represented as verified.
4. A reviewer compares each proposal with the sealed corpus and current official source. The outcome is recorded separately; the expert never edits the benchmark.
5. Hypotheses link to trace steps and distinguish `observed`, `candidate`, `tested`, `rejected`, and `promoted`. Promotion needs a replayable implementation, a paired baseline, and unseen cases with no precision or scope regression.

## Pilot

Use three different failure shapes: KAIST (correct page at rank 30 in the saved search probe), Toronto (campus ambiguity despite same registrable domain), and Aalto (correct page at rank 17 and an identity/language trap). Existing probe notes are retrospective observations, not blind expert traces. The first genuinely blinded expert run must use a newly exported pack and a separate workspace; the expert must not read `ground_truth.reviewed.json` or `SEARCH_PROBE.md` before submitting its trace.

## Success and falsification

Success is a small set of reproducible, transferable recovery hypotheses plus a downstream handoff that states exactly how to test them. `62/62` on the development corpus is neither a promotion gate nor an acceptable reason to overwrite UNKNOWN. Reject a hypothesis if the learner cannot perform the action, it relies on seeing gold data, it improves only a named university, or a paired unseen run loses a correct source or adds an unsupported/wrong-scope accepted claim.
