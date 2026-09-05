<!-- One brief task per PR. Title = final commit message in repo style (lowercase, feat:/fix:/test:/docs:, behaviour not file). -->

## Task
`[x.y]` from `analysis/AI_TASK_BRIEF.md` §6 — worked on by: `claude-opus-5` / `gpt-6-astra` / both (see `git log --format='%h %(trailers:key=Agent)'`)

## What changed (behaviour, not files)
-

## Acceptance criteria from the brief (copy and tick)
- [ ]
- [ ]

## Contract changes
`none` — or the lines added to `docs/process/HANDOFF.md` §8

## Verification (paste real output — a reviewer will re-run it)
```
ruff check / ruff format --check:
mypy:
pytest --cov (count, coverage %):
frontend typecheck / lint / test / build (if touched):
seed_demo.py order (if pipeline touched) — must match brief §5.7:
alembic heads (if migration):
```

## Invariants touched (I1–I10) and the test guarding each
-

## Reviewer checklist (the other agent, before the owner merges)
- [ ] gates re-run locally, numbers match the ones pasted above
- [ ] no decision D1–D12 re-opened; no formula differs from `analysis/reference/ranking_v2.py`
- [ ] domain imports no adapters; no network outside `Fetcher`; no real LLM / internet in tests
- [ ] no "probability" / "chance" / "%" near the ranking
- [ ] v1 scoring and its tests untouched; `--cov-fail-under=92` untouched
- [ ] one behaviour per test; names describe behaviour
- [ ] exactly one alembic head
- [ ] `HANDOFF.md` §2 = `ready-for-review (PR #…)`, §3 hashes match this PR
