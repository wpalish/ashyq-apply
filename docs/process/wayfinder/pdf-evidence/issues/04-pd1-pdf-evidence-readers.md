# PD-1 `PDF_EVIDENCE_READERS`: every stage reads a PDF as pages, classifies it by its own title, and claims with a page number

Type: task
Status: claimed
Blocked by: 03, (previous map 13 and 14 landed — workers C and D hold the three stage files)
Map: ../map.md · AFK task behind one flag; one paired run on cohort / dev2 / dev3 / dev4.

## Goal

The pipeline already spends reads on PDFs (≈ 30 distinct per base2 set on dev2/dev3) and throws every one away:
the funding stage parses PDF bytes as HTML (auckland's scholarship guidebook rejected 8/8, uct's bursaries booklet,
ntutw's international prospectus), the requirements and costs stages extract text but classify with no title
(`unknown` → `page_type_rejected`: unsw UAC key dates, uppsala ×3, um's faculty PDF). With 03's module, each stage
reads the PDF as pages, classifies it from the PDF's title / first headings / per-page text, runs **the same readers**
(`extract_requirements`, `extract_costs`, `extract_table_requirements` on the IR, the AP-1 award eligibility sentences,
FE-2's prose fee readers) over the per-page text, and every claim carries `relevant_section = "p. N"` and a verbatim
excerpt the verifier checks against the PDF text.

## Flag and loop id

`PDF_EVIDENCE_READERS = False` in `app/adapters/pdf_evidence.py` (new module that owns the dispatch), harness flag
`--pdf-evidence-readers`, loop id **PD-1**. Off: byte-identical behaviour (the stages keep their current PDF paths).

## What changes, per file (hooks only; the logic lives in the new module)

- **New** `app/adapters/pdf_evidence.py`: `classify_pdf(doc, url) -> PageClassification` (calls
  `classify_page(url=url, html="", text=pdf_text(doc))` **after** prepending the PDF title and the first-page headings
  as the "head", so the existing title/heading signals fire — no new classifier words); `read_pdf_claims(doc,
  builder, *, stage) -> list[Claim]` (runs the stage's existing readers over `pdf_text(doc)` and `build_pdf_ir(doc)`,
  then stamps `relevant_section` with `page_of`); `pdf_page_outcome(doc)` (`fetch-failed · PDF without a text layer`
  for `no_text_layer`; `unparseable` for malformed; `fetched-ok · PDF, N pages (truncated)` otherwise).
- `scholarship/web_scholarships.py` (≤ 6 lines, after C/D land): where a fetched page becomes `html` for the award
  reader (L878–890 and L1423), branch on `res.is_pdf` → `pdf_evidence` path; `_off_award_shape` unchanged (an official
  PDF under a `scholarship` path is already kept).
- `requirements/web_requirements.py` (≤ 4 lines at L1175–1196): `text` and `page` come from `pdf_evidence` when
  `res.is_pdf`; `page_title` = the PDF title (today: the file name).
- `cost/web_costs.py` (≤ 4 lines at L109–140): same; `page_title` «Fee schedule (PDF)» becomes the PDF title;
  `extraction_method` stays `pdf_rule`.
- Scope: a PDF's `read_scope(text, title=pdf title)` is computed **per page** that yields a claim, not per document —
  a 40-page prospectus states many degrees; a page that names another level or population scopes its own claims.
- `applicability.py` / AP-1: unchanged; it reads the sentences `read_pdf_claims` hands it.

## Bar (loop-engineering)

One paired run per set (`expert_paired`, 2 reps per arm). **No new wrong claim is the hard line** (precision 1.00
today). No stable loss. Gain accepted as either ≥ 1 stable core answer **or** identical labels with the PDF page
outcomes turning from `classifier-rejected · unknown` into a named type on ≥ 3 cases (the honest expectation on
today's labels is +0 questions — the gold PDFs are not reached; the rule earns default-on by stopping the waste and
by making 05 and 07 measurable). Reads must not rise above the off arm (no new fetch is added by PD-1). Budget: 0 cases
over 6 / 60 / 120 s; `parse_ms` logged per PDF and summed per case into the trace.

## Done when

- Offline tests on fixtures: the synthetic award PDF (one named award, eligibility sentence «open to international
  students») yields `SCHOLARSHIP_EXISTS` + `SCHOLARSHIP_INTERNATIONAL_ELIGIBLE` with `relevant_section="p. 1"`; the
  synthetic fee PDF yields `TUITION` from page 2 with the right population when the page names it, and **abstains**
  when the page lists two programmes' rows and neither names the confirmed programme (ticket 08's rule in its simplest
  form — a row that does not name the programme is not claimed); the image-only PDF yields the `fetch-failed` outcome
  and no claim; flag off → the existing tests' outputs byte-identical.
- The paired run recorded in the loop report with the bar's four numbers; default-on by the cycle-4c delegation if
  the bar holds; HANDOFF §8 line with the final flag name.
- Offline guard: `pdf_evidence.py` imports no network module; the stages call it only behind `res.is_pdf`.

## Evidence

Map Notes (code lines per stage); `scratchpad/pdfmap/captures_pdf.json` (the 29 met PDFs and their outcomes);
`claim_verifier.CLAIM_TYPE_PAGE_TYPES` (which types each family admits — a PDF must classify into one of them or stay
silent); `page_classifier.classify_page` L739–760 (title/headings are the signals that `html=""` starves).
