# Programme-page discovery v3 — the plan on one page

Prototype for [Prototype: the discovery plan v3](../issues/16-prototype-discovery-plan-v3.md) · 2026-10-18 ·
claude-opus-5 · branch `claude/greeting-16wj2z`, code at `295c469`.

**What this is.** A rough, concrete page for the owner (Диас) to react to — "this, not that" on any row, and
`16-Q<n> да / нет / обсудить` on the numbered choices in §5. It is not the design until the owner says so; when
he does, the loop (`loop-engineering`, paired runs, owner approval per rule) builds it in the order of §3.

**What it rests on.** The owner's decisions in tickets 01–07, 18–20 (every ➡️ there is a decision, not restated
here), the research answers 08–14, `PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md` §3 (LI-2 / LQ-1 / LC-1) and
`STRUCTURAL_ANALYSIS_2026-10-18.md` §4, and the code. Development sets only (cohort, dev2, dev3; dev4 when
signed). No heldout gold, capture, log or per-case row was opened; the nine are mentioned only as the countries
they sit in.

**Standing invariants — not decisions on this page.** 6 queries / 60 reads / 120 s per university; no robots
bypass, no UA spoofing, no proxies; no applicant attribute in any query (language comes from the
*institution's* country, aliases from the bundled ontology); `Fetcher` is never weakened; nothing goes to an
LLM beyond the privacy table.

**Where we start (today's defaults, SB-1c in since `f568c35`).** Programme page under the old scorer: cohort
5/10, dev2 3/6, dev3 4/11; under ticket 03's identity rule 17 of 35 development cases have a confirmed page
(5 of them twins or siblings the gold did not list). The 18 misses: 7 access (out of scope), 6 local-language
pages never listed by any stage, 3 wrong programme confirmed, 2 pages read and refused
([Where the programme page is lost today](../issues/08-loss-stages-today.md)). Budget: `cases_over_budget` is
4–5 on dev3 (Imperial 68–71 reads, Chula 61–63; loop report correction of 2026-10-18).

---

## 1. Measurement prerequisites — these land first, in this order

No rule's paired run in §3 is *read* before M0–M3 are in; M4–M5 gate the rules that name them.

| # | prerequisite | what lands (harness / scorer / data — no discovery rule) | why before the rules | status |
|---|---|---|---|---|
| **M0** | **Hard read cap: 60 reads per case, in the pipeline** | one counter for the whole case (discovery *and* evidence stages — `DISCOVERY_READ_CAP = 28` bounds discovery only), stops at 60, the case reports `budget_exhausted` and keeps what it confirmed; scorecard `cases_over_budget` must read 0 on every development set | every bar in §3 says "reads not above today's"; with 4–5 cases over 60 that bar has no floor and a rule that adds 3 reads cannot be judged. Where the reads go is a separate analysis (in progress); this plan needs only that the cap *exists* | not built; shape → §5 Q1 |
| **M1** | Provider result lists, twins recorded both ways, twin scored as a hit, `gold_seen` per case, trace persisted at the confirm checkpoint | [Record provider results](../issues/17-record-provider-results.md) | splits "never seen" into not returned / returned not read / seen as link; kills no longer erase a confirmed page | **landed** `a5e5512`, `295c469`, checkpoint `1184f66`; the first paired run after them is the first capture with the fields |
| **M2** | Scorer: the **related** outcome and canonical variants | `metrics.adjudicate` gains `related` (neither hit nor wrong; out of the wrong-page count); canonical variant = same path ± intake-year segment, trailing slash, `index.html`; `?lang=` only when `<html lang>` confirms it ([What counts as the programme page found](../issues/03-programme-identity-equivalence.md) Q2–Q3) | R2 turns UCT/Imperial-type confirmations into `related`; without the third outcome they score as losses or stay wrong | not built; re-score the frozen captures — no published number may move except wrong → related |
| **M3** | Benchmark arm `--through-identity-gate` + scorecard line "identity established n/N" | the entry is built from the seed row and runs `CatalogueDiscoveryAdapter._identify_site`; today `live.dev2_entry` hands discovery a verified homepage ([Production site-identity gate](../issues/05-identity-gate-in-design.md) Q3) | R6 is unmeasurable without it; the acceptance run uses both arms ([Acceptance protocol](../issues/21-heldout-acceptance-protocol.md) Q3) | not built |
| **M4** | dev4 labels | `evaluation/research/data/dev4.draft1.json` (≤ 10 rows, programme page + twin), `DEV4` in `live.py`, a scorecard line ([Commission the dev4 labels](../issues/15-commission-dev4-labels.md)) | the only development cases in the heldout countries' languages; R1, R4, R5 go **default-on** only after a dev4 run (→ §5 Q7) | in progress |
| **M5** | Serper probe: ≤ 300 credits, five query shapes × six local-language development cases, from the runner | a one-off script; M1 keeps every result list ([Serper probe and query language](../issues/07-serper-probe-and-query-language.md)) | decides whether R5 exists and in which shape (gold or twin in the top 10 on ≥ 4 of 6) | can run now (M1 is in) |
| **M6** | Glossary entries | `GLOSSARY.md`: programme twin, canonical variant, related programme, wrong page, programme identity, programme title, subject head, filler word, related field, catalogue host, section link (03 Q5, 19 Q5, 20 Q6) | the loop's tests and traces use these names | docs only |

---

## 2. The v3 stage table

One institution, one discovery clock (SB-1: `DISCOVERY_DEADLINE_SECONDS = 55`, `DISCOVERY_READ_CAP = 28`
discovery reads; the case's 60 is M0's). v3 changes **no** budget constant. "Guard" is what keeps the stage
from adding a wrong page; the confirm predicate (stage 4) is the single authority for every stage.

| # | stage | inputs & budget | rule in v3 | precision guard | motivating development case(s) | flag(s) | measurement & bar | lands |
|---|---|---|---|---|---|---|---|---|
| **0** | **Site identity** (production path only; benchmark arm M3) | seed row: name, country, `official_domain` / `official_site`; the homepage read `_probe_site` already makes | identity is established when **any** of: (i) probed host = `official_site` host after redirects; (ii) `<html lang>` is a language of the country **and** the title holds the row's native-script name; (iii) the English name appears in the homepage's `hreflang="en"` alternate, read once, same registrable domain; (iv) today's rule. The branch that fired is recorded as `site_identity.proof` | (i) accepts no redirect off the row's own host; (ii) needs both signals — and a native name the seed data does not hold today (→ §5 Q8); (iii) one read, same registrable domain; the 147 rows without a domain keep today's one-query fallback (05 Q4) | tsinghua, ntutw, utokyo, uio, ucph, uppsala, iitd, tcd — 8 of 15 conclusive development homepages fail today ([Identity gate offline](../issues/12-identity-gate-offline.md)) | `SITE_IDENTITY_V2` (`--site-identity-v2`), arm `--through-identity-gate` | on the identity arm, all development sets: identity established on every conclusive development homepage that passes by hand (today 7/15), **0 false identities** (a host that is not the university accepted); programme-page numbers on the arm within one case of the default arm | **R6**, own track |
| **1** | **Entry** | robots.txt, the first sitemap document, the homepage; `MAX_FALLBACK_PAGES = 5` | as today, plus: a homepage or section-page link whose **label** is a study-section / catalogue word in a language of the institution's country becomes a catalogue lead even when its URL categorises as nothing — ≤ 2 hops (homepage → section → catalogue) ([Local catalogue entry](../issues/20-local-catalogue-entry.md) Q1) | the page is read and classified like any lead; a non-catalogue is dropped as today (`not_program_catalog`); the lexicon is dictionary-grade per language, the same shape for every language, language from `entry["country"]` | puc "Carreras de pregrado" → `admision.uc.cl/carreras/`; uio "Studier" → "Finn studier"; ucph `/studier/bachelor`; psaclay "choisir sa formation"; kuleuven `onderwijsaanbod.` | `LOCAL_CATALOGUE_ENTRY` (`--local-catalogue-entry`) | trace `kept_by_link_text` names the section link on puc and uio; no stable loss; 0 new wrong claims; reads per case not above today's (20 Q5) | **R4** |
| **2** | **Sitemaps** | ≤ 13 documents (`DISCOVERY_SITEMAP_ALLOWANCE`), ≤ 40 kept per category, slow host ≤ 3 documents | (a) `keep()` keeps a URL on **subject + level** evidence without a structural word, ≤ 10 of the 40 slots, never displacing a structural pick, read after them ([Sitemap keep rule](../issues/18-keep-rule-evidence-sum.md)); (b) local listing words become URL signals (`/carreras/`, `/formation/`, `/studier/program/`, `/opleidingen/n/…`, …) (20 Q2); (c) the sitemap of a **catalogue host on the same registrable domain** linked from a page read, ≤ 3 documents **inside** the 13 (20 Q3) | the same `keep()`, the same confirm; a wrongly kept URL costs a read, not a page; (c) stays inside `same_institution` and the catalogue host's own robots.txt | (a) um ×4, uba, vienna, psaclay-fr — 7 of 39 gold URLs dropped today ([URL lexicon audit](../issues/09-url-lexicon-audit.md)); (c) `admision.uc.cl/carreras-sitemap.xml` (71 URLs, gold in it), `ingresantes.exactas.uba.ar` (38) | (a) `SITEMAP_KEEP_EVIDENCE_SUM` (`--sitemap-keep-evidence-sum`); (b)+(c) under `LOCAL_CATALOGUE_ENTRY` | (a) +1 on um or uba, reads not above today's, no stable loss (18 Q3); (b)(c) as row 1 | (a) **R3**; (b)(c) **R4** |
| **3** | **Search** | 6 families, 3 in pass 1, the rest in pass 2 only when nothing is confirmed; the shared budget leaves 5 discovery queries (UiO's SB-1c check sent 5); first query by 33 s when nothing is confirmed; identity recovery ≤ 8 reads, reserve 3 | **SB-1c (landed, both arms):** unconfirmed sitemap leads no longer refuse the early search, and a refused search is retried after the walker. **v3:** when the institution's country has a non-English language with an ontology alias, a `local_language` family (`site:{domain} "{alias}" {local bachelor word}`, in the shape M5 selects, Serper `hl`/`gl` only if that shape wins) takes the **third pass-1 slot**; `programmes` → reserve ahead of `courses`; `admissions` dropped; six stay six; English-country plans byte-identical (07 Q3) | aliases and degree words from the ontology, language from the institution's country — never the applicant; prefilter learns local news slugs (`/nyheter`, `/aktuelt`, `/haberler`, `/uudised`, `/naujienos`, `/новости`, …); `names_other_degree_level` learns local master slugs so a master's page does not take a recovery read; the same confirm predicate | uio (0 queries before SB-1c), puc and uba (only pass 1 ever sent), kuleuven, tsinghua-cn, tec-es — pages whose text has no "computer science" ([Queries and the search-skip defect](../issues/11-queries-and-search-skip.md)) | `LOCAL_LANGUAGE_QUERIES` (`--local-language-queries`) | R1 on in both arms; `search_results` rows with family `local_language` and `gold_seen` moving off `never` on ≥ 1 local-language case; +1 stable programme page across dev2/dev3/dev4; no stable loss; 0 new wrong claims; `cases_over_budget` 0 | **R5**, after M5 |
| **4** | **Confirm** | ≤ 8 candidates (`MAX_PROGRAM_CANDIDATES_CHECKED`), score-descending; the classifier, CG-1 campus guard | (a) **LI-2 lexicon**: degree words per language for bachelor **and** master (earliest match wins; a master's page is never read as a bachelor's), dictionary-grade aliases for every language in one table (incl. es "ingeniería en ciencia de la computación" — 19 Q3), `related_not_equivalent` local forms refused by name; a declared `hreflang` twin followed in **either** direction and recorded (03 Q1; recording landed in M1). (b) **Title shapes** (19 Q1–Q4): the subject is the head before `:` / ` – ` / ` - `; a place in the institution's country and a form word are filler; the applicant's own field words get the same remaining-words test as aliases, with Business / Engineering / Economics / Mathematics and the ontology's related heads as **non**-filler → **related**, not the page | the page's own text decides — nothing inferred from the URL; master words in the same table; es stays on "ciencia(s) de la computación" (`informática` alone is IT), `ingeniería informática` / `ingegneria informatica` / `enginyeria informàtica` stay computer engineering; a foreign campus is still refused (CG-1); `claim_precision` and `wrong_scope_claim_rate` guard the pages R1 newly accepts — LX-1's paired run is **off** because of one wrong Imperial deadline, so R1 lands only with that cause found | (a) iitd B.Tech, uba and puc *licenciatura*, ucph-da *datalogi* — refused today for a word ([Classifier audit](../issues/10-classifier-audit.md)); (b) uio "Informatikk: programmering og systemarkitektur", kuleuven "Bachelor in de informatica (Leuven) - Studieprogramma" accepted; uct "Business Science specialising in CS" and imperial "mathematics-computer-science" become related | (a) `LOCALIZED_PAGE_IDENTITY` (`--localized-page-identity`) — absorbs LX-1's `LEXICON_V2` entries (→ §5 Q4); (b) `SUBJECT_TITLE_SHAPES` (`--subject-title-shapes`) | (a) 0 expected gain on today's captures (none of these pages is reached yet), **0 stable loss, 0 new wrong claims**, offline unit tests on the eight saved gold pages both ways; (b) uct's wrong page gone (precision +1), no stable loss, 0 new wrong claims; M2 in so related is scored | (a) **R1**; (b) **R2** |
| **5** | **Walker / navigation on opaque hosts** | the catalogue walker (`MIN_LABEL_CHARS = 10` → `short_label`), the navigation fallback | **not in v3** — fog on the map: link-text-first identity on hosts whose URLs say nothing (`content?menu=188`, `UKEN-556.html`, `plan?p7_code=`), and department hosts the homepage never links (`cs.`, `csie.`) stay with search (20 Q4) | — | kaist (gold seen by the walker, dropped as `short_label`; the page's own text carries no identity), tsinghua, ntutw | — | it enters the plan only when dev4 shows the shape on ≥ 2 readable proxies; then its own ticket | — |
| **6** | **Stop & report** | SB-1 stop when confirmed; M0's cap; the checkpoint trace | stop at the first confirmed page (as today); report one of **found** (page or twin), **related**, **wrong** (scored, never shown as found), **unresolved** (lead not readable, SPA / PDF-only — 01 Q6), **unavailable** (robots unreachable, 403, challenge, dropped connections — never a guess), **budget_exhausted** (M0); the trace and `programme_urls` survive a kill | nothing is reported found that confirm did not accept; a refused host is never retried with another identity | ubc, imperial (killed at 115 s with a page confirmed — now kept), aalto, toronto, ub, kuleuven (unavailable), tec (SPA), uba / utokyo study-plan PDFs (unresolved) | none new (M0, M1, M2) | the scorecard's budget row 0 on every set; `unavailable` only on access classes; 0 pages confirmed on a refusing host | with M0–M2 |

---

## 3. Rules in landing order — one flag, one paired run each

Paired run = off / on / on / off, two repetitions, every development set that exists at the time, read for
stable gains and stable losses only (DoD loop step 3). A rule that fails twice is recorded as rejected in
`hypotheses.json` and not retried without new evidence. Precision rules land before the recall rules that
would feed them pages.

| order | rule | flag · harness · loop id | files | what changes | expected effect (stated, not measured) | bar to go default-on | rejected if |
|---|---|---|---|---|---|---|---|
| — | SB-1c (search not refused by unconfirmed leads) | no flag; `f568c35` | `live_discovery.py` | landed; both arms of every run below | UiO 0 → 5 queries (check run 39106597318) | already in | — |
| **R1** | **Local-language page identity** | `LOCALIZED_PAGE_IDENTITY` · `--localized-page-identity` · LI-2 | `page_classifier.py` (`_LOCALIZED_DEGREE_WORDS`), `live_discovery.py` (`english_alternate` both directions), `ontology.json` (aliases, `related_not_equivalent` local forms), a `languages.json` country → languages table | stage 4(a). LX-1's `LEXICON_V2` entries move under this flag (§5 Q4) | 0 gain by itself on today's captures; it is the gate for R4 and R5. Offline: uba, ucph-da, iitd accepted; puc with the es alias; psaclay-fr with the fr degree word | 0 stable programme-page loss; 0 new wrong claims (the Imperial deadline cause from LX-1's run found or shown unrelated); offline tests on the eight saved pages | any new wrong claim; any stable loss |
| **R2** | **Subject title shapes** | `SUBJECT_TITLE_SHAPES` · `--subject-title-shapes` · ST-1 | `live_discovery.py` (`matches_field_text`, `_matches_field_text_localized`, `_LOCAL_TITLE_FILLER`) | stage 4(b); refusals on a related head are recorded as `related_programmes` on the trace (§5 Q6) | uio and kuleuven titles pass when reached; uct → related (wrong page −1); imperial math-CS → related | no stable loss; uct's wrong confirmation gone; 0 new wrong claims; M2 in | a development gold page refused on the new non-filler list |
| **R3** | **Sitemap keep on evidence sum** | `SITEMAP_KEEP_EVIDENCE_SUM` · `--sitemap-keep-evidence-sum` · SK-1 | `live_discovery.py` (`keep()`, `_select_candidates`) | stage 2(a) | um or uba +1 (gold URL now kept and read); vienna, psaclay-fr listed | +1 on um or uba, reads not above today's, no stable loss (18 Q3) | reads up with no gain; any stable loss |
| **R4** | **Local catalogue entry** | `LOCAL_CATALOGUE_ENTRY` · `--local-catalogue-entry` · LC-1 | `live_discovery.py` (`_navigation_fallback`, `_URL_SIGNALS`, `_CATALOGUE_PATH`, `SitemapReader`), `navigation.py` (`_SECTION_WORDS` per language), `catalog_walker.py` | stages 1, 2(b), 2(c) — one flag as decided (20 Q5) | puc listed through the carreras sitemap or the catalogue page; uio through "Studier" → "Finn studier"; kuleuven if the runner is ever unblocked | `kept_by_link_text` names the section link on puc and uio; no stable loss; 0 new wrong claims; reads per case not above today's | reads above today's on slow hosts; a "carreras"-type label leading to a non-catalogue that still costs a read on ≥ 3 cases |
| **R5** | **Local-language query family** | `LOCAL_LANGUAGE_QUERIES` · `--local-language-queries` · LQ-1 | `intent.py` (`queries_for`, `DiscoveryIntent.languages`), `retrieval.py` (`rank_candidates`), `prefilter.py`, `ontology.json` (`degrees.bachelor.localized_aliases`), `serper.py` only if shape (d) wins | stage 3; **conditional on M5**: built only if a shape returns the gold or twin in the top 10 on ≥ 4 of 6 cases; that shape is the family | uba, puc, uio titles carry the query words; kuleuven, tsinghua-cn, tec-es same shape | R1 on in both arms; `local_language` results read on ≥ 1 case; +1 stable programme page across dev2/dev3/dev4; no stable loss; 0 new wrong claims; `cases_over_budget` 0 | M5 finds no shape (then R5 does not exist and the slot stays `programmes`); a local master's page confirmed; any stable loss |
| **R6** | **Site identity v2** (parallel track — touches `catalogue/discovery.py` only) | `SITE_IDENTITY_V2` · `--site-identity-v2` on the `--through-identity-gate` arm · IG-1 | `backend/app/catalogue/discovery.py` (`_identify_site`, `_probe_site`), `importer.py` if a native name is kept (§5 Q8) | stage 0 | tsinghua, ntutw, utokyo, uio, ucph, uppsala pass through (iii) or (ii); tcd and iitd through (i) when the row carries the domain | identity established on every conclusive development homepage that passes by hand; 0 false identities; programme-page numbers on the arm within one case of the default arm | a false identity on any development or seed row sampled |
| then | development exit → [Acceptance protocol](../issues/21-heldout-acceptance-protocol.md) | — | — | R1–R6 default-on under their bars; every remaining readable development miss named with the reason v3 does not cover it (opaque URL, department host, SPA / PDF) (§5 Q9) | — | — | — |

---

## 4. What this plan will NOT do

- **No access bypass.** Robots unreachable, 403, Cloudflare, dropped connections → `unavailable`, by definition
  (01 Q5). Track E (another runner) is infrastructure, not this design.
- **No budget change** except tightening: 6 / 60 / 120 and every SB-1 constant stay; M0 adds the hard 60 cap.
- **No applicant word in a query, ever.** Language from the institution's country, words from the ontology.
- **No model page picker** in v3 (06). A later, priced, proposer-only experiment after the rules plateau on dev4.
- **No per-institution hardcode, no seeds for the nine, no entry tuned to a case.** Every lexicon is a
  dictionary translation of the same words, added for all languages at once (§5 Q5).
- **No browser tier.** SPA catalogues (tec) and PDF-only study plans (uba, utokyo) are `unresolved`, not guessed.
- **No second registrable domain** (DI-1 stays built, off, its own decision), **no department hosts the
  homepage never links** (kaist `cs.`, ntutw `csie.` stay with search), **no national registries** off-domain.
- **No provider change**; `hl`/`gl` only if the probe says so.
- **No change to the evidence stages** (routing, awards, extraction — STRUCTURAL Changes 2–3) and **no product
  payload change**: twins, `related_programmes` and `site_identity.proof` live on the trace and the benchmark
  `Observation`; surfacing them in the product is a later ticket.
- **No re-measure of SM-1 / SO-1** inside v3; whether a slow-host order is still needed after SB-1c is read
  off R3–R5's runs, then ticketed if it is.
- **No heldout look** until every rule above is default-on and ticket 21 says when.

---

## 5. Open choices for the owner

"Да" accepts the recommendation as written; "нет" or "обсудить" opens that point for a round of its own.

❓ **16-Q1** — **The 60-read cap lives in the pipeline (product), not only in the harness**: one counter per case
across discovery and the evidence stages, stop at 60, outcome `budget_exhausted`, what was confirmed is kept;
`cases_over_budget` must read 0 on every development set before any §3 run is read. The separate reads analysis
decides *where* the reads go, not *whether* the cap exists.

➡️ Yes. DoD target 5 is a product property; a harness-only cap would make the benchmark report a budget the
product does not keep, and every "reads not above today's" bar needs the floor first.

---

❓ **16-Q2** — **Landing order R1 → R2 → R3 → R4 → R5, R6 on its own arm in parallel; nothing before M0 and M2;
R5 only after M5.** Precision rules (R1, R2) before the recall rules that would feed them pages (R3–R5).

➡️ Yes. R4 and R5 reach local pages R1 must accept and R2 must sort; landing them first would turn each recall
run into a precision run as well.

---

❓ **16-Q3** — **The "read the English homepage once" step stays out of v3.** It appeared in ticket 16's sketch
(stage 1) and in [Language alternates](../issues/13-language-alternates.md) as an option; no decision covers
it. R4 reaches the local catalogue in the site's own words; the English homepage would reach the English
catalogue, whose twin M1 already records when a page is confirmed. It returns as a ticket only if, after R4, a
readable local-first development case still lists nothing.

➡️ Yes — out for now. One read is cheap, but it is a sixth rule competing for paired runs, and in production
branch (iii) of R6 already makes that read where it matters; reusing that page is a later free step.

---

❓ **16-Q4** — **LX-1 is absorbed by R1**: the `LEXICON_V2` entries (B.Tech, *licenciatura*, *grado en*,
bachelor compounds; *informatikk*, *datalogi*, *informàtica*, *ciencia de la computación*) move under
`LOCALIZED_PAGE_IDENTITY`, one flag, one paired run; `LEXICON_V2` is removed once R1 is on. R1 lands only with
the cause of LX-1's one new wrong claim (Imperial deadline 2026-04-28 / 2026-09-28) found or shown unrelated.

➡️ Yes. Two overlapping lexicon flags measured separately cannot be read; the wrong claim is the one thing
LX-1 taught and R1 must not repeat it.

---

❓ **16-Q5** — **Aliases and degree words for every language in the `languages.json` table are added in one
commit, dictionary-grade, each flagged until measured; the heldout countries' languages (cs, de, tr, et, it,
lt, kk) are in that same commit and are checked on dev4 only.** No alias is added or edited after a heldout look.

➡️ Yes. Adding them language by language as cases arrive is how a lexicon gets tuned to a case; one table, one
rule, checked on proxies, is the only honest route to target 6.

---

❓ **16-Q6** — **Related programme, in discovery**: when confirm refuses a page *only* on the subject-head rule
(R2) and the page is otherwise a programme page at the requested level, discovery records it as
`related_programmes` on the trace (public URL and title), and the scorer scores `related`; the product payload
does not change in v3.

➡️ Yes. The scorer needs the trace to say *why* a page was refused, or UCT and Imperial keep scoring as plain
misses; the product's wording for "a related programme exists" is a product decision for later.

---

❓ **16-Q7** — **Before dev4 is signed, R1–R4 may be built and paired-run on cohort/dev2/dev3 for *no loss*; a
rule goes default-on only after its dev4 run as well** (04 Q3). If dev4 is late, the loop waits rather than
turning a local-language rule on.

➡️ Yes. The three sets can show a loss; only dev4 can show the gain these rules exist for, and a default-on
decision without it would be a decision on faith.

---

❓ **16-Q8** — **Identity branch (ii) needs a native-script name the seed rows do not hold** (`importer.py` keeps
the English name and a parenthesised suffix; the rows carry `name`, `country`, `official_domain`,
`official_site`). Build (i), (iii), (iv) now; build (ii) so that it fires wherever a `native_name` exists,
and add the column as a data task (one line per row, from the institution's own homepage title, verified by
the Fetcher) only after R6's first run shows which rows (i) and (iii) leave behind.

➡️ Yes. 353 of 500 rows carry a domain, so (i) is the cheap proof; a 500-row data task before knowing the
residue would be spent on rows (i) already covers.

---

❓ **16-Q9** — **The development exit criterion** (what the loop reports before ticket 21 is opened): R1–R6
default-on under their bars; `cases_over_budget` 0 on every set; 0 wrong page on every set; and every
remaining readable development miss named with the v3 reason it is not covered (opaque URL, department host,
SPA / PDF, access). No recall number is pre-set here — the heldout expectation is ticket 21's.

➡️ Yes. A named residue is what ticket 21 needs to pre-register an expectation; a target number chosen now
would be chosen without dev4.
