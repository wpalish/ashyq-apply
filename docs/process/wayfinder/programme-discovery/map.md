# Map — Programme-page discovery on unseen universities

Label: `wayfinder:map` · Tracker: local markdown (`issues/NN-<slug>.md`; `Type:`, `Status:`, `Blocked by:` lines)
· Charted 2026-10-18 by claude-opus-5 at the owner's request ("use the wayfinder skill to solve: for unseen
universities the programme page itself is not found"). Owner (Диас) answers every HITL ticket; agents only
recommend.

## Destination

An owner-approved **design for programme-page discovery v3** — the ordered, flagged rules, each with its
precision guard and the development-set case that motivates it, the measurement changes the loop needs
first, and the acceptance protocol for the next heldout check — such that DoD target 3 ("the programme page
is found on every readable site; a site that refuses us says *unavailable*, never a guess") and target 6
(heldout within 15 pp of the cohort) are credibly reachable without any rule tuned on the heldout nine.
The design is handed to the loop (`loop-engineering`, paired runs, owner approval per rule); this map does not
build it. *Draft — the owner confirms or redraws it in
[Confirm the destination and its boundaries](issues/01-destination.md).*

## Notes

- **Domain.** `backend/app/adapters/discovery/live_discovery.py` (stages: seeds → sitemaps → navigation →
  confirm → walker → search → identity recovery, under the SB-1 stage budget), `backend/app/adapters/search/*`
  (intent, prefilter, retrieval, serper), `backend/app/adapters/page_classifier.py` (the confirm predicate's
  authority), `backend/app/catalogue/discovery.py` (the production path for a university outside the
  19-entry registry: site identity → the same discovery with no seeds). Measurement:
  `backend/evaluation/research/{live.py,scorecard.py,metrics.py}`; captures under
  `scratchpad/runs/bundle5-*` (today's defaults); gold `evaluation/research/data/{ground_truth.reviewed10,
  dev2.draft1,dev3.draft1}.json`.
- **Skills every session consults.** `grilling` + `domain-modeling` for every HITL ticket (owner answers; the
  agent writes numbered questions with a recommended answer and waits); `research` for AFK tickets;
  `loop-engineering` is *not* run from this map — it runs the design once the way is clear.
- **Standing rules (brief §7.4, AGENTS §6, DoD).** No robots bypass, no UA spoofing, no proxies; no applicant
  attribute in any query; 6 queries / 60 reads / 120 s per university; nothing sent to an LLM beyond the
  privacy table; Fetcher is never weakened. These are not decisions on this map.
- **Evidence policy.** The heldout nine (`nu metu sabanci charles masaryk tum tartu polimi vilnius`) are a
  validation split: no ticket opens their gold, drafts, captures, logs or per-case scorecard rows. Only the
  public facts that they sit in Kazakhstan, Turkey ×2, Czechia ×2, Germany, Estonia, Italy and Lithuania
  inform the plan. Design evidence comes from the three development sets (cohort, dev2, dev3) and from code.
  `docs/process/DISCOVERY_ANALYSIS_2026-10-17.md` was written from heldout traces at stage level; its
  mechanism claims are used here only where a development case or the code shows the same mechanism.
- **Committed analyses the tickets cite.** `docs/process/PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md` (per-case
  funnel against gold, local-language pages, the proposed changes LI-2 / LQ-1 / LC-1, `scratchpad/pd_tools/`)
  and `docs/process/STRUCTURAL_ANALYSIS_2026-10-18.md` (stage clock, evidence stages). Tickets cite them and
  do not repeat the per-case funnel.
- **Landed (a5d9d2a cherry-picked) outside this map (2026-10-18).** The fix for defect D1 — early search refused while *unconfirmed*
  sitemap leads fill the slots, then never retried
  ([Queries, provider parameters and the search-skip defect](issues/11-queries-and-search-skip.md)) — is being
  implemented as a bug fix under the paired-run protocol. Tickets assume it lands; nothing here decides it.
- **Tracker conventions.** A session claims a ticket by setting `Status: claimed` before any work; resolves by
  appending `## Answer`, setting `Status: resolved`, and adding one gist line below. HITL tickets stay `open`
  until the owner answers through the orchestrator. The owner brief is `OWNER_QUESTIONS.md` beside this map
  (Russian; round 1 is [Confirm the destination and its boundaries](issues/01-destination.md)).

## Decisions so far

<!-- one line per closed ticket: gist, then the link holds the detail -->

- [Confirm the destination and its boundaries](issues/01-destination.md): owner, yes to all six — a design for the loop; production path incl. identity gate; DoD 3 & 6 for the programme page only; heldout quarantine absolute; access/budget/provider/seeds/browser tier out of scope.
- [Where the programme page is lost today on the development sets](issues/08-loss-stages-today.md): on the 35
  development cases under today's defaults, 17 programme pages are confirmed (5 wrong or disputed); the 18
  misses split into access-blocked (7), local-language-only pages never returned by English keyword queries
  (6), classifier/subject refusals of a page that was read (3), and a stage-order defect (1). The two killed
  cases (ubc, imperial) had already confirmed a page; the clock went to the evidence stages.
- [URL lexicon audit against every development gold programme URL](issues/09-url-lexicon-audit.md): the
  sitemap `keep()` rule keeps 20 of 39 gold URLs; 7 of the 19 it drops name the subject (and 6 of them the
  level) in the slug but carry no structural programme word, and are discarded before that evidence is
  counted (uba, um ×4, vienna, psaclay-fr). Opaque URLs (kaist, kuleuven, tsinghua, ub, auckland plan) score
  zero by construction. The dormant LX-1 lexicon adds puc, uio, ucph-da.
- [Classifier audit on hand-fetched development gold pages](issues/10-classifier-audit.md): 10 of 20 testable
  gold pages are accepted by today's confirm predicate; the refusals are three lexicon gaps LX-1 already
  closes (iitd B.Tech, uba/puc *licenciatura*), three subject-title shapes no flag handles (uio subtitle,
  kuleuven location + "Studieprogramma", puc *ingeniería en*), one structural label (Auckland's BSc page
  names no major), and two pages whose identity is not in the text (kaist Korean title, ub timetable).
- [Queries, provider parameters and the search-skip defect](issues/11-queries-and-search-skip.md): discovery
  sends six English operator queries (`site:` + quoted field + quoted level) and Serper is given no language
  or country parameter; there is no local-language family and QA-1 (aliases) is off. **Defect confirmed:**
  when the SB-1b 33-second rule fires search while three *unconfirmed* sitemap picks fill the programme
  slots, search returns "slots already filled", is marked attempted, and never runs again after confirm
  empties the slots (uio, both repetitions, 0 queries). Fix belongs to the loop (in flight 2026-10-18); no
  decision needed.
- [Production site-identity gate on development homepages](issues/12-identity-gate-offline.md): the
  production rule for a university outside the registry (homepage title or h1 must contain the English seed
  name, or an acronym equal to the host label) fails offline on 8 of 15 conclusive development homepages
  (tsinghua, ntutw, utokyo, uio, ucph, uppsala, iitd, tcd), so in the product those universities never enter
  discovery at all. The benchmark bypasses the gate (`live.dev2_entry`), so none of the loop's numbers
  measure it.
- [Language alternates: page-level hreflang vs sitemaps](issues/13-language-alternates.md): none of the
  nine saved development sitemaps carries `xhtml:link` alternates; the page-level `<link rel=alternate
  hreflang>` is the only twin source, it is followed local→English only, only on a read whose `<html lang>`
  is not English, and the twin is never recorded for the scorer.
- [Measurement gaps that hide discovery outcomes](issues/14-measurement-gaps.md): the trace records
  rejections and reads but not the provider's result lists, so "never seen" cannot be split into "not
  returned" and "returned, not read"; a capture killed at 115 s writes no trace; the scorer matches canonical
  URLs only (query kept, trailing slash dropped), so twins and `/2027/` variants are misses unless the gold
  lists them.

## Not yet specified

<!-- in-scope fog: questions coming, not yet sharp enough to ticket -->

- **Stage order on slow hosts after the search-skip fix.** SO-1 (search first when reads are slow) and SM-1
  (programme sitemaps first) were measured "no effect" before SB-1 and before the defect above was known;
  whether either is still needed once search cannot be skipped is unknown until the fix is measured.
- **Opaque-URL sites.** When URLs say nothing (`content?menu=188`, `UKEN-556.html`, `info/1303/4316.htm`,
  `plan?p7_code=`), only link text and page identity can lead; the walker and navigation fallback treat
  short labels as noise (`short_label` on 120 KAIST links). What a link-text-first route looks like, and
  on which hosts it may start (department sites, admission systems), is not yet specifiable.
- **Department hosts the homepage never links.** On kaist (`cs.`) and ntutw (`csie.`) the programme lives on a
  host no read page links, so search is the only route there today. (Catalogue hosts the homepage *does* link
  in its own words — `admision.`, `onderwijsaanbod.`, `ingresantes.exactas.` — graduated to
  [Local catalogue entry: section labels and the catalogue host's sitemap](issues/20-local-catalogue-entry.md);
  another registrable domain stays DI-1's case.) Whether a bounded "department host" step exists at all waits
  on the dev4 proxies.
- **Scorer equivalence implementation** (twins, canonical variants, the related-programme outcome): a task once
  [What counts as the programme page found](issues/03-programme-identity-equivalence.md) is answered — its
  shape (two outcomes or three) *is* that answer. Twin recording itself is already in
  [Record provider results and persist the trace at checkpoints](issues/17-record-provider-results.md).

Graduated on 2026-10-18: the browser-tier question → [Confirm the destination](issues/01-destination.md) Q6;
the heldout acceptance protocol → [Acceptance protocol for the next heldout check](issues/21-heldout-acceptance-protocol.md).

## Out of scope

<!-- ruled beyond the destination; never graduates -->

- **Sites that refuse the measurement network** — robots.txt unreachable (aalto, kaznu, hku/kaist admission
  hosts), HTTP 403 (toronto), Cloudflare challenge (ub), dropped connections (kuleuven). No bypass; they are
  DoD target 3's "unavailable" by definition. Only Track E (a Fly runner, `SEARCH_FINISH_PLAN_V2.md`) changes
  the denominator, and that is infrastructure, not discovery.
- **The per-university budget** (6 queries / 60 reads / 120 s) and the production 300 s enrichment limit.
- **The evidence stages** (question routing, award route, extraction) — STRUCTURAL_ANALYSIS Changes 2–3;
  they start where this map ends (a confirmed programme page).
- **Registry seeds for the heldout nine** or any per-institution hardcode: a seed is a human-verified fact
  for the 19, never a discovery rule.
- **Choosing a different search provider.** Cycle 1 showed Serper vs Exa moves the failure mode, not the
  count; the design must work on a keyword engine.
