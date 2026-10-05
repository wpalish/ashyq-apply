# Local source transport — prospective requirements

Recorded 2026-10-05. This is an offline feasibility decision, not an implemented
runtime, launch authorization, source capture or quality score. Original V13
remains CLOSED_UNSCORED on its immutable source/tag/trial; its baselines cannot
be reused in a future pair.

## Findings

GitHub's original Aalto annotation confirms failure to acquire a hosted runner.
Moving controlled source execution to the owner's computer may remove that
compute queue, but desktop source connectivity has not been tested here.

The stock controller can invoke the unchanged Fetcher locally. A separate CLI
process per action creates a new Fetcher each time: request pacing and robots,
stalled-host and refused-host state do not persist. Strict counters alone do
not prove continuity of those protections.

Settings may load a working-directory `.env`; the selector and source launcher
inherit environment variables. Source HTTP clients also allow environmental
proxy and CA settings. A worker-only credential and explicit clean environments
are required before local execution can be measured as an isolated trial.

## Selected prospective direction

Prepare a persistent controlled worker per case around the stock Fetcher and
controller APIs, with an opt-in shared admission guard at the existing final
pre-I/O boundary for every page read and provider query. Preserve current
production defaults. A published provider/batch STOP must refuse the next
action before its executed flag or counter advances. Already-admitted in-flight
actions need explicit terminal accounting; do not claim retroactive cancellation
of completed I/O.

This direction requires implementation and meaningful offline regression gates.
It has not been implemented or validated. A conservative globally serialized
CLI with a ten-second post-exit barrier is another prospective option, but does
not reproduce Fetcher state continuity; its worst-case feasibility within the
same guard has not been established.

## Required proof before any new pilot

- Pin the new source, worker, parent/report helpers, dependencies, interpreter,
  process argv, clean environment policy and real workspace device/inode identity.
- Give each local worker a genuine local run identity and hash-bound originals;
  retain separate GitHub receipt validation. Never synthesize GitHub run IDs.
- Keep the existing owned Exa identity. Pass its key only to the controlled
  worker; exclude it and credential files from blind selectors, prompts,
  snapshots, logs, manifests and Git. Scrub proxy/CA overrides rather than
  weakening DNS/IP/redirect, robots, rate or privacy checks.
- Test secret isolation, shared STOP races, counters, pacing/state continuity,
  process expiry, original output delivery and strict report rejection of
  missing/unknown tails using synthetic no-network fixtures.
- Preserve expert60 reads/6 queries, normal Astra effort and one immutable900s
  wall guard. Thinking does not consume the action budget. The algorithm keeps
  its120s/60reads/6queries and finalization reserve; use the same local transport
  for both sides of a new pair with explicit provenance.
- Obtain genuine exact-runtime neutral/OS proof and required source gates, then
  freeze a new source/transport once. Allocate one fresh complete same-ten pair.
  Seal raw originals before reviewed62 labels, diagnose every supported
  expert-only miss and retain outside_policy separately. Keep40/62 and heldout150.

## Current external input

The same existing Exa credential is not configured locally. The owner has been
asked to put `UNIMATCH_EXA_API_KEY` in ignored `backend/.env`, or identify an
existing local credential file. The prepared placeholder is empty; GitHub cannot
reveal its encrypted secret. No credential value was printed or committed.

No local source/provider/model call, new trial, runner registration, deployment
or `probe_access.py` execution occurred during this feasibility work.
