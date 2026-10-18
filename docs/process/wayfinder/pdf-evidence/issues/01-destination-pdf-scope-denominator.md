# Confirm the destination, which PDFs count, and how PDF labels return to the target-4 denominator

Type: grilling
Status: open
Blocked by: —
Map: ../map.md · HITL — owner round. Tickets 02 and 03 start without waiting; 04/06 need only the *wording* of Q2
and Q4; 07 needs Q3 and Q6 signed; 09 opens only through Q7.

## Question

The owner's question is «как потом будем доставать ответы из pdf?». The previous map's 01-Q2 (owner: «Все да»)
put every PDF-sourced core label **outside** the target-4 denominator because "browser tier and PDFs are outside the
design". The code tells a different story: `Fetcher` already fetches PDFs (29 distinct PDF URLs across dev2/dev3/dev4
in base2, counted in the 60 reads), `pdf_to_text` already exists and is used by the requirements and costs stages,
and `verify_evidence.py` already checks a quote against a PDF. What is missing is small and nameable (per-page text
with provenance, a classification path that does not need an HTML title, the funding stage's text path, a reach
rule for a linked PDF) — but the **gain on today's labels is 0** because none of the seven gold PDFs is ever reached,
and 5 of the 7 need a model to read clause polarity. Which PDFs are in scope, under what rule do their labels count
again, and which parts of the route does the owner want built now versus held as an escalation?

❓ **Q1 — Destination as written on the map**: a measured, budget-safe route (find → fetch under the unchanged
`Fetcher` → per-page text with page number + verbatim quote → the same deterministic readers first → optional priced
model extractor), scanned PDFs `unavailable`, fee schedules scoped to the confirmed programme and population; done
when the scope and the re-entry rule are signed, each reader ticket has a paired-run verdict, and the PDF residue is
handed to the previous map's 16 by class.

➡️ **Yes.** It is the DoD's own sentence ("wherever the official site publishes the answer and lets us read it") applied
to a PDF the site publishes and `Fetcher` can read.

---

❓ **Q2 — Which PDFs count as "the site lets us read it"**: on the institution's own registrable domain (same rule as
pages); `Content-Type: application/pdf` or a `.pdf` path; ≤ 5 MB (today's `MAX_BYTES`, unchanged); a text layer on at
least one of the first 40 pages (`pdf_to_text`'s cap, unchanged); reached either as a provider result or as a link
from a page the run reads. Anything else — scanned, > 5 MB, > 40 pages for the fact's page, another domain — is
`unavailable` and leaves the denominator exactly as a refusing host does (01-Q3 of the previous map).

➡️ **Yes.** Every one of the seven gold PDFs passes the first three conditions (75–815 KB, text layers, own domain);
whether they pass the fourth is what ticket 02 measures.

---

❓ **Q3 — Re-entry rule for the DoD (dated entry, exact wording)**: «A known core label whose evidence is a PDF counts in
`core_known_readable` from the capture in which `PDF_EVIDENCE_READERS` (PD-1) is on by default, provided the PDF
meets Q2; a PDF the run could not reach in that repetition is `pdf_unreached` and stays in the denominator (like a
non-English page), a PDF without a text layer or over the caps is `unavailable` and leaves it.» Until PD-1 is
default-on, the scorecard keeps printing both numbers (with and without PDF labels) so the move is visible before it
is made.

➡️ **Yes.** Arithmetic: +7 labels in the denominator (6 after 02-Q7), +0 answered today → the readable rate falls by
≈ 6–8 pp the day they re-enter; each PDF question later answered is worth ≈ +1.6 pp. The alternative — keeping
PDFs out for good — makes target 4 blind to the one evidence shape that fee and scholarship regulations actually use
on dev3/dev4 sites, and the heldout countries' sites are expected to use it more, not less.

---

❓ **Q4 — Scanned PDFs**: no OCR tier in this map; a PDF whose first 40 pages have no text layer is reported
`unavailable` with the class `pdf_scanned` (page outcome `fetch-failed`, detail «PDF without a text layer»), never
a guess. (kaznu's fee PDF is the only scanned one gold names, and its label is already `unknown`.)

➡️ **Yes.** OCR is infrastructure like the browser tier (previous map 01 Q6); it also changes the cost shape per read.

---

❓ **Q5 — Cache-buster query parameters before the PII guard**: `?_t=1761184801` (um's international fee schedule, refused
4/4) and `?177667006` (ucph's study regulation) are refused as «long digit sequence (passport/ID/card)». Proposal:
canonicalise a link **before** it is queued — drop a query parameter whose *name* is a known cache-buster
(`_t`, `t`, `ts`, `v`, `ver`, `version`, `rev`, `timestamp`, `cache`, `cb`, `nocache`) **or** whose whole query is a bare
number, when the value is purely numeric and the URL path ends in `.pdf` or the link sits on the institution's own
domain; the guard's regex and its reach do not change (a digit sequence in any other position still refuses).
Flag `CACHE_BUSTER_CANONICAL` (PD-2), new module, one call at the queue.

➡️ **Yes.** It removes a parameter the server ignores; it does not teach the guard to accept a passport number. If
«нет», um's and ucph's PDFs stay `unavailable` with class `pdf_pii_guard` and are counted so in 10.

---

❓ **Q6 — Page provenance in the corpus**: gold `evidence[]` entries gain an optional `page` (1-based) beside `url` and
`excerpt`; `verify_evidence.py` checks the quote on that page's text when `page` is given (whole document otherwise,
as today); pipeline claims from a PDF carry `relevant_section = "p. N"`; the scorer compares values, not pages (a
page is for the human reviewer and the verifier). Existing PDF labels are back-filled with their page by ticket 07
from the hand-fetched copies, then signed by you with the next corpus round.

➡️ **Yes.** Without a page a 95-page regulation is "verified" by a substring search over 96 k characters — true but
unreviewable.

---

❓ **Q7 — The model extractor on PDF pages (D9)**: not built in this map. It opens either (a) now, as its own priced
experiment (ticket 09: one page at a time, ≤ 40 pages, the §6.3 excerpt validator, a new privacy-table row «official
page/PDF text + question schema», ≈ $0.006–0.02 per university at the smallest tier), or (b) only through the
previous map's 18 if target 4 is still short after the rules. Of the six PDF questions, ≤ 2 are reachable by rules
and 3–4 only by a model (clause polarity in Polish, Russian, Portuguese, Japanese).

➡️ **(b), not now.** Rules first; the number that justifies a model is written in 10 and read in 18. If you want the
experiment in parallel because the five non-English PDFs will not read any other way, answer «01-Q7 (a)» and 09
opens at once on the development sets only.

---

❓ **Q8 — Stopping rule for this map**: stop at 10 (PDF labels stay outside the denominator, residue by class) when
ticket 02 shows fewer than two of the seven gold PDFs are one same-domain link away from a page the run reads, or
when PD-1 or PD-3 fails its paired run twice on the same cause. Otherwise the map ends with 07's re-score.

➡️ **Yes.**

## Evidence

- `backend/app/adapters/fetching.py` `ALLOWED_CONTENT_TYPES` (L513), `MAX_BYTES` (L509), `_QUERY_DIGITS` (L863),
  `FetchResult.is_pdf` (L600), `tier_counts["pdf"]` (L1801); `extraction.pdf_to_text` (L77, `max_pages=40`);
  `web_requirements.py` L1175/L1196, `web_costs.py` L109/L124 (text yes, classification with `html=""`);
  `web_scholarships.py` L885 (`readable_text(html)` on PDF bytes); `claim_verifier.page_type_admits` (L490: `unknown`
  admits nothing); `scripts/verify_evidence.py` L212.
- Counts: map Notes; scripts `scratchpad/pdfmap/*.py` (read-only over gold and base2 captures; heldout excluded by name).
- Previous map 01-Q2 wording and the DoD change-log form (`SEARCH_DEFINITION_OF_DONE.md`).
