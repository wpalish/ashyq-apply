# How many target-4 questions sit behind a non-English evidence page, and what the cheapest route is

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK research — the fact ticket 08's decision waits on. Output:
`docs/process/NON_ENGLISH_EVIDENCE_2026-10-18.md`.

## Question

Every development programme page confirmed before R1/R5 was an English page, and every reader in the evidence
stage (`extraction.py`, `structured_extraction.py`, `web_requirements.py` question links, `web_scholarships.py`
award names) is English-only: "deadline", "tuition", "IELTS", "scholarship". After R5 the pipeline confirms local
pages (uba, puc, ucph-da, uio, kit/ktu/rwth on dev4) — and the six core questions on those pages are then read
in Spanish, Danish, Norwegian, German, Lithuanian. Across cohort/dev2/dev3 (and dev4 once 09 labels it, and the
12 unadjudicated cases once 10 signs them), **how many known core questions have their gold evidence on a page
whose `<html lang>` is not English** (A6 "local language" in CORE_GAP: warsaw PDF, uba beca, puc deadline, tec,
kaznu, msu, usp, utokyo), does that page declare an English `hreflang` twin that carries the same fact, and for
the ones that do not: which of the three routes below reaches them cheapest?

(i) **English twin of the evidence page** — follow `hreflang="en"` of a question page/award page as discovery
already does for programme pages (M1 records twins; the evidence stage does not follow them) — zero new words;
(ii) **per-language keyword tables for the six questions** — the 16-Q5 rule: one commit, dictionary-grade, every
language at once, checked on dev4 only, flag-off (deadline / fecha límite / søknadsfrist / Bewerbungsfrist /
termin / son başvuru / tähtaeg / scadenza / terminas / срок подачи; tuition; IELTS is a proper noun; scholarship /
beca / stipendium / Stipendium / stypendium / burs / stipendium / borsa / stipendija / стипендия) — the readers
still parse numbers and dates, which are language-neutral apart from month names;
(iii) **a model extractor** (D9, proposer-only, the classifier/verifier still confirms, priced per university).

## Done when

- One table: case · label key · evidence URL · `<html lang>` · English twin declared? (fetch the page once by
  hand with the production fetcher, no pipeline) · does the twin hold the gold value? · route (i)/(ii)/(iii)/none.
- Totals: questions behind non-English evidence today; reachable by (i); by (ii) with which words per language;
  left for (iii). The month-name and decimal-comma problem for (ii) stated with examples from the pages.
- A cost line per route: files touched, flags, expected paired runs; (iii) with the privacy-table rows it would
  need (`SPEC_matching_v2.md` §6.4) and a per-university price estimate from the provider's public price list.
- No heldout page, label or language table entry is derived from a heldout case; the heldout countries'
  languages (cs, de, tr, et, it, lt, kk) enter (ii)'s table only as dictionary translations, as 16-Q5 decided.

## Files

Read-only: the gold files, `scratchpad/runs/base2-*/x/`, the readers named above, `scratchpad/core_gap_pages/`.
Writes the analysis file and hand-fetched pages under `scratchpad/non_english_pages/` (untrusted data).

## Evidence

`docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` §1 (A6 rows: group F 5 labels, group R 13 labels, group X 3),
§2 (puc deadline on `admision.uc.cl`, uba `extension.uba.ar`, warsaw `bpm.uw.edu.pl` + PDF);
`docs/process/PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md` §2 (English-only readers and queries);
previous map [Language alternates](../../programme-discovery/issues/13-language-alternates.md).
