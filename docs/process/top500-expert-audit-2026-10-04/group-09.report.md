# Group 09: scale, repeated research, cache and provenance

Audit date: 2026-10-04. Source baseline: 144881b (packet). All 50 assigned records were exercised using the actual importer/retrieve against an isolated SQLite database containing all 500 seed records and the curated registry: 501 identities, 500 initial observations, 19 curated identities globally. Only the three group-09 outputs were written. No provider, network, production database, admissions validation or source edits. Every row has `live_checked=false`; seed tuition/tests remain `unverified_seed`.

## Reproduce

From repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-09.probe.py
```

The script prints machine-readable summary and regenerates `group-09.rows.json`. It blocks socket connections, creates in-memory databases, and uses a temporary directory only for the synthetic ResponseCache test. Exit code 0; runtime approximately 4.4 seconds on this machine, not a production latency benchmark. No retained historical capture is used as current evidence.

## Actual catalogue results

| Measurement | Result |
|---|---:|
| Assigned records individually exercised | 50/50 |
| Exact-name retrieval retains target | 50/50 |
| Canonical-name retrieval retains target | 50/50 |
| Case/spacing variant retains target | 50/50 |
| Name plus city retains target | 50/50 |
| Supplied/generated suffix alias retains target | 8/8 queries across 8/50 records |
| Alias target ranked first | 7/8; GIST target is second of two |
| Name plus original seed country retains target | 33/50 |
| All recorded retrieval queries | 258 |
| Curated route | 1/50: University of Tartu |
| Generic route | 49/50 |
| Imported domain absent | 21/50 |
| Existing shared normalized domain in assigned records | 0/50 |
| Assigned records in unconstrained first20 / first40 | 2/50 / 5/50 |
| Identical full import adds observations | 0/500 |

These are engineering inputs, not a held-out validation set. Missing hints indicate an extra identification task; they do not establish that a university or its website is broken. Imported domains, including apparently questionable hints, were not independently verified.

## Ranked general hypotheses and evidence

### 1. Persist scoped research routes to reduce repeated discovery cost

**Observed design limitation; performance benefit remains a hypothesis.** 49/50 assigned universities use generic discovery. `catalogue/discovery.py:88-96` obtains an entry anew whenever there is no curated `registry_entry`. `_identify_site` reuses the checked domain as a hint (`:101-108`), but still calls the homepage probe. `_probe_site` persists a domain plus identity observation and returns only name/country/city/homepage (`:168-193`). It does not persist discovered programme/admissions/fee entry points. `adapters/discovery/live_discovery.py:1081-1123` only reads manual entry seeds, then collects sitemaps again. `pipeline/runner.py:177-193` constructs a new catalogue adapter per stage/run; the fetcher shares a disk cache (`:158-168`), so repeated method calls are not necessarily repeated network requests.

**Measured synthetic evidence:** all 50 identities were given matching fake homepage HTML. Three identification calls produce three fake fetcher calls per identity. For the 49 generic identities, a checked domain survives an identical reimport (49/49), but `registry_entry` remains empty (49/49); returned entry keys contain no route seeds (50/50 probes). The actual production enrichment bypasses `_identify_site` for the curated Tartu record, which is the negative control; directly probing Tartu in the synthetic exercise does not imply production does so.

**Student effect:** later searches can repeat sitemap/navigation/search work after page cache expiry, consuming a fixed research budget before new programmes are assessed. Missing domains affect 21/50 initial candidates, but even successful site identification alone does not promote reusable programme routes.

**Proposed experiment:** use unseen institutions outside these500, stratified by domain hint and curated/generic route. Compare baseline with a separate, provenance-bearing route store keyed by institution, degree, field, language and source version; do not put learned routes into the curated field. Give both arms identical max reads, max provider calls and wall-time budgets. Run cold, warm and expired-cache passes using the same dated fixtures. Measure verified programme yield per read, latency, stale-route rejection, and explicit source provenance. Controls: changed programmes, wrong degree routes, homepage failures, redirects and institutions sharing a registrable domain. Reuse routes as leads only; source facts still require freshness checks.

### 2. Normalize country phrases and rank exact aliases before broad substring matches

**Observed retrieval defects/limitations:** 17/50 exact canonical names become zero-result queries when the original seed country is appended. The importer normalizes countries (`catalogue/importer.py:23-43`), while retrieve uses raw normalized query tokens against stored country/name/city/aliases (`catalogue/retrieval.py:88-100`). Examples: UCLA + United States of America, SKKU + Republic of Korea, Sun Yat-sen + China (Mainland), Istanbul Technical + Türkiye, RUDN + Russian Federation. Their exact and canonical name controls all succeed. The country-specific filter already has alias normalization (`retrieval.py:73-76`), so this is specifically the free-text path.

GIST returns two identities and the intended Gwangju Institute is rank2; `retrieval.py:98` uses substring matching and `:104-111` sorts by curated priority/alphabetic name rather than exact alias match. The other seven suffix aliases are unique and rank1. Repeating more queries or adding a cache cannot fix this semantic mismatch.

**Student effect:** adding sensible location context can erase a valid university; an acronym can suggest another university first. Domain/provenance reuse needs a stable, correctly resolved university ID upstream.

**Proposed experiment:** freeze an unseen set of multiword country queries and acronym collisions before implementation. Compare structured country-span normalization plus exact-name/alias-first ranking against baseline at the same returned-list and CPU budget. Report target recall, top1 precision and ambiguity disclosure. Negative controls: actual names containing country words, acronyms that are substrings of other names, multi-country institutions, city aliases. Do not rewrite country-looking tokens blindly.

### 3. Preserve fetch-tier provenance across cache reads

**Observed implementation defect, synthetic reproduction.** `adapters/fetching.py:185-214,217-235` writes URL metadata but omits `fetch_tier` both when storing and restoring. A `FetchResult(fetch_tier='browser')` therefore restores as the dataclass default `http`. `fetching.py:996-1004` increments tier counts from that restored value. The probe writes one synthetic browser result and reads it both through ResponseCache and actual offline Fetcher: original browser becomes http; counts are `http=1,browser=0`. Cache hit, fetched timestamp, content and ETag are preserved. Adding a validator intentionally skips cache and returns `network_unavailable` in offline mode: this is a correct negative control, not a cache regression.

**Affected count:** 50/50 records use the same Fetcher path when researched; zero actual institution browser-cache outcomes were measured. The demonstrated defect denominator is 1/1 synthetic browser cache entry, not 50 live failures.

**Student effect:** provenance/operational reports can misattribute rendered content to HTTP and hide browser work during repeated research. It does not prove that admissions values are incorrect.

**Proposed experiment:** equal-budget replay on held-out cached HTTP, browser, PDF and legacy entries. Require exact tier/content/timestamp/validator round trips and stable pipeline source-page metadata across cold and warm runs. Preserve compatibility for legacy entries without inventing a past tier. Include corrupted metadata, expired entries and same-site redirect cases.

### 4. Separate institution identity from registrable-domain deduplication

**Observed validation gap, synthetic counterexample.** Validation checks uniqueness of full public hostnames (`catalogue/importer.py:91-115`), while `seed_domain` reduces them to a registrable domain (`:138-144`). Replacing only two assigned records' seed hints with `one.collision-audit.edu` and `two.collision-audit.edu` in a copy of the full500 document passes actual validation/import and produces two identities with the same domain `collision-audit.edu`. The original group has zero shared normalized domains (0/50); this is not a claim that UCL and UNSW share a real website.

**Related reimport control:** verified generic domains persist (49/49). The registry loop unconditionally overwrites domain/status (`importer.py:157-173`) for Tartu (1/1 curated record), resetting a synthetic runtime checked domain to curated `ut.ee`. This may be intentional authority precedence, but it should be explicit in future learned-route versioning. Observation history is retained, so proof is not erased; current identity fields are replaced.

**Student effect:** domain-based work deduplication could wrongly share programme routes between institutions/campuses or suppress needed research. Conversely, always splitting by full URL may repeat same-site work. Domain equality alone is insufficient authority to merge identities.

**Proposed experiment:** an unseen fixture set with universities sharing hosting, multiple campuses, genuine aliases, old domains and curated/runtime disagreements. Give baseline and proposal identical discovery budgets. Compare source reads saved while requiring no false identity merges. Validate normalized-domain collisions as explicit ambiguous relationships, not automatic institution equality; preserve distinct institution IDs and per-route provenance.

### 5. Bound observation growth without erasing evidence history

**Observed storage behavior; optimization hypothesis.** For each of 50 synthetic identities, observation increments across first read / same timestamp read / unchanged HTML two days later are `[1,0,1]`. Thus 50/50 repeat identical cached proof without a new row, while 50/50 create another observation on a new fetched timestamp. `catalogue/discovery.py:169-179` hashes `accessed_at` with evidence. `catalogue/importer.py:174-176` loads every historical observation fingerprint on each import; this costs more as history accumulates. Identical seed reimport adds zero observations (negative control). This test does not establish a production bottleneck or justify deleting history.

**Student effect:** at higher run volume, repeated research can expand identity observation history even when page evidence is unchanged; broad importer scans can make refreshes more expensive. Timestamp history is useful and must remain available.

**Proposed experiment:** equal CPU/memory budgets on held-out synthetic histories at 1x,10x,100x repeated observations, with identical evidence versus changed excerpts/domains. Compare indexed existence checks or a distinct evidence fingerprint plus an append-only observation/revalidation history. Require preserved source/time lineage, idempotent retries, and no collapsed conflicting identities. Report peak memory, rows scanned and runtime before recommending schema changes.

## Additional bounded observations

ResponseCache keys hash the literal URL (`fetching.py:185-188`); an exact URL hits and a trailing-slash variant misses in the synthetic test. This is a tradeoff, not automatically a bug: slash/no-slash and query variants can legitimately return different content. Any canonical cache aliasing should rely on verified redirects and origin semantics.

Default unconstrained ordering puts only2/50 group records in the first20 and5/50 in the first40. This is an exposure measurement, not evidence of ranking fairness or applicant fit. Selected university IDs and preferred countries alter the path. Expanding live coverage has to be evaluated with fixed budgets, not by increasing network calls until success.

All individual names, query outputs, aliases, hint availability, route type, synthetic before/after state, observations and risk are recorded in `group-09.rows.json`. Every row includes `tests`: its executed retrieval checks and one grouped synthetic identity/reimport check (308 entries total: 258 retrieval and 50 grouped synthetic checks covering 150 identity calls). The original `retrieval` field is retained for compatibility. The audit establishes reproducible implementation behavior; it neither certifies official sites/admissions nor measures live success, current cache hit rate, provider quotas or full pipeline latency.
