# G3 initial gate preparation review

Reviewed at: 2026-10-12T05:57:23Z (UTC)  
Reviewer: local_release_readiness  
Qualification: **PREPARATION_QUALIFIED_ONLY — NOT_EXECUTED — SOURCE_NOT_APPLIED**

## Scope and authority

This review read the two authorized stage metadata documents first, then compared the declared external G2/G3 helper members and hashed only the 772 declared baseline source files in the primary and G3 lab roots. No source proposal packet was read. No helper, interpreter, application, test, import, migration, database, Git, HANDOFF, provider, auth, network, or stopped workflow was executed or changed. Only this external review and its seal are produced.

Stage directory:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/docs/process/design/admissions-actions-today-2026-10-12`

Authorized metadata:

| Document | SHA256 |
|---|---|
| G3_INITIAL_SOURCE_GRANT.json | `2d69074ecf90d164b8535484004667feca1529c9eea92a8352acd503c190ceb2` |
| G3_INITIAL_GATE_PREPARATION.json | `08f1af1a8dc089d6cb4d6a24f3fc7fa4f27dabbb7225fb0ad99b515ffc8e77a0` |

Metadata declares branch `task/admissions-actions-today`, released parent `e58443ef1d8909e3b4faecd5b0bba52114cdd925`, predecessor Draft PR 87, and root as the sole source/Git/runtime writer. Those Git identities were not independently queried because Git activity was outside this task.

## Baseline source binding

Primary source:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`

Prepared G3 lab source:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g3-execution/source`

| Check | Observed result |
|---|---|
| Grant baseline entries | 772 |
| Preparation source entries / unique paths | 772 / 772 |
| Preparation path/hash mapping equals grant appbaseline772 | true |
| Absolute source paths equal source_root + relative path | true |
| Invalid absolute/traversal/tab/newline paths | 0 |
| Restricted-looking secret/userdata/frozen/heldout/gold paths | 0 |
| Declared source files checked | 772 |
| Missing source or lab files | 0 |
| Primary SHA256 differs from declared hash | 0 |
| Lab SHA256 differs from declared hash | 0 |
| Primary/lab byte comparisons differ | 0 |

Hashes were computed with `shasum -a 256`; equality was additionally checked with `cmp`. No application files were imported or executed.

The three future source files are excluded from the baseline manifest and were absent in both source roots at review time:

- `backend/app/schemas/admissions_actions.py`
- `backend/app/domain/admissions_actions.py`
- `backend/tests/test_admissions_actions.py`

The prepared `backend/.venv` is a symlink whose literal target is exactly the declared existing G2-owned directory:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source/backend/.venv`

The target directory exists. Its interpreter was not executed and its runtime/dependencies were not inspected.

## External backend-full helpers

Compared:

- `product-platform/2026-10-12/g2-execution/backend-full`
- `product-platform/2026-10-12/g3-execution/backend-full`

Both directories contained exactly the following 12 declared regular files. All 12 observed G2/G3 SHA256 pairs matched the original/current hashes in preparation metadata.

| Member | Comparison | Observed G3 SHA256 |
|---|---|---|
| mock_endpoint_plugin.py | byte-identical | `fee728e2ff824b07b0e927b47c8087f08acc2111277d41053caffc3e37b48588` |
| os_network_probe.py | byte-identical | `7ff451578d221dce4d781d0180bfb6bbc45b576d4a7cc61719b12586286105e5` |
| pytest_full.py | byte-identical | `ae987bac75d8d22c63be7448d67cefd04480cb1ff67894d18f3288090300ffe1` |
| run_full_backend.py | approved one-line delta | `6058410c2c668def03ffab69a028e008e24e2851fcab6fc5dcdf74ebc7ef8551` |
| expected-native-source-pins.predecessor.json | byte-identical | `86698d7828d71bd5fddd2abc84685370c901f6fba3a3b2b4700bf9e72c7a0536` |
| guard_optional.py | byte-identical | `e309aa99aaf671f70a0e8292600b82d46eb77215af3316703553a98daba03627` |
| guard_runtime.py | byte-identical | `6835a7e41d7abe67ed02afef30c1feb142d36bf87648c1638fd98920aa3728a3` |
| sitecustomize.py | byte-identical | `747bb4ba27a5f002f45d28e590776e8e052039a8acf949da0ddba61dc12d8bc7` |
| asset-requirements.json | byte-identical | `852b12e28dd3f62bcaead8589609ec7127c5b78040b6f00f8f9b80a4ba20087c` |
| existing-public-fixture-paths.json | byte-identical | `913254fd326c5f89c159b33941753d9aac8e70b270ad8ea03ca02825e5e5f849` |
| expected-native-source-pins.json | byte-identical | `0c13a397c86d053c84de2efb8438dd7b3060e4d6719c4c872ff8fd1464a87794` |
| transitive-requirements.json | byte-identical | `64c90bb19bfbf9972079075dee038ddd708fb548ec0e72800ed6288a748ca4c4` |

G2 `run_full_backend.py` SHA256:

`f17818c4a3a158ee8bdbb71f85a3387b168f438572dc77ff9492173d542da0bc`

Its complete unified diff has a single changed line:

```diff
-DIAGNOSTIC_TARGETS = ['tests/test_shared_route_allocator.py', 'tests/test_shared_route_api.py', 'tests/test_preparation_write_concurrency.py']
+DIAGNOSTIC_TARGETS = ['tests/test_admissions_actions.py']
```

No guard, timeout, floor, locking, network policy, or runtime logic changed relative to the approved G2 helper. This conclusion is based on the complete byte comparison and diff, not on executing the protection.

## Static helper

Compared the explicitly approved G2 `run_backend_static_initial2.py` with G3 `run_backend_static_initial1.py`.

| Helper | Observed SHA256 |
|---|---|
| G2 static initial2 | `69842b6432032e9b02e5b9a0a226d710e1990575aed9fef530ec57d2944b0909` |
| G3 static initial1 | `4c2d4a4c6ac66f6c75000862a60b52e2be81562c31adbdce9a967eba73d8fa44` |

Both hashes match preparation metadata. The complete diff changes only one source/output binding line:

- Source prefix: `g2-execution/source` → `g3-execution/source`
- Evidence output: `evidence/backend-static-initial2` → `evidence/backend-static-initial1`

All other bytes are unchanged, including the nontruncating `r+` opening of the existing shared lock and its `fcntl` acquisition.

## Qualification and remaining boundary

**No mismatch was observed in the reviewed preparation.** The metadata, 772-file baseline copy, interpreter symlink binding, 12 helper members, and static helper have the declared bindings and permitted deltas.

This review does not authorize or report execution. G3 schema/domain/test proposal remains **NOT_APPLIED**. G3 focus/static, physical/native/full gates remain **NOT_RUN**. Unchanged G2 source-pin files and earlier G2 successes do not constitute a G3 PASS. After any permitted source application, source bindings and gate inputs require fresh qualification for those new bytes.

Migration remains ungranted in this step. All prior provider/model/quota/security/reset/live/expert/heldout/controller STOP boundaries remain unchanged.

