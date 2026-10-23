# G3 initial lint1 + native import-context2: independent finite review

2026-10-12 14:33 UTC · SOURCE-ONLY · NOT_IMPORTED / NOT_COLLECTED / NOT_RUN

## Disposition

**No source blocker found in the finite combined change. Qualified for root application and its native gates, not runtime acceptance.** The original first Ruff failure and both authored packets remain immutable. This review ran no Ruff, mypy, application import, pytest, browser, database, provider or Git command.

The root identified that lint1's external source-root context classified `app` with third-party imports. Its external Ruff success therefore does **not** establish the primary/lab import grouping. Contextrepair2 restores explicit first-party `app` grouping in only three import blocks. The native static2 gate must confirm that classification.

## Packet integrity and complete-diff reconciliation

| Packet | Seal SHA-256 | Declared members verified |
| --- | --- | --- |
| `proposals/g3-initial-lint-repair1` | `d1d6a9605582693540eabda5bb365b2e4f803ab7f9eba536e42177802d8a3ce2` | 16 hashes and sizes |
| `proposals/g3-initial-lint-context-repair2` | `8fad490b5dd25e70e0170365e775fd23806f6f8f0d3064b18228338c747bbaab` | 11 hashes and sizes |

Every declared member was verified before source review. All six supplied unified diffs were independently reconstructed **in memory as text** against their sealed originals; each reproduced the complete exact postimage. Contextrepair2's three originals equal lint1's three postimages. No application patch was applied by this reviewer.

The complete test suffix beginning at `AT = datetime(` is byte-identical between the original primary preimage and final contextrepair2. The same ordered 50 `def test_...` declarations remain; their decorators, parameters, bodies, helpers below that marker and assertions are unchanged. This is source preservation, not 50 tests passing.

## Eighteen non-import repairs

| Change | Exact final source location | Finite review |
| --- | --- | --- |
| Nine RUF021 groupings | Domain:688, 1018, 1115, 1302 | Existing `and` precedence within `or` and original short-circuit order remain. Role association, source authorization, demo/fixture text, case ownership and lesson-versus-own-review access predicates are unchanged. |
| One RUF007 pairwise | Domain:727 | `history` is already a local validated list. Both loops produce the same N−1 adjacent ordered pairs for N≥2 and none for N=0/1. Contiguous revisions, uniqueness, predecessor ID and state-digest checks remain; the loop does not mutate history. |
| Two SIM102 guards | Schema:1471, 1555 | Type guard/colon guard still short-circuits before its original inner condition. Every compared value and original rejection stays; no condition/body or else behavior was removed. |
| Six UP040 aliases | Schema:249–1005 | Alias names and RHS type unions/Annotated discriminators/BeforeValidator are retained. Python3.12 `type` creates runtime alias objects, so this is **not** a claim of identical Pydantic runtime behavior or schema internals. Root's native import/mypy/focused validation gate must resolve them. |

“Domain” and “Schema” refer to the exact sealed final files under `proposals/g3-initial-lint-context-repair2/files/backend/app/`.

The runtime target is source-bound: native Ruff `target-version="py312"`, native mypy `python_version=3.12`, native requirements `pydantic==2.13.4`. The existing LearningTaskRef is a discriminated Annotated alias; this review does not claim an existing native PEP695 runtime precedent. The six new aliases are used as annotations/validation types, not in runtime `isinstance(..., alias)` checks.

## Final pins and retained primary observations

| Relative source | Primary preimage observed before application | Final contextrepair2 postimage |
| --- | --- | --- |
| `backend/app/schemas/admissions_actions.py` | `225e8b1b2862c92daeb52f239c4e0dd98dd804f9ba3c93713aec61adbc2efd4b` | `9f516e35f9b5486960c7dcdef720b2794d58f5bc18c8cb9d3f15ab6a158d477d` |
| `backend/app/domain/admissions_actions.py` | `d800f46a159c29c09147467b8f1e7d401e05bd17211106e8e20456c4c6b46223` | `e3d0c99b72a67b82c694596c7904bab0ae42122aafc6138abb668159f9c0c64a` |
| `backend/tests/test_admissions_actions.py` | `1b978ffa9aad5482f440550670f4690173bcaf71e661c30a961f3709a7d03e3d` | `0c6ff0e8c4c6179e801c98c6923a21bf1ab31357dd26f37a7137b2be1e2c9cae` |

Native configuration pins observed read-only:

- `backend/ruff.toml`: `120fd12496a7783db8a367b4ed00162d22b5503daf80a6e8e9db2246dd3e1ffc`.
- `backend/mypy.ini`: `55078c0c6a1cf044a3581ca8c0adf1dda477106fec1cc8d2b260445d7d6cd782`.
- `backend/requirements.txt`: `4d98978db7324e2a4529fdae5a51130375fb6e5417b2324d42a5b04d69601267`.

## Evidence limits

The read producer receipt binds lint1's external Ruff/format outputs to lint1 bytes and explicitly says no app imports or tests. Contextrepair2 preserves a three-import-fix output and says native context awaits static2. Neither saved observation is upgraded into a primary gate result here.

No new command, exception, weakened validator, changed error dictionary, limit, receipt field, Today ordering, URL predicate, test assertion/selector or persisted configuration was introduced by these diffs. Existing owner/CAS/API/browser/release acceptance remains outside this finite review. Root's next necessary checks are native static2 and the already planned focused initial G3 runtime gate; no broader prerequisite is added.

