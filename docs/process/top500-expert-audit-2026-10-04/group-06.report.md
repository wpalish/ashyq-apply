# Expert 06 — candidate ordering, geography, allocation, identities

Audit date: 2026-10-04. Requested source baseline: `144881b`. This is non-blind offline engineering diagnosis, not official-source research, admissions certification, or held-out validation. All 50 assigned records have `live_checked=false`. No network, secrets, production data, source changes, or ranking-formula changes were used.

## Reproduce

From the repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-06.probe.py
```

This writes `group-06.rows.json` and prints its summary. Actual catalogue importer and retrieval run in fresh in-memory SQLite databases with the full 500-record seed and curated registry: 501 institutions, 19 curated routes, 500 seed observations. The second import returns zero new observations. Discovery budget and route tests invoke actual `CatalogueDiscoveryAdapter.discover`/`_enrich` with external seams replaced by explicitly synthetic no-I/O functions. These are allocation/branch tests, not successful website research. A `SimpleNamespace` profile is used only where the actual loop accesses preferences; `Preferences` itself is validated.

## Results and controls

- Exact seed name recall: **50/50**; canonical, normalized/accent-folded, and reversed-word variants: **50/50 each**. Stored alias retrieval: **60/60 queries**, including canonical-name aliases.
- Exact seed-name target is first: **46/50**. Four queries return two institutions and put the other institution first.
- Country filters accept canonical and seed country spelling for **50/50**. Literal canonical country preference/exclusion matches final country scoring for **50/50**.
- Synthetic region preference/exclusion disagrees with final country scoring for **50/50**: retrieval recognizes membership, while `u_country` returns 0.35 for the preferred region and does not raise a knockout for an excluded region. This does **not** prove excluded candidates escape normal catalogue filtering; they are removed there. It proves a semantic inconsistency for reranking and shared callers.
- Raw seed country spelling disagrees with canonical final country scoring for **15/50**. This is a synthetic input scenario, not an assertion that the UI sends these spellings.
- Routes: **3/50 curated**, **47/50 generic identity**. Domain absent in **14/50**. Missing hints are research limitations, not proof of a wrong university or unavailable official website. Actual synthetic routing selected the correct branch for every row; failed generic identification retained the candidate.
- Default synthetic allocation (`limit=40`, `live_limit=20`, no country preferences) includes **3/50** assigned rows and researches those same **3/50**. The full 501 population allocates **19/20** slots to curated routes, with 16 countries represented. Two identical runs allocate identically. A synthetic UK preference allocates **20/20** slots to the UK, showing preference does take precedence over curated status.
- Selected-single-ID/no-enrichment tests return the intended ID and no seed-derived programme/ranking entries for **50/50**. Reversing an explicit 50-ID selection gives the same candidate order: selection is set membership, not a user-specified ordering contract.
- Reversing all 500 seed records and replacing unverified ranks/tuition/admission snapshots leaves all **501** IDs and the entire retrieval order unchanged. This is a useful negative control: seed prestige and estimated affordability are not silently used as student fit here.

## Ranked transferable hypotheses

### 1. Share canonical geographic semantics across selection and final country scoring

**Observed inconsistency; affected 50/50 under region scenarios, 15/50 under raw seed country spelling.** `backend/app/catalogue/retrieval.py:73-76` resolves regions and country aliases; `backend/app/domain/ranking_v2.py:167-177` only lowercases and compares literals. The final scorer passes preferences through directly at `ranking_v2.py:536`. Thus a student choosing Europe gets European candidates prioritized during discovery, but the country utility labels them outside the preferred list. Example: Cambridge + Europe retrieves in-region but scores 0.35; Cambridge + United Kingdom scores 1.0. An excluded region removes candidates before discovery, but the scoring function by itself does not enforce that exclusion.

Related validation issue: `backend/app/schemas/profile.py:273-279` rejects identical preferred/excluded strings but accepts preferred UK + excluded United Kingdom. Actual retrieval gives exclusion precedence. That precedence is safe but the accepted contradictory profile is confusing; overlapping region and country preferences need explicit semantics, not indiscriminate rejection.

**Proposal:** reuse a pure geography canonicalizer for applicable callers, preserving all approved utility values, geometric aggregation, weights, and knockout rules. Test country aliases separately from intentional region-minus-country combinations. **Countercontrol:** all 50 canonical literal country inputs already behave consistently. **Promotion experiment:** fresh unseen profiles and country/region aliases, fixed saved programme results, no added requests; compare disagreement count and exact literal-score preservation. Require zero semantic mismatches and no change to unrelated axes.

### 2. Allocate bounded discovery using measured exploration and expose unattempted status

**Observed allocation limitation, not proof of lower fit: 47/50 receive no default enrichment; 19/20 full-population slots are curated.** Retrieval sorts by preference, curated route, alphabetical name, ID (`retrieval.py:104-111`); discovery truncates before enrichment and uses the first live-limit rows (`backend/app/catalogue/discovery.py:43-68`). Runner wires verification limit to enrichment at `backend/app/pipeline/runner.py:178-188`; server defaults are 40/20 (`backend/app/config.py:57-58`). A student can therefore repeatedly see the same research coverage, while later alphabetic or generic routes remain unknown. This is different from incorrect ranking: the final model deliberately separates unknown evidence and fit (`ranking_v2.py:284-295`). Route convenience is an intentional useful prior, not a demonstrated student-fit signal.

The 20 candidates outside the synthetic enrichment budget have empty limitation/error traces. Add explicit `not_attempted_budget` provenance so consumers distinguish no research from attempted but unsuccessful research. Group exposure denominators differ: 47 assigned rows are outside the initial 40; the blank-trace measurement is 20/40 in the full-population default run.

**Proposal:** evaluate a constrained exploration reserve among noncurated candidates, stratified by preferred countries and route readiness, with deterministic reproducibility. Never promote seed rank or unverified prices into fit. **Countercontrols:** 16 countries already appear in baseline 20; this is not evidence that baseline has no geographic diversity. UK preference gets 20/20 UK candidates; explicit single-ID selection works 50/50. **Promotion experiment:** equal 40 candidates, 20 enrichment attempts, same fetch/search/token/time caps, held-out institutions/profiles and source snapshots; compare confirmed relevant programmes per request, country/route coverage, repeated-run coverage and clarification burden. More diversity alone is not a success criterion.

### 3. Put exact identity matches ahead of incidental token and city matches

**Observed relevance weakness: 4/50 full exact seed queries return another institution first.** Search uses all tokens as substrings over joined name/country/city/aliases, then sorts alphabetically without query relevance (`retrieval.py:97-110`). Examples:

| Exact query | First returned other institution | Target position |
| --- | --- | --- |
| Wuhan University | Huazhong University of Science and Technology | 2 |
| Universidad de Chile | Pontificia Universidad Católica de Chile | 2 |
| Tianjin University | Nankai University | 2 |
| University of Kent | Tashkent Institute of Irrigation and Agricultural Mechanization Engineers - National Research University | 2 |

The Kent case exposes substring matching inside Tashkent; Wuhan/Tianjin can match another university's city. This affects catalogue navigation and which row a student chooses. It is not a claim that these institutions are academically unrelated, and all targets remain present.

**Proposal:** exact normalized full name/alias tier, then whole-token name matches, then broader city/country matches; retain ID tie-breaking and typo recall only after exact identity preference. **Countercontrols:** 46/50 exact queries already rank target first; 50/50 reordered/normalized variants and 60/60 aliases are recalled. **Promotion experiment:** zero-network paired replay on new, held-out disambiguation queries and typographical/alias controls, same 501-row search cost ceiling; require exact target improvement without reducing variant recall. This audited 500 is not held out.

### 4. Keep identity continuity explicit if future seed names change

**Hypothesis, not observed production defect.** Current stable IDs derive from normalized canonical name and country (`backend/app/catalogue/importer.py:45-55`). All 501 IDs survived the seed permutation/value mutation and idempotent import. A synthetic appended name change changes the hash, as designed. Name-only identification could split history if a future real rename arrives without a migration alias; no such real rename is established by this audit. Existing explicit Nanyang alias handling is a counterexample to universal fragility.

**Proposal:** document identity migration rules and verify explicit continuity before accepting future seed name changes; do not merge on a shared domain alone. **Affected count:** current stable-ID failure **0/50**; synthetic rename sensitivity demonstrated on **1/50** (Cambridge), not 50 real renames. **Promotion experiment:** fixed importer budget, frozen old/new snapshots with adjudicated real name/country changes and distinct same-name controls; test 100% known continuity without any false merge, preserving observation history and selected IDs. No ranking formula changes are implicated.

## Historical context and limits

Inspected the retained `analysis/scripts/01_discovery_sensitivity.py` and `ai-team/outputs/c2-t29-a1/qa-test-live-discovery-baseline.log` as prior engineering context only. The first operates on fixture discovery and older scoring; the second is an undated retained walker-test baseline. Neither is used as current catalogue evidence or as an official source capture. No historical webpage facts were reused. Current results come only from the reproducible probe above. There is no end-to-end live admission, cost, scholarship, programme relevance, or final shortlist quality claim.

All 500 audit inputs are training/diagnosis exposure. Any proposed change must receive a separately frozen held-out evaluation, equal provider/fetch/token/time budgets, blind adjudication of official evidence, and unchanged approved ranking invariants before promotion.

## Per-university coverage

The machine-readable file includes all query strings, positions, collisions, country and region controls, route/domain hints, actual synthetic branch counts, allocation position, observations and risk for every assigned row. The following is a compact index; rank here means retrieval position, not fit or university standing.

| Seed ID | University | Exact position/count | Route | Domain hint | Default position | Enriched |
| --- | --- | --- | --- | --- | --- | --- |
| qs2027-006 | University of Cambridge | 1/1 | generic_identity | cam.ac.uk | 387 | False |
| qs2027-016 | Cornell University | 1/1 | generic_identity | cornell.edu | 65 | False |
| qs2027-026 | Fudan University | 1/1 | generic_identity | fudan.edu.cn | 89 | False |
| qs2027-036 | Shanghai Jiao Tong University | 1/1 | generic_identity | sjtu.edu.cn | 237 | False |
| qs2027-046 | University of British Columbia | 1/1 | curated | ubc.ca | 13 | True |
| qs2027-056 | Universiti Malaya (UM) | 1/1 | generic_identity | um.edu.my | 356 | False |
| qs2027-066 | Brown University | 1/1 | generic_identity | brown.edu | 45 | False |
| qs2027-076 | Université Paris-Saclay | 1/1 | generic_identity | universite-paris-saclay.fr | 352 | False |
| qs2027-086 | Universität Heidelberg | 1/1 | generic_identity | unknown | 334 | False |
| qs2027-096 | University of Alberta | 1/1 | generic_identity | ualberta.ca | 365 | False |
| qs2027-106 | Technical University of Denmark | 1/1 | generic_identity | dtu.dk | 266 | False |
| qs2027-116 | Lomonosov Moscow State University | 1/1 | generic_identity | msu.ru | 163 | False |
| qs2027-126 | Aalto University | 1/1 | curated | aalto.fi | 1 | True |
| qs2027-136 | University of Exeter | 1/1 | generic_identity | ex.ac.uk | 402 | False |
| qs2027-146 | Tongji University | 1/1 | generic_identity | tongji.edu.cn | 299 | False |
| qs2027-156 | Nagoya University | 1/1 | generic_identity | nagoya-u.ac.jp | 179 | False |
| qs2027-166 | Wuhan University | 2/2 | generic_identity | whu.edu.cn | 495 | False |
| qs2027-176 | Queen's University Belfast | 1/1 | generic_identity | unknown | 219 | False |
| qs2027-186 | Universidad de Chile | 2/2 | generic_identity | uchile.cl | 311 | False |
| qs2027-196 | Université catholique de Louvain (UCLouvain) | 1/1 | generic_identity | ucl.ac.be | 343 | False |
| qs2027-206 | Gadjah Mada University | 1/1 | generic_identity | unknown | 90 | False |
| qs2027-216 | Hong Kong Baptist University | 1/1 | generic_identity | hkbu.edu.hk | 106 | False |
| qs2027-226 | Universidad Autónoma de Madrid | 1/1 | generic_identity | uam.es | 308 | False |
| qs2027-236 | Tianjin University | 2/2 | generic_identity | tju.edu.cn | 296 | False |
| qs2027-246 | Université Paris 1 Panthéon-Sorbonne | 1/1 | generic_identity | unknown | 350 | False |
| qs2027-256 | University of Porto | 1/1 | generic_identity | unknown | 445 | False |
| qs2027-266 | Singapore University of Technology and Design | 1/1 | generic_identity | sutd.edu.sg | 245 | False |
| qs2027-276 | Universitas Airlangga | 1/1 | generic_identity | unair.ac.id | 327 | False |
| qs2027-286 | University of Southern Denmark (SDU) | 1/1 | generic_identity | unknown | 456 | False |
| qs2027-296 | Stellenbosch University | 1/1 | generic_identity | unknown | 253 | False |
| qs2027-306 | Sultan Qaboos University | 1/1 | generic_identity | squ.edu.om | 256 | False |
| qs2027-316 | University of Leicester | 1/1 | generic_identity | le.ac.uk | 419 | False |
| qs2027-326 | Case Western Reserve University | 1/1 | generic_identity | case.edu | 51 | False |
| qs2027-336 | Southeast University | 1/1 | generic_identity | seu.edu.cn | 250 | False |
| qs2027-346 | Mahidol University | 1/1 | generic_identity | mahidol.ac.th | 171 | False |
| qs2027-356 | Sunway University | 1/1 | generic_identity | unknown | 259 | False |
| qs2027-366 | Université de Liège | 1/1 | generic_identity | unknown | 344 | False |
| qs2027-376 | Goethe-University Frankfurt am Main | 1/1 | generic_identity | unknown | 95 | False |
| qs2027-386 | Northeastern University | 1/1 | generic_identity | unknown | 197 | False |
| qs2027-396 | Università degli Studi di Pavia | 1/1 | generic_identity | unipv.it | 324 | False |
| qs2027-406 | University of Turin | 1/1 | generic_identity | unito.it | 469 | False |
| qs2027-416 | University of Kent | 2/2 | generic_identity | unknown | 416 | False |
| qs2027-426 | Northwestern Polytechnical University | 1/1 | generic_identity | unknown | 198 | False |
| qs2027-436 | Universitat Politecnica de Valencia | 1/1 | generic_identity | unknown | 339 | False |
| qs2027-446 | University of Science and Technology Beijing | 1/1 | generic_identity | ustb.edu.cn | 451 | False |
| qs2027-456 | Masaryk University | 1/1 | curated | muni.cz | 5 | True |
| qs2027-466 | Chongqing University | 1/1 | generic_identity | cqu.edu.cn | 57 | False |
| qs2027-476 | Universidad Nacional de La Plata (UNLP) | 1/1 | generic_identity | unlp.edu.ar | 317 | False |
| qs2027-486 | Royal Holloway, University of London | 1/1 | generic_identity | rhul.ac.uk | 225 | False |
| qs2027-496 | Universitas Padjadjaran (UNPAD) | 1/1 | generic_identity | unpad.ac.id | 329 | False |
