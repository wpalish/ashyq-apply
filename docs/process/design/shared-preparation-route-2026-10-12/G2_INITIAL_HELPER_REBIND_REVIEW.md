# G2 initial helper rebinding — read-only review

2026-10-12. **DESIGN / NOT_REBOUND / NOT_IMPORTED / NOT_RUN.** Only predecessor helper source, approved inventory/pin metadata, symlink metadata and retained gate-summary metadata were read. No helper/probe/import/test/runtime/source/Git/HANDOFF write or provider/closed-evaluation activity occurred. Root creates the actual binding only after the sealed three-file packet is applied and WIP-pushed.

## 1. Exact predecessor and initial delta

Predecessor root: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution`.

Metadata-only comparisons found **759 unique inventory paths**, **579 active expected pins**, no expected-pin disagreement with FINAL8 inventory, and no disagreement among the existing pins listed in `G2_INITIAL_SOURCE_PREIMAGES.json`. All three new paths are absent from the predecessor inventory/expected map:

- `backend/app/schemas/shared_route.py`
- `backend/app/domain/shared_route_allocator.py`
- `backend/tests/test_shared_route_allocator.py`

The future `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source` must contain exactly those approved 759 predecessor files plus the three sealed, actually applied root files: **762 inventory / 582 active expected pins**, provided no separately reviewed source change occurs. Preserve all 759 old values, including frontend/package/assets, native fixtures, migrations, requirements and approved evaluation code. Do not snapshot arbitrary additional current-checkout files, credentials, user data, caches or research artifacts. New hashes and source/WIP commit are pending root application; this review does not invent them.

Use the **active FINAL8 expected map**, SHA `c36648b7736cd3be95174ee0e2b278904263b987a5983c6ad55068a5fd4b4f8c`, as old→new authority. The packet's older `expected-native-source-pins.predecessor.json` is historical metadata, not the new active baseline; do not revert to its smaller set. Keep earlier inventories/evidence unchanged.

## 2. Minimal backend helper change

Copy the finite approved `g1-execution/backend-full` packet into a fresh `g2-execution/backend-full`. The sole Python source change is the fixed constant in `run_full_backend.py:25`:

```text
DIAGNOSTIC_TARGETS = ['tests/test_shared_route_allocator.py']
```

Everything else in that runner remains exact: `PACKET` already resolves to its new directory; source/output roots are explicit CLI arguments. Preserve all function bodies, full-mode branch/defaults, global workspace/primary exclusion, environment, timeout bounds, probes, guards, asset rules, plugins, result validation, source hashing, process-group termination and owned cleanup. Record old/new runner hashes plus exact constant-only diff. Do not add selectors, CLI target overrides, `--noconftest`, collection exclusions, mocks, skipped assertions or coverage changes.

The active `expected-native-source-pins.json` receives **three additions only**, with actual applied/sealed file hashes; record predecessor/new map SHA/counts and the explicit path delta. Guard/probe/plugin/asset JSON files remain byte identical. No requirements, dependency installation, node/venv upgrade, synthetic DNS allowance or runtime policy change is needed.

**Do not invoke `run_static_diagnostic_full7.py`.** It chains the seven-step static/frontend script, the focused diagnostic and a third **full backend** invocation. It exceeds the requested initial pure gate. `run_static_frontend_final7.py` also hard-codes the G1 source/output and runs frontend tests/build. These are inspected predecessor evidence, not suitable unchanged G2 entry points.

## 3. Runtime/dependency boundaries to retain

Existing symlink targets, observed from the predecessor source:

| Dependency link | Exact target |
| --- | --- |
| `backend/.venv` | `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/.venv` |
| `frontend/node_modules` | `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend/node_modules` |

Reuse those links only; installations are outside the helper. The inherited frontend/font binding was retained by predecessor `HELPER_REBINDING.json`; this increment changes no frontend/config/font bytes. Preflight must still verify installed package metadata and bundled PG binaries rather than assume they remained available from old PASS.

Preserve the same non-truncating shared flock at `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock`; existing holders cause queue refusal, not lock deletion/takeover. Evidence goes in a new timestamped G2 directory outside source/primary. No source edits may race an active gate.

The unchanged runner creates fresh 0700 `/tmp/um-full-*` runtime/home/cache/exports/PG directories, empty 0600 pgpass, and a whitelist environment: synthetic SQLite default, demo=true, search provider=none, browser=false, auth=false, payments=false. Native corpus directory is the approved source fixture directory, not live crawl/user data. Retain `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, the explicit cov/asyncio/mock plugin list, coverage-safe no-app-preimport, source-before/after maps and fail-closed child startup.

Retain the inherited macOS sandbox denying all IP/DNS/outside network; only owned private Unix sockets below the fresh runtime are allowed for synthetic PostgreSQL. Negative transport/descendant probes and strict libpq validation are unchanged. Do not replace private PG with a real/remote database or loopback TCP. Keep durable outside-attempt metadata and startup failure receipts, original argument forwarding, the lazy optional-driver/urllib3 hook, five mock API module mappings and six exact browser-case mappings; no new resolver case is needed for the allocator.

The diagnostic still boots **private PG for its positive `SELECT 1` isolation probe**, even though selected tests exercise a pure allocator and the diagnostic phase uses SQLite settings. `phase` requires `pg_connection_events > 0` for acceptance. Removing this bootstrap/probe or weakening that condition would be an unapproved helper change. It is not a G2 persistence/concurrency test or a full PostgreSQL phase.

Approved prerequisite metadata remains exact: asset requirements **45 entries**, transitive requirements **7 entries**, public fixture paths **112**. Do not broaden them or inspect closed label contents. The pre-existing synthetic `u-groningen/fees.pdf` inventory hash is `c61a8a9f546d0cc38e2e7f326961aaef7afd74413efc8272aa943f5d5ad7a2cc`; preserve it so native corpus fixtures cannot build into pinned source during the gate. These historical native prerequisites grant no new benchmark/controller/gold/heldout/live-provider run.

## 4. Initial gate classification

After source/packet binding is sealed and root authorizes execution, invoke the rebound runner with explicit new source/output roots, **`--execute --diagnostic --phase-timeout 300`**. The actual interpreter comes from the unchanged approved venv. Do not omit `--diagnostic` or use the chain script. Existing default timeout remains 1800 with 60–3600 bounds; diagnostic execution is capped at 300 without changing the helper.

Expected result category is only `FOCUSED_DIAGNOSTIC_PASS_NOT_FULL` or its failure category. Acceptance still requires nonzero native JUnit cases, zero failure/error/skip, zero outside/startup failures, armed guard receipts, restored IPv6 trait, no application preimport, positive owned PG connections, source equality, complete owned shutdown and runtime removal. An isolation/prerequisite failure stops immediately; no silent retry, fallback dependency or widening. Use receipt mode/status rather than the helper's generic “full native” stdout headline.

Fresh backend static commands retain the approved command contracts under the same network-denied sandbox, shared runner lock and source-before/after comparison:

```text
.venv/bin/python -m ruff check app tests evaluation
.venv/bin/python -m ruff format --check app tests evaluation
.venv/bin/python -m mypy app tests
```

They operate in the new frozen source's backend. Root may prepare a narrow recorded backend-static invocation rather than run the predecessor frontend/full chain; this review writes no launcher. These commands plus focused allocator tests are an **initial pure engineering check**. They do not establish full coverage, API persistence/CAS/history/export/delete, user UI/E2E, admissions readiness, deployment or live search quality. No full-mode coverage floor/test set is changed; a future full gate remains a separate source-bound task.

Frontend is **not freshly run** in this increment. The retained G1 static receipt reports seven steps passed; its before/after map covers 127 frontend paths, all matching FINAL8 inventory, with no frontend before/after drift. FINAL8 has 140 frontend inventory files including broader assets/configuration. Carry predecessor frontend results only after root proves equality of every old consumed frontend path **and all 140 inventoried frontend files**, package/config/font/assets and unchanged dependency binding in the new snapshot. Label them “predecessor result carried by byte equality”, never a new G2 UI test or a claim of a new full seven-step PASS. No new G2 UI/API exists in the three-file increment.

## 5. Required binding receipt before first execution

Record: predecessor inventory/expected/helper hashes; source/WIP commit and 762 exact paths; all 759 predecessor values unchanged; three new postimages; old/new active expected maps with 579→582; constant-only runner diff; all other helper/guard/assets hashes unchanged; exact symlink targets; no forbidden private paths; unique new evidence namespace; runner/argv/lock ownership; frontend conditional carry statement. Preserve every old receipt. The retained G1 full receipt's 615 runtime-pinned paths are a **different map** from 759 inventory/579 expected; the unchanged runtime pin function should add the same three paths, with actual count recorded, not silently replace the expected inventory.

No blocker was found requiring runtime-policy widening. Actual readiness remains conditional on root's sealed apply/WIP push and new binding/preflight; this inspection did not validate new G2 bytes or execute any gate.

## 6. Inspected predecessor hashes (SHA-256)

| Path relative to `g1-execution` | SHA-256 |
| --- | --- |
| `backend-full/run_full_backend.py` | `3ed463bd966cec9aba7c04274f217768b1fb5b6ce5ebf2995a12b606aa9fb311` |
| `backend-full/guard_runtime.py` | `6835a7e41d7abe67ed02afef30c1feb142d36bf87648c1638fd98920aa3728a3` |
| `backend-full/guard_optional.py` | `e309aa99aaf671f70a0e8292600b82d46eb77215af3316703553a98daba03627` |
| `backend-full/sitecustomize.py` | `747bb4ba27a5f002f45d28e590776e8e052039a8acf949da0ddba61dc12d8bc7` |
| `backend-full/pytest_full.py` | `ae987bac75d8d22c63be7448d67cefd04480cb1ff67894d18f3288090300ffe1` |
| `backend-full/os_network_probe.py` | `7ff451578d221dce4d781d0180bfb6bbc45b576d4a7cc61719b12586286105e5` |
| `backend-full/mock_endpoint_plugin.py` | `fee728e2ff824b07b0e927b47c8087f08acc2111277d41053caffc3e37b48588` |
| `backend-full/asset-requirements.json` | `852b12e28dd3f62bcaead8589609ec7127c5b78040b6f00f8f9b80a4ba20087c` |
| `backend-full/transitive-requirements.json` | `64c90bb19bfbf9972079075dee038ddd708fb548ec0e72800ed6288a748ca4c4` |
| `backend-full/existing-public-fixture-paths.json` | `913254fd326c5f89c159b33941753d9aac8e70b270ad8ea03ca02825e5e5f849` |
| `INITIAL_SOURCE_COPY.final8.json` | `0333294ea67bc760b2bfad1b60511532308fff4bdaa0e3e50eb976d55f5bd347` |
| `FINITE_REBINDING.final8.json` | `c7ef2ebf9b54371b5f7123085caf8e595d075955216644048e0e215b35d34710` |
| `APPLIED_SOURCE_PINS.final8.json` | `a8f5499860690fdc5f59ede9787401ea48a97701fcb290c5af341d371a1c6e9a` |
| `HELPER_REBINDING.json` | `8ff4d94abb0fdddfb7500b007d6c64485958d52a4b74877e222d717f94155dc2` |
| `FULL_TERMINAL_VERIFICATION.json` | `1872c448db6627a93cf1baafd729b95e97f7cb5e57f767678889556118fc6051` |
| `evidence/static-frontend-final7/result.json` | `bdcd3b829582611b23df1f54f0a3b328b9519059ae47bb49823054f2f7c9b524` |
| `evidence/static-frontend-final7/source-before.json` and `source-after.json` | `716129be10de85b2524f89794dcff3044406d858545ba6fe09364940579395c1` |

**Terminal review state: READ_ONLY / NOT_REBOUND / NOT_RUN.** Source writer and actual helper execution remain with root after the new source packet is sealed. Existing STOPs, closed labels, model/provider boundaries and production permissions remain unchanged.
