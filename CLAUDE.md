# CLAUDE.md

Read `AGENTS.md` first — it is the shared rulebook for both AI engineers on this repository and all of it
applies to you. This file only adds what is specific to you.

## Identity
Your commit trailer is `Agent: claude-opus-5`. Add it to every commit.

## First thing, every session
```bash
git fetch --all --prune && python3 scripts/handoff_check.py
```
Then `docs/process/HANDOFF.md` in full. If Codex held the baton last, its §3–§7 are your code review input.

## Effort
Default `high`. Switch to `ultracode` only for `[0.5]`, `[1.4]`, `[3.2]` and for reviewing a Codex PR that
touches `runner.py` or a migration. Do not burn the cap on schema fields or docs — the owner will switch
to Codex when you run out, and a half-finished pipeline step is the most expensive thing to hand over.

## Skills
`.claude/skills/*/SKILL.md` — `applicant-fit-scoring` (never a probability), `scholarship-audit`,
`university-admissions-research`, `loop-engineering` (run it, don't declare it). They match the brief's
invariants; use them.

## Where you are strongest — use it
Pipeline changes with the demo order as the oracle: after touching `runner.py` or `scoring.py`, always run
`seed_demo.py` and compare against brief §5.7 before writing tests. When porting
`analysis/reference/ranking_v2.py`, keep the function names — Codex will look for them.
