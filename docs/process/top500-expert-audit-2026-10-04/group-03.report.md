# Group 03: generic traversal and starvation before search

**Scope:** non-blind engineering audit of all 50 assigned seed rows, baseline `144881b`, 2026-10-04. This is not verified admissions research. Every row has `live_checked=false`; ranking, tuition, test scores and other seed statistics remain unverified. No network/provider calls, production edits, gold edits or commits were made. The parent owns HANDOFF and git. The probe uses the actual importer and retrieve against an isolated SQLite in-memory database; mocked identity/discovery responses explicitly test orchestration only.

## Reproduce

From repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-03.probe.py
```

The probe imports the complete frozen seed so positions reflect real competition with other rows and the curated registry. It audits only the 50 packet rows. It writes `group-03.rows.json`, runs nine assertions per assigned row, checks reimport idempotence and runs synthetic spies through actual discovery orchestration. Socket connection methods are blocked. It does not invoke a real fetcher or provider.

## Measurements

| Measure within assigned group | Result |
|---|---:|
| Audited rows | 50/50 |
| Local assertions passed | 450/450 |
| Full source name, canonical name and every stored alias retrieve target identity | 50/50 |
| Curated registry coverage | 1/50 |
| Generic identity/discovery route | 49/50 |
| Imported domain status: seed / unknown / curated | 29 / 20 / 1 |
| Seed domain versus website conflicts | 4/50 |
| Source name differs from imported canonical name | 7/50 |
| Rows with at least one non-unique alias query | 6/50 |
| Inside default 40-candidate window, no preferences | 4/50 |
| Inside default 20-live window, no preferences | 1/50 |
| Inside 20-live window when each row's own country is preferred | 37/50 |
| Live sites checked / actual provider requests | 0 / 0 |

Whole-import context, not group metrics: 500 seed observations produce 501 institutional identities (the registry contributes an additional institution); repeating the import creates zero observations. The scheduling spy returns 40 candidates and attempts exactly 20 enrichments. These are scheduling counts, not successful page research counts. Defaults come from `backend/app/config.py:57-58`; account limits or explicit run parameters can produce different windows.

Charles University is the group's sole curated row and position 2 globally. Bologna, American University of Beirut and Beijing Institute of Technology are positions 28, 29 and 39 respectively: returned as default candidates, but not live enriched. Stanford is position 252; University of Connecticut is 396; University of Trento is 467. Their availability in catalogue search does not establish programme research coverage. With a preferred country, many move forward; Stanford still ranks 29 within a US-preferred ordering and Connecticut 46.

Four hint conflicts are preserved safely as `unknown`: HKUST (`ust.hk` versus `hkust.edu.hk`), Sheffield, University of Washington and Southampton. These are observed snapshot inconsistencies, not a finding that either site is legitimate or current. Six non-unique alias queries include `Korea University` (13 returned identities because country text participates in substring matching), `Barcelona` (5), `CAU` (3), `Columbia University` (2), `Universitas Indonesia` (3), and `University of Victoria` (2). All still retrieve the intended row; ambiguity is distinct from recall failure.

## Findings and prioritized transferable hypotheses

### H1 — Reserve a bounded exploration share for generic institutions (P1)

**Mechanism and evidence:** `backend/app/catalogue/retrieval.py:104-110` sorts preferred country first, then curated status, then normalized name. `backend/app/catalogue/discovery.py:44-49` slices before enrichment and `:65-68` enriches only the initial live window. There is no intended subject input to local ordering. In this group, 49/50 rows use the generic route but only the curated Charles row is offered default live research. Name availability is already good; programme research opportunity is the missing measurement.

**Hypothesis:** a deterministic resumable queue that reserves a fixed share for generic identities, and rotates previously attempted entries after actual evidence coverage, will improve the number of institutions receiving useful programme research at equal total cost. Keep country exclusions and explicit selections. Do not replace the ordering with QS scores or imported prices/tests: those do not establish applicant fit.

**Counterexample / cost:** curated entries have known page routes and may produce more useful evidence per fetch. A small preferred country or explicit institution selection already avoids much global starvation: own-country preference places 37/50 group rows inside the live window. Reserved exploration can reduce immediately useful results if generic sites are inaccessible.

**Held-out equal-budget experiment:** freeze a country/registry-status-stratified set outside this group and prespecify an allocation (e.g. 15 established-route + 5 rotating generic attempts versus current 20). Hold total institution attempts, wall time, HTTP/browser reads, provider queries and applicant fields fixed. Report per-route completion, confirmed programme pages, evidence precision, timeout rate, and probability-free coverage of unique institutions across repeated runs. Include late alphabetical names and explicit-ID counterexamples. Do not interpret catalogue recall as programme recall.

### H2 — Allocate a search opportunity before pre-search traversal exhausts the clock (P1)

**Mechanism and evidence:** `backend/app/adapters/discovery/live_discovery.py:99` has `SEARCH_BEFORE_NAVIGATION=False`. The actual orchestrator at `:1096-1165` runs sitemap, navigation, confirmation and catalogue walker before the search stage; the synthetic stage probe reproduces that order without fetching. Sitemaps can attempt 12 documents (`:64`, `:939`); navigation reads up to five pages (`:120`, `:1945`). The walker permits two roots, 20 leads per root and up to three descent reads (`catalog_walker.py:62-77`, `:424-471`). Count bounds therefore do not reserve wall-clock time for a later strategy.

**Retained historical evidence:** `backend/evaluation/research/expert/data/runs.2026-10-03/er15.37112534809/groningen.json:10-23` records 77 HTTP fetches, zero search calls, 115.00755570999999 seconds and `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED`. Its adjacent log reaches `/education/programme-search` at t=110s after many research/navigation URLs. Groningen is outside this group. This is one historical failure of the mechanism, not a measured 50-row failure rate, not proof a provider query would succeed, and not the separate successful direct-source extraction check.

**Hypothesis:** after a bounded initial sitemap opportunity, reserve a measured fraction of institution wall time for search, or interrupt a low-yield route when its allowance expires while preserving already found candidates. Merely switching the current early-search flag still leaves sitemap collection before search; test a real stage allowance, not only flag names.

**Counterexample / cost:** a fast catalogue can confirm a correct programme without provider cost; search may be unavailable or worse on local-language sites. `catalog_walker.py:446-452` already stops after a confirmed programme, preventing one known post-success waste pattern. Preserve that gain and evaluate multi-field coverage separately.

**Held-out equal-budget experiment:** use a frozen disjoint panel with slow sitemap, JS catalogue and fast curated-route strata. Compare existing ordering against an allowance schedule within the same total wall clock, maximum page reads, browser reads and six-query ceiling. Save first-search latency, whether the search stage was reached, confirmed programme identity, evidence precision and work salvaged at timeout. Run identical frozen-response replays first; any future authorized live run must use the same budgets. Do not increase limits to claim improvement.

### H3 — Give generic routes verified catalogue entry points with provenance (P2)

**Mechanism and evidence:** `backend/app/catalogue/discovery.py:88-96` sends generic institutions through identity discovery; `_probe_site` returns only name/country/city/homepage at `:193`. No curated programme/admissions seeds are created by that successful identity result. Explicit institution IDs are tested and retrieve exactly the selected identity; the default-window figures do not imply universal starvation under user selections. `live_discovery.py:1080-1095` can seed categories only when the entry has explicit seeds. `:1349-1369` falls back to the homepage as walker root when navigation found no catalogue. Thus 49/50 group rows must discover useful entry points from scratch even when their identity hint is present (29 seed domains).

**Hypothesis:** persist observed, classified catalogue/admissions entry points separately from institution identity and unverified seed facts, with source URL, fetch timestamp, status and expiry. Reuse the verified route on subsequent runs under the same site identity; preserve fallback when it fails. This scales beyond hand-adding 49 bespoke registry records and keeps programme assertions dependent on fetched evidence.

**Counterexample / cost:** homepage/campus/domain migrations, redirects and programme reorganization can make a remembered route harmful. Charles already has curated routes and should not lose their useful priority. A successful homepage identity check does not validate every linked subdomain or prove a catalogue is degree-specific.

**Held-out equal-budget experiment:** select generic institutions from held-out groups stratified by usable versus missing hints and language, with two equal-budget visits. Baseline spends its budget rediscovering roots; variant reuses only routes actually verified in visit 1. Compare combined two-visit cost, visits yielding confirmed pages, stale-route rejection, same-source safety failures and precision. Include a frozen moved-catalogue fixture; charge route discovery/warmup cost to the variant.

### H4 — Rank exact institutional identities above incidental alias/country matches (P2)

**Mechanism and evidence:** `backend/app/catalogue/importer.py:195-201` retains source/canonical names and every final parenthesized suffix as alias. `retrieval.py:97-99` matches tokens against name, country, city and aliases together; sorting then ignores match specificity. Therefore `Korea University` returns 13 institutions and the location suffix `Barcelona` becomes a five-match alias. This is a selection ambiguity, not evidence those universities are duplicates. Domain conflicts are deliberately discarded at `importer.py:139-144` and should stay unresolved until checked.

**Hypothesis:** when users search/select an institution, tier exact canonical/source-name matches above exact aliases and only then broad token matches. Classify suffixes as acronym, location or alternative name for weighting; do not erase source labels. Use this only to improve explicit institution selection, not to manufacture programme suitability or mark conflicting hints trusted.

**Counterexample / cost:** `Barcelona` can intentionally be a city search, and `CAU` can name several institutions. Full-name recall is already 50/50, explicit IDs are exact 50/50, and all stored aliases retrieve their target. A rule that forces a single answer could reduce valid alternatives.

**Held-out equal-budget experiment:** use new ambiguous short-name/acronym/location queries from other groups, with gold institution selection labels collected independently. Compare top-1 identity accuracy and recall@5, including broad city-search controls, at identical local query budget. Keep domain resolution and network quotas unchanged. Only after that use selected IDs in programme research; do not claim the retrieval change by itself improves admission evidence.

## Boundaries

Risk labels in the row file describe discovery opportunity and missing hints, not institution quality, admissions eligibility or factual accuracy. The 450 assertions exercise identity import/retrieval and routing decisions; they do not test page correctness. Synthetic successful site identification cannot prove any of the 20 unknown rows will identify successfully. Historical traces are inspected as engineering evidence and are not fresh live results. No institutional seed statistics were promoted to verified facts.

## All assigned rows

The accompanying JSON contains all tests, aliases, domain states, route events and observations. The following compact table makes coverage reviewable; positions use the full imported catalogue with no preferences.

| Seed ID | University | Route / domain state | Global position | Default live slot |
|---|---|---|---:|---|
| qs2027-003 | Stanford University | generic / seed | 252 | no |
| qs2027-013 | Peking University | generic / seed | 203 | no |
| qs2027-023 | The University of Melbourne | generic / unknown | 286 | no |
| qs2027-033 | The Hong Kong University of Science and Technology | generic / unknown | 279 | no |
| qs2027-043 | Columbia University | generic / seed | 62 | no |
| qs2027-053 | Korea University | generic / unknown | 148 | no |
| qs2027-063 | KFUPM | generic / unknown | 141 | no |
| qs2027-073 | Sorbonne University | generic / unknown | 248 | no |
| qs2027-083 | The University of Sheffield | generic / unknown | 291 | no |
| qs2027-093 | University of Washington | generic / unknown | 475 | no |
| qs2027-103 | Tohoku University | generic / seed | 298 | no |
| qs2027-113 | University of Southampton | generic / unknown | 454 | no |
| qs2027-123 | Alma Mater Studiorum - Università di Bologna | generic / seed | 28 | no |
| qs2027-133 | Universidade de São Paulo | generic / seed | 319 | no |
| qs2027-143 | National Tsing Hua University - NTHU | generic / unknown | 190 | no |
| qs2027-153 | University of Southern California | generic / seed | 455 | no |
| qs2027-163 | Washington University in St. Louis | generic / unknown | 492 | no |
| qs2027-173 | University of California, Santa Barbara (UCSB) | generic / seed | 385 | no |
| qs2027-183 | Emory University | generic / seed | 80 | no |
| qs2027-193 | Universitas Indonesia | generic / seed | 328 | no |
| qs2027-203 | Loughborough University | generic / seed | 164 | no |
| qs2027-213 | Hamad Bin Khalifa University (HBKU) | generic / seed | 99 | no |
| qs2027-223 | American University of Beirut (AUB) | generic / seed | 29 | no |
| qs2027-233 | Universidad de los Andes | generic / seed | 313 | no |
| qs2027-243 | Beijing Institute of Technology | generic / seed | 39 | no |
| qs2027-253 | University of Maryland, College Park | generic / seed | 425 | no |
| qs2027-263 | Universitat Pompeu Fabra (Barcelona) | generic / seed | 340 | no |
| qs2027-273 | Charles University | curated / curated | 2 | yes |
| qs2027-283 | Radboud University | generic / seed | 221 | no |
| qs2027-293 | Universidad Nacional de Colombia | generic / seed | 316 | no |
| qs2027-303 | Université Paris Cité | generic / unknown | 351 | no |
| qs2027-313 | The University of Arizona | generic / unknown | 282 | no |
| qs2027-323 | University of Delhi | generic / seed | 398 | no |
| qs2027-333 | Universität Innsbruck | generic / seed | 335 | no |
| qs2027-343 | University of Coimbra | generic / unknown | 393 | no |
| qs2027-353 | Brunel University of London | generic / unknown | 46 | no |
| qs2027-363 | City St George’s, University of London | generic / unknown | 60 | no |
| qs2027-373 | University of Victoria (UVic) | generic / seed | 472 | no |
| qs2027-383 | University of East Anglia (UEA) | generic / seed | 400 | no |
| qs2027-393 | The American University in Cairo | generic / unknown | 274 | no |
| qs2027-403 | National and Kapodistrian University of Athens | generic / unknown | 182 | no |
| qs2027-413 | Singapore Management University | generic / seed | 244 | no |
| qs2027-423 | Murdoch University | generic / seed | 178 | no |
| qs2027-433 | Chung-Ang University (CAU) | generic / unknown | 59 | no |
| qs2027-443 | University of Trento | generic / seed | 467 | no |
| qs2027-453 | Central South University | generic / seed | 54 | no |
| qs2027-463 | University of Connecticut | generic / seed | 396 | no |
| qs2027-473 | University of Bayreuth | generic / unknown | 371 | no |
| qs2027-483 | Kyungpook National University | generic / unknown | 153 | no |
| qs2027-493 | University of Electronic Science and Technology of China | generic / seed | 401 | no |
