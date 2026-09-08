# T36 / A1 — ashyq-developer output

- ROLE: ashyq-developer, ATTEMPT: A1, CAMPAIGN: c3 (trusted proxy last-hop + unpublished API port)
- STATUS: IMPLEMENTED
- CHECKED_SHA (start): 054331fa50a8069e0ff7d9d9b43ed6096b1169b7 (QA RED commit; parent = baseline edf546de9f998c0909337d0abe6f8e1c9c4a0be5, confirmed `git rev-parse HEAD^`)
- WORKTREE: /Users/wpalish/ashyq-worktrees/c3-t36-dev, branch ai/c3/t36/dev, tree clean before work, clean after commit
- CANDIDATE_SHA: b7cdc812d39f3a12ac507d590a637e4f2185fd16 (frozen; commit message + trailer `Agent: ashyq-developer`)

## CHANGED_FILES (3 files, +44 / -17)
- `backend/app/main.py` (+9/-5): `client_address` only — when `trust_proxy_headers=True`, split XFF into `hops = [h.strip() for h in forwarded.split(",") if h.strip()]` and return `hops[-1]` (fall back to socket peer on empty); docstring rewritten truthfully (exactly one trusted proxy in the stack appends the real client to the END of the header; everything left of the last hop is the client's spoofed prefix). trust=False → peer, unchanged.
- `docker-compose.yml` (+10/-2): api service `ports: "${API_PORT:-8099}:8099"` → `expose: ["8099"]`; adjacent comment explains why (published 8099 + UNIMATCH_TRUST_PROXY_HEADERS=true = spoofable per-address limits); commented `# - "127.0.0.1:8099:8099"` variant for local /docs inspection, noting verify_compose.sh refuses any host publication.
- `scripts/verify_compose.sh` (+21/-8): (a) NEW pre-flight gate — `$COMPOSE config | awk` isolates the `api:` service block and fails on any `published:` entry containing 8099; (b) host-side API probes rerouted from `localhost:${API_PORT:-8099}` (no longer published) to the web nginx proxy (`API="$WEB/api"`), which is the only remaining host route and the same path users take.
- `backend/app/config.py`: NOT touched — no `trusted_proxy_hops` generalization (see DESIGN_NOTES). Zero conflict surface with T34/T35 despite the recorded serialization order.

## ROOT_CAUSE_FIXED
1. `client_address` took `forwarded.split(",")[0]` — the FIRST XFF hop. nginx uses `$proxy_add_x_forwarded_for` (APPENDS the real client), so the left-most entry is client-controlled: a script naming a fresh left-hand address per request never filled a bucket (RED-A). Fix: last hop.
2. The api service published 8099 on all host interfaces while the stack sets `UNIMATCH_TRUST_PROXY_HEADERS=true`, so any direct client could forge XFF and reset its own limits (compose RED-1/RED-2). Fix: expose-only.

## GATES (real runs, backend venv /Users/wpalish/ashyq-worktrees/c3-t36-dev/backend/.venv)
- a. `./.venv/bin/python -m pytest tests/test_security.py tests/test_compose_publishes_no_api_port.py` → 28 passed in 22.25s (exit 0)
- a-per-test: `TestForwardedAddressSemantics::test_the_last_forwarded_hop_is_the_limiting_address`, `::test_xff_is_ignored_when_proxy_headers_are_not_trusted`, `::test_empty_or_absent_forwarded_for_charges_the_socket_peer`, `test_the_api_service_does_not_publish_its_port_to_the_host`, `test_the_api_port_stays_reachable_on_the_compose_network` → 5 passed in 11.65s
- b. `./.venv/bin/python -m mypy app tests` → Success: no issues found in 165 source files (exit 0; two pre-existing `[annotation-unchecked]` notes only)
- c. `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` → All checks passed! / 165 files already formatted (exit 0)
- d. `./.venv/bin/python -m pytest tests/test_api.py tests/test_metrics.py` → 80 passed in 33.01s
- e. `bash -n scripts/verify_compose.sh` → SYNTAX OK (exit 0)
- f. verify_compose.sh full run → **NOT_RUN**: docker CLI/daemon unavailable in this environment, and the script builds images and starts the five-service stack. Offline validation of the new awk check on synthetic `docker compose config`-shaped fixtures: expose-only config → CLEAN; config with a published api 8099 → FLAGGED `published: "8099"`; a loopback 8099 publication on a DIFFERENT service (web) correctly NOT flagged (api-block scoping works).

## RED_TO_GREEN (per QA author's naming)
- RED-A `test_the_last_forwarded_hop_is_the_limiting_address`: RED (assert 401 == 429) → GREEN, both guards engaged post-fix: probe with XFF "5.6.7.8" → 429 (same bucket as the spoofed pair "1.2.3.4, 5.6.7.8"); bare "1.2.3.4" probe → 401 (fresh bucket).
- RED-B `test_xff_is_ignored_when_proxy_headers_are_not_trusted`: was GREEN on baseline (coverage) → stays GREEN (trust=False path untouched).
- RED-C `test_empty_or_absent_forwarded_for_charges_the_socket_peer`: was GREEN (coverage) → stays GREEN (empty-hops fallthrough to peer preserved).
- compose RED-1 `test_the_api_service_does_not_publish_its_port_to_the_host`: RED (`['${API_PORT:-8099}:8099']`) → GREEN (no ports entries at all).
- compose RED-2 `test_the_api_port_stays_reachable_on_the_compose_network`: RED (expose empty) → GREEN (`"8099"` in expose).
- Existing `TestAbuseLimits` (24 in test_security.py incl. per-proxy budget, address rotation, per-email limit, Retry-After): GREEN, unmodified — they use single-hop XFF where first == last.

## DESIGN_NOTES
- Generalization: chose the card's simplest compliant option — NO new `trusted_proxy_hops` setting, take `hops[-1]`. Default behavior identical to the generalized form with hops=1 for this single-proxy stack; one fewer config knob, and config.py untouched removes any T34/T35 hunk interaction. Multi-proxy chains are out of scope for this stack (documented residual).
- verify_compose.sh strictness: the new gate fails on ANY host publication of 8099 by the api service (the packet's "NO host publication"), which is stricter than the QA file-contract test (loopback allowed). Coherent: the shipped compose has no ports at all; the commented loopback variant is documented in-file as ad-hoc local debugging, not a releasable state.
- Script probe rerouting was a necessary consequence of un-publishing 8099 within an allowed file: without it the health probe at `localhost:8099` would fail unconditionally. Through-web probes also make the gate exercise the real user path (web → api).
- Comment wording in main.py states the invariant in code-adjacent English: the single trusted proxy appends the real client to the end; charging the first hop lets a script mint fresh buckets.

## MIGRATIONS
None.

## RESIDUALS / RISKS
- Two-proxy chains would charge the inner proxy's address (accepted design of the card; `trusted_proxy_hops` remains an available generalization).
- nginx APPENDS to XFF (`$proxy_add_x_forwarded_for`): correct for last-hop semantics; if someone later switches nginx to a hard rewrite the semantics still hold (last entry = client), but a pass-through `proxy_set_header X-Forwarded-For $http_x_forwarded_for` would reintroduce spoofing — nginx.conf is frozen out of scope here.
- verify_compose.sh end-to-end behaviour (web-routed probes against the live stack) validated by reading nginx.conf (`location /api/` → `proxy_pass http://api:8099`, URI passed unchanged) but not executed (no docker); first real run should be watched by whoever owns the release gate.
- Full-repo coverage gate (`--cov-fail-under=92`) and frontend gates not run in this phase (packet gates a–e only).

## BLOCKERS
None.

## NEXT_ACTION
Dispatch ashyq-qa VERIFY_CANDIDATE on b7cdc812d39f3a12ac507d590a637e4f2185fd16 in a separate verification worktree, then ashyq-reviewer + ashyq-security (mandatory roles for T36). Integration order T34 → T35 → T36 stands; this candidate's config.py region is untouched.

---

# REPAIR R1 (QA VERIFIED_FAIL on b7cdc81) — ashyq-developer

- QA finding: scripts/verify_compose.sh:45 — the health PROBE was still `"$API/api/health"` while `API="$WEB/api"`, resolving to `/api/api/health` which no route serves (routes_meta serves `/api/health` only) → the health gate would fail unconditionally. My A1 commit had updated the adjacent fail message but missed the probe line among the five `$API`-prefixed URLs. Confirmed valid.
- FIX: line 45 → `"$API/health"`. No other changes; main.py and docker-compose.yml untouched.
- $API URL inventory checked post-fix (base `API="$WEB/api"`, nginx `location /api/` → `proxy_pass http://api:8099`, URI passed unchanged):
  1. L45 probe `"$API/health"` → `/api/health` — FIXED this repair
  2. L49 fail msg `"$API/health"` — already correct
  3. L58 `"$API/auth/register"` → `/api/auth/register` — correct
  4. L68 `"$API/profiles"` → `/api/profiles` — correct
  5. L73 `"$API/runs"` → `/api/runs` — correct
  6. L78 `"$API/runs/$run"` → `/api/runs/{id}` — correct
- GATES re-run (real): a. pytest tests/test_security.py tests/test_compose_publishes_no_api_port.py → 28 passed in 20.13s; b. pytest tests/test_api.py tests/test_metrics.py → 80 passed in 33.98s; c. mypy app tests → Success: no issues found in 165 source files; d. ruff check + format --check app tests → clean; e. bash -n scripts/verify_compose.sh → SYNTAX OK. Full script run still NOT_RUN (no docker daemon here).
- COMMIT: f9c90bf "fix: T36 repair — verify_compose health probe path after web-proxy base", trailer `Agent: ashyq-developer`, diff = 1 file / 1 insertion / 1 deletion, tree clean.
- NEW CANDIDATE_SHA: f9c90bf90f057d35c6ef72fcf70bdd14afc8bd80 (supersedes b7cdc81; parent = b7cdc81, so the full T36 change set is b7cdc81 + f9c90bf)
- NEXT_ACTION: QA re-verify f9c90bf90f057d35c6ef72fcf70bdd14afc8bd80.
