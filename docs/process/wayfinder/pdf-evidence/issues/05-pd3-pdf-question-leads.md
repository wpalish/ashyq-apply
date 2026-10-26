# PD-3 `PDF_QUESTION_LEADS`: follow a question-named PDF link from a read page, at most two PDF reads per case

Type: task
Status: open
Blocked by: 02 (≥ 2 of the 7 gold PDFs one same-domain link away), 04 (a reached PDF must be readable first)
Map: ../map.md · AFK task behind one flag; the only ticket on this map that can move a known core question.

## Goal

None of the seven gold PDFs is fetched in any base2 repetition; the pipeline reaches the page that links them (or a
page one link away) and stops. Examples the captures and the hand-fetch show: utokyo's application guidelines
`/content/400291798.pdf` (the deadline) hang off the Japanese admissions pages; msu's `rules.pdf` / `minimum.pdf` hang
off `cpk.msu.ru` pages the funding and requirements stages never queue; usp's `PAPFE2026_EDITAL.pdf` hangs off
`prip.usp.br`; warsaw's regulation hangs off the English award page `bpm.uw.edu.pl/en/rectors-scholarship/` (read in
no repetition); tec's English regulation PDF hangs off `/es/profesional/becas`. The rule: when a page the run reads
for a question (programme, admissions, fees, award / funding index) links to a **same-registrable-domain PDF** whose
**anchor text or file name names the question or the document kind** — regulations / regulamin / reglamento /
regulamento / edital / 募集要項 (application guidelines) / положение / правила / fee structure / fee schedule / tuition
fees / scholarship(s) / stipendium / beca(s) / bolsa(s) / 奨学金 / deadlines / key dates / admission guidelines —
queue it as a question lead for that stage, **after** every HTML lead of the same stage, at most **two PDF leads per
case** (one per question family at most), charged like any read.

## Flag and loop id

`PDF_QUESTION_LEADS = False` in `app/adapters/pdf_evidence.py` (shares 04's module), harness `--pdf-question-leads`,
loop id **PD-3**. The anchor/file-name word table is one module-level tuple **for every language at once**, dictionary
grade, heldout-country languages (cs, de, tr, et, it, lt, kk) included as translations only (16-Q5 rule of the
discovery map; no heldout page is opened to pick a word).

## Where the hook goes

The link scan that already exists per stage — `web_requirements.queue_leads` / `queue_questions`,
`web_scholarships._funding_route_links`, the costs page's fee links — gets one extra predicate call
`pdf_evidence.pdf_lead(link_text, url, stage)` (≤ 3 lines per site), **after** C and D land. No change to
`live_discovery.is_excluded_path` (it keeps `.pdf` already) or to `retrieval.py`.

## Bar

One paired run per set. No new wrong claim; no stable loss; reads not above the off arm by more than 2 per case;
stable gain ≥ 1 core question on the sets whose gold PDFs 02 marked reachable (expected: tec `applicability.
international` via AP-1 on the English regulation — the one PDF question the deterministic readers can take; usp
`exists` only if the previous map's 08 lands per-language words; utokyo / msu / warsaw stay `pdf_non_english`). A PDF
lead that is read and yields nothing is logged `fetched-ok · PDF, no claim` — it counts as a read against the bar.

## Done when

- Offline tests: an admissions fixture page linking `guidelines-2027.pdf` («Application Guidelines») and
  `newsletter-03.pdf` queues the first and not the second; two fee PDFs and one scholarship PDF → at most two leads, one
  per family; a PDF on another registrable domain is never queued; flag off → byte-identical.
- Paired run recorded; default-on or rejected per the bar; HANDOFF §8 line.
- Offline guard: the predicate is pure; the fetch still goes through the stage's own `Fetcher` call.

## Evidence

Map Notes (none of the 7 reached); ticket 02's Table A (which are one link away, with the anchor text — the word
table is built from those anchors plus dictionary translations, never from a heldout page);
`NON_ENGLISH_EVIDENCE_2026-10-18.md` §1 rows 1, 3, 8, 13, 15–16 and §4 (word table to extend with document-kind words).
