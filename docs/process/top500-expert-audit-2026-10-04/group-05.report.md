# Group 05: multilingual identities, intent and evidence abstention

Date: 2026-10-04. Baseline supplied by parent: `144881b`. Non-blind offline engineering diagnosis; no admissions certification, live university checks, provider calls or production changes. All 50 assigned seed rows were audited against the **actual full importer output: 500 seed observations, 501 university identities including the curated registry**. The dataset is an engineering input, not a held-out benchmark.

## Reproduce

From repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-05.probe.py
```

The script imports into isolated in-memory SQLite, runs 661 actual retrieval calls and 10 clearly synthetic classifier probes, writes `group-05.rows.json`, and prints counts and synthetic results. Each of the 50 records contains seed identity, imported canonical name/aliases, domains/hints, route, queries, complete matching identities, target position, observations, risk and `live_checked: false`. Only the three assigned group files were written. No live enrichment is invoked.

## Measured coverage

| Actual local check | Result | Meaning |
|---|---:|---|
| Exact seed name / canonical name | 50/50 targets found in each | Basic identity recall works |
| Exact name unique result | 42/50 | Eight names also match other universities |
| Exact name target ranked below first | 7/50 | Exact identity has no relevance preference |
| Stored aliases | 74/74 calls find intended identity | 11 ambiguous calls across 9/50 universities |
| Mechanical accent/case/punctuation normalization | 50/50 | Includes six names containing non-ASCII characters |
| Mechanical reversed tokens | 50/50 | AND-of-substrings ignores token order |
| Original country as structured filter | 50/50 | Existing country mapping works |
| Original country appended to name in q | 34/50 | 16/50 return zero results |
| Canonical country appended to name | 50/50 | Direct control for the country-normalization mismatch |
| Name plus `computer science bachelor` | 0/50 | Synthetic programme intent is outside identity retrieval; no claim these programmes exist |
| Imported domain as q | 1/37 intended identities | 35 empty, one wrong-only result; 13/50 have no domain |
| Mechanical initials | 9/50 intended identities | 27 ambiguous queries; not verified abbreviations |
| Added nonexistent token / deliberately wrong country | 50/50 empty in each | Negative controls remain conservative |

Routes: **3/50 curated** (Technical University of Munich, KAIST, Middle East Technical University); **47/50 generic site identification**. Domain status: 3 curated, 34 seed hints, 13 unknown. Missing hints are coverage limitations, not confirmed official-domain errors. No programme/language facts were inferred from country or institution name.

## Ranked hypotheses and promotion conditions

### 1. Apply country synonym normalization consistently to free text, with explicit scope

**Observed mismatch: 16/50.** `Harvard University United States of America`, `KAIST Republic of Korea`, `Bilkent University Türkiye`, and `Shanghai University China (Mainland)` each lose their target and return zero results. The equivalent name plus structured country filter works. Breakdown: 6 United States, 4 South Korea, 3 Turkey, 3 China records. Every affected ID is recoverable from `seed_country_in_query` tests in rows.json.

Evidence: `backend/app/catalogue/importer.py:22-42` maps synonyms; `backend/app/catalogue/retrieval.py:73-75` applies that mapping to country constraints, while lines 89 and 97-99 only normalize punctuation/diacritics in q and search imported canonical country strings. `frontend/src/components/UniversityCatalogue.tsx:50` explicitly invites a country in free text.

**Hypothesis:** recognize complete known country phrases or index their synonyms as country metadata, keeping identity tokens separate. Student consequence: copy-pasted seed-country wording should find the same candidate as the dropdown. Do not translate arbitrary university names or treat a substring such as `us` as a country anywhere inside a word.

**Controls:** all 50 canonical-country queries and all 50 structured filters already work; 50 wrong-country controls exclude the target. A future held-out set must include institution names containing country-like terms, country exclusions and ambiguous abbreviations.

**Equal-budget experiment:** freeze baseline and challenger; 100 independently sourced user identity/country queries outside these 500 audit inputs, identical full catalogue and zero network calls for both. Measure intended-identity recall and wrong-country additions; no improvement promotion if exclusions regress.

### 2. Rank exact institution identity ahead of city/token coincidences

**Observed ambiguity: 8/50; target below first: 7/50.** `Durham University` returns Duke University first because Duke's city is Durham. `University of Gothenburg` returns Chalmers first. `Shanghai University` returns five institutions, with Shanghai University fourth. `University of Science and Technology of China` is fifth of five. `Northwestern University` returns Northwestern Polytechnical University first. This is a search relevance defect, not an incorrect institution record.

Evidence: `backend/app/catalogue/retrieval.py:97-99` allows every query token to occur anywhere across name, country, city and aliases, then lines 104-110 sort by country preference, curated route and alphabetic name; no exact identity score exists.

**Hypothesis:** preserve broad candidate recall but tier full normalized canonical-name and authoritative alias matches above weaker token/city matches. Student consequence: a named university becomes selectable without misleading first results. Exact identity ranking must not assert programme fit.

**Controls:** all 50 names already have recall; none may disappear. A city-only query should continue returning multiple city institutions. UPM is genuinely ambiguous in imported identities, so exact alias alone should not silently collapse to one university.

**Equal-budget experiment:** 100 held-out identity and city queries, both versions retrieving the same full catalogue with zero network calls and identical top-20 output budgets. Measure intended rank, unique-identity precision and recall. Include names absent from the tuning set and cross-country same-token institutions.

### 3. Treat abbreviations, parenthetical qualifiers and domain intent as different identity evidence

**Measured exposure:** 9/50 have ambiguous stored-alias queries; 36/37 available domain queries miss the intended university (36/50 of all assigned rows); mechanical initials miss 41/50, but those are synthetic and do not establish missing official aliases.

Concrete cases: stored `UPM` yields KFUPM, Universidad Politécnica de Madrid and Universiti Putra Malaysia. `Jinan University (China)` creates alias `China`, yielding 38 identities; `System` is likewise a parenthetical qualifier for Minnesota, not an independently verified institution name. Domain query `ub.es` returns only Universidad de Buenos Aires, not Universitat de Barcelona. `mcmaster.ca` happens to find McMaster through name/country substring matches; the domain column is not actually searched.

Evidence: `backend/app/catalogue/importer.py:195-200` stores every parenthesized suffix as an alias; `backend/app/catalogue/retrieval.py:98` concatenates aliases without word-boundary matching and omits domain. `backend/app/adapters/discovery/registry_identities.py:11-16` explicitly distinguishes recorded aliases from generated aliases in the separate discovery identity reader.

**Hypothesis:** tag alias provenance and qualifier type; use whole-token matching for short aliases and a separate exact host query branch for domain-shaped input. Seed domains remain unverified hints: matching a hostname must not certify it or a programme. Do not automatically add the 50 mechanical initialisms as official aliases.

**Controls:** preserve every current 74/74 stored-alias target hit; retain multi-institution UPM ambiguity; reject short substring collisions, country-only pseudoaliases and mismatched domain proof. Imported domain routing is a proposed feature, not a current UI contract violation.

**Equal-budget experiment:** held-out 100 queries split between recorded acronyms, unverified initials, geographic qualifiers and domain-shaped input; same catalogue and zero provider calls. Judge intended identity, ambiguity presentation and no false provenance upgrades. Authority for real aliases must come from separately captured official evidence, not this diagnosis.

### 4. Route programme intent without treating an empty catalogue query as programme absence

**Observed design boundary: 50/50** synthetic name-plus-programme queries return no universities. Actual catalogue search considers identity fields only. This is not a proved programme-search implementation bug: the catalogue UI says “University, city or country” and its note says programme research follows selection (`frontend/src/components/UniversityCatalogue.tsx:50,62`). The separate shortlist screen searches already-researched programme fields (`frontend/src/screens/ShortlistScreen.tsx:66,383`). The two flows must not be conflated.

Evidence: `backend/app/api/routes_universities.py:35` passes q to identity retrieval; `backend/app/catalogue/discovery.py:44-49` discovers using preferred/excluded countries and selected IDs, not catalogue free text. In enrichment, the programme comes from applicant profile and source checks.

**Hypothesis:** when programme intent is detected, retain the identifiable university and guide the subject/degree into profile research while displaying its unverified state. Never drop `master` or `bachelor` from a source-confirmation predicate merely to recover a result.

**Controls:** valid institution-name terms such as “Science and Technology” must not be removed as programme intent. All exact identity and wrong-country controls must continue passing. Empty result is not evidence of ineligibility or no programme.

**Equal-budget experiment:** 100 held-out human-authored queries across identity-only, subject-only, combined and ambiguous institution names. Both systems receive identical queries; compare intent routing offline first. Only then compare identical selected institutions under the same 60-fetch/6-search-call/300-second caps per case, recording confirmed correct programme recall, wrong-degree admissions and cost separately.

### 5. Expand explicit multilingual evidence only where it preserves abstention

**Confirmed university-level classifier errors: 0/50 established here.** The only new page inputs are 10 synthetic fixtures, not official pages. All 50 are conceptually subject to classification; actual per-university multilingual page prevalence is unknown. Generic site-identification exposure is 47/50 and missing-domain exposure 13/50; neither proves a current failure.

Synthetic evidence: a `BSc Computer Science` page with English instruction confirms a bachelor subject with explicit English evidence. The same page with `Spanish`, `Turkish`, or synthetic German label `Unterrichtssprache: Deutsch` keeps a valid bachelor programme but leaves language null. No language declaration also leaves language null. The synthetic mixed-language title `Grado en Computer Science` is unknown; it is not a claimed real title or an official translation. Wrong-level MSc, wrong-subject History, degree-absent Computer Science and catalogue fixtures are rejected for bachelor Computer Science. Thus the demonstrated gap is explicit-language vocabulary/label coverage, not a need to weaken subject/degree gates.

Evidence: `backend/app/adapters/page_classifier.py:100-104` degree vocabulary and `:221-231` language vocabulary currently cover six language values with English labels; `:561-610` retains evidence and creates programme classifications. `backend/app/adapters/discovery/live_discovery.py:725-733` enforces page type, subject and a stated degree mismatch; `:1770-1772` additionally requires the requested degree in provider confirmation. `backend/app/catalogue/discovery.py:153-167` checks homepage name aliases and an English institutional-word vocabulary for acronym proof; that is another multilingual hypothesis, untested on real homepages here.

**Hypothesis:** add bounded, evidence-backed labels/degree lexicons and preserve explicit source excerpts. Keep language unknown when only the UI/page language is known; official homepage identity and course existence cannot establish teaching language. Do not use institution country to infer language or promote all unknown pages.

**Historical context, not current proof:** `backend/evaluation/research/expert/data/runs.2026-10-02/paired.kaist-on.capture.json`, captured `20261002T154119Z`, pipeline `a64492ff72fdb4f57713aeec6202978b9b610621`, reports zero programme URLs, 37 HTTP fetches and six search calls. Its Korean admissions URL produced a five-character “KAIST” page classified unknown: this does **not** prove Korean vocabulary was the failure. `paired.metu-on.capture.json`, captured `20261002T155208Z`, pipeline `bf9233d21d4d7b11c4a66ed6a90baabf9eda920a`, reports zero programme URLs and `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED` after 47 HTTP fetches, three PDF fetches and six search calls. That timeout must not be counted as a classifier failure. Both universities are assigned group rows; current live status remains unchecked.

**Equal-budget experiment:** freeze a separately gathered, bilingual-reviewed held-out source corpus outside the audit inputs, with explicit language labels, degree synonyms, missing-language pages, wrong-level/subject and catalogue controls. Run baseline and challenger on exactly the same bytes, zero network/LLM budget. Then equal 60-fetch/6-search/300-second discovery caps if live research is authorized. Require additional correct explicit-language evidence with no wrong-subject/degree or inferred-language increases; record abstentions and retrieval failures separately.

## Limits

The hypotheses are candidate experiments, not implemented repairs. The 500-university input is not blind validation. No real-world alias, translation, programme availability, teaching language, admissions threshold or official-domain status was newly certified. Memory was consulted only to retain the prior distinction between narrow extraction checks and whole-product readiness; all counts above were freshly measured locally. Parent owns integration, HANDOFF and commits.
