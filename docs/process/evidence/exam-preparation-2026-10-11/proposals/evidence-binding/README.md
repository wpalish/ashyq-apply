# Shared-page requirement evidence binding proposal

Status: **PREPARED_NOT_APPLIED_NOT_RUN**. This packet changes only three external copied files. Root is the sole integration/gate writer. Source root is integration-2026-10-11/source; parent reported frozen source HEAD731e241c. SHA256 preimages, not a new Git read, bind the proposal.

## Concrete defect and observation boundary

Current domain/preparation.py:155–162 selects every EXAM_CLAIM_TYPES claim whose source_url is in a RequirementCheck.claim_ids list. The native eligibility generator records source URLs, not claim IDs, at deadline/GPA/SAT/type/waiver/overall/component/TOEFL checks. A shared admissions page therefore causes a non-exam deadline or GPA check to acquire unrelated exam claims; IELTS Writing/Reading checks also acquire SAT/overall/type peers. The original RequirementCheck remains exact, but the preparation claims and possible starter links no longer describe that check.

The backend peer reports the saved native demo showed extraneous mixed claims on deadline/GPA/type/components, with all rows conflicted and lesson_ids empty. That actual demo does **not** prove an observed wrong Reading recommendation. This packet's conflict-free synthetic controls exercise the separate `_lessons` consequence: SAT_MIN_TOTAL has priority and previously adds SAT tracks to an IELTS component; IELTS_MIN_OVERALL can previously add Reading to Writing. Actual RED/after results are **NOT_RUN** here.

## Narrow production contract

- Keep the original eligibility algorithm, RequirementCheck values/status/explanation/scope/refs, API tenant filters, subscription/quota behavior, freshness/scope rules and unresolved conflict logic exact.
- Skip only the native canonical non-exam labels (deadline, GPA, intake, portfolio, interview, credentials, subjects and generic academic entry checks) from preparation goals.
- Resolve legacy URLs through the native exam-label/type map. IELTS component dict claims must explicitly contain that band; numeric blanket subscore claims retain the generator's all-band meaning. A URL with zero or multiple compatible candidates remains unresolved, without fabricated selection.
- Exact-ID references select that specific compatible exam claim. A paired URL supplies its provenance only; it does not pull in same-page peers. Known label/type/component mismatch remains unknown. Unknown refs still contribute unknown state.
- Unsupported exam-like legacy labels remain visible with unknown evidence; future country/degree exam labels need an explicit binding contract. Generic URL ownership is not enough.
- Starter links require their named canonical label. SAT total links both original starters; named Math/Reading and Writing retain their existing component links. IELTS overall retains partial Reading practice; IELTS Reading links Reading only; Writing/Listening/Speaking/type/policy get no unrelated shortcut.
- Claim payloads/quotes/source URLs/IDs/scope/status and source order are retained verbatim for selected evidence. Shared-URL unresolved conflicts remain conservatively blocking under the unchanged conflict rule; this packet does not settle programme policy or AND/OR semantics.

## Actual native label map

| Native source label | Legacy URL allowed claim type |
|---|---|
| SAT total | sat_min_total |
| SAT policy | sat_policy |
| Accepted IELTS test type | ielts_accepted_types |
| English test waiver | english_test_waiver |
| IELTS overall | ielts_min_overall |
| IELTS listening / reading / writing / speaking | ielts_min_subscore; matching band required for dict |
| TOEFL total | toefl_min_total |
| Entrance examination | entrance_exam_required |

These labels come from ordinary domain/eligibility.py:349–398 and491–587. Existing named SAT skill aliases are retained from the original planner/tests. adapters/applicability.py governs award degree applicability and does not produce RequirementCheck labels. Other enum families (DET, generic language/English evidence, test validity, scholarship scores, superscoring) have no canonical RequirementCheck label emitted here; exact-ID evidence is retained, while unsupported legacy URLs fail unknown instead of guessing.

## Test packet and staged reproduction

Native files are copied with their original entire bytes as an exact prefix: no old test/import/assertion/mocks/fixture changes. Adds21 pure cases and8 API cases (4 semantic cases × native SQLite/PG fixture). Existing30 pure+92API remain; conditional foundation count151 and full native count4682 only if no other backend change intervenes.

1. Root verifies current preimage hashes, then stages **proposed-tests.patch only** into an owned isolated copy. Existing domain source stays unchanged for actual RED.
2. Root runs the exact selectors in new-control-selectors.json through the existing owned guarded local harness; retain both API database variants. Record product failures separately from setup/guard failures. No provider/LLM/search call is needed or authorized.
3. After independent review and actual RED, root applies proposed-source.patch unchanged. Rerun the identical new assertions, all retained preparation controls and the required native/static/source-binding gates. Do not skip cases or weaken mocks/assertions to make green.
4. Final prepared counts/hashes are metadata, not executed acceptance. A source change invalidates the earlier backend595 terminal binding until refreshed. Search quality and GLOBAL_PROVIDER_STOP/UNSCORED remain unchanged.

Artifacts: proposed-source.patch; proposed-tests.patch; proposed.patch; source-pins.json; new-control-selectors.json. No install, network, test or app runtime was performed by the author. Only AST parse, source-prefix/body equality and metadata/hash checks were performed. Ruff/mypy/runtime are NOT_RUN by this author; root owns them.
