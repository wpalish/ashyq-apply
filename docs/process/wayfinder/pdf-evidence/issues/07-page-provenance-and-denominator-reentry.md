# Page-aware verification, `page` in gold evidence, and PDF labels back in `core_known_readable`

Type: task
Status: open
Blocked by: 01 (Q3, Q6), 04 (PD-1 default-on, or its rejection — the re-entry wording depends on which), (previous map 03 landed — `scorecard.py` is held until then)
Map: ../map.md · AFK task, measurement only; no pipeline behaviour; one re-score of frozen captures, no run.

## Goal

Make the PDF route visible in the Definition of Done without a run: (1) `backend/scripts/verify_evidence.py` checks a
gold quote on the **page** the evidence names when `page` is present (today: whole-document `pdf_to_text`); (2) the
corpus evidence schema gains optional `page` (1-based) and the seven PDF labels are back-filled from the hand-fetched
copies' page texts (`scratchpad/non_english_pages/<sha1[:10]>.txt`, tec's from CI) for the owner to sign with the next
corpus round; (3) `core_known_readable` applies 01-Q3's wording: a PDF label counts from the capture in which PD-1 is
default-on, provided the PDF meets 01-Q2; `pdf_unreached` stays in the denominator, `pdf_scanned` / `pdf_too_large`
leave it; both numbers are printed until the DoD entry is dated.

## Files

`backend/scripts/verify_evidence.py` (page branch; uses 03's `read_pdf` + `page_of`), `backend/evaluation/research/
scorecard.py` **after the previous map's 03 lands** (the `readable` denominator's PDF predicate — a few lines; if 03 put
the predicate in a helper module, edit that instead), a schema note in `backend/evaluation/research/data/README` or
the corpus doc that defines `evidence[]`, the DoD change-log line (text proposed here, dated by the owner), and
`docs/process/SIGN_<set>_…` rows for the seven back-filled pages (not the gold JSON itself — those files are a worker's).

## Done when

- `verify_evidence.py --page-aware` (default on when `page` is present): the seven PDF labels verify on exactly one
  page each, listed as `url · page · quote found`; a quote that verifies on two pages is reported `ambiguous_page`, on
  none `not_found` (the row stays `unknown`).
- Scorecard prints, per set and pooled, `core_known_readable` with and without PDF labels; the delta on base2 is the
  predicted −7 labels (−6 after 02-Q7) in the denominator, +0 answered; after PD-1 and PD-3 captures exist, the same
  rows from those.
- DoD change-log entry proposed verbatim (01-Q3's sentence) in a docs commit for the owner to date; nothing in the
  DoD edited before that.
- Offline guard: the scorer change is a pure predicate over the frozen capture (`evidence URL ends in .pdf` or the
  capture's page outcome says PDF) — no fetch.

## Evidence

`verify_evidence.py` L130–147 (`quote_in`), L212–219 (PDF branch); `expert/models.py` L523–530 (page-exact quote check
to mirror); previous map's 01-Q2 wording and its 03 (scorecard rows); `scratchpad/pdfmap/labels_pdf.json` (the seven
rows with their URLs and values).
