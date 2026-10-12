# G3 API finite static repair 1 — independent source review

2026-10-12 · **SOURCE_ONLY / NOT_IMPORTED / NOT_RUN**.

**Disposition: no concrete blocker in the finite two-path repair.** Root-owned import ordering/formatting is not covered by this receipt and remains a later separate source inspection. This review does not claim static, API, database or runtime PASS.

`proposals/g3-api-static-repair1/SEAL.json` SHA256: `390e9ac8ac790423fbc50e1a24ae9c8c505e4cdc9214e253b7dd2df330197196`. The seal and all nine declared member SHA256/byte sizes match. The copied first native Ruff log matches the original external log: `aa93364693496f270f5ce834a9ae400810d4e53b12df0d5e0b30c18b16442b43`. It reports I001, C416 and six B023 variable captures. No new runner or formatter was invoked by this reviewer.

| Exact path | Preimage | Postimage |
| --- | --- | --- |
| `backend/app/api/routes_admissions_actions.py` | `3cb752cd624ec084275f6796225112df16f2943acf6d2bfe9cafaa43653cb3b7` | `3fea2df65bd575917f9b4d5b45aeaa9437c3260f997cb9a70180d5cf27b38cb2` |
| `backend/tests/test_admissions_actions_api.py` | `6ff736b776d26aca16519874e4a4dd0785d9d0b8b40b54ee1869ccf97fc0ddc9` | `4db39ea9192a3897e498d1b6a830586a733dac77b02529966609c7f071fe43af` |

The preimages matched the actual primary files when read for this review. Complete independent original-to-postimage diffs with the sealed labels match both supplied diff hashes:

- Route diff: `8840d008c0e7087a02c630c1b8745b32a17f173101c61e91e7df911ff7195074`.
- API test diff: `994dcefbdfddd32115a3ccb95f8421fd084308198beb8621b6d54727e7a93b2b`.

## Semantic checks

1. Route line1562 replaces `[item for item in events]` with `list(events)`. Here `events` was just constructed as a list of validated receipt objects. Both expressions make a new shallow list in the same order with the same receipt references. Full-history validation, the final scalar head recheck and export contents remain unchanged.
2. API test line284 captures `method`, `case`, `suffix`, `body` in lambda defaults. The callback still supplies the same request method, owned/foreign case path, suffix and body for the current loop iteration.
3. API test line863 captures `offset` and `limit` in lambda defaults. The current history query and its expected receipt slice/cursor assertions remain unchanged.
4. Existing native `tests/test_preparation_graph_api.py::_capture` lines84–95 invokes `callback()` synchronously with no arguments and removes its SQL listener in `finally`. Defaults retain the intended iteration values and are compatible with that existing call surface.

The two complete diffs contain no changed assertions, test parameter sets, request paths, decision/access predicates, control branches, DTOs, source scopes, imports or runtime policies. The six B023 findings concern **six variables in two lambdas**, not six callback functions. The package intentionally leaves I001 for root's narrow native import/format step.

No application import, AST parsing, test collection/execution, database operation, network request, primary/lab/producer-packet write, Git/HANDOFF/config/runtime-helper edit occurred. The only reviewer outputs are this external note and its seal. The earlier immutable source/review packets remain unchanged.
