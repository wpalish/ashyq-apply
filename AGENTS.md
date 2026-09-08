# AGENTS.md — relay rules for the AI engineers on this repository

Two AI engineers work here — **Claude Code (Opus 5)** and **Codex (GPT-6 Astra)** — but **never at the same
time**. The owner switches between them when one runs out of tokens. A session can therefore end at any
moment, without a goodbye, in the middle of a task. Everything below exists to make that harmless.

The task list is `analysis/AI_TASK_BRIEF.md`. The spec is `analysis/SPEC_matching_v2.md`. The baton is
`docs/process/HANDOFF.md`. This file tells you how to pick the baton up and how to hold it.

## 0. Three laws

1. **Origin is the only memory.** Chat context dies with the session. Anything not pushed to `origin` or
   written in `docs/process/HANDOFF.md` does not exist for the next agent — including you, next time.
2. **HANDOFF before code.** Write what you are about to do into HANDOFF §5 *before* you do it. If you are
   cut off, the next agent finds a plan, not a mystery.
3. **Push after every green step.** Small commits, at most ~45 minutes apart, pushed immediately. `wip:`
   commits are allowed on task branches (main only ever receives squash-merges).

## 1. Start of every session — no exceptions

```bash
git fetch --all --prune
python scripts/handoff_check.py        # python3 on macOS/Linux
```

1. Paste the script output into the chat. It shows branch, HEAD, unpushed/uncommitted work, the Alembic
   head count and what HANDOFF.md claims.
2. Read `AGENTS.md` (this) and `docs/process/HANDOFF.md` **in full**. First session on this repo: also
   `analysis/AI_TASK_BRIEF.md` §0–§4, §7, and the §6 block of the current task.
3. **Reconcile.** Does the tree match HANDOFF §1–§5? Typical mismatches after a cut-off: uncommitted files,
   a `wip:` HEAD, HANDOFF §5 already done, HANDOFF §5 half done, tests red. Run the gates (§5 below) to
   learn the real baseline. Write every discrepancy down in the chat and fix HANDOFF to match reality.
4. **Review first if needed.** If HANDOFF §2 says `ready-for-review` and the author was the other agent,
   review that work against `.github/PULL_REQUEST_TEMPLATE.md` before starting anything new. Write your
   findings into HANDOFF §7 and the PR. The relay *is* the code review.
5. **Take the baton.** Update HANDOFF §1 (Holder, since UTC, branch, HEAD), append one line to §11, then:
   `git commit -am "handoff: <you> takes the baton at [<task>]"` with the trailer `Agent: <you>` and push.
6. Tell the owner in ≤ 10 lines: where the previous session stopped, the exact next step, the files you
   will touch. Then proceed. Stop and ask **only** if HANDOFF and the code disagree in a way you cannot
   resolve from git, or if a brief decision D1–D12 looks wrong. Never guess; never "improve" a decision.

If `git pull --ff-only` refuses (histories diverged): do **not** force anything. Run
`git pull --rebase`; on conflicts, stop, write them into HANDOFF §7, and ask the owner.

## 2. While holding the baton

- **Write-ahead.** Before each sub-step: HANDOFF §5 = the exact step (file, function, test). After it:
  move the item to §3 with the commit hash. Commit HANDOFF together with the code.
- **Sub-steps ≤ 45 minutes, each ending in a pushed commit.** Green gates → normal commit. Not green yet →
  `wip: [0.3] u_* ported, aggregate() still fails T3` — the message *is* a mini-handoff: name what is red.
- **Every commit carries the trailer** `Agent: claude-opus-5` or `Agent: gpt-6-astra`, and the task id in
  the message. `git log` must show who did what without asking anyone.
- **Never leave red tests undocumented.** Red at push time → `wip:` prefix + HANDOFF §6 lists the failing
  tests and your current hypothesis.
- **Traps you fall into go to HANDOFF §9** (a command that must run first, a flaky port, a misleading
  README line). That knowledge otherwise dies with the session.
- **Contract changes go to HANDOFF §8**, one line each: new field, enum value, config flag, API shape,
  module path. The other agent reads §8 before touching the code.
- **Alembic:** before creating a migration, `alembic heads` must show exactly one head; after, still one.
  Record the revision id in §8. Never rewrite a migration that is already on `main`.
- Work only on the task in HANDOFF §2. Finished early? Mark it `ready-for-review`, do the end-of-session
  steps, and only then open the next task from §10 in the brief's order.

## 3. End of session (when you get the chance)

1. Gates green or a `wip:` commit that names what is red.
2. HANDOFF: §1 `Holder: nobody`, §2 status, §3 done list with hashes, §5 next step **exact and executable**,
   §6 gate numbers from the last run, §7 blockers/questions, §11 session line with `from → to`.
3. `git commit -am "handoff: <you> releases the baton at [<task>] — <next step in five words>"`, push.
4. Tell the owner: "baton released, HEAD <hash>, next: <§5 in one line>".

You will often not get the chance. That is why §2 above exists: a session cut off after following §2 is
already a clean handoff.

## 4. Branches, commits, PRs

- One branch per brief task: `task/<id>-<slug>` from `main`, e.g. `task/0.3-ranking-v2`. Both agents commit
  to it in turn. Never commit to `main`. Never `--force` on a shared branch.
- Commit style is the repository's: lowercase, `feat:` / `fix:` / `test:` / `docs:` / `refactor:` /
  `wip:` / `handoff:`, describing **behaviour**, English.
  `feat: rank with a geometric mean so an unaffordable place cannot buy its way to the top`
- Task done = every acceptance criterion in the brief §6 ticked, gates green → open a PR with
  `.github/PULL_REQUEST_TEMPLATE.md` filled in with **real command output**, set HANDOFF §2 to
  `ready-for-review (PR #)`. The owner squash-merges; `wip:` commits disappear there.
- Merge order is the brief's task order; do not start a task whose predecessor is not on `main` unless
  HANDOFF §5 explicitly says to branch from the predecessor's branch.
- Do not touch `claude/payments-phase-2`, `social/community`, `claude/production-completion` unless the
  task says so (HANDOFF §9 explains why).

## 5. Gates — identical to CI, green before any non-`wip` commit

```bash
cd backend
./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests
./.venv/bin/python -m mypy app tests
./.venv/bin/python -m pytest --cov=app --cov-fail-under=92
cd ../frontend && npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Windows: `.venv\Scripts\python.exe`. E2E (`npm run e2e`) needs ports 5173/8099 free and runs one at a time.
Pipeline tasks additionally: `UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`
must print the order in brief §5.7 (Groningen #1, UBC in OUT_OF_BUDGET).

## 6. Hard rules (brief §7.4 — not negotiable by either agent)

### UI design-system contract

Before writing or modifying any UI code, read the relevant spec file in specs/. Use only tokens from tokens.css. Run the token audit script before committing. Zero errors required.

- Decisions D1–D12 and invariants I1–I10 are final. Contradiction → HANDOFF §7 + ask; do not guess.
- `backend/app/domain/` imports nothing from `app.adapters.*` and does no I/O.
- Do not weaken `Fetcher` (robots, rate limit, PII guard); no network outside it. Tests never call a real
  LLM or the internet — mock providers only.
- Send nothing to an LLM beyond the privacy table in `SPEC_matching_v2.md` §6.4.
- Never show "probability", "chance" or "%" next to the ranking.
- Do not rename `unimatch` / `UNIMATCH_`. Do not delete v1 scoring or its tests. Do not lower
  `--cov-fail-under=92`.
- Never commit `backend/data/*`, `.env*`, keys or applicant data.

## 7. Local setup (once per machine / sandbox)

```bash
cd backend && python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
UNIMATCH_DEMO_MODE=true ./.venv/bin/alembic upgrade head
UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false ./.venv/bin/python seed_demo.py
cd ../frontend && npm ci
```

If your environment cannot reach `origin` (some sandboxes cannot), say so in your first message: the owner
will push through the tool's UI after every sub-step, and you keep HANDOFF.md current inside the diff.
