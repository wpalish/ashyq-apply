# Expert 04 — observations, verified facts, scope, and research priorities

Date: 2026-10-04. Baseline supplied by coordinator: `144881b`. Group: 50 assigned universities; full actual search space: **500 seed records + curated registry = 501 university identities**. Seed SHA-256: `5ab134e331add59884ff5bca548dc17d5a428a7a5d69fdec09c7863babe08a58`.

This is non-blind engineering diagnosis, not official admissions research or held-out validation. No network/provider calls, persistent database, source changes, applicant data, secrets, or production changes. Every individual result has `live_checked=false`. Group04 rows are not evidence that any institution's current admission/fee facts are correct or wrong.

## Reproduce and inspect

From repository root:

```bash
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-04.probe.py
```

Script imports the actual complete seed and registry into in-memory SQLite, checks all 50 packet rows against that database, writes `group-04.rows.json`, and prints the machine-readable summary and synthetic controls. Source fixture equality and SHA-256 are asserted. It uses a fetcher that raises if called; discovery controls set live_limit=0. Synthetic claims use `example.edu` strings and never fetch them.

## Counts and interpretation

| Measurement | Observed denominator and result |
|---|---:|
| Per-university coverage | 50/50 |
| Actual retrieval calls recorded | 533 |
| Exact, canonical, upper-case, accent-folded, reversed-token recovery | 50/50 for each family |
| Supplied alias recovery | 58/58 alias queries across 50 universities |
| Exact-name queries with multiple results | 6/50 |
| Exact-name target not first | 2/50: Western University rank 6; York University rank 5 |
| Name plus `admissions`; name plus `bachelor` | 0/50 targets recovered, each family |
| Name plus original seed country | 41/50; structured country control 50/50 |
| Domain as query | 2/25 retained-domain rows recovered |
| Curated route / generic route | 0/50 / 50/50 |
| Retained domain status | seed 25/50; unknown 25/50 |
| No domain/site hints at all | 19/50 |
| Unknown domain but retained website hint | 6/50 |
| Admission snapshots / tuition snapshots / either | 15/50 / 19/50 / 28/50 |
| SAT and GRE or GMAT co-listed without degree scope | 5/50 |
| Seed observations remain unverified with no observed_at | 50/50 |
| Zero-live candidates contain no programme/admissions/costs facts | 50/50 |
| Default unfiltered retrieval first 20 / first 50 membership | 0/50 / 5/50 |

Unknown domain is not equivalent to no research route. Oxford, Illinois Urbana-Champaign, Queen Mary, Keio, Ruhr Bochum, and Montpellier retain website hints even though their imported domain status is unknown. No attempt was made to resolve the correctness of their conflicting or incomplete seed hints.

**Seed isolation is working in the tested paths.** Mutation control changes fee and exam snapshots for all 500 seed rows to synthetic extremes (USD 999,999; IELTS 9; SAT 1600). Full retrieval ordering stays identical, and all 50 zero-live Candidate payloads stay identical. This is affirmative evidence against seed contamination in local retrieval and unenriched Candidate construction. It does not prove all downstream code is invariant during live enrichment.

The five mixed-test rows are Oxford, Chicago, Boston, Sussex and York. Their snapshots combine SAT with GRE/GMAT without programme, degree or intake. That is a data-scope limitation, **not proof that any listed value is false**. A fee snapshot similarly lacks programme, degree, intake, fee population, currency provenance/FX time and net funding basis. Missing seed fields are not observed admission failures.

## Reproduced defects, limitations and controls

### A. Scope context is reduced before eligibility checks (synthetic assessment defect; live reachability unproven)

`backend/app/domain/eligibility.py:63-79` builds RequestedScope from claim intake only. Programme, degree, nationality, residency and qualification remain empty, despite `ClaimScope` supporting those dimensions (`backend/app/domain/claim_scope.py:40-55,121-157`). `_english_checks` invokes that request (`eligibility.py:485-488,527-535`), and the runner calls `evaluate_program(self.profile, claims, ...)` (`backend/app/pipeline/runner.py:991`).

The synthetic bachelor CS applicant has IELTS 6. A VERIFIED_CURRENT IELTS minimum of 7, whose source scope explicitly says MBA/master/fall 2027, produces `confirmed=true` and hard_filter_failures `["IELTS overall"]` in actual `evaluate_program`. The same source evaluated against explicit Computer Science/bachelor/fall 2027 RequestedScope correctly returns NO. A wrong-intake 2026 source produces no hard filter. This isolates discarded request dimensions rather than a broken `covers()` comparator.

Actual caller trace: the runner creates each ProgramResult from the selected CandidateProgram (`runner.py:537-555`), calls requirements verification with that programme (`574`), and later rebuilds only its persisted claims before assessment (`988-991`). The current adapter rejects a classified wrong-degree page when it is the programme URL (`backend/app/adapters/requirements/web_requirements.py:238-258`); this guard must remain. It also reads source scope from page text separately from request metadata and supplies verbatim/domain/page-type verification context (`260-286`). The synthetic test starts at the actual assessment entry point with a manually constructed VERIFIED_CURRENT claim, so it does not establish that those adapter guards currently admit the example. If explicit request scope is introduced, derive the programme from the selected ProgramResult/CandidateProgram and profile degree; do not equate a list of broad `intended_fields` with one canonical programme or copy the source scope into the request. Preserve identity refusal, source-domain, excerpt, page-classification, wrong-intake and degree guards.

A second synthetic control shows `scope=None` with VERIFIED_CURRENT status hard-filters; `ClaimScope()` yields no hard filter. `_confirmed` deliberately retains legacy behavior at `eligibility.py:149-155`; its earlier `_scope_verdict` documentation at lines85-88 suggests stronger protection than that actual behavior. Empty-scope result still has eligibility GAP, so no hard filter must not be described as no negative assessment.

**Affected count:** 1/1 injected wrong-programme/degree scenario and 1/1 legacy-none scenario reproduce; 0/50 real university misclassifications demonstrated. All 50 eventually depend on the shared eligibility path. Upstream claim verification and programme isolation may prevent these claims reaching that path in real runs; this audit does not bypass that distinction or assert end-to-end incidence.

### B. Campus is not a typed scope dimension (observed representation limitation)

`ClaimScope` and RequestedScope omit campus (`claim_scope.py:40-55,68-112`); `from_mapping` ignores unknown keys (`184-193`). Synthetic mappings with identical programme/intake but campus A versus campus B become equal. ProgrammeIdentity also has university/degree/field/active/intake, but no campus (`backend/app/domain/programme_identity.py:66-75`). Campus may be encoded in programme prose, which is less reliable than a separate dimension; no actual cross-campus leak was measured.

A retained trace illustrates why campus preservation deserves testing: `backend/evaluation/research/expert/data/runs.2026-09-27/toronto.trace.json:50-80`, captured 2026-09-27, baseline ff23db09a2d506af68df2172e6ae7bcb5a93166a, records programme proposals explicitly labelled UTSC/Scarborough. It is an older retained expert proposal outside group04, not fresh verification, not an accepted gold answer, and not evidence that current Toronto facts match it.

**Affected count:** campus is absent from typed schema for all 50 rows' potential future claims; 1/1 synthetic collision; 0/50 confirmed real campus errors.

### C. Identity search interprets all words as mandatory identity fragments (observed query behavior)

`backend/app/catalogue/retrieval.py:88-100` requires each query token to be a substring of concatenated name/country/city/aliases; domains and search intent are excluded. Sorting at lines104-110 prefers curated routes then alphabetical names, not exact-name agreement. API `q` goes directly to retrieve at `backend/app/api/routes_universities.py:35`.

Western and York exact-name targets rank sixth/fifth behind broader substring/city matches. Boston University also returns Northeastern because Boston matches its city; that is observed over-broad retrieval, not proven bad user selection. All50 fail appended admissions/bachelor intent; 9/50 fail raw country appended while structured country works. Domain query misses23/25. Canonical, accent and reversed-token controls all recover all50, so deleting normalization would be a regression.

### D. Research budget follows route/alphabetical ordering (observed scheduling limitation)

`retrieval.py:102-110` orders by preferred country, registry presence and alphabetical name. `backend/app/catalogue/discovery.py:43-65` slices candidates, then enriches only index < live_limit; `backend/app/pipeline/runner.py:497-500` similarly selects its first verify_limit. Under the no-preferences control, group04 has0/50 in the first20 and5/50 in the first50 of501. This describes that ordering only: it is not an estimated production exclusion rate, actual configured budget, or evidence of profile mismatch.

All50 need scoped programme research, and19/50 have no site hints. Paying for identity discovery, programme discovery and fee/requirements verification blindly in name order can spend the budget before high-impact questions are answered. Existing unverified seed numbers must not be used as cheap hard exclusion rules to solve this problem.

## Four ranked transferable hypotheses and equal-budget falsification

These are proposed algorithm changes, not promoted fixes. Freeze implementation and thresholds before testing. None of these500 universities is a held-out set. Reserve 60 previously unaudited institutions/campus-programme combinations, stratified across languages, regions and degree levels, with separate adjudicators. Pair baseline and intervention on identical frozen official page captures, identical cache state, at most60 Fetcher calls and120 seconds per case, same provider-result fixture and page/extraction caps. Report refusals, abstentions, claims and elapsed/fetch budgets, not just recovered fact count. A later authorized live trial must use equally measured budgets and independent source adjudication.

1. **Pass explicit requested programme, degree, intake and applicant qualification/population to eligibility; require positive scoped evidence for hard filters including legacy facts.** Motivation: A; potential shared-path reach50/50, observed real incidence0/50. Primary metric: wrong-scope hard exclusions per evaluated candidate; secondary: correctly decisive exclusions and unknown rate. Negative controls: same programme+degree+intake must remain decisive, explicit wrong-intake must remain rejected, genuinely unknown scope must remain provisional. Falsify improvement if false exclusions fail to decrease or valid decision coverage collapses beyond preregistered tolerance. Do not force population inference where no institution-specific status is known.

2. **Preserve campus/programme identifiers as typed context through discovery, evidence and deduplication.** Motivation: B; synthetic1/1 campus collision, confirmed affected universities0/50. Use paired same-title programmes on different campuses plus single-campus controls. Score cross-campus attribution error and false splits. Falsify if structured campus does not reduce mistaken transfers, or guessed campus assignment creates more false exclusions. No blanket claim that every group04 university has multiple campuses.

3. **Schedule reads by unresolved decision-critical questions while preserving seed/claim separation.** Motivation: D and28/50 rows with seductive unscoped numeric hints; seed contamination itself was0/50 in measured paths. First establish institution→programme→degree→campus→intake, then qualification equivalence/required subjects, applicable fee population and mandatory costs, then funding eligibility and relevant deadlines. The ordering should adapt to applicant constraints and verified evidence, not QS rank or seed price. Compare route/alphabetical ordering against balanced exploration plus expected decision impact; measure correctly answered critical questions per fetch, coverage across countries and missing-hint strata, and inappropriate candidate exclusion. Retain the500-row adversarial seed mutation as a zero-budget negative control. Falsify if equal-budget decision completeness does not improve or hint-rich schools capture more exposure without better evidence.

4. **Parse identity, country and research intent separately and rank exact identity agreement first.** Motivation: C;2/50 wrong first result,9/50 raw-country misses,50/50 appended-intent misses. Domain input should select an institution candidate, not certify ownership. Pair name-only, alias, geographic and intent-bearing questions; hard negative controls include York/University of York and Western/Northwestern and ambiguous acronyms. Measure target MRR/top1, recall and false identity merges. Falsify if improved recall depends on merging distinct schools or programme adjectives are silently dropped when they define the requested programme. Preserve structured country controls and successful normalization.

## Individual coverage

The JSON contains every actual query/result, snapshot status, hint route, zero-live Candidate, next research priorities and risk. The compact table below is an index; E=exact target rank, A=admission hint count, T=fee hint present, H=retained site hints. Every row uses the generic route and remains unverified.

| Seed | University | E | A | T | H |
|---|---|---:|---:|---:|---:|
| qs2027-004 | University of Oxford | 1 | 4 | 1 | 1 |
| qs2027-014 | Tsinghua University | 1 | 0 | 1 | 2 |
| qs2027-024 | University of Chicago | 1 | 5 | 1 | 2 |
| qs2027-034 | Université PSL | 1 | 0 | 0 | 0 |
| qs2027-044 | Institut Polytechnique de Paris | 1 | 2 | 0 | 0 |
| qs2027-054 | National Taiwan University (NTU) | 1 | 3 | 1 | 0 |
| qs2027-064 | Kyoto University | 1 | 0 | 1 | 2 |
| qs2027-074 | University of Illinois Urbana-Champaign | 1 | 0 | 1 | 1 |
| qs2027-084 | Universidad de Buenos Aires (UBA) | 1 | 0 | 0 | 2 |
| qs2027-094 | Boston University | 1 | 5 | 0 | 2 |
| qs2027-104 | Queen Mary University of London | 1 | 0 | 1 | 1 |
| qs2027-114 | University of Waterloo | 1 | 0 | 1 | 2 |
| qs2027-124 | University of Helsinki | 1 | 0 | 0 | 2 |
| qs2027-134 | Indian Institute of Technology Bombay (IITB) | 1 | 0 | 0 | 2 |
| qs2027-144 | Western University | 6 | 2 | 1 | 0 |
| qs2027-154 | Wageningen University & Research | 1 | 0 | 0 | 0 |
| qs2027-164 | Lancaster University | 1 | 0 | 1 | 0 |
| qs2027-174 | Chalmers University of Technology | 1 | 4 | 0 | 2 |
| qs2027-184 | University of Cape Town | 1 | 0 | 1 | 2 |
| qs2027-194 | University of Bern | 1 | 0 | 1 | 0 |
| qs2027-204 | Università di Padova | 1 | 6 | 0 | 0 |
| qs2027-214 | Keio University | 1 | 0 | 0 | 1 |
| qs2027-224 | University of Twente | 1 | 0 | 1 | 2 |
| qs2027-234 | University of Lausanne | 1 | 0 | 0 | 0 |
| qs2027-244 | The University of Newcastle, Australia (UON) | 1 | 3 | 0 | 0 |
| qs2027-254 | Maastricht University | 1 | 2 | 1 | 2 |
| qs2027-264 | Norwegian University of Science And Technology | 1 | 0 | 0 | 2 |
| qs2027-274 | University of Sussex | 1 | 8 | 1 | 2 |
| qs2027-284 | University of Bergen | 1 | 0 | 0 | 2 |
| qs2027-294 | University of Waikato | 1 | 0 | 1 | 2 |
| qs2027-304 | Xiamen University | 1 | 0 | 0 | 2 |
| qs2027-314 | Rutgers University–New Brunswick | 1 | 4 | 0 | 0 |
| qs2027-324 | York University | 5 | 7 | 0 | 2 |
| qs2027-334 | Technion - Israel Institute of Technology | 1 | 0 | 0 | 2 |
| qs2027-344 | University of Rome "Tor Vergata" | 1 | 0 | 0 | 0 |
| qs2027-354 | Birkbeck, University of London | 1 | 3 | 0 | 0 |
| qs2027-364 | Cairo University | 1 | 0 | 1 | 2 |
| qs2027-374 | Western Sydney University | 1 | 3 | 0 | 2 |
| qs2027-384 | National University of Sciences & Technology (NUST) Islamabad | 1 | 0 | 0 | 0 |
| qs2027-394 | East China Normal University | 1 | 0 | 0 | 2 |
| qs2027-404 | Ruhr-Universität Bochum | 1 | 0 | 0 | 1 |
| qs2027-414 | University of Saskatchewan | 1 | 0 | 1 | 2 |
| qs2027-424 | HSE University | 1 | 0 | 0 | 0 |
| qs2027-434 | Czech Technical University in Prague | 1 | 0 | 0 | 0 |
| qs2027-444 | Aix-Marseille University | 1 | 0 | 1 | 0 |
| qs2027-454 | Shoolini University of Biotechnology and Management Sciences | 1 | 0 | 0 | 0 |
| qs2027-464 | Dalian University of Technology | 1 | 0 | 0 | 2 |
| qs2027-474 | Université de Montpellier | 1 | 0 | 0 | 1 |
| qs2027-484 | Amirkabir University of Technology | 1 | 0 | 0 | 2 |
| qs2027-494 | National Taipei University of Technology | 1 | 0 | 0 | 0 |

Only the three group04 artifacts were written. No production fix is claimed. No offline success is counted as official-source verification.
