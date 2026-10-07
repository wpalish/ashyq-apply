# Claude search relay — 7 October 2026

## Start here

Status: in progress. Branch: `task/search-claude-relay`. Base: `1b2a554129f5744eb297848472f1c8fe8c7fde26` (main, PR #60 merged).
Local checkout: `/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply`.
This journal is committed/pushed so Claude can resume without this chat. Newest entries take precedence over older HANDOFF paragraphs.

## Authorization and session reviewed

Owner: “проанализируй сессию и продолжи его работу ... записывай в какой то файл”. Read-only native Claude session reviewed through computer use, no prompt sent and no model request made. Session ID `session_0142YLhoNdiGxNVtxJBDaNfX`, name “Привет”, branch `claude/greeting-16wj2z`.
Latest response: PR #60 merged; RL-1 in main; four open decisions: development-cohort extension, G-1 gold signature, free Exa capacity, Aalto/NTU Fly recheck. Earlier owner delegation is reported in the PR as “делай по своим рекомендациям”. The new continuation authorizes ordinary engineering decisions; it does not sign gold or authorize purchases.

## Confirmed starting state

- PR #59 and #60 are merged. Current main is `1b2a554`.
- Default rules: DF-1 and RL-1 on; TS-2/SR-2/SP-1 off after no measured gain. Check constants for exact implementation.
- Original fresh measurements are in `backend/evaluation/research/runs/2026-10-06/`; reviewed9 has 73 known labels.
- Control two-pass: reported 20/73 labels, 10/60 core. RL-1: reported 12/60 core, precision 1.0; this describes saved runs, not current general reliability.
- Heldout run 37554279823 timed out at 55 minutes. Claude reported 5/216 core, 7/9 programme misses and failed target 6. Completeness/denominator must be audited before treating this as a completed evaluation.
- `docs/process/HANDOFF.md` was stale: it still described draft8 and pending DL-2/BL-1. Updated active branch-specific entries; preserved history.
- Other local `task/expert-500-phase1` checkout has uncommitted funnel work. It was inspected only and not modified. No duplication of that work planned.
- Takeover script: clean tree, zero ahead/behind main, 19 migrations with sole head `d8e412c6a901`. Complete script output retained locally in `work/handoff-initial.log` (large historical HANDOFF included).

## Write-ahead plan

1. Archive current Fly status and repeat unchanged production Fetcher probe only for Aalto and NTU. No settings, secrets or deployment changes.
2. Download original heldout and RL-1 artifacts; audit completed/partial captures, core counts and budgets offline.
3. Fix a reproduced measuring-stick defect first if present. Do not tune rules on the nine heldout cases or touch the separate expert500 HELDOUT150.
4. Continue with a general discovery improvement on a disjoint development cohort, retaining 6/60/120 limits, truthful unknowns and existing Fetcher protections.
5. Run required source gates, push each green step, prepare a reviewable PR; owner merges.

## Decisions still pending

G-1/G-2 gold corrections are not applied. Paid Exa is not authorized. A free query cache requires inspection of the existing cache/budget/privacy semantics before proposing a change. Source availability must remain distinct from programme discovery or claim accuracy.

## Resume checkpoint

Next action: execute step 1, inspect the saved heldout artifact and add actual results below. No source edits made at takeover.
