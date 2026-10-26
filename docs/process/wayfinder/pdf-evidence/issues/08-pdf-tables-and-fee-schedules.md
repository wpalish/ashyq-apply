# Tables in PDFs and multi-programme fee schedules: what the deterministic readers may claim, and where they must abstain

Type: research
Status: open
Blocked by: 02, 03
Map: ../map.md · AFK research first (the facts), then at most one task ticket if the facts justify it.

## Question

Fee schedules and admission tables are the PDFs universities publish most (um's «Fee Structure, UG, International»,
ktu's Faculty of Informatics sheet, uct's bursaries booklet, ntutw's prospectus). `pypdf` returns a table as lines of
text whose columns are separated by runs of spaces or by nothing; `document_ir`'s table blocks (`row_headers`,
`column_headers`) do not exist for a PDF, so FE-2's `extract_programme_fee_rows` and EN-2's
`extract_table_requirements` have no grid to read. On the PDFs ticket 02 fetched: **(a)** does the per-page text keep
one table row per line often enough that a simple rule — a line that names the confirmed programme (`programme.name`
or a strong alias) **and** carries one money amount with a period word — yields the right tuition, with the population
taken from the page or section heading («International», «Malaysian», «Home») and never from a neighbouring row?
**(b)** How often do two programmes' rows or two populations' columns collapse into one line (the scope risk the map
forbids: never claim another programme's or population's row)? **(c)** Which of the deterministic readers survive the
per-page text unchanged (prose readers: FE-2's "RM 12,000 per year", EN-2's "IELTS 6.0"), and which need the grid
(fee tables by programme, English-test tables by faculty)? **(d)** Is the honest answer for grid-only facts «abstain,
leave to ticket 09», or is one narrow row rule worth a flag?

## Done when

- A table over every fee / requirement table found in 02's PDFs: PDF · page · what the table says · one-row-per-line?
  · does the row name the programme? · population from heading / column / neither · what the prose readers already
  yield on that page · what a row rule would yield · wrong-scope risk (yes / no, with the colliding row quoted).
- The rule proposal, if any: `extract_pdf_fee_rows(doc, builder, programme_name)` in `pdf_evidence.py` behind
  `PDF_FEE_ROWS` (loop id **PD-4**), with its abstain conditions written as tests before code (a line with two
  amounts, a line without the programme name, a heading that names another level → no claim); or the verdict
  «abstain: grid facts go to 09», recorded in 10 as the class `pdf_table_scope`.
- Nothing in this ticket edits `structured_costs.py` / `structured_extraction.py` (workers' files); the reader, if
  built, lives in `pdf_evidence.py` and is called only from the PDF branch.

## Evidence

Ticket 02's Table B; `structured_costs.extract_programme_fee_rows` (L248, the HTML grid rule whose abstain conditions a
PDF row rule must keep); `scope_reader.read_scope`; map Out-of-scope (the corpus year convention keeps um's tuition
`unknown` whatever the reader does — the rule is judged on page outcomes and on dev4 labels when 09 of the previous map
lands, not on um alone).
