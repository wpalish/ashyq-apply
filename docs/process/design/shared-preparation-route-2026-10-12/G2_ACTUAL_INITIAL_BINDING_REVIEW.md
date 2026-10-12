# G2 actual initial1 binding review

Status: **SOURCE_ONLY_BINDING_RECONCILED / NO_BLOCKER_FOUND / NOT_RUN_BY_REVIEWER**.

This report pins the initial1 observations collected before the root's first G2 static execution. It is not a gate result. The root subsequently reported a Ruff SIM102 failure and prepared initial2; the separate `G2_ACTUAL_INITIAL2_BINDING_NOTE.md` records that one-path rebind. Do not treat initial1 metadata as the current lab source.

## Scope and pins

Base: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/`.
Reviewed source commit from metadata: `8f21153b7b71146db632d1bc73ea8d78399f2428`.

| Initial1 artifact | SHA-256 |
| --- | --- |
| `g2-execution/INITIAL_SOURCE_COPY.json` | `b13276bb4a68d4ac230fca875e945d860478b41789bfa853f63df664efc1cefb` |
| `g2-execution/HELPER_REBINDING.json` | `2c5efa0e2eb17aceea7b2c8f1e2f67fe69a2c7dd8ecdea7ea96b19cfefae592f` |
| `g2-execution/runner-constant-only.diff` | `0bd01f8cecea304fc214d4c8240b489d413824667aa7262c3a78bfc0e22f5679` |
| `g2-execution/run_backend_static_initial1.py` | `e54496e72ac59e5ec56012ebaba36fc02c0581eb2b3d5fa0abf2a6e3d9b27de6` |
| `g2-execution/backend-full/run_full_backend.py` | `be4a3f8a645166ab7f5e495f92d47407b74aea0eb5a7603ca26907923f200db6` |
| Initial1 expected map, now `g2-execution/expected-native-source-pins.initial1.json` | `e2e62a31edba2b7cd154ce1ab3d201e732f9a4cd68bc994157f8fc43a9fe26c3` |

## Source and expected-map reconciliation

- G1 FINAL8 inventory: 759 entries. Initial1: 762 unique paths. Metadata comparison preserved all 759 predecessor path/hash values and added exactly the three paths below.
- Active expected-source map: 579 predecessor entries to 582. All 579 old values unchanged; exactly those same three additions, matching the inventory.
- All 140 frontend inventory values unchanged. This supports carrying the source-bound predecessor result only; it is not a fresh G2 UI run.
- Independently hashed initial1 new-file bytes matched the root checkout, lab, inventory and expected map at inspection time.

| New file | Initial1 SHA-256 |
| --- | --- |
| `backend/app/schemas/shared_route.py` | `42a97317d9ca7e418f54136cf29deed713083bdc4ce687d0566d81255e5eb5cb` |
| `backend/app/domain/shared_route_allocator.py` | `da57a45f674133db42995138842d0ce8b904cea09f3b57e7abb0b851f776913b` |
| `backend/tests/test_shared_route_allocator.py` | `8588134bdd2129c3d376a6c1dae3ff5cdd3df52182f6bfce78c3ea4f234e2b48` |

The initial1 schema is now preserved at `g2-execution/rejected/static1-source/backend/app/schemas/shared_route.py`; its actual hash still matches the table. Inventory comparison is not a fresh full physical source preflight: this reviewer independently hashed the new paths and finite helper packet, and compared predecessor source values as metadata.

## Finite helper packet

The actual `backend-full` packet has **12 files**, distinct from runtime helper/receipt counts. Ten files retain the exact G1 bytes; only the runner's diagnostic-target constant and active expected-source JSON changed.

| Unchanged packet file | SHA-256 |
| --- | --- |
| `guard_runtime.py` | `6835a7e41d7abe67ed02afef30c1feb142d36bf87648c1638fd98920aa3728a3` |
| `guard_optional.py` | `e309aa99aaf671f70a0e8292600b82d46eb77215af3316703553a98daba03627` |
| `sitecustomize.py` | `747bb4ba27a5f002f45d28e590776e8e052039a8acf949da0ddba61dc12d8bc7` |
| `pytest_full.py` | `ae987bac75d8d22c63be7448d67cefd04480cb1ff67894d18f3288090300ffe1` |
| `os_network_probe.py` | `7ff451578d221dce4d781d0180bfb6bbc45b576d4a7cc61719b12586286105e5` |
| `mock_endpoint_plugin.py` | `fee728e2ff824b07b0e927b47c8087f08acc2111277d41053caffc3e37b48588` |
| `asset-requirements.json` | `852b12e28dd3f62bcaead8589609ec7127c5b78040b6f00f8f9b80a4ba20087c` |
| `transitive-requirements.json` | `64c90bb19bfbf9972079075dee038ddd708fb548ec0e72800ed6288a748ca4c4` |
| `existing-public-fixture-paths.json` | `913254fd326c5f89c159b33941753d9aac8e70b270ad8ea03ca02825e5e5f849` |
| `expected-native-source-pins.predecessor.json` | `86698d7828d71bd5fddd2abc84685370c901f6fba3a3b2b4700bf9e72c7a0536` |

The direct runner diff matches the stored constant-only diff: `DIAGNOSTIC_TARGETS` changes from the two G1 graph tests to `['tests/test_shared_route_allocator.py']`. Preimage runner SHA: `3ed463bd966cec9aba7c04274f217768b1fb5b6ce5ebf2995a12b606aa9fb311`; all other runner bodies, defaults, guards and full-mode behavior remain byte-identical. Expected-map preimage: `c36648b7736cd3be95174ee0e2b278904263b987a5983c6ad55068a5fd4b4f8c`.

## Narrow static launcher and dependency links

The static launcher differs from the seven-step predecessor in source/output namespace, removal of four frontend steps, and the three-step success count/status. It invokes only backend Ruff check, Ruff format check, and mypy, stopping after the first failure. No pytest, frontend, browser or full-run chain is present.

It preserves the shared `.run.lock` opened with nontruncating `r+`, exclusive nonblocking flock, inherited `(deny network*)` sandbox policy, before/after source maps and `BACKEND_STATIC_PASS_NOT_FULL` status only if all three steps succeed and sources match. The new launcher has no application import.

Actual symlink targets remain unchanged:

- `source/backend/.venv` → `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/.venv`.
- `source/frontend/node_modules` → `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend/node_modules`.

No dependency was installed or upgraded by this review. The carried frontend receipt is `bdcd3b829582611b23df1f54f0a3b328b9519059ae47bb49823054f2f7c9b524`, explicitly predecessor-only.

## Conclusion

No new binding blocker was found for the narrowly prepared initial1 static/focused diagnostic boundaries. Initial1 did not acquire full-backend, frontend, API/persistence/CAS, deployment or live-search acceptance by this review. Runtime preflight, guards, JUnit and tool results belong to separately recorded root executions. The later Ruff failure does not invalidate this finite binding comparison and must not be concealed by an initial2 receipt.

Reviewer operations: ordinary source/JSON reads, hashes, metadata comparisons and diffs; external report write only. No application/helper imports, execution, tests, providers, labels, Git or checkout edits.
