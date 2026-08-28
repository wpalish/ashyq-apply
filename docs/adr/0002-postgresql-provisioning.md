# ADR 0002 — PostgreSQL provisioned in-process for development and tests

**Status:** accepted
**Date:** 2026-08-28

## Context

Production must run on PostgreSQL with real migrations. The claim
"PostgreSQL-ready" was in the README for weeks without the schema ever having
touched PostgreSQL — exactly the sort of unverified claim this project is meant
not to make.

No PostgreSQL, Docker or Homebrew is installed here.

## Decision

Use `pgserver`, which ships PostgreSQL binaries and starts a server against a
local data directory, for development and for the test suite. It is a
development and CI dependency only; a deployed environment connects to a managed
PostgreSQL through `UNIMATCH_DATABASE_URL`.

The test suite runs the **whole** schema, the migrations and the queue against
this real server, so "works on PostgreSQL" is asserted rather than asserted-to.

## Consequences

* Tests are slower to start (a server boots once per session) and are worth it.
* SQLite stays supported for a quick local run. Anything PostgreSQL-specific —
  `SKIP LOCKED`, JSONB, partial indexes — is behind a dialect check and is
  covered by tests on both.
* `docker-compose.yml` still declares a normal `postgres:16` service; that is
  the deployment shape. `pgserver` exists so a developer, and CI, need nothing
  installed.
