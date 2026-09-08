# developer-a3.md — T32 A3 (integration repair, campaign c2) — ClaimStatus TS union + tone sync

ROLE_PHASE: ashyq-developer / IMPLEMENTING (completed after dispatcher scope extension)
STATUS: IMPLEMENTED
CHECKED_SHA (start): 2dd9c4c7da4c2a58ad2027f32776610cb41454e5 (integration head, branch ai/c2/t32/dev-a3, tree clean at start — verified)
CANDIDATE_SHA: 9b362c823fa65bf3c95fe154419c8f6ba1b2dc51 — commit "fix: T32 A3 sync ClaimStatus TS union + status tone with backend SUPERSEDED", trailer `Agent: ashyq-developer`, parent 2dd9c4c, 2 files changed (+5/-1). NOT pushed. Worktree clean at this SHA; frozen for review.
HISTORY_NOTE: the intermediate wip commit 6019460 (BLOCKED state, reported earlier) was soft-reset off the branch per dispatcher instruction; it exists only in this report and reflog, not in candidate history. The candidate replaces it 1:1 in content plus the authorized format.ts key.

## CHANGED_FILES

1. `frontend/src/types.ts` (+3/-1): `ClaimStatus` union gained the seventh member `| 'SUPERSEDED';` with a one-line comment, mirroring backend enum order (the union parser strips comments before matching; no semicolon inside — the guarded case).
2. `frontend/src/lib/format.ts` (+2): `claimStatusTone: Record<ClaimStatus, Tone>` gained `SUPERSEDED: 'neutral',` with a one-line comment — the only exhaustive consumer (survey: `grep -rn "Record<ClaimStatus" frontend/src` = this one hit), authorized by the dispatcher with the `neutral` tone (same informational family as NOT_FOUND/UNVERIFIED). `STATUS_LABEL` is `Record<string, string>` — not exhaustive, untouched.

No test file touched; QA assertions byte-untouched. No backend changes. No other frontend file.

## ROOT_CAUSE_FIXED

Backend `app/domain/enums.py` `ClaimStatus` gained `SUPERSEDED = "SUPERSEDED"` in T32 (historical
record, kept forever, invisible to conflict detection/freshness). `frontend/src/types.ts` still
declared the original 6 members, so
`tests/test_frontend_contract.py::test_the_typescript_union_matches_the_backend_enum[ClaimStatus-ClaimStatus]`
failed with `Extra items in the right set: 'SUPERSEDED'`. The exhaustive `Record<ClaimStatus, Tone>`
in format.ts then made the union addition unbuildable — TypeScript was the only gate catching the
missing tone key (the backend contract test only checks tone keys ⊆ backend values, not the reverse).
Both halves are now synced: union member + matching tone.

## GATES (real runs on the exact candidate content; cwd noted; raw exit codes for FE)

| gate | command | result |
|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_frontend_contract.py` (backend/) | **24 passed in 0.52s — GREEN** (was 1 failed, 23 passed at baseline: exactly the ClaimStatus param, `Extra items in the right set: 'SUPERSEDED'`) |
| b1 | `npm run typecheck` (frontend/) | **exit 0 — GREEN** (was exit 2: TS2741 Property 'SUPERSEDED' missing in Record<ClaimStatus, Tone> at format.ts:111) |
| b2 | `npm run lint` (frontend/) | **exit 0 — GREEN** |
| b3 | `npx vitest run` (frontend/) | **182 passed (20 files) — GREEN** |
| b4 | `npm run build` (frontend/) | **built in 450ms, exit 0 — GREEN** (was exit 1 via tsc) |
| c | `./.venv/bin/python -m pytest tests/test_api.py` (backend/) | **66 passed, 1 warning in 32.23s — GREEN** |

Commit sequencing: gates ran on the working tree containing exactly the candidate bytes, then the
single commit was created from that tree (`git status` clean immediately after commit proves
working tree == committed tree), so the results above are valid for 9b362c8.

## RED_TO_GREEN

- Contract test ClaimStatus param: RED at baseline (6-member union) → GREEN at candidate (7-member
  union == backend enum set).
- FE typecheck/build: RED after types.ts-only change (exhaustive Record) → GREEN after the authorized
  `SUPERSEDED: 'neutral'` tone entry. Lint and vitest were green at every stage (esbuild transform,
  no cross-file typecheck — runtime tests never depended on the 6-member union; no exhaustive-usage
  surprises beyond the single surveyed Record).

## MIGRATIONS

None. Type-level + tone-map change only.

## REMAINING_RISKS

- UI rendering of SUPERSEDED claims is declared future work; the tone entry only keeps the exhaustive
  Record honest (a neutral chip if/when such rows surface). No current FE source produces or renders
  SUPERSEDED rows (grep: no references outside the two contract files).
- Tone semantics for SUPERSEDED (neutral vs. a dedicated muted/historical style) remain a product
  call for the future UI work; `'neutral'` was dispatcher-approved for this attempt.
- QA tests implemented as written; zero assertion edits. No coverage changed.

## BLOCKERS

None.

## NEXT_ACTION

Independent QA verify on candidate 9b362c8 in a fresh verification worktree (this report claims no
QA/review passage). Reviewer after QA. No push performed (dispatcher/user gate).
