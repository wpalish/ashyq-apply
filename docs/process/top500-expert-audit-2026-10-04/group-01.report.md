# Expert 01 — normalization, token matching and diacritics

Non-blind engineering audit of all 50 exact packet records at source baseline `144881b`. No official facts certified; `live_checked=false` for every record. Seed rankings, domains, tuition and admissions remain unverified. No network/provider calls, secrets, signed gold edits or production source edits. Parent owns git/HANDOFF.

## Reproduction and scope

From repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-01.probe.py
```

The probe asserts the packet seed hash and equality of every assigned record against the retained snapshot, imports all 500 seed records with actual `import_catalogue`, and runs actual `retrieve` in an isolated SQLite memory database. The full 501-identity search space, including 19 curated registry identities, is important for observing collisions. Only group 01's 50 rows are reported. No app settings or database connector is loaded. `group-01.rows.json` contains one record per university, tests, observations, risk, route, hints and unverified status. Tests are mechanical retrieval controls, not adjudicated university truth.

571 query checks cover exact seed names, canonical names, every imported alias, uppercase, Unicode decomposition, accent folding, reversed tokens, original seed country both as filter and free text, domain hints, admissions intent, parenthetical tokens, and applicable punctuation/German digraph variants.

| Check | Target recovered | Interpretation |
| --- | ---: | --- |
| Exact seed name / canonical name | 50/50 each | Four rows return additional identities; York's exact target ranks second |
| Imported aliases | 68/68 | Five alias queries have additional results, across five universities |
| Uppercase / NFD / accent-folded | 50/50 each | All four names with diacritics pass accent/decomposition controls |
| Reordered tokens | 50/50 | Confirms bag-of-tokens behavior; four return additional identities |
| Original seed country as structured filter | 50/50 | Country aliases work in this path |
| Original seed country appended to free text | 32/50 | 18 misses after country canonicalization |
| German umlaut digraphs | 0/2 | Muenchen/Wuerzburg and Universitaet are not normalized to the retained spelling |
| Punctuation deletion | 1/6 | Five joined-character variants miss; deleting the spaced TIIAME separator passes |
| Parenthetical tokens | 10/10 | Includes embedded IISc, despite importer only extracting a trailing suffix alias |
| Domain query | 0/34 | Domain is outside searchable fields; `lu.se` even returns two unrelated identities |
| Name + admissions | 0/50 | Local identity filter does not parse admissions intent; not a demonstrated defect in a name-only search contract |

48/50 take the generic site-identification route; Hong Kong and Vienna have curated routes. Imported domain statuses: 32 seed, two curated, 16 unknown. All 16 unknown rows lack both retained hints. This describes local coverage and route selection, not 16 confirmed broken websites.

## Prioritized general hypotheses

### P1 — Exact identity should outrank cross-field token matches

**Observed behavior:** `University of York` returns Stony Brook first and York second. Four of 50 full exact-name queries have extra candidates: Hong Kong (four results), Queensland (two), York (two), George Washington (two). Only York is a demonstrated exact-target top-one failure in this group. George Washington also matches Georgetown because `george` is a substring and Washington comes from the city.

**Code:** `backend/app/catalogue/retrieval.py:97-99` performs substring checks across name, country, city and aliases; `:104-110` sorts by preference, curated status, then alphabetically, without exact-query relevance.

**Hypothesis:** A normalized exact-name/alias match tier before the existing stable tie-breakers improves name-search top-one accuracy without removing exploratory matches. Measure query relevance separately from admissions fit; an exact-name boost need not change the default no-query shortlist.

**Counterexamples:** The other 46 exact names return only the target; the other three ambiguous exact queries already rank their target first. Reversed-word queries deliberately recover all 50 and should remain supported.

**Equal-budget validation:** Freeze the same 501 identities and 50 exact plus 50 reordered queries; compare top-one accuracy, recall@20 and unrelated top-five identity count at identical candidate cap. Require York improvement and no exact/alias recall regression. Use a separate held-out group before enabling.

### P1 — Short aliases need boundary-aware relevance

**Observed behavior:** `MIT` returns MIT and RMIT. This specific acronym collision affects one of 50 institutions (one of ten parenthetical-token probes). MIT is still first, so this is observed overmatching, not a target miss.

**Code:** `backend/app/catalogue/retrieval.py:98` uses Python substring membership. `backend/app/catalogue/importer.py:196-200` retains supplied names and a trailing parenthetical alias; it does not create an exact-alias ranking tier.

**Hypothesis:** Exact short-alias matches should precede substring results; use token boundaries for acronym matching while retaining a separate explicit prefix mode if desired. Avoid replacing all substring matching blindly because it currently supports partial-name input.

**Counterexamples:** UCB, UCSD, NCKU, UTP, UCAS, UIC, NSYSU and TIIAME-NRU recover their target without other results. The embedded `IISc` also recovers its row directly from the retained full name, so absence of a separate IISc alias is not a confirmed retrieval bug.

**Equal-budget validation:** Same ten parenthetical queries and 68 alias queries, same result cap, plus fixed negative probes such as an acronym occurring inside a longer institution token. Measure exact-alias top-one, false-positive identities, and prefix-query recall. No additional provider requests.

### P2 — Preserve accent folding and add bounded orthographic variants

**Observed behavior:** All four diacritic-bearing names (LMU München, Universitat Autònoma de Barcelona, Koç, Würzburg) recover under NFD and accent folding. Both German digraph probes miss. Punctuation deletion misses in five of six applicable rows: MichiganAnn, LudwigMaximiliansUniversität, Queens, JuliusMaximiliansUniversität, and Yatsen. Union of affected rows is five of 50, since both German rows also fail punctuation deletion. Hyphen joining is a mechanical stress test, not evidence that users routinely enter every generated form.

**Code:** `backend/app/domain/dedupe.py:37-41` removes combining marks and converts punctuation into spaces; it does not equate `ü` with `ue`, or `Queen's` with `Queens`. `backend/app/catalogue/retrieval.py:89,97-99` requires every normalized query token.

**Hypothesis:** Store secondary search forms for bounded German umlaut digraphs and apostrophe elision; keep canonical identity keys unchanged to avoid accidental identity merges. Hyphen joining needs measured user demand before general expansion.

**Counterexamples:** `Munchen`/`Wurzburg` accent-folded controls already work; Koç and Autònoma need no change. The spaced hyphen in TIIAME deletes cleanly and already matches.

**Equal-budget validation:** Freeze the same 50 base queries, four accented controls, two digraph variants, six punctuation variants and negative names differing in meaningful letters. Use identical candidate caps; measure target recall and identity collisions, with no change to stable IDs. Expand variants only if held-out positives improve without merging distinct identities.

### P2 — Country synonyms are inconsistent between filter and free query

**Observed behavior:** All 50 original seed-country filters match, while 18 full name + original country strings miss: 12 US universities and one each from Hong Kong, Turkey, China, South Korea plus two from Russia. The misses occur despite exact names matching. This is an observed interface inconsistency; whether free-form country text is promised is a product-contract question.

**Code:** `backend/app/catalogue/importer.py:22-42` canonicalizes countries, while retrieval `:73-75,95` resolves aliases only for the structured country filter. The free-text haystack `:98` contains the canonical country, not the original seed country or its alias set.

**Hypothesis:** Index country aliases as a separate searchable field or detect supported country phrases before name token matching. Avoid globally replacing arbitrary substrings inside university names.

**Counterexamples:** The other 32 name + seed-country queries succeed; structured country filters succeed in every case. A canonical-country-only UI may avoid this mismatch already.

**Equal-budget validation:** Pair the same 50 queries with original and canonical country strings, with/without filters; compare identity recall at identical result caps. Include ambiguous words such as US/UK and exclusions as negatives; maintain no-query regional filter behavior.

### P2 — Validate generic routes under the same discovery budget

**Observed coverage:** 48 generic routes, two curated; 16/50 have no retained domain/site hint. 34 retained domain queries recover zero targets because domains are not search fields. A `lu.se` query returns Complutense and Institut Teknologi Sepuluh Nopember through unrelated token substrings. These are design/coverage limitations; no site or provider was contacted and no programme-discovery failure was established.

**Code:** `backend/app/catalogue/discovery.py:88-99` dispatches curated versus identity-first discovery; `:101-115` tries at most two hints before one provider identity query with three results. `:135-166` requires matching title/H1 identity. `:43-49,65-68` bounds and orders enrichment. Importer `:171-173,190-192` sets curated versus seed/unknown domain states.

**Hypothesis:** Domain-shaped queries can have a local exact-domain route without treating seed hosts as verified facts. Independently, measure whether generic/no-hint institutions consume their discovery budget establishing identity and leave less for programme discovery. Do not claim adding domains or curated routes will fix live search until measured.

**Counterexamples:** The two curated institutions skip `_identify_site`; 32 generic rows already have hints, so generic does not mean provider-first. Successful offline name retrieval is 50/50 despite 16 missing hints.

**Equal-budget validation:** Use unchanged 50 identities, one fixed applicant profile, provider, fetch limit, total wall clock, and programme verification rules in both arms. Stratify by two curated / 32 hinted generic / 16 no-hint generic. Compare official identity acceptance, verified programme recall, fetch/provider counts and abstentions. Keep no-evidence outputs unknown. Only conduct a live experiment when explicitly scheduled outside this offline audit.

## Interpretation limits

The reported corpus is non-blind and drawn from supplied seed rows. Query variants are engineering stress tests, not a sampled user-query distribution. No controlled A/B improvement is claimed. Current top-one/recall findings concern local retrieval, not programme relevance or eligibility. Missing alias/domain data alone is not a confirmed algorithm defect. No retained historical traces were used. Production fixes and any full acceptance checks remain with the parent task.
