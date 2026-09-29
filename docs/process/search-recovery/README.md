# Search recovery, 2026-09-28

Owner-directed bug fix, PR #32. These are ordinary pipeline/source probes and paired rule trials, not a blind expert trace or human certification. Signed gold labels were not edited.

## Reproduced failures

1. Discovery supplied three programme URLs, but `ResearchRunner._stage_verify` checked `programs[:2]`. The third programme disappeared. The regression in `test_pipeline.py` fails when the main-branch method is injected and passes with the shared discovery cap of three.
2. Search titles/news/journal results occupied programme slots without matching fetched content. Content recovery now rejects wrong types, unstated/wrong degree levels and explicit alternate programme variants, then backfills within eight reads.
3. A search result may be a catalogue. Warsaw's `/en/programmes-all/IN` classifies UNKNOWN and has no full degree title, but its own matching link reaches `/en/programmes-all/IN/S1-INF`. A real Fetcher source probe moved from no selected page to the correct detail page with two reads. Both recognized and ambiguous catalogues are tested.
4. Explicit `Language / German` and `Language: Polish` fields were unreadable by the old prose-only rule. Unique labels now establish language; conflicting labels and foreign-language exam names remain unknown.
5. NTU's JS award index exposes no award anchors. An empty funding walk can use one public institution/degree scholarship query, at most three official leads, and the existing Fetcher/classifier. It runs only for a programme with recorded existence, is memoised across programme fields, and search snippets never become claims.
6. `Open to all nationalities` acquired an international-only scope from a later paragraph. That explicit unrestricted audience now stays unrestricted, while eligibility is assessed separately.
7. A continuing course for teachers could acquire bachelor identity from audience qualification words. A fetched course identity/path naming a teacher/professional course now rejects that interpretation before programme extraction.

8. Toronto's topic-course page acquired undergraduate programme identity from its enrolment rules. Explicit topic-course/course-description identity now rejects that route.
9. Groningen graduate awards acquired bachelor applicability from earlier-study GPA/diploma requirements. Decimal GPA points remain inside their clauses, earlier qualifications do not establish award level, and global navigation is excluded from applicability. Actual-source replay now says no for bachelors and yes for masters on both Richard A. Freund and Bolashak pages.
10. A full-title listing claim could carry more than 300 characters of surrounding quote, failing the owner's support rule. Listing-page identity context is bounded without losing the full degree title. Normal programme-detail quoting is preserved; the first broader change failed the byte-identical demo gate and was corrected without changing the golden baseline.

Five earlier Claude faculty/document/oracle commits were also recovered from the branch of already-merged PR #29. Faculty now carries the programme and degree confirmed by the same page; completion-state document forms are preserved.

## Measurements and rejected versions

All paired cases use off/on/on/off on one GitHub cloud runner, 120 seconds and 60 network page reads. HTTP requests may exceed 60 because robots, redirects and retries are separate requests. Every failure remains in the data. No cost estimate is invented when telemetry is null.

| Run | Cases / rule | Result |
|---|---|---|
| [36467254400](https://github.com/wpalish/ashyq-apply/actions/runs/36467254400) | Warsaw, Vienna, HKU / first content recovery | Rejected for promotion: Vienna accepted teacher-education/digital-literacy programmes. Warsaw confirmed once per arm; HKU kept 2/4 correct known facts in every arm. |
| [36467258532](https://github.com/wpalish/ashyq-apply/actions/runs/36467258532) | Tartu, Vilnius, Charles / first recovery | Held-out routing exposed courses, journal pages and ancillary exam pages; no certified claim metrics for these institutions. |
| [36468117996](https://github.com/wpalish/ashyq-apply/actions/runs/36468117996) | NTU, HKU / first award fallback | Found Nanyang once but introduced incorrect international-only scope. Not promoted in that form. |
| [36468122153](https://github.com/wpalish/ashyq-apply/actions/runs/36468122153) | Sabanci, METU / award fallback | Neither arm recovered facts; METU spent its time before search. Sabanci exposed extra funding reads on unconfirmed programmes, now guarded. |
| [36470118064](https://github.com/wpalish/ashyq-apply/actions/runs/36470118064) | Warsaw, Vienna / revised recovery | Vienna keeps 2/4 known facts in all four runs and excludes earlier teacher variants. Warsaw off 0/2 twice, on 0/2 then 2/2. Follow-up actual-source probe fixes the ambiguous catalogue missed by the zero on run. |
| [36470122257](https://github.com/wpalish/ashyq-apply/actions/runs/36470122257) | Tartu, Charles / revised recovery | Charles reduces selected URLs to the primary degree page. Tartu reveals an already-confirmed teacher course, addressed by the classifier repair. Held-out sources remain separate from certified metrics. |
| [36470126611](https://github.com/wpalish/ashyq-apply/actions/runs/36470126611) | NTU / corrected award scope | Off 1/21 correct known facts twice; on 1/21 then 6/21. The successful on run finds the Nanyang award with 0/19 wrong-scope judged predictions. Search-provider drift remains visible; success is not guaranteed for every run. |

`paired-observations.json` records all 60 paired observations, configuration, SHA, capture digest, telemetry, errors and available strict metrics. The source bundles remain in each linked run's log.

The target configuration is also captured across all ten reviewed institutions in [36471138628](https://github.com/wpalish/ashyq-apply/actions/runs/36471138628). This capture uses `9f8a93d`; the later continuing-course classifier repair is independently checked on Tartu. **Measured results:** programme-page recall 6/10, precision 6/20; known-claim recall 18/62, precision 25/27; award discovery 1/3. The earlier Claude capture [36466967792](https://github.com/wpalish/ashyq-apply/actions/runs/36466967792) measured programme recall 4/10 and known-claim recall 10/62 under the same bounds. These are separate live captures, not a paired causal comparison. `full-cohort.json` preserves the target metrics and case diagnostics.

The scorer reports wrong scope 1/27: Groningen's EU/EEA deadline table row, alongside a separately recorded non-EU/EEA row with the same date. Both are actual source rows; the evaluation compares against its single non-EU label. Report the strict number unchanged. The other incorrect scored prediction is Nanyang degree applicability: the adapter records a structured bachelor verdict, while the reviewed value is bachelor_full_time. Full-time applicability has not been extracted and is not inferred from that weaker verdict. Unsupported evidence is 3/14: two Vienna claims on an alternate official copy absent from the signed evidence, plus HKU's quote exceeding 300 characters. The quote is repaired; no signed labels are changed and the recorded capture is not retroactively rescored.

**Remaining bounds:** Aalto robots.txt timed out, Toronto sources answered 403, KAIST admissions timed out and other hosts failed robots reads; UBC exhausted its wall-clock budget after preserving partial facts. Some available pages still do not establish the requested identity, and many required fields remain unknown. This patch is not acceptance of universal coverage or of the entire research engine; it fixes the reproduced search and extraction failures with the negative cases preserved.

## Contracts and verification

No API, persisted schema, migration, ranking formula, signed corpus or Fetcher guard changed. The internal scholarship adapter has an `allow_search` keyword; the pipeline supplies it from recorded programme existence. Diagnostic switches have both positive and negative forms and capture the actual implementation defaults:

- `--recover-search-candidates` / `--no-recover-search-candidates`
- `--search-funding-fallback` / `--no-search-funding-fallback`

Older rank-only experiments must explicitly disable content recovery to isolate their mechanism. Their original assertions remain intact; the stub fetchers intentionally have no page bodies.

Before the final defaults: 2418 backend tests, 94.76% coverage, mypy 296 files; unchanged frontend typecheck/lint/unit/build passed. Golden demo unchanged, Groningen #1 and UBC OUT_OF_BUDGET. Final local gates at 0f5b99d: **2428 passed**, **94.89% coverage**, ruff check/format passed, mypy **296 files**. Golden demo byte identity passes after narrowing compact quotes to listing claims. GitHub gates additionally include SQLite/PostgreSQL, Playwright demo/auth, security audits and container builds; their completion is linked from PR #32. Do not claim universal university coverage from these bounded trials: inaccessible sources, absent programme identity and unresolved facts remain explicit.

## Tartu follow-up and workflow limitations

[36472040264](https://github.com/wpalish/ashyq-apply/actions/runs/36472040264) completed the pipeline capture with zero claims and an explicit HTTP 404 for the stale teacher-course URL. This is a source failure, not live proof that the new classifier ran. The job failed **after** capture when the blinded packet exporter tried to find Tartu in the ten-case signed dataset; the capture and source logs are preserved in its bundle. The classifier regression is verified offline, including preserving a real degree that mentions teacher courses only in body text.

The earlier multi-case expert_baseline invocation stopped before reads; that mode accepts one case. Ordinary benchmark mode covers all ten. A proposed workflow edit was refused because the existing OAuth credential has no workflow scope; it was reverted unpublished. Both diagnostic flags now read implementation defaults, so ordinary benchmark needs no workflow modification.

The superseded a648578 full capture [36474876085](https://github.com/wpalish/ashyq-apply/actions/runs/36474876085) was cancelled after the quote-only demo regression. It is not a final measurement; the corrected candidate is recaptured.

Source code `0f5b99d` was recaptured across all ten institutions in [36475528223](https://github.com/wpalish/ashyq-apply/actions/runs/36475528223): programme URLs 7/10 (precision 7/21), known facts 13/62 (precision 20/21), award discovery 0/3. Warsaw timed out after saving 2/2 known facts but before final URLs; UBC hit its page budget after saving 3/3. Toronto rejects the topic course, but remaining URLs are unreachable HTTP-403 leads: a URL hit is not verified programme existence. NTU returned general indices only. These negatives remain recorded and are not replaced by the earlier 18/62 result. Code CI [36475520836](https://github.com/wpalish/ashyq-apply/actions/runs/36475520836) passed every gate.

## Final award-policy query

The negative NTU capture led to a separate public-query repair at `854cb7e`, initially disabled. It adds degree aliases (bachelor/undergraduate etc.) and eligibility/benefits terms to the single award search. There are no university/award hardcodes or applicant fields; the same maximum five results and three official Fetcher leads apply. CLI `--target-award-search` / `--no-target-award-search` records and forwards the actual selected default.

Paired development [36478314618](https://github.com/wpalish/ashyq-apply/actions/runs/36478314618): NTU off found Nanyang once (6/21 then 1/21 known facts), on found it twice (6/21 each). All four used seven searches/25 HTTP requests; wrong-scope judged facts were zero. The structured bachelor applicability still does not establish the signed bachelor_full_time value. HKU on retained 2/4 known facts twice; off had 2/4 then zero as sources drifted. The expected HKU entrance award remains missing.

Paired held-out [36478319826](https://github.com/wpalish/ashyq-apply/actions/runs/36478319826): Charles preserved the same six predictions in all four arms. Sabanci returned zero in all four, with a wall-clock failure once per arm and inaccessible sources; neither institution has certified labels. This is routing evidence, not signed accuracy. `award-policy-observations.json` records all sixteen observations, including failures. The query is promoted after this comparison; final default capture and gate links belong in PR #32. No synthetic ten-case aggregate is made by mixing these runs with the earlier cohort. The public site is not claimed deployed.

Final promoted-query local gates: **2429 passed**, **94.89%**, 294.74s; ruff check/296-file formatting and mypy 296 files green. Frontend typecheck/lint/**193 unit tests**/build green. Seed again confirms Groningen #1 and UBC OUT_OF_BUDGET; golden bytes unchanged; one Alembic head c5d01b7e4f83. Selected-head cloud checks and normal-default NTU capture are linked with exact completion in PR #32.


## Provider outage diagnostics, 2026-09-29

Both ordinary-default NTU captures (36480602681, 36481185172) failed all seven Serper calls: six programme queries explicitly HTTP400; the award path previously discarded status. After user login, the authenticated Serper dashboard shows -5 credits and 2,505 requests, confirming credit exhaustion. No purchase, card entry or key change was performed; owner top-up/provider choice is pending. Product code does not infer quota from HTTP400 alone. No additional live calls are made while credit is exhausted.

Source `d20ab66` fixes a separate visibility defect: programme outages previously stayed in traces, and funding outages appeared as uninterpretable pages. Optional structured HTTP status and controlled provider labels now reach the existing persisted/API errors through retrieval and live discovery. Logs and diagnostics exclude arbitrary exception text, queries, headers, keys and vendor bodies. Partial programme candidates survive; unknown facts remain separate. UI groups service outages distinctly and counts research issues. API/schema/query/ranking/Fetcher/gold contracts unchanged.

Final local gates: **2439 passed**, **94.91%**, 307.04s; ruff/296-file formatting and mypy 296 files green. Frontend typecheck/lint/**195 tests**/build green; golden unchanged, Groningen #1 PLAUSIBLE, UBC #11 OUT_OF_BUDGET; one Alembic head c5d01b7e4f83. Initial attempt failed only two legacy navigation stub tests, repaired with the new empty diagnostic field and unchanged assertions; full rerun passes. Updated selected-head cloud checks belong in PR #32. Live restoration and public deployment are not claimed.


## PDF-informed structural integrity repair (2026-09-29)

Source `1b40a6b517be2368d96f4f570128eb0492e5b7f0` repairs two independently reproduced defects. IELTS state formerly persisted across the whole document: international Reading 6.0 and domestic Writing 7.0 could become one VERIFIED_CURRENT international map, and the domestic overall disappeared. Extraction now isolates (table_id, row), retains separate requirements, quotes every included cell in source order and abstains before the existing 600-character cap can remove a later band.

Normal HTML Transcript/Diploma labels in a table header, heading or dt were separated from their conditional forms by flattened line breaks. The pure reader now accepts optional DocumentIR, identifies one exact label and both forms within one body block, stores only that body as the verbatim quote, reads population locally and restores page scope. Production and oracle share it; plain text/no-structure input keeps legacy parsing. Ambiguous labels, split forms and overlong proof abstain. No API, schema, provider, query, budget, ranking, Fetcher or gold change.

Eighteen new backend scenarios; 37 focused tests pass. Final: 2457 passed, two warnings, 300.53 seconds, 94.92%; ruff/format and mypy 296 files pass. Frontend typecheck, lint, 195 tests and build pass; golden unchanged. Isolated migrated seed: Groningen #1 PLAUSIBLE, UBC #11 OUT_OF_BUDGET; one Alembic head c5d01b7e4f83. The initial full run was interrupted for a peer-confirmed plain-text regression; final rerun passes. Peer review also caught and closed quote clipping before final gates. Exact-head cloud results belong in PR #32.

The PDFs contain historical explanations and proposed hypotheses. Their 5–7/62 and 70–80% signals are outdated. Retained full-cohort run 36475528223 (0f5b99d) recovered 13/62 known facts with 20/21 precision. An offline 62-row audit proves 13 recovered and two exact Toronto HTTP 403 failures; 47 first failure stages remain unmeasured because the captured candidate pool is incomplete. The direct-source oracle is a separate readability probe with another denominator; not_measured does not prove schema absence. These are historical measurements, not current E2E proof. Serper's last confirmed balance (-5) blocks new live validation; merge and deployment are not claimed.
