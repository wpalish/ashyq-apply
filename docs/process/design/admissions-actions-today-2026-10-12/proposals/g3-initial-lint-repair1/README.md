# G3 initial finite lint repair1

2026-10-12 · EXTERNAL SOURCE PROPOSAL · NOT_APPLIED / NOT_IMPORTED / APPLICATION_TESTS_NOT_RUN

## Exact scope

Root granted only the21 Ruff errors in the primary's three initial G3 source paths. The first failing root output remains unchanged at /Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g3-execution/evidence/backend-static-initial1/ruff.log. This proposal preserves the exact primary preimages in `original/`, three full proposed postimages in `files/` and three narrow diffs.

No primary/lab application source, Git, HANDOFF, helper, browser, database or provider was changed. The application modules were not imported and tests were not collected or executed. All prior STOPs remain unchanged. Root is the sole application writer.

## Twenty-one reported changes

- I001×3: import ordering in the schema, domain and test files.
- RUF021×9: parentheses around the existing and/or subexpressions; their parsed logic is retained.
- RUF007×1: successive receipt pairs now use `itertools.pairwise(history)` instead of `zip(history, history[1:], strict=False)`.
- UP040×6: the six reported TypeAlias declarations use the Python3.12 `type` keyword; the declared alias expressions/names remain intact.
- SIM102×2: combine only the reported self-report validation and default-port nested conditions using short-circuit and.

The domain, schema validators, limits, error dictionary, receipts, ordering rules, tests/assertions and grants were not broadened. The test file change is import ordering only: its complete non-import AST, including all50 source test functions and assertions, exactly matches the pinned preimage. No noqa, ignore, relaxed assertion or changed test selector was introduced.

## Bounded external Ruff observation

Only the three external `files/` copies were supplied to the existing Ruff through the approved g3-execution/source/backend/.venv interpreter. Every Ruff process inherited macOS sandbox rules `(deny network*)`, `(deny file-write*)` with a single file-write allowance for this external proposal directory. `-I -B` isolates the interpreter and avoids bytecode writes; `--no-cache` avoids Ruff cache writes.

The safe fixer was restricted to I/RUF021 after the nine manual requested repairs. Raw command/output records and exit codes are preserved in `evidence/`:

1. Safe fixer: exit0, `Found 12 errors (12 fixed, 0 remaining).`
2. Formatter: exit0, `2 files reformatted, 1 file left unchanged`.
3. Full configured Ruff check of the exact external copies: exit0, `All checks passed!`
4. Format-check: exit0, `3 files already formatted`.

The configured line length and Python3.12 target are unchanged. Ordinary stdlib AST parsing was used only to confirm grammar and preserve the complete test AST outside imports. These checks qualify external lint/format only; no mypy, Pydantic model, app import, runtime, fixture, pytest or native product result is asserted. Root must bind/apply the source pins and run its own required gates.

## Pins

| Relative source path | Primary preimage SHA-256 | External postimage SHA-256 |
| --- | --- | --- |
| `backend/app/schemas/admissions_actions.py` | `225e8b1b2862c92daeb52f239c4e0dd98dd804f9ba3c93713aec61adbc2efd4b` | `5712dbae6a70f7acd21e3e42776e2da132560d97e7b6d412d0602b940601567f` |
| `backend/app/domain/admissions_actions.py` | `d800f46a159c29c09147467b8f1e7d401e05bd17211106e8e20456c4c6b46223` | `cf0c97753b8404fc375ee9ff017b8ce7acb7a88adf84484520d12e747b6218a3` |
| `backend/tests/test_admissions_actions.py` | `1b978ffa9aad5482f440550670f4690173bcaf71e661c30a961f3709a7d03e3d` | `aa25530d91ddc72faf806ef3eb80872d9f3ea77024915620d71548a88c48add3` |

## Integrity and next step

SEAL.json binds all exact originals/postimages/diffs, PREIMAGES.json, this README and four raw external Ruff logs plus their receipt. Current primary bytes were rechecked and still match all three original pins. The root's first failure/log and earlier source proposals were not modified.

The immutable authored packet is ready for root source review/application. This is not source acceptance, a repaired primary gate, full test success, release or product completion.
