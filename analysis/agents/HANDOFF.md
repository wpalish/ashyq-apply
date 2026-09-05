# HANDOFF — the baton

One file, always current, committed with the code. The agent who holds the baton keeps it true.
Rules for using it: `AGENTS.md`. Task definitions: `analysis/AI_TASK_BRIEF.md` §6.
Write for a reader who has **zero** chat history — because that is exactly who reads it.

## 1. Baton

| | |
|---|---|
| Holder | nobody |
| Since (UTC) | — |
| Branch | `main` |
| HEAD when written | `627d42d` |
| Previous holder | owner (manual setup) |

## 2. Current task

`none` — next task is `[0.1]` (see §10). Status vocabulary: `not-started` · `in-progress` · `blocked` ·
`ready-for-review (PR #)` · `merged`.

## 3. Done in this task (commit hash per item — a claim without a hash is not done)

_(empty)_

## 4. Half-done / uncommitted at the moment of writing

_(empty — if you are reading this after a cut-off and `git status` is not clean, the previous agent did not
get to update this. Inspect `git diff`, decide what it was, and record it here before doing anything else.)_

## 5. NEXT STEP — exact and executable

```
Before any brief task: bootstrap this workflow (first agent with tokens):
1. verify the owner unpacked the bundle: AGENTS.md, CLAUDE.md at repo root; docs/process/HANDOFF.md (this file);
   scripts/handoff_check.py; .github/PULL_REQUEST_TEMPLATE.md; analysis/ with AI_TASK_BRIEF.md, SPEC_matching_v2.md,
   reference/ranking_v2.py. Missing → copy from analysis/agents/ (templates) and say so.
2. if not yet committed: commit "docs: relay workflow for the two ai engineers, with a handoff file and a check script"
   (trailer Agent: <you>), push to main — the one time main is allowed
3. run the gates once on clean main and write the real numbers into §6 (baseline)
4. create branch task/0.1-profile-priorities from main; set §1–§2; start [0.1] per brief §6
```

## 6. Gate status at last run (numbers, not adjectives)

| Gate | Result | When / commit |
|---|---|---|
| ruff check / format | — | |
| mypy | — | |
| pytest (count, coverage %) | docs claim 818 green / 92 % on `627d42d` — **not re-run by an agent yet** | |
| frontend typecheck / lint / test / build | docs claim 137 unit green | |
| seed_demo order (§5.7) | v1 order (UBC #1) — expected until [0.5] | |
| alembic heads | 1 (`e7c4a91b6f20`) | 2026-09-05 |

## 7. Blockers / questions for the owner

_(none)_

## 8. Contract changes since the brief (append-only; the other agent reads this before coding)

| Date | Task | Change (path · field/signature) | Why |
|---|---|---|---|
| 2026-09-05 | setup | Brief §1 counts are stale: main now has **818** backend tests (not 785), **19** institutions in `institution_registry.json` (not 10), `domain/transcript.py`, i18n scaffolding in `frontend/src/lib/i18n.ts`, and `types.ts` grew. Anchors in the brief (`_stage_verify` L344, `_stage_assess` L722, `_update_result` L973, `ExplainableScore` L166, `UnresolvedQuestion` L96) are still correct. | keeps the brief honest without rewriting it |

## 9. Traps and lessons (things that cost a session; keep them)

- `seed_demo.py` raises `SchemaOutOfDate` until `UNIMATCH_DEMO_MODE=true alembic upgrade head` has run.
- `Fetcher(...)` takes `(cache_dir, *, delay_seconds, respect_robots, offline, cache_ttl_seconds, timeout, contact, corpus_dir)`; it has no `close()`, only `__aexit__`.
- `backend/setup.sh` needs `uv`; plain `python -m venv` + `pip install -r requirements-dev.txt` works. Without Playwright installed, run with `UNIMATCH_ENABLE_BROWSER_TIER=false`.
- E2E uses fixed ports 5173/8099 with `reuseExistingServer: true` — never two e2e runs on one machine.
- Long-lived branches exist and are **not** part of this work: `claude/payments-phase-2` (74 commits ahead, conflicts with main in 12 files, adds 2 migrations off `c3a1f4e9b2d7` → merging it later will need one Alembic re-point), `social/community` (3 commits, merges clean, adds migration `f2a8c17d9e04`), `claude/production-completion` (Aug 30, superseded by main). Do not rebase them, do not branch from them.
- `README.md` still says "547 tests"; `docs/CURRENT_STATE.md` says 818. Trust pytest, not prose.
- Git author on recent commits is the owner's name for both agents — the `Agent:` trailer is the only reliable authorship signal. Always add it.

## 10. Queue (brief §6 order; do not reorder without the owner)

`[0.1]` → `[0.2]` → `[0.3]` → `[0.4]` → `[0.5]` → `[0.6]` → `[0.7]` → `[0.8]` → `[1.1]` → `[1.2]` → `[1.3]` → `[1.4]` → `[2.1]` → `[2.2]` → `[2.3]` → `[3.1]` → `[3.2]` → `[4.1]` → `[4.2]` → `[5]`

## 11. Session log (one line per session, newest last)

| Session (UTC) | Agent | From → to | Summary |
|---|---|---|---|
| 2026-09-05 | owner | `627d42d` → `627d42d` | workflow files created; no brief task started yet |
