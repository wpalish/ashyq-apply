# Local Docker verification — 2026-09-06

Source: `7ecfaf5` plus the Compose changes on `task/docker-stack-verification`.
Docker Desktop 4.89.0, Engine 29.7.2, Linux containers under WSL2.

`docker compose up --build -d` built all images and migrated a fresh PostgreSQL
volume. The first API start failed with PermissionError creating
`/app/data/httpcache`: the tmpfs masked image ownership and belonged to root.
Setting uid/gid 10001 and mode 0750 fixed startup without running the API as root.

The worker inherited the image's API HTTP healthcheck but does not serve HTTP.
That probe is now disabled for the worker; successful queue consumption is the
worker evidence below, not a claim of continuous worker health monitoring.

Verified with PowerShell HTTP requests through nginx at `http://localhost:8080`:

- GET /api/health: status=ok, database=ok.
- POST /api/auth/register: a synthetic verification workspace and session created.
- POST /api/profiles: bundled DEMO_PROFILE loaded from the API image.
- POST /api/runs, then polling GET /api/runs/{id}: awaiting_user_decision.
- GET /api/runs/{id}/results: 20 results.
- GET /: HTTP 200.
- Run ID: `3bf7c35510614ab1816e5a9fffda6536`.
- Final `docker compose ps -a`: postgres/api/web healthy; worker running;
  migrate exited 0. Reapplying Compose also migrated successfully.

The shell verification script was inspected but not used: its migration check
uses `compose ps` without `--all`, which can hide the successful exited job.
The direct HTTP verification above also routes API traffic through nginx.

Containers remain running. Synthetic data lives in Docker volumes. Existing
host databases were not used. No external deployment or full unit-suite rerun
is claimed by this operational verification.

## kb mode in CI — CS-1, 2026-10-20

Since CS-1 the compose stack ships the launch mode: `UNIMATCH_DEMO_MODE`
defaults to `false`, `UNIMATCH_KNOWLEDGE_MODE` to `kb` and
`UNIMATCH_SEARCH_PROVIDER` to `none` on `migrate`, `api` and `worker` (one
shared environment block). A demo run is still a per-run choice
(`"demo_mode": true` on `POST /api/runs`); `UNIMATCH_DEMO_MODE=true` restores
the old server-wide default. `fly.toml` writes `UNIMATCH_KNOWLEDGE_MODE = "kb"`
explicitly (the code default, so no behaviour change).

`scripts/verify_compose.sh` now runs, after the unchanged demo run:

1. `GET /api/capabilities`: `knowledge_mode` is `kb` and
   `live_coverage.mode` is `kb`.
2. Two universities from `GET /api/universities?verified=true` and one
   catalogue row whose `knowledge.in_kb` is false.
3. `POST /api/runs` with those three `university_ids` and no `demo_mode`
   (the server's default), polled to `awaiting_user_decision`.
4. `GET /api/runs/{id}`: `demo_mode` false, `settings.knowledge_mode` `kb`,
   `pages_checked` 0, every `fetch_tiers` count 0.
5. `GET /api/runs/{id}/questions`: the non-KB university has a blocking
   question starting "No verified data yet", and it is the only university
   that does.

Two fixes to the script itself: the migration wait uses `compose ps --all`
(a finished one-shot job is hidden without it — the reason the script was not
used on 2026-09-06), and JSON is read with `python3` rather than `sed` (the
`sed` over `GET /api/runs/{id}` matched the last `"stage"` key, the final
entry of the `stages` list, so it read `completed` for a run that was
`awaiting_user_decision`).

CI: the `compose-stack` job in `.github/workflows/ci.yml` (`ubuntu-latest`,
push and pull request) runs the script with
`COMPOSE="docker compose -f docker-compose.yml -f docker-compose.ci.yml"`.
The override gives `api` and `worker` `HTTP_PROXY`/`HTTPS_PROXY` =
`http://127.0.0.1:9` (nothing listens there), with `NO_PROXY` for
`localhost,127.0.0.1,postgres`, so a stray outbound read fails instead of
succeeding on the runner's open network. Compose logs are uploaded on failure
(`compose-logs` artifact); the stack is torn down with `down -v` always. The
only credential is the literal `POSTGRES_PASSWORD=ci-only-not-a-secret`.

First green CI run: **pending** — the commit has not been pushed from the
authoring sandbox. Record the `release-gates` run id and the job's output here
when it lands (gate 101 needs it twice).

Pre-CI evidence (authoring sandbox, 2026-10-20). Image builds could not run
there (no registry or apt access from inside a build), so the script was run
against a stand-in for `docker compose` that starts the same entrypoints
natively — `alembic upgrade head`, `uvicorn app.main:app`,
`python -m app.jobs.worker`, a static page for `web` — with the stack's
environment and the CI fence, on SQLite instead of PostgreSQL:

```
==> kb mode: the server reports the knowledge base as its reach
live_coverage: The verified knowledge base answers for 95 of 501 catalogue universities (bachelor's in Computer Science). A university outside it, or another programme, gets 'No verified data yet'; no page is read during a run.
==> kb mode: two universities with verified data and one without
==> kb mode: a run on the server's default mode
==> kb mode: no page was read
pages_checked=0 fetch_tiers={'fixture': 0, 'http': 0, 'browser': 0, 'pdf': 0} knowledge_base=2026-10-20.kb-cs-bachelor.22
==> kb mode: the university without verified data says so
No verified data yet for Aalto University: the bachelor's in Computer Science.

PASS: web -> api -> worker completed a demo run in containers.
PASS: the stack completed a kb-mode run with no page read.
```

The same stand-in with `UNIMATCH_DEMO_MODE=true` fails as intended:
`FAIL: capabilities.knowledge_mode is not kb (is UNIMATCH_DEMO_MODE on?)`.
`bash -n` and shellcheck (koalaman/shellcheck:stable) pass;
`docker compose config --quiet` passes with and without the CI override.
