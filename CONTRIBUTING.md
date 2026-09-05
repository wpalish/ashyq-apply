# Contributing

The product's rule comes first: **every material value on screen traces to the
page it was read from, and an unknown is never converted into a guess.** A
change that makes the software more helpful by inventing a value is not an
improvement here. If a page does not say, the answer is "not published", and
the applicant is told what to ask.

## Setup

Python 3.12 and Node 22.

```bash
cd backend && ./setup.sh          # uv-managed venv, dependencies, demo corpus, Chromium
cd frontend && npm install
```

`setup.sh`, `run.sh` and `worker.sh` resolve the interpreter themselves, so the
same commands work on Linux, macOS and Windows (`bin/` vs `Scripts/`).

## Running it

```bash
cd backend && ./run.sh --with-worker    # API on :8099, worker alongside
cd frontend && npm run dev              # http://127.0.0.1:5173
```

Demo mode is the default: the pipeline reads a bundled corpus, touches no
network and needs no API keys.

## The gates

Everything below must be green before a commit. They are the same commands CI
runs.

```bash
cd backend
./.venv/bin/python -m pytest
./.venv/bin/python -m ruff check app tests
./.venv/bin/python -m ruff format --check app tests
./.venv/bin/python -m mypy app
```

```bash
cd frontend
npm run typecheck && npm run lint && npm test && npm run build
npm run e2e            # needs the Playwright browsers: npx playwright install chromium
```

### The PostgreSQL branch

The suite runs on SQLite by default. `pgserver` provisions a real PostgreSQL
in-process for the queue and cascade tests:

```bash
cd backend && ./.venv/bin/python scripts/pg.py ./.venv/bin/pytest
```

If `pgserver` cannot start a cluster (its `initdb` does not run on Windows),
those tests **skip** rather than fail, and the skip message says why. CI runs
them on Linux, so a change to the queue or the cascades is still checked
against the real thing before it lands.

## Tests

Test-first for defects: write the failing test that reproduces it, then fix it.
Name tests after the product behaviour they protect, not the function they
call — `test_a_rejected_row_is_kept_not_deleted`, not `test_set_decision_2`.

A test that cannot fail is not a test. If you are unsure yours can, break the
code deliberately and watch it go red.

## Commits

One logical change per commit. Messages in English, in the imperative, saying
what was wrong as well as what changed:

```
fix: saving a note is not deciding the row

Editing a note re-POSTed the decision endpoint, which stamps decided_at...
```

Prefixes in use: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `style:`.

## Naming

The product is **ASHYQ Apply** everywhere a person can read it. Internal
package, database and environment names remain `unimatch` (`UNIMATCH_` prefix,
`unimatch.db`, logger names) — a deliberate decision, not an oversight. See the
note at the top of the README.

## Where the rules live

- `docs/FIX_PLAN.md` — the audit backlog and the phase it belongs to.
- `docs/PROFILE_FIELDS.md` — what every profile field does, or why it was
  removed. A new field belongs in that table before it belongs in the form.
- `docs/adr/` — decisions with consequences, and why the alternative was not
  taken.
- `RELEASE_CHECKLIST.md` — a gate becomes PASS only with a command or a test
  behind it. `WRITTEN, NOT RUN` is an honest status; a guessed PASS is not.
- `SECURITY.md` — the trust boundaries, and what is deliberately not enforced.
