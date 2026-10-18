# CI facts for the 36 PDFs: text layer, size, pages, parse time, and how far each gold PDF is from a read page

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK research, runs now; disjoint from every worker. Output:
`docs/process/PDF_EVIDENCE_FACTS_<date>.md` (and a JSON beside it under `backend/evaluation/research/runs/`).

## Question

The sandbox cannot import `pypdf` (its `cryptography` binding panics) and cannot reach `tec.mx`, so the map's facts
about the PDFs are from byte-level probes and the hand-fetched copies. For the **7 gold PDFs** (map Notes) and the
**29 PDFs the pipeline met** in base2 (`scratchpad/pdfmap/captures_pdf.json`), measured once in CI through the
production `Fetcher` (robots honoured, production UA, no retries): does the PDF have a text layer, how many pages
and bytes, how long does `pypdf` take per page and for the first 40 pages, does the gold quote verify on exactly one
page (`is_verbatim_excerpt` per page — which page), and — the fact 01-Q8 hangs on — **is the gold PDF linked
(anchor text, link position) from a page the run already reads in any base2 repetition of that case**, or from a page
one same-domain link away from one?

## Done when

- Table A (gold PDFs, 7 rows): case · label key · URL · bytes · pages · text layer (yes / no / partial) · pypdf ms
  (per page, first 40) · quote found on page N (exactly one page? more?) · linked from `<read page URL>` with anchor
  `<text>` / one link away via `<page>` / not linked from any read page.
- Table B (met PDFs, 29 rows): case · URL · stage that fetched it (funding / requirements / costs / discovery) ·
  outcome today · bytes · pages · text layer · what the first page's title and headings say (as 03's IR would read
  them) · which core question, if any, its text answers for the confirmed programme (value + page) · whether gold
  already has that question `known` (then why unmatched) or `unknown` (the corpus year convention, or not labelled).
- A one-line verdict for 01-Q8 and ticket 05: how many of the 7 are **one same-domain link away** from a page the
  run reads (≥ 2 opens 05; < 2 is a stop).
- Parse-time line for 03's cap: p95 of per-PDF parse ms at 40 pages; the largest file (usp `res.pdf`-like, 2.9 MB /
  95 pages, if met) as the worst case.
- No heldout host is fetched or named.

## Files

Read-only: gold files, `scratchpad/runs/base2-*/x/*/*/*.{json,log}`, `scratchpad/pdfmap/*.json`,
`scratchpad/non_english_pages/*.pdf` (text already extracted beside each as `.txt`). Writes the analysis file and a
small CI script under `backend/evaluation/research/` (new file; no production import changes). The CI job is one
`workflow_dispatch` of the existing capture workflow in a probe mode or a one-off script run — no paired run.

## Evidence

Map Notes (counts and the code lines); `NON_ENGLISH_EVIDENCE_2026-10-18.md` §1 rows 1, 3, 8, 11, 13, 15–16 (the
hand-fetch method and the quotes); `expert/controller.py` L858–890 (per-page extraction pattern to reuse);
`test_expert_pdf_view.py` (scanned/malformed/40-page behaviour already specified on the evaluation side).
