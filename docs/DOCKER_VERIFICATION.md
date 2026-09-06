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
