# Independent starter curriculum and requirement-plan review

**Date:** 2026-10-11. **Verdict:** `STATIC_REVIEW_QUALIFIED`, limited to the exact files below. **Outstanding concrete blockers in this scope:** none. **Runtime/tests:** `NOT_RUN` by this reviewer. This is review of an external proposal, not primary integration, deployment, calibrated learning effectiveness, an official exam score, or admissions/search-quality acceptance.

Reviewer: `/root/audit_search_logic`. Author: `/root/audit_backend_product`; root remains the sole integration writer. I changed only this external review document. No proposed source, Git, runtime, provider, stopped model, closed evaluation, labels or heldout input was accessed or changed for this review. No additional web retrieval was needed: exam statements were compared with the already completed official-source audit, whose access date is 2026-10-11.

## Exact inputs and read coverage

Proposal root: `exam-preparation-2026-10-11/proposals/backend/`.

| File | Read coverage | SHA256 |
| --- | --- | --- |
| `CONTRACT.md` | Full, 32 lines; reread after the additive exam metadata and history/current-scope clarifications | `681cca32ae0ed6d96e0e149d379ec3916e65b639f55a29ad51c81bd0ad6c3809` |
| `files/backend/app/preparation/catalogue.py` | Full, 375 lines; all 9 prompts, every choice, answer and explanation, six exam notices, projection and grading functions | `8ca74f40b88df74a27bc5b0d5aa52d5e60ce5b5417f4e37c049690b47d716169` |
| `files/backend/app/domain/preparation.py` | Full, 213 lines; reread after the SAT policy correction and root-requested SAT component links | `c66f4a31a656f2e664bf90b75e6130085ab31471335103057ca7a610c74cfcc4` |
| `files/backend/app/schemas/preparation.py` | Full, 143 lines | `8cae2435eda20de914313aaff734a28790dd3a0e7d2784559e00bdc4ac0500aa` |
| `files/backend/tests/test_preparation_domain.py` | Full, 203 lines; assertions read, including three added SAT component cases; no collection or execution | `6234322046285b8e283e7cc0bcc23fb8ca71283c8d39da6900c5069b96d2fa4a` |
| `files/backend/app/api/routes_preparation.py` | Full, 330 lines, as contextual snapshot for stored-result freshness, ownership and scope construction; not a review of the wider API packet | `f98fdd452cc4d98432c24530ac5d34558ffeecb697bf872c0dcfbc8d111944cc` |
| `audits/official-exams.md` | Full; primary-source facts, rights boundaries, retrieval qualifications and date | `23b1ee778dece61edf0d1721011ac582c76617208fae2e03e77b2e152a882cdd` |

The initial five proposal hashes independently matched the author's bounded READY message. A final hash recheck detected root-requested SAT component links and contract clarifications after READY; I fully reread the three changed files and rebound this receipt to the hashes above. The author then confirmed these exact final stable curriculum hashes, with catalogue/schema unchanged. Route context was independently hashed after the full reread. Changes to any of these files require requalification; this receipt does not cover unseen later bytes.

Imported base contracts were inspected only in the preserved external `release-reconciliation-2026-10-09-v3/source/` ordinary source:

| Base file | Read coverage | SHA256 |
| --- | --- | --- |
| `backend/app/domain/claim_scope.py` | Full, 193 lines; particularly `covers`, contradictions and gaps | `e29c2f751734396d2208a8c968588f8f561813017785cd1a58067a56d1f5753c` |
| `backend/app/schemas/claim.py` | Full, 143 lines; `ClaimOut`, original excerpt/source/scope, 600-character existing excerpt cap, `Conflict` | `109d65d69da8d0d773618b8ff35487d4bea1bb37b8f60acb8895d1baaa9bf794` |
| `backend/app/schemas/result.py` | Lines 40–85 only; exact `RequirementCheck` fields | `f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974` |
| `backend/app/domain/eligibility.py` | Relevant symbols plus lines 344–382 and 440–460 only; native SAT optional/blind distinction | `ec246fc2c2b6953c901d3ba1658e92f26a20d7dd678d3434d05cd72512bf0387` |

These partial reads are not a whole-backend review. Payment models, migrations, wider API tests, frontend rendering, concurrency and persistence gates are outside this curriculum receipt.

## Question correctness: independent manual review

Every item has one defensible answer among its stated choices. Explanations support the actual prompt; they add no claimed official score conversion or unverifiable admissions fact.

| Item | Correct choice | Reason and excluded distractors |
| --- | --- | --- |
| `ir-1` | b | The passage states increased visits. A permanent policy and cost savings are not stated. |
| `ir-2` | c | Harvest figures are absent. Neither garden's greater yield follows from watering frequency. |
| `ir-3` | a | Heavy rain is expressly the delay's cause; director and visitor details are absent. |
| `sm-1` | b | `6 + 4h = 22` gives 4 hours, rather than 3 or 7. |
| `sm-2` | a | One quarter of 80 is 20; 25 is the percentage, and 60 is the complement. |
| `sm-3` | c | Constant rate is 6 boxes/minute; 5 minutes gives 30. |
| `sr-1` | b | The survey reports only new-route users' journeys. City-wide outcomes and elimination of traffic delays are unsupported. |
| `sr-2` | c | It has a complete main clause. The other two choices leave dependent constructions without a main clause. |
| `sr-3` | a | The prompt asks for contrast; “However” supplies it. Causation and exemplification are not the stated relation. |

The current nine items are deliberately elementary, short original exercises. They do not approximate a full IELTS Academic Reading paper, a four-skill course or an adaptive Digital SAT. That is acceptable for the declared **starter** scope, and cannot establish exam readiness or mastery. Original authorship is declared in the module; this review confirms internal correctness and the absence of imported official item assets in these files, not a global plagiarism clearance.

`public_lesson` exposes prompts and choices, without `correct_choice_id` or explanations. `grade` requires every question exactly once, rejects unknown choices, returns the authored explanation and raw correct/total, and does not write or estimate an official score. Content version participates in request binding; the module requires a new version when items change. No band, SAT scale conversion, certificate or admission probability appears here.

## Evidence and policy contracts

- **IELTS type and components:** the catalogue is explicitly IELTS Academic and the starter covers Reading only. It requires checking overall **and** component minima plus delivery/retake/waiver acceptance. A current overall claim can link reading practice, but the original check remains visible and no other component is inferred. Only an explicitly named IELTS Reading subscore receives the Reading lesson. General Training, UKVI Academic, Online and One Skill Retake are not automatically accepted.
- **Original requirement is preserved:** `project_checks` returns the original `RequirementCheck`, including status, values, explanation and `published_scope`, plus referenced `ClaimOut` objects and their original IDs/URLs. It does not recompute a minimum, replace a GAP with PASS, or compare raw practice totals with an admissions score.
- **Unknown scope remains unknown:** current evidence requires verified-current status, official domain, non-discovery specificity, HTTPS, recorded scope and `ClaimScope.covers(requested) == YES`. The base contract treats unnamed requested dimensions as gaps, not universal coverage. Unrecorded scope, empty scope, old intake, wrong programme and unresolved reference cannot create current evidence or a lesson recommendation.
- **Freshness/conflicts:** the route derives the requested institution/programme, degree, intake, nationality, residency and qualification from the owned case/result; recomputes claim freshness; marks a result stale when the saved profile is newer; and propagates unresolved conflicts. Malformed conflict evidence is not silently declared resolved. No official page is fetched or research enqueued.
- **Alternatives and waivers:** coexisting English score families do not imply AND/OR or a highest combined threshold. They become `alternatives_unresolved`; a waiver claim becomes `waiver_check`, never verified waived. Neither state supplies automatic lesson recommendations. Applying this check to all stored claims may conservatively withhold suggestions when an irrelevant claim is present; it cannot grant an unsupported waiver or acceptance.
- **Research and practice remain separate:** a locked research result returns no checks/claims. Current source evidence means a stored snapshot is applicable under these recorded dimensions, not that the learner satisfies it. An unknown check/unsupported exam receives no inferred threshold or substitute lesson.
- **SAT optional is separate from not considered:** the final projection recognizes only explicit optional/test-optional/not-required strings with a matching NOT_APPLICABLE stored check. Test-blind, “not considered” and “not optional” remain `unknown`; the exact original policy is retained.
- **SAT component practice is narrow:** exact `SAT Math`/`SAT Mathematics` labels link the Math starter; exact `SAT Reading and Writing`, `SAT Reading/writing` or `SAT Reading_writing` labels link the Reading and Writing starter (case-insensitive). SAT total retains both. These are lesson suggestions only; the original threshold/status is not split or re-evaluated.

## Catalogue, source and rights handling

Six families are present, but only IELTS Reading and the two SAT tracks have lessons. TOEFL iBT, DET, HSK/HSKK and CSCA have `course_status=planned` and empty track IDs. The notices retain the materially relevant qualifications from the official-source audit:

- TOEFL tests from 21 January 2026 have the changed report scale/edition; no old section conversion is invented, and legacy profile fields are explicitly called out.
- DET recognition is not programme/intake or visa acceptance, and practice range is not a certificate.
- HSK3.0's announced 13 December 2026 rollout is future relative to the checked date; syllabus publication does not prove a booked test switched. The exact CTI dated notice is now linked.
- CSCA exists but subject combination depends on institution/programme/route; it is distinct from HSK. No universal China mandate, entry score, verified score-validity duration or automatic reuse of 2026 requirements for 2027 is claimed.

All exam URLs are external link-only metadata; these modules contain no downloader, official test item bank, exam images/audio, copied full paper, branding asset or provider request. The original reading passages, math and grammar prompts require no official exam-item ingestion. Stored admissions `ClaimOut` excerpts retain source URL/scope/status rather than being converted into official practice questions. The existing 600-character excerpt cap is not a commercial reproduction licence.

The rights evidence remains in `official-exams.md`, including [IELTS commercial-use permission](https://ielts.org/legal/ielts-copyright-and-trade-mark-statement), [College Board reproduction rules](https://privacy.collegeboard.org/copyright-trademark/request-instructions), [College Board AI-use restrictions](https://privacy.collegeboard.org/copyright-trademark/request-form), [ETS permissions](https://www.ets.org/legal/permissions.html) and [CTI legal notice](https://www.chinesetest.cn/legal-notice). These links were verified for the prior official audit on 2026-10-11, not newly fetched during this static review. No licence grant is asserted. Future hosted official material still requires specific licence evidence; linking an owner resource does not supply it.

## Findings sent before seal and disposition

1. **Confirmed draft policy bug, corrected before this receipt:** initial `_policy` converted any matching NOT_APPLICABLE SAT_POLICY into `optional`, although native `eligibility.py` also emits NOT_APPLICABLE for test-blind. Sent exact ordinary-source evidence to author/root. Final `domain/preparation.py:108` narrows the strings, and the new test asserts blind/not-considered/negative optional remain unknown. No legacy eligibility or stored check was changed.
2. **Source provenance improvement, applied:** the first HSK metadata draft described a dated rollout but linked only general overview/HSKK pages. Final `catalogue.py:255` retains the exact official CTI rollout notice used by the official audit.

Neither point remains an outstanding blocker at the pinned READY hashes. No additional broad audit or source repair was attempted.

## Prepared assertions and exact remaining verification boundary

The domain test file defines nine test functions and **30 parametrized/single cases** by static inspection: four component cases; five SAT optional/blind cases; three alternative/waiver cases; five IELTS test-type cases; seven scope/officiality cases; one conflict case; one unresolved-reference case; one content/public-projection case; three SAT total/Math/Reading and Writing lesson-link cases. They use named synthetic scope and values, not official entry thresholds or closed data. The content-integrity assertion verifies IDs/key membership/public projection; semantic uniqueness was independently reviewed in the table above rather than inferred from that assertion.

These assertions have **not been executed by this reviewer**. The author reported focused mypy/Ruff success in the READY message; that is an author report, not an independently rerun gate here. Root must bind subsequent local gates to the applied proposal bytes and retain the starter/unknown/not-official-score notices in the frontend. API/subscription/database/retry/privacy and UI interaction acceptance remain separate engineering gates. No passing practice test, static review or previous external search gate establishes admissions quality, learner effectiveness, primary integration or release readiness. `GLOBAL_PROVIDER_STOP` and the unmeasured live search-quality boundary remain unchanged.
