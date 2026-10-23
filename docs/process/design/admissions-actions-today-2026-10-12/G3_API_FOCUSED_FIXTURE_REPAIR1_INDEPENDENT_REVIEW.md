# G3 Today fixture repair1: independent finite source review

Reviewed on 2026-10-13, completed at 06:03:20 UTC.
Reviewer: /root/open_search_solutions.

**Disposition: NO SOURCE-ONLY BLOCKER FOUND in the four fixture/test changes and the one formatting-only wrapper.**
This is source review, not application, import, collection, execution, runtime PASS, full-gate qualification, or product acceptance. Root owns application and authorized gates.

## Exact scope and integrity

- Grant: G3_API_FOCUSED_REPAIR1_GRANT.json, SHA256 b786a779c02610a7077bb7c172d2de1ac3621baf928d9aaa7ce373b6f84ea60b.
- First packet: proposals/g3-api-focused-fixture-repair1/SEAL.json, SHA256 3085b5585273d3ad1137b7fcaa2a6982553d117a454369c8debc41f1954842a1.
- Formatting wrapper: proposals/g3-api-focused-fixture-format1/SEAL.json, SHA256 55dab4fd5f0e35e04459a0df7b3ee88e3d62ddd680901b595d71e665b84ab6dd.
- All five declared members in each packet independently match their SHA256 and byte count; both seal hashes match. The wrapper input is exactly the first packet postimage.
- Actual primary backend/tests/test_today.py still matched the sealed preimage when inspected: 2925c3fbbf4c10bc24744d4579e25f838690e441503195ae41d2fed8979fda16, 22088 bytes.
- First postimage: 0acb3fcdbb9929fb921920fbcdb57f5d50bd63ef025e38d4871aa432b0c8a86d, 23268 bytes.
- Formatted postimage: 2505c188aeb0d37eea2cdd4762a57279500e9e98d979cebad1175abaf958693b, 23260 bytes.
- Each of the four intended new textual spans occurs exactly once. Independently reversing exactly those four spans reconstructs the entire first preimage byte-for-byte. Reversing the single format line consolidation reconstructs the entire first postimage byte-for-byte. No AST/import/runtime was used by this reviewer.

## Finite change review

Line numbers below refer to the final formatted postimage in proposals/g3-api-focused-fixture-format1/postimages/backend/tests/test_today.py.

| Change | Source evidence | Disposition |
|---|---|---|
| Saved lessons and own attempt may have distinct native content versions | Lines 149-161 retain the full ordered tuple equality of occurrence ID, date, timezone, entire ref and minutes against accepted allocation slots. At 167, version-set comparison uses those saved slots; at 172, the exact own attempt UUID is additionally required to retain its submitted version. The prior attempt-presence assertion and single-ledger/no-DML/no-premium/all-row snapshots remain. | Correct fixture expectation. No latest-version substitution or loss of exact attempt version. |
| Accepted personal dependency | At 417, the dependency is the ID from the first accepted own task receipt, rather than an invented absent ID. Native domain/admissions_actions.py:349-350 rejects a missing task before creating a record; the new accepted dependency is valid. | Correct positive fixture; no fabricated accepted invalid state. |
| Missing dependency refusal and exact repeat | At 420, a deep copy of the accepted personal input changes only its dependency to the missing 32-hex ID. One command and one UUID are created before the two-call loop at 431, with expected revision 4. Both requests must return the native record_not_found error, emit no DML, preserve all native and G3 current/event rows, and leave the exact original request body unchanged. | Meaningful refusal/repeat control retained alongside the valid Today scenario. No UUID regeneration, fake ACK, or clock/state repair. |
| Honest dependency readiness | At 470, the undated card expects dependency_not_reported_ready for the existing own dependency. Native domain/admissions_actions.py:1225-1230 emits this when its applicant report is not prepared/sent/received or requires review. | Matches the real accepted state; defensive dependency_missing read behavior is not treated as an invalid command acceptance path. |

The full first postimage and both full diffs were read. Imports, helper definitions, other native tests, assertions outside these four spans, source contracts, database/config/guard code and application code are unchanged by the first packet. The format wrapper only joins the two lines of the existing kind-and-attempt-ID filter; predicate order, literals and assertions are identical. Its saved manifest reports root AST equality, but the reviewer's independent preservation proof is textual inverse equality, not AST execution.

## Native supporting pins and controls

Only ordinary source reads and file hashing were performed:

| Native file | SHA256 | Read seam |
|---|---|---|
| backend/app/domain/admissions_actions.py | 86483457542cfd79c13b630c7d06eed5afe446a39fd2bf070d1f04f808e29bc8 | Missing dependency 349-350; readiness reasons 1191-1232; record_not_found maps to 404 at 22. |
| backend/tests/test_shared_route_api.py | 84c166681851a448e24aaeb14bcdab4587777c47e3e137027760130c9fcfeee8 | route_input and own_review 169-179 preserve exact attempt ID, lesson ID and submitted content version. |
| backend/tests/test_preparation_api.py | fde8e742aabc908f807937241f7480b9a1260e88faa9465045c874b258e79437 | body 135-148 uses the native submitted content version. |
| backend/tests/test_preparation_graph_api.py | 61d52735b742a9a527e78331965a19a2a7f55d7ab76db947c2e380e77afd7987 | _capture 84-95 records statements around each actual callback and removes its listener in finally. |
| backend/tests/test_admissions_actions_api.py | af984816e28aa0af12f69c49eba8dff5d555c5804a4cbd7d887f5106440eea6a | command 71-77 generates UUID once; safe_error 134-137 checks exact native status and error envelope; new_personal uses accepted HTTP receipt. |
| backend/tests/test_admissions_actions_concurrency.py | 987429f69ef3784ee84f46e06fd123e62b8535577746fc453eeddb032b20b3d8 | native_snapshot 70-84 reads all native tables; stored 98+ reads fresh-session G3 current and all ordered events. |

No source proposal/application edits, primary/lab writes, AST, imports, formatting/linting by this reviewer, test collection/execution, database access, Git/HANDOFF/helper edits, providers/network, or stopped research work occurred. Only this new external review and its metadata seal were written; all reviewed packets remain immutable.

## Remaining qualification

No extra source prerequisite is proposed. Root may apply the exact final formatted postimage under the existing grant and use the already authorized native gates. Executable correctness, both-database results and cleanup/source equality remain root's runtime qualification, not this source-only disposition.

