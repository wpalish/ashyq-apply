# A bounded model extractor on PDF pages (D9): page-at-a-time, proposer-only, priced — opened only by the owner

Type: grilling
Status: open
Blocked by: 01 (Q7 = «(a) сейчас»), 04 (PD-1 default-on — the model proposes over the same per-page text), or the previous map's 18 opening it
Map: ../map.md · HITL — the owner decides; this ticket exists so the shape and price are written once and not
re-argued. It is **not** on the critical path.

## Question

Of the six PDF questions (after 02-Q7), two are reachable by deterministic readers at best; **four need clause
polarity in Polish, Russian, Portuguese or Japanese** (warsaw «może otrzymać student cudzoziemiec, o ile spełnia
warunki…», msu «на бюджетной основе … иностранные граждане … межправительственных соглашений», usp «Todos os estudantes
regularmente matriculados…», utokyo 第1種 window among two) — the exact shape the non-English analysis already said
keywords cannot read without new wrong claims. If the owner opens it, what is the bounded design?

❓ **Q1 — Shape**: a proposer only. Input: one PDF page's text (≤ 40 pages, each a separate bounded call; stop at the first
page that yields a validated value for the question), the six question names and the programme's level / field /
intake (`preferences_only` fields only — no citizenship, GPA, scores, budget, name); output: for each question, a
value, a verbatim excerpt ≤ 600 chars, the page number. Acceptance by the **existing** rule only: §6.3 excerpt validator
(normalised excerpt ⊂ page text, value inside the excerpt), `claim_verifier.verify_claim` (verbatim, range, domain,
page type via 04's `classify_pdf`), `extraction_method="llm_assisted"`, `confidence ≤ 0.9`, `relevant_section="p. N"`;
the deterministic readers run first and the model runs only for questions still unanswered on that PDF.

➡️ Yes — it is the spec's §6.3 escalation shape, applied per page.

❓ **Q2 — Privacy row**: `SPEC_matching_v2.md` §6.4 gains the row «official page / PDF text and the six question names:
✓ in both modes»; nothing from the applicant's profile beyond the `preferences_only` row enters the prompt; the I3-style
test asserts the prompt for the demo profile contains no `"4.8"`, `"7.0"`, `"Kazakhstan"`, `"6000"`, no name.

➡️ Yes — required before any call; the owner signs the row.

❓ **Q3 — Budget and price**: calls do not count against the 60 HTTP reads (not a university request) but against the
120 s (a page call ≈ 1–3 s; cap 10 calls per university → ≤ 30 s, inside `CORE_RESERVE_SECONDS` logic); price at the
provider's smallest tier ≈ $0.006–0.02 per university (≤ 60 k input tokens worst case), ≈ $0.1–0.3 at the mid tier;
a paired run on the four sets ≈ $1–2 small tier. Provider: whichever meets D9 (zero-retention, no training), named
in config only, never in the repository's text.

➡️ Yes — development sets only; one paired run; the heldout look stays the previous map's 19.

❓ **Q4 — Bar and stop**: no new wrong claim (the validator makes a fabricated quote impossible, but a *wrong-scope*
quote is not — the scorer's wrong-scope row must stay 0); stable gain ≥ 2 PDF questions, else rejected and the four
stay `pdf_non_english` residue. Flag `PDF_MODEL_EXTRACTOR` (loop id **PD-5**), new module `app/adapters/
llm_pdf_extraction.py` behind the existing provider seam; tests with a fake provider only.

➡️ Yes.

## Evidence

`SPEC_matching_v2.md` §6.3 (validator), §6.4 (privacy table), brief D5/D6/D9; `NON_ENGLISH_EVIDENCE_2026-10-18.md`
§2 («7–8 need (iii)»), §3 (price lines); map Notes (which four PDF questions need polarity).
