# Group 02: official identity, acronyms, domain conflicts and redirect policy

Date: 2026-10-04. Source baseline: `144881b`; packet seed SHA-256: `5ab134e331add59884ff5bca548dc17d5a428a7a5d69fdec09c7863babe08a58`. This is a **non-blind offline engineering audit**, not official-fact certification, live search acceptance, or a production improvement measurement. All 50 packet universities were exercised against the actual importer and retrieval implementation in a newly created in-memory SQLite database containing the full 500-row seed plus the registry-only institution. All HTML and Fetcher responses in identity probes are synthetic. Every row has `live_checked=false`.

Reproduce from repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-02.probe.py
```

The executable verifies the seed hash, forbids socket connections and provider construction, imports twice, executes actual `retrieve` and `CatalogueDiscoveryAdapter._probe_site`, rolls back identity writes after each scenario, and writes `group-02.rows.json`. It makes no network/provider requests. It changes no production code, gold, seed, persistent database, secrets or git state. Parent owns HANDOFF and commits. No historical traces were used.

## Measured coverage

| Check | Result |
|---|---:|
| Packet coverage | 50 unique seed IDs / 50 |
| Full import | 500 seed records, 501 universities, 500 observations |
| Reimport | 0 new observations |
| Exact supplied-name retrieval | 50/50 target found; 49/50 target first |
| Canonical-name retrieval | 50/50 target found |
| Normalized-name retrieval | 50/50 target found |
| Imported alias queries | 60/60 target found |
| Explicit uppercase acronym tokens inside supplied names | 7/7 target found |
| Exploratory hostname-label queries | 18/41 target found; 23 misses |
| Total labelled query probes | 258; 235 include target |
| Country-filter and ID selection checks | 50/50 each |
| Curated / generic route | 2 / 48 |
| Imported domain statuses | 2 curated, 40 seed, 8 unknown |
| Seed domain absent | 9/50; NTU has a curated route despite this |
| No usable imported-domain or seed-site hint | 8/50 |
| Conflicting seed domain/site registrable domains | 0/50 |
| Synthetic full-name title / H1 acceptance | 50/50 each |
| Synthetic full-name H2-only acceptance | 0/50 |
| Synthetic unofficial-guide title acceptance | 50/50 |
| Synthetic unrelated host with exact institution title acceptance | 50/50 |
| Synthetic unrelated title acceptance | 0/50 |
| Synthetic same-site www redirect acceptance | 50/50 |
| Synthetic cross-site final redirect acceptance | 0/50 |

There are 411 per-university synthetic identity calls and one separate synthetic conflicting-hint call. Repeated spellings under different query kinds deliberately verify separate contracts; 258 is the number of labelled probes, not 258 unique strings. Hostname labels are **exploratory variants**, not verified aliases or established user demand. Their absence from retrieval is not by itself an algorithm defect. Missing seed hints likewise describe input coverage, not a missing or invalid official website.

## Five general hypotheses and falsifiable experiments

### H1. Name containment should be corroborated before authorizing a discovered domain

`backend/app/catalogue/discovery.py:149-176` accepts any normalized full name of at least eight characters appearing anywhere in title/H1, then labels the result `site_identity_checked`; `:190-193` persists that domain. On all 50 rows, the actual method accepted both `Unofficial guide to <full name> fees` and the full name at `https://unrelated-college.edu/`. The latter hint can enter through provider results (`:113-130`); homepage-only probing does not prove organizational ownership. This is a reproduced false-acceptance condition, not a claim that any seed website or real provider result is malicious. Normal `_enrich` exposure in this group is the 48 generic rows; the two curated rows bypass this method (`:88-96`).

Counterexamples/guards: unrelated title was rejected 50/50; cross-site final URLs were rejected 50/50. The redirect guard proves a response stayed at its requested source, but an initially wrong requested source still passes it. Stronger identity matching must not accept a site merely because its host resembles the name.

Experiment: freeze equal sets of independently adjudicated official homepages and negative directories, unofficial guides, affiliated entities, and brand impersonations. Randomize order and hold one fetched homepage per candidate constant. Compare current containment with a candidate rule using explicit negative cues plus independently established identity evidence; when corroboration needs another read, give both arms the same maximum two reads. Measure false-authorized domains first, verified identity recall second, and abstentions/read cost separately. Require zero added false authorizations; a negative-cue blacklist alone is not sufficient for arbitrary impersonation. Do not promote a rule from these synthetic positive titles as though they were live labels.

### H2. Distinguish recorded short aliases from incidental acronym tokens and preserve ambiguity

The importer extracts only the final parenthesized suffix as an extra alias (`backend/app/catalogue/importer.py:196-200`). The identity check canonicalizes whole aliases and allows a short alias only when it exactly equals the first hostname label and the page contains an English institution word (`discovery.py:153-165`). Four imported short aliases occur in this group: LSE, IITK, AUT pass their synthetic acronym-only titles; CityUHK fails on `cityu.edu.hk` because the host label is `cityu`. These are structural outcomes, not observations about current homepage titles.

Three of seven supplied uppercase acronym-token title scenarios fail: NTU, EPFL, KTH. Their tokens are not standalone imported aliases. UCSI succeeds via the long match on the existing full name `UCSI University`, not a newly derived short alias. NTU is curated in normal operation, so its isolated identity failure is not a present route failure. Counterexamples LSE/IITK/AUT demonstrate that current strict host matching already handles some cases safely.

Retrieval independently returns four institutions for AUT and two for NTU. The seed includes two different hostname labels `psu` in this group (Pennsylvania State University and Prince Sultan University), and `psu` retrieves neither today. Automatically registering every host label as an authoritative alias would introduce ambiguity; a query variant and an official identity assertion need different trust treatment.

Experiment: compare current behavior with evidence-backed alias normalization, stratifying recorded parentheses, embedded uppercase tokens, host-label mismatch and collisions. Use the same alias strings and same one homepage response per identity candidate in both arms; include every colliding institution in each retrieval pool. Measure target rank, ambiguity retained, acronym-only identity recall, false authorizations and wrong automatic merges. Expansion must remain an unverified search lead until corroborated and must never collapse PSU-like collisions by first result.

### H3. Preserve contradictory hints as competing leads, while retaining the cross-site redirect refusal

`seed_domain` returns unknown when domain/site registrable domains disagree (`backend/app/catalogue/importer.py:139-144`). `_identify_site` then uses `uni.domain` and the saved `official_site`, but does not read the saved `official_domain` (`discovery.py:101-108`). A separate synthetic conflict produced `seed_domain=None`, probed only `https://second-college.edu/`, and accepted it from the matching title. The first hint was never tested. There are **zero actual conflicts among these 50 seed rows**, so the evidence is a general synthetic branch test and contributes no observed affected-university count.

Counterexamples: ordinary matching seed domains remain usable for 41 rows; NTU receives a curated domain despite its missing seed domain. Nankai's `nku.nankai.edu.cn` becomes `nankai.edu.cn` while the original site survives as a second hint, reflecting intentional registrable-domain normalization. The synthetic same-site redirects pass 50/50 and cross-site redirects fail 50/50. `backend/app/adapters/fetching.py:637-649` independently refuses cross-site redirects; this audit did not execute the real HTTP redirect loop. Do not weaken that policy to follow a presumed rebrand.

Experiment: replay independently adjudicated paired hints covering match, parent/subdomain, contradiction, stale host and cross-domain successor. Hold a maximum of two homepage reads and one provider call with at most three results equal in both arms. Compare retaining both unresolved hints as leads with current second-hint-only behavior. Count correctly resolved identities, abstentions, wrong domain authorizations, reads, and conflict provenance. A legitimate new domain must be independently identified under the existing Fetcher controls; a redirect is not ownership evidence.

### H4. Broader identity surfaces may improve recall only with equally strong negative controls

Identity extraction uses only title and H1 (`backend/app/catalogue/discovery.py:149-152`). All 50 synthetic H2-only pages are rejected while all 50 title and H1 controls pass. This is a source-shape sensitivity, not 50 live failures. Of the 48 generic rows, eight have no domain/site hints, meaning a provider is needed before any such page can be inspected. Missing hints and an unrecognized reached page are different loss stages.

Counterexample: title/H1 works for every supplied full name in the controlled fixture, so indiscriminately searching whole body text would expand the H1 false-positive problem from H1/title into page mentions.

Experiment: fix an independently labelled homepage corpus spanning title/H1, structured Organization names, logos/accessible names, local-language identity and negative pages mentioning the institution. Fetch exactly one frozen page per arm. Test structured, bounded identity surfaces with explicit organization-role attribution, avoiding arbitrary body containment. Report added correct identities against added false authorizations; evaluate local-language and missing-surface groups separately. No provider budget increase may be credited as an extraction improvement.

### H5. Rank exact names before token containment without hiding legitimate alternatives

`backend/app/catalogue/retrieval.py:97-100` checks token substrings across concatenated name/country/city/aliases; `:104-110` sorts by country preference, curated route, then alphabetically, with no exact-match preference. All 50 exact names retrieve their target, but eight exact queries return multiple institutions. University College Dublin is second: Trinity College Dublin, The University of Dublin is first. Its city/name together satisfy the same words. Seven other exact-name queries also have a second match, including Pennsylvania State University and Arizona State University. This is directly measured local behavior, independent of site verification.

Counterexamples: 49/50 exact-name targets are already first; full normalized and canonical names are never lost. Querying AUT correctly preserves multiple candidates rather than an unsafe automatic identity merge.

Experiment: use the identical 501-institution in-memory pool and all 258 queries. Compare current sort with an exact normalized full-name/recorded-alias tier before broad token matches, keeping every existing result and route/preference ordering within tiers. Measure target rank/MRR/top-1 and unchanged result-set recall; separately inspect short ambiguous aliases and country constraints. Hold page/provider budgets at zero. Alias/seed facts remain unverified; improved list ordering must not grant official-site status.

## Priority and limitations

Prioritize H1 false authorization safeguards, then H5 deterministic exact-name ordering. H2 is promising but requires independently supported aliases and collision negatives; H3 has only synthetic conflict evidence in this group; H4 needs labelled real page shapes. This audit proposes experiments, not a production patch or demonstrated search-quality uplift. The catalogue's correct full-name inclusion does not establish programme discovery, admissions evidence, affordability, deployment or live user-flow quality.

The following per-row index is derived from `group-02.rows.json`; that JSON contains every executed query, returned names/ranks, hint values, synthetic scenario results, observations and risk classification. Seed domains and sites below are unverified inputs, not current official-source certifications.

## All 50 audited rows

| Seed ID | Supplied name | Route / domain status | Exact query rank / hits | Hint state |
|---|---|---|---:|---|
| qs2027-002 | Imperial College London | generic / seed | 1 / 1 | imperial.ac.uk |
| qs2027-012 | Nanyang Technological University, Singapore (NTU Singapore) | curated / curated | 1 / 1 | ntu.edu.sg |
| qs2027-022 | EPFL – École polytechnique fédérale de Lausanne | generic / seed | 1 / 1 | epfl.ch |
| qs2027-032 | University of Toronto | curated / curated | 1 / 1 | utoronto.ca |
| qs2027-042 | Yonsei University | generic / unknown | 1 / 1 | no usable hint |
| qs2027-052 | City University of Hong Kong (CityUHK) | generic / seed | 1 / 1 | cityu.edu.hk |
| qs2027-062 | The London School of Economics and Political Science (LSE) | generic / seed | 1 / 1 | lse.ac.uk |
| qs2027-072 | University of Texas at Austin | generic / seed | 1 / 1 | utexas.edu |
| qs2027-082 | KTH Royal Institute of Technology | generic / seed | 1 / 1 | kth.se |
| qs2027-092 | Pennsylvania State University | generic / seed | 1 / 2 | psu.edu |
| qs2027-102 | University College Dublin | generic / seed | 2 / 2 | ucd.ie |
| qs2027-112 | Sapienza University of Rome | generic / unknown | 1 / 1 | no usable hint |
| qs2027-122 | Rice University | generic / seed | 1 / 1 | rice.edu |
| qs2027-132 | University of Wisconsin-Madison | generic / seed | 1 / 1 | wisc.edu |
| qs2027-142 | Georgia Institute of Technology | generic / seed | 1 / 1 | gatech.edu |
| qs2027-152 | Eindhoven University of Technology | generic / seed | 1 / 1 | tue.nl |
| qs2027-162 | Université de Montréal | generic / seed | 1 / 1 | umontreal.ca |
| qs2027-172 | Arizona State University | generic / seed | 1 / 2 | asu.edu |
| qs2027-182 | Michigan State University | generic / seed | 1 / 2 | msu.edu |
| qs2027-192 | Technische Universität Wien | generic / seed | 1 / 1 | tuwien.ac.at |
| qs2027-202 | Waseda University | generic / seed | 1 / 1 | waseda.ac.jp |
| qs2027-212 | Chulalongkorn University | generic / seed | 1 / 1 | chula.ac.th |
| qs2027-222 | Indian Institute of Technology Kanpur (IITK) | generic / seed | 1 / 1 | iitk.ac.in |
| qs2027-232 | University of Strathclyde | generic / seed | 1 / 1 | strath.ac.uk |
| qs2027-242 | Victoria University of Wellington | generic / seed | 1 / 1 | vuw.ac.nz |
| qs2027-252 | University of California, Irvine | generic / seed | 1 / 1 | uci.edu |
| qs2027-262 | University of Göttingen | generic / unknown | 1 / 1 | no usable hint |
| qs2027-272 | Taylor's University | generic / unknown | 1 / 1 | no usable hint |
| qs2027-282 | UCSI University | generic / seed | 1 / 1 | ucsi.edu.my |
| qs2027-292 | University of Johannesburg | generic / seed | 1 / 2 | uj.ac.za |
| qs2027-302 | University of Witwatersrand | generic / seed | 1 / 1 | wits.ac.za |
| qs2027-312 | Simon Fraser University | generic / seed | 1 / 1 | sfu.ca |
| qs2027-322 | Swansea University | generic / seed | 1 / 1 | swansea.ac.uk |
| qs2027-332 | Nankai University | generic / seed | 1 / 2 | nankai.edu.cn |
| qs2027-342 | South China University of Technology | generic / seed | 1 / 2 | scut.edu.cn |
| qs2027-352 | University of Tsukuba | generic / unknown | 1 / 1 | no usable hint |
| qs2027-362 | University of Oulu | generic / seed | 1 / 1 | oulu.fi |
| qs2027-372 | University of Münster | generic / unknown | 1 / 1 | no usable hint |
| qs2027-382 | Quaid-i-Azam University | generic / seed | 1 / 1 | qau.edu.pk |
| qs2027-392 | Sharif University of Technology | generic / seed | 1 / 1 | sharif.ac.ir |
| qs2027-402 | University of Naples - Federico II | generic / seed | 1 / 1 | unina.it |
| qs2027-412 | Oxford Brookes University | generic / seed | 1 / 1 | brookes.ac.uk |
| qs2027-422 | Prince Mohammad Bin Fahd university | generic / seed | 1 / 1 | pmu.edu.sa |
| qs2027-432 | Auckland University of Technology (AUT) | generic / seed | 1 / 1 | aut.ac.nz |
| qs2027-442 | Umea University | generic / seed | 1 / 1 | umu.se |
| qs2027-452 | Universitat de Valencia | generic / unknown | 1 / 2 | no usable hint |
| qs2027-462 | University of California, Santa Cruz | generic / seed | 1 / 1 | ucsc.edu |
| qs2027-472 | Leibniz University Hannover | generic / unknown | 1 / 1 | no usable hint |
| qs2027-482 | Hiroshima University | generic / seed | 1 / 1 | hiroshima-u.ac.jp |
| qs2027-492 | Prince Sultan University | generic / seed | 1 / 1 | psu.edu.sa |
