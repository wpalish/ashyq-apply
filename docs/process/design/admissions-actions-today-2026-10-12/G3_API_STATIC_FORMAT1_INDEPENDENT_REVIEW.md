# G3 API static-format1 independent review

Date: 2026-10-12 17:49:21 UTC  
Reviewer: `/root/open_search_solutions`  
Disposition: **SOURCE_ONLY — NO NEW BLOCKER IN THE FINITE DELTA**. Application imports, AST execution, lint/type checking, collection, tests, DB and application runtime: **NOT_RUN by this reviewer**.

## Exact inputs and verification

- Packet: `proposals/g3-api-static-format1/SEAL.json`, SHA256 `acbc216142e5cf7c8493308bbbdbdedc7fbfcaa4e78f452df0bf1c62feaa2d76`.
- All **29 declared members** independently matched their sealed SHA256 and byte size. Read the complete six diffs, manifest, formatter logs, root mechanical AST-check source and its saved output.
- Independently reconstructed each sealed unified diff as text against its declared original, checked every consumed context/deletion line, and hashed the resulting stream. All six reconstructed postimages exactly matched the sealed final bytes below. This was text processing; no application import, AST parse, patch application or test execution.
- `format-input` uses precisely the accepted two-path repair (`g3-api-static-repair1`, seal `390e9ac8ac790423fbc50e1a24ae9c8c505e4cdc9214e253b7dd2df330197196`) plus four unchanged inputs. That repair has a separate immutable independent review, `G3_API_STATIC_REPAIR1_INDEPENDENT_REVIEW.md`, SHA256 `39b108ab0341fd91122e108e855b0ea9c2a9bfd9639fec669ebe9b2cedb5e1bf`.

## Complete finite disposition

1. **Route:** the pre-approved `[item for item in events]` to `list(events)` change remains exact. New formatting adds parentheses, splits arguments, expressions and query chains, and reorders `PreparationAccess` before `PreparationGraph` within the same first-party import group. No predicate, ownership/replay order, CAS, source-access condition, error code, receipt field or endpoint contract changed.
2. **API tests:** the only approved behavioral delta remains two synchronous no-argument callback lambdas capturing six loop values through defaults (`method/case/suffix/body`, `offset/limit`). Final formatting preserves the original assertions, parameter values and control flow. No skip, fixture scope, expected failure or permission relaxation was added.
3. **Today tests:** formatting retains the previously repaired four own-`profile_id` schedule lookups. Saved-slot/version/order, single-budget, no-fallback, independent permissions, mixed-read and no-DML assertions remain unchanged.
4. **Concurrency tests:** the complete diff has only three formatting hunks at original lines 927, 999 and 1165, in appended API controls. All seven prior storage test bodies and their helper region lie outside those hunks and are unchanged. The three edited assertions/comprehension retain identical operands and ordering.
5. **Profile export:** only line wrapping of `len(admissions_actions["submission_declarations"])`; keys and values unchanged.
6. **Main:** complete byte equality; empty diff.

No new native route, schema, model, fixture policy, configuration, guard, dependency, test assertion or source scope is introduced by this formatting delta. Earlier core/source-review limitations remain intact; this narrow review does not reopen the architecture or qualify API behavior.

## Bound final postimages

| Path | Final SHA256 |
| --- | --- |
| `backend/app/api/routes_admissions_actions.py` | `6fc7ff0875fe496307bd0cf1d8964f85a5151c9b6a11f1b35e57a3aba6727040` |
| `backend/app/api/routes_profile.py` | `4f69baf65680c533f252c836406118b3974ab5e3969fcbcdb50bc455018ac39c` |
| `backend/app/main.py` | `ce08e0a7672283a94aa6f255115e9403c5fcd851be3cf04ad2ada59fe0174573` |
| `backend/tests/test_admissions_actions_api.py` | `ecd23075788374447c2c96470dcd36b576dd207b18c4af1815ebf36392b6479c` |
| `backend/tests/test_admissions_actions_concurrency.py` | `987429f69ef3784ee84f46e06fd123e62b8535577746fc453eeddb032b20b3d8` |
| `backend/tests/test_today.py` | `2925c3fbbf4c10bc24744d4579e25f838690e441503195ae41d2fed8979fda16` |

## Evidence boundaries

Root's saved formatter logs record route-only import sorting (one fix) and formatting of the six granted files (five changed, main unchanged), both exit 0. These are formatting operations, **not a full lint/type/runtime gate**.

Root's `verify_format_ast.py` (SHA256 `f754cb2a363282f41dcfb7f85054872e94002a251f6b3611521fdfe31a76b2b6`) and `format-ast-result.log` (SHA256 `16456ad24988d7a64151c4c458933a4d4e72809d2e9c81a0fb751ca0e2367f48`) were read, not executed here. The saved proof compares all non-import AST nodes and sorted exact import nodes for every file against `format-input`; all six are reported equal. Attribution is explicitly **root-generated mechanical proof**, not this reviewer's independent AST or runtime result.

This reviewer wrote only this new external note and its seal. Existing packets/reviews remain immutable; no primary/lab source, Git, HANDOFF, helper, configuration or runtime state was changed. Application, gates, release, CI and deployment are not asserted by this receipt.
