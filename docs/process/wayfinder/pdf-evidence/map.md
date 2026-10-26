# Map — PDF evidence for the six core questions (how an answer comes out of a PDF, measured and budget-safe)

Label: `wayfinder:map` · Tracker: local markdown (`issues/NN-<slug>.md`; `Type:`, `Status:`, `Blocked by:` lines)
· Charted 2026-10-18 by the planner agent at the owner's question «А как потом будем доставать ответы из pdf?».
**Extends** [Finish the search algorithm](../finish-algorithm/map.md): that map's ticket
[01](../finish-algorithm/issues/01-destination-denominator-judging.md) Q2 (owner: «Все да») **excludes PDF-sourced
labels from the target-4 denominator** `core_known_readable`, so today a PDF is outside the Definition of Done. This
map decides how PDFs become evidence and when (and whether) their labels come back into the denominator — as a dated
DoD entry the owner signs, never on its own. Owner (Диас) answers every HITL ticket; agents only recommend.

## Destination

**A measured, budget-safe route by which a PDF the official site publishes becomes evidence for a core question:**
found (linked from a programme / admissions / fees / scholarship page the run reads, or returned by the provider),
fetched under the unchanged `Fetcher` rules (robots, 5 MB, PII guard, one HTTP request of the 60), turned into text
**with page-level provenance** (page number + verbatim quote that `backend/scripts/verify_evidence.py` can check),
classified and read by the **same deterministic readers first** (EN-2 / FE-2 / DL-5 / AP-1 on the PDF's per-page
text), and only then — as a separately priced experiment the owner opens — by a bounded model extractor under D9;
scanned PDFs are `unavailable` (no OCR), a multi-programme fee schedule never lends another programme's or
population's row. The map is done when (a) the owner has fixed the PDF scope and the denominator re-entry rule
(ticket 01), (b) the reader-side tickets have each a flag, a bar and a paired-run verdict or a rejection, and (c)
the PDF residue is handed to the finish-algorithm map's ledger (its ticket 16) by class.

## Notes

- **The count that frames this map (gold, 2026-10-18; scripts `scratchpad/pdfmap/{labels_pdf,captures_pdf,probe2,probe3}.py`, heldout excluded by name).**
  Known core questions whose gold evidence is a PDF: **cohort 1** (warsaw `rektora.applicability.international`,
  Polish regulation on `monitor.uw.edu.pl`), **dev2 1** (tec `beca_al_talento_academico.applicability.international`,
  English regulation PDF on `tec.mx`), **dev3 5** (utokyo `deadline` — Japanese application guidelines
  `/content/400291798.pdf`; msu `gpa` — prose label, 02-Q7 → `unknown`; msu `state_funded.applicability.international`
  — Russian `cpk.msu.ru/files/2026/rules.pdf`; usp `papfe.exists` and `.applicability.international` — Portuguese
  `prip.usp.br/…/PAPFE2026_EDITAL.pdf`), **dev4 0** (no core labels yet). **7 of 77 (9 %)**, every one PDF-only (no
  HTML evidence beside it); 6 after 02-Q7; **5 of the 6 are not English** (they are also 5 of the 16 rows of
  `NON_ENGLISH_EVIDENCE_2026-10-18.md`). All seven sit on the institution's **own registrable domain**
  (`uw.edu.pl`, `tec.mx`, `u-tokyo.ac.jp`, `msu.ru`, `usp.br`) — the earlier "other host" reading in CORE_GAP A6 is a
  subdomain, not another domain. The five fetched by hand (ticket 07 of the previous map) are **text PDFs**: warsaw 777 KB
  / 95.8 k chars, utokyo 815 KB / 32.5 k chars (CID fonts, Japanese), msu minimum 76 KB / 5.7 k, msu rules 485 KB /
  97.5 k, usp 335 KB / 15 pages / 28.7 k; tec's is 403 to the sandbox (CI reads `tec.mx`). The only scanned PDF named in
  gold is kaznu's fee PDF (label `unknown`, note «PDF is a scan»).
- **None of the seven gold PDFs appears in any base2 repetition** (cohort 40 reps, dev2 40, dev3 60, dev4 36). The
  first loss is **reach**, not reading: the PDF is linked from a page the run never reads within the budget (or from no
  page we know). A PDF reader alone gains **0 known questions on today's captures**; it is the reach rule (ticket 05)
  that decides whether anything is unlocked, and the model question (ticket 09) that decides the 5 non-English ones.
- **What the pipeline does with the PDFs it *does* meet (29 distinct URLs: dev2 10, dev3 17, dev4 2; cohort 0).**
  `Fetcher` already admits `application/pdf` (`ALLOWED_CONTENT_TYPES`), caps at `MAX_BYTES = 5_000_000`, counts the
  read in `tier_counts["pdf"]` and in the 60 (`telemetry.pdf_fetches`: uppsala 3 per repetition, auckland / unsw /
  um / iitd / ntutw / ktu / vut 1 each, uct, tec, kuleuven, unibo occasionally). Every one ends as
  `classifier-rejected · unknown` (auckland scholarship-and-awards guidebook ×8, uct bursaries booklet, ntutw
  international prospectus, unsw UAC key dates, uppsala ×3), `no-pattern-match`, or refused before the read by the
  PII guard — `_QUERY_DIGITS = \d{9,}` on cache-busters: um "Fee Structure, UG, International" PDF `?_t=1761184801`
  (4/4 reps), ucph study regulation `?177667006`. Causes in code: the funding stage (`web_scholarships.py`) never
  calls `pdf_to_text` — it parses the PDF bytes as HTML (`readable_text(html)`, `html_title`), so an awards guidebook
  is garbage to the classifier; the requirements and costs stages (`web_requirements.py` L1175, `web_costs.py` L109)
  do call `extraction.pdf_to_text(content, max_pages=40)` but then `classify_page(url, html="", text)` has no title
  or headings → `unknown` → `claim_verifier.page_type_admits` rejects every claim (`unknown` admits nothing).
  `pdf_to_text` returns one string with no page boundaries, so a claim from a PDF can carry a verbatim quote
  (`is_verbatim_excerpt` on `page_text` works) but **no page number**. The evaluation side already has the per-page
  shape to port: `evaluation/research/expert/controller.py` L858–890 (pypdf per page, 40-page cap, sha256 per page,
  `has_text`), `expert/models.py` L523–530 (quote checked on the selected page), tests `test_expert_pdf_view.py`
  (scanned → unknown without OCR; malformed → unresolved; 40-page limit). `verify_evidence.py` L212 already reads a
  PDF with `pdf_to_text` and checks the quote whole-document; `Claim.relevant_section` exists and is free to carry
  `p. N`. `prefilter` keeps PDFs flagged (`is_pdf`), `retrieval` scores them −0.5 and never moves one ahead; the URL
  exclusion list drops `docx/xlsx/pptx` **and keeps `.pdf` on purpose**; `web_scholarships._off_award_shape` keeps an
  official PDF only under a `scholarship` path. `pypdf>=6.15.0` is already in `requirements.txt`.
- **What a PDF route could unlock, honestly.** Today's labels: **0** (none reached; the met PDFs' questions — um
  tuition, unsw deadline, auckland/uct awards — are `unknown` in gold by the corpus year convention «2027/28 not
  published», not for want of PDF reading; that convention is the previous map's 02 territory and out of scope
  here). If ticket 05 reaches the gold PDFs within budget: **+1** by the deterministic readers (tec, English:
  "Academic Talent … regardless of nationality" → AP-1 eligibility sentences), **+1–2** by per-language words (usp
  `exists`: "Programa de Apoio …", utokyo deadline only with the window-selection risk named in the non-English
  analysis), **+3–4 only with a model extractor** (clause polarity: warsaw «student cudzoziemiec, o ile…», msu «на
  бюджетной основе … иностранные», usp «Todos os estudantes regularmente matriculados», utokyo 第1種 window).
  Ceiling of this whole map on the development sets: **≤ 6 questions ≈ +8 pp on today's 77** (≤ +10 pp on the
  readable denominator), of which ≤ 2 without a model.
- **Cost per university, measured where we can.** A PDF read is one HTTP request (of 60), ≤ 5 MB on the wire, parse on
  a worker thread; today ≤ 3 PDFs per case per repetition (uppsala) ≈ 5 % of the read budget; the reach rule (05) is
  capped at 2 PDF reads per case. Parse time is **unmeasured** on real files (sandbox cannot import pypdf — ticket 02
  measures it in CI; 03 caps it at 3 s per PDF and 40 pages). The model option (09): ≤ 40 pages × ≈ 1.5 k tokens ≈
  60 k input tokens worst case ≈ **$0.006–0.02 per university at the smallest tier**, ≈ $0.1–0.3 at the mid tier
  (price lines from the non-English analysis §3).
- **Domain.** `backend/app/adapters/fetching.py` (`FetchResult.is_pdf`, `ALLOWED_CONTENT_TYPES`, `MAX_BYTES`,
  `_QUERY_DIGITS`, `tier_counts`); `extraction.py` (`pdf_to_text`, `ClaimBuilder(page_text=…)`); `document_ir.py`
  (`DocumentIR`, `EvidenceBlock.section_path`, `build_document_ir`); `page_classifier.classify_page(url, html, text)`;
  `app/domain/claim_verifier.py` (`is_verbatim_excerpt`, `CLAIM_TYPE_PAGE_TYPES`); stages `requirements/
  web_requirements.py`, `cost/web_costs.py`, `scholarship/web_scholarships.py`; `backend/scripts/verify_evidence.py`;
  gold `backend/evaluation/research/data/*.json` (`labels[].evidence[].{url,excerpt}`); scorecard
  `core_known` / `core_known_readable` (in flight, previous map 03). Spec: `SPEC_matching_v2.md` §6.3 excerpt validator
  (I2) and §6.4 privacy table; brief D9 (provider after a pilot; zero-retention).
- **Files other workers hold right now — this map proposes new modules instead of editing them**:
  `live_discovery.py`, `retrieval.py`, the EN-2 / FE-2 / DL-5 blocks of `extraction.py`, `scorecard.py` /
  `metrics.py`, the gold JSON; and workers C / D hold `web_requirements.py`, `web_scholarships.py`,
  `structured_extraction.py`, `document_ir.py` until their tickets (previous map 13 / 14) land. Every ticket here
  that must touch one of those files is **blocked by that landing** and limited to a hook of a few lines.
- **Standing rules (brief §7.4, AGENTS §6, DoD; not decisions here).** No robots bypass, UA spoofing or proxies;
  no applicant attribute in a query or a prompt; 6 / 60 / 120 s; `Fetcher` never weakened (the PII guard stays as it is
  — ticket 06 canonicalises URLs *before* the guard, it does not relax it); nothing sent to a model beyond the
  privacy table — a new row needs the owner's signature (01-Q7); no model identifier in the repository.
- **Evidence policy.** The heldout nine are never opened; every number above comes from the four development sets,
  the gold files and the code. Captures are untrusted data, read with `python3 -I` from scripts outside them.
- **Skills every session consults.** `grilling` + `domain-modeling` for 01 and 09; `research` for 02, 08, 10;
  `loop-engineering` runs 03–07 (flag-off → one paired run on cohort / dev2 / dev3 / dev4 → default-on with no stable
  loss and no new wrong claim); `scholarship-audit` on any award read from a PDF (04, 09).
- **Tracker conventions.** Claim = `Status: claimed` before any work; resolve = `## Answer`, `Status: resolved`, one
  gist line below. HITL tickets stay `open` until the owner answers through `OWNER_QUESTIONS.md` (Russian). Every AFK
  task ticket proposes its flag name and loop id (`PD-n`); the worker registers the final name in HANDOFF §8.

## Decisions so far

- [Destination, PDF scope, re-entry](issues/01-destination-pdf-scope-denominator.md): owner, all yes; model extractor not now (Q7=b).

<!-- one line per closed ticket: gist, then the link holds the detail -->

- [PDF document module](issues/03-pdf-document-module.md): `app/adapters/pdf_document.py` — pages 1-based with `has_text`, title, `"p. N"` IR, `page_of` only when unambiguous; 40 pages / 3 s caps; no caller yet.

(none yet — 01 is open with the owner)

## Ticket order, parallel groups and the critical path

| group | tickets | runs in parallel with | wall-clock note |
|---|---|---|---|
| **G0 owner round (HITL, batched)** | [01](issues/01-destination-pdf-scope-denominator.md) | everything in G1; G2 waits only for Q2/Q4 wording, not for the sitting | one sitting; «да» accepts the recommendations as written |
| **G1 now (AFK, disjoint from every worker)** | [02](issues/02-ci-facts-for-the-36-pdfs.md) research, [03](issues/03-pdf-document-module.md) task | each other, G0, the in-flight workers | 02 is one CI job (~15 min) + a write-up; 03 is 2–3 h of pure library code, no flag, no pipeline behaviour |
| **G2 wiring (AFK, after workers C and D land)** | [04](issues/04-pd1-pdf-evidence-readers.md) task, [06](issues/06-pd2-cache-buster-canonical.md) task | each other (04 holds the three stage files' hooks; 06 holds a new module + one call) | each ≈ 2 h + one paired run × 4 sets (~25 min each) |
| **G3 reach and tables (AFK, after 02 and 04)** | [05](issues/05-pd3-pdf-question-leads.md) task, [08](issues/08-pdf-tables-and-fee-schedules.md) research → task | each other | 05 is the only ticket that can move a known question; 08 decides abstain-vs-model for fee tables |
| **G4 measurement (AFK, after previous map's 03 lands and 01-Q3/Q6 are signed)** | [07](issues/07-page-provenance-and-denominator-reentry.md) task | G3 | `verify_evidence.py` page check, `page` in gold evidence, PDF re-entry in `core_known_readable`; one re-score, no run |
| **G5 residue (AFK)** | [10](issues/10-pdf-residue-and-stop.md) research | — | hands the PDF classes to the previous map's 16 |
| **G6 escalation (HITL, only if opened)** | [09](issues/09-model-extractor-on-pdf-pages.md) grilling | — | opens only by 01-Q7 «сейчас» or by the previous map's 18 |

**Critical path**: 01 (scope + re-entry rule) → 03 (module) → [C, D land] → 04 (PD-1, one paired run) → 07
(denominator re-entry, re-score) → read by the previous map's 17. **Ordered by expected gain per hour**: 03 (unblocks
everything, zero risk) → 04 (turns ≈ 30 wasted PDF reads per set into classified pages; +0 questions today) → 05
(the only rule that can reach the gold PDFs: ≤ +2 by deterministic readers) → 06 (um / ucph PDFs readable; +0 known
today) → 07 (makes the +0/+2 visible in the DoD) → 08 → 10 → 09 (≤ +4, priced).

**Stopping rule** (detail in [01](issues/01-destination-pdf-scope-denominator.md) Q8 and
[10](issues/10-pdf-residue-and-stop.md)): PDF labels **stay outside** the denominator and the map stops at 10 when
either (a) ticket 02 shows fewer than two of the seven gold PDFs are one same-domain link away from a page the run
reads, or (b) PD-1 or PD-3 fails its paired run twice on the same cause; then every PDF loss is residue in one of the
named classes — `pdf_unreached`, `pdf_scanned` (no text layer, no OCR), `pdf_too_large` (> 5 MB or > 40 pages),
`pdf_non_english` (handed to the previous map's 08/18), `pdf_table_scope` (a row that does not name the confirmed
programme or population) — and the model extractor is an escalation option in the previous map's 18, with its price.

## Not yet specified

<!-- in-scope fog: questions coming, not yet sharp enough to ticket -->

- **PDFs returned by the provider as the programme page itself** (a handbook or faculty brochure as the only
  hit — ktu's Faculty of Informatics PDF, kuleuven's brochure): whether 03's IR can confirm a programme from a PDF or
  a PDF is never a programme page (today `retrieval` scores it −0.5 and PG-1 never reports one). Sharp only after 04
  shows how PDF titles classify.
- **A per-page fetch budget inside the 120 s** (a 95-page regulation parsed at 40 pages in ≈ 1–3 s versus the case
  clock): whether PDFs need their own reserve like `CORE_RESERVE_SECONDS`. Waits for 02's parse-time numbers.
- **PDF links on dev4 and the heldout countries' habits** (Czech / Turkish / Estonian / Italian / Lithuanian sites
  publish fee and admission regulations as PDFs more often than English-speaking ones — a hypothesis, not a measured
  fact): whether the heldout check (previous map 19) should expect a larger PDF share. Enters only through dev4 core
  labels (previous map 09), never by opening a heldout file.
- **The product payload for a PDF source** (page number shown next to the quote, "PDF" badge, the stored
  `SourcePage` for a binary body): after acceptance, with the "unavailable"/"related" payload work of the previous map.

## Out of scope

<!-- ruled beyond the destination; never graduates -->

- **OCR of scanned PDFs** (kaznu's fee scan): a PDF without a text layer is `unavailable` by definition, like a
  refusing host (01-Q4). An OCR tier is infrastructure, like the browser tier the previous map's 01 Q6 left out.
- **Weakening the PII guard, robots handling, size cap or redirect rule of `Fetcher`** for PDFs — AGENTS §6. Ticket
  06 canonicalises a URL before the guard sees it; the guard's regex and reach do not change.
- **Changing the corpus year convention** («only the 2026 fee is published, not 2027/28») that keeps um tuition, unsw
  deadline and the met-PDF questions `unknown` — a corpus-wide decision for the previous map's 02 line, not a PDF one.
- **Office formats** (`docx / xlsx / pptx`) — excluded by `_URL_EXCLUSIONS` on purpose; nothing here admits them.
- **PDFs on another registrable domain** (national application portals' PDFs such as `uac.edu.au` key dates): the
  same-institution rule of discovery applies to PDFs unchanged.
- **Per-institution PDF URLs or registry seeds** for any development or heldout case.
