# QA VERIFY_CANDIDATE — T32 A3 (ClaimStatus backend↔frontend contract sync), campaign c2

- ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE
- DATE: 2026-09-07
- WORKTREE: /Users/wpalish/ashyq-worktrees/c2-t32-verify-a3 (branch ai/c2/t32/verify-a3)
- BASELINE: 2dd9c4c7da4c2a58ad2027f32776610cb41454e5
- CANDIDATE: 9b362c823fa65bf3c95fe154419c8f6ba1b2dc51

## STATUS: VERIFIED_PASS

## CHECKED_SHA
- `git rev-parse HEAD` → `9b362c823fa65bf3c95fe154419c8f6ba1b2dc51` (matches frozen candidate)
- `git status --porcelain` → empty (clean tree, before and after all gates)
- `git rev-list --count 2dd9c4c..HEAD` → 1 (single commit on baseline: `9b362c8 fix: T32 A3 sync ClaimStatus TS union + status tone with backend SUPERSEDED`)

## SCOPE_CHECK
`git diff 2dd9c4c..HEAD --numstat`:
```
2	0	frontend/src/lib/format.ts
3	1	frontend/src/types.ts
```
Exactly the dispatcher-approved 2-file scope; no other files.

Hunk review (full diff read):
1. `frontend/src/types.ts` (+3/−1): `ClaimStatus` union gains `| 'SUPERSEDED';` appended last, matching backend enum order (`backend/app/domain/enums.py` `ClaimStatus`: VERIFIED_CURRENT, POSSIBLY_STALE, CONFLICTING, UNVERIFIED, NOT_FOUND, NEEDS_OFFICIAL_CLARIFICATION, SUPERSEDED-last). One preceding doc-comment line. Semicolon moved to the new last member. NOTHING else.
2. `frontend/src/lib/format.ts` (+2): `claimStatusTone: Record<ClaimStatus, Tone>` gains `SUPERSEDED: 'neutral',` plus one doc-comment line. Tone 'neutral' matches the NOT_FOUND/UNVERIFIED informational family. NOTHING else.

Critical scope cross-checks:
- `claimStatusTone` is the ONLY exhaustive consumer (`Record<ClaimStatus, Tone>`); `STATUS_LABEL` and `STATUS_MEANING` are `Record<string, string>` (non-exhaustive by design — already lack NOT_FOUND/CONFLICTING/UNVERIFIED), so no further hunks were required for typecheck.
- No `.py` files, no behavior/logic branches, no test files modified.

## GATES (all re-run for real in the verification worktree; logs in logs/)
| Gate | Command | Result | Exit |
|---|---|---|---|
| a. contract | `cd backend && ./.venv/bin/python -m pytest tests/test_frontend_contract.py` | 24 passed in 3.90s | 0 |
| b1. typecheck | `cd frontend && npm run typecheck` | clean | 0 |
| b2. lint | `cd frontend && npm run lint` | clean | 0 |
| b3. vitest | `cd frontend && npx vitest run` | 20 files / 182 passed (182) in 2.44s | 0 |
| b4. build | `cd frontend && npm run build` | built in 447ms | 0 |
| c. backend | `cd backend && ./.venv/bin/python -m pytest tests/test_api.py tests/test_pipeline.py` | 94 passed, 1 warning in 46.20s | 0 |

Extra confirmation run: `pytest tests/test_frontend_contract.py -o addopts= -v` (pytest.ini has `addopts = -q`, which masked per-test output on the first run) → all 24 individually listed PASSED, including the exact previously-failing case `test_the_typescript_union_matches_the_backend_enum[ClaimStatus-ClaimStatus] PASSED`.

## CONTRACT_SEMANTICS_CHECK
Read `backend/tests/test_frontend_contract.py` (195 lines) in full:
- `test_the_typescript_union_matches_the_backend_enum` asserts `parse_union(types_source, alias) == {member.value for member in enum_cls}` — Python set `==` is equality in BOTH directions (no extras on either side). The original integration failure message ("Extra items in the right set: 'SUPERSEDED'") matches exactly this assertion failing on the backend-only extra; the fix (adding SUPERSEDED to the TS union) is the correct remedy, not an expectation weakening.
- The parser strips `//` and `/* */` comments before parsing (`strip_comments`), so the new doc comments inside the union cannot leak tokens; `test_the_union_parser_is_not_fooled_by_comments` additionally guards `;` inside comments. Verified the added comments contain no stray quotes/semicolons that could break the regex — and the test passes regardless.
- 16 CONTRACT aliases × union test + 8 standalone tests = 24 → all pass, so no OTHER enum drifted (EligibilityStatus, AdmissionsFit, Bucket, FundingFit, FundingClassification, SourceSpecificity, UserDecision, PipelineStage, CostCategory, ScholarshipType, ApplicationMode, DocumentOwner, DegreeLevel, ApplicantStatus, DirectMessagePolicy, JobStatus all verified equal).
- `test_every_status_the_ui_colours_is_a_real_backend_value` confirms every `claimStatusTone` key (incl. new SUPERSEDED) maps to a real backend value.

## SECURITY_SKIP_JUSTIFICATION_CONFIRMED
Confirmed from the diff: the candidate changes exactly 2 `.ts` type-declaration files — one union member + one Record entry, zero behavior branches, zero `.py` changes, zero test changes. A3 does not touch any production code covered by the A2 security review (T32 backend SUPERSEDED logic at 2dd9c4c). Security re-review intentionally NOT dispatched — justification holds.

## BLOCKERS
None.

## OBSERVATIONS (non-blocking, for the record)
- `STATUS_MEANING` (`Record<string, string>`) has no SUPERSEDED gloss, so a SUPERSEDED chip would have tone but no tooltip text. Outside the approved 2-hunk scope; not enforced by typecheck or contract tests; flagged as a possible follow-up for the planner, NOT fixed here.
- First contract-suite run used `-v` which was neutralized by `pytest.ini` `addopts = -q`; re-ran with `-o addopts= -v` to capture per-test evidence. No retries were used to mask failures; no timeouts altered.

## NEXT_ACTION
Candidate 9b362c8 is verified for T32 A3. Hand back to the dispatcher/integrator to re-gate on the integration branch (full backend suite per integrator role) and proceed with reviewer sign-off. QA does not grant merge approval.

## ARTIFACT_REFS
- /Users/wpalish/ashyq-apply/ai-team/outputs/c2-t32-a1/qa-verify-candidate-a3.md (this file)
- logs/qa-a3-gate-contract.log — contract suite, 24 passed
- logs/qa-a3-gate-contract-verbose.log — per-test listing incl. [ClaimStatus-ClaimStatus] PASSED
- logs/qa-a3-gate-typecheck.log — exit 0
- logs/qa-a3-gate-lint.log — exit 0
- logs/qa-a3-gate-vitest.log — 182 passed
- logs/qa-a3-gate-build.log — exit 0
- logs/qa-a3-gate-api-pipeline.log — 94 passed
