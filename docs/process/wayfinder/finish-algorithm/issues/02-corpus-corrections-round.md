# Corpus and binding corrections, one signing round

Type: task
Status: claimed
Blocked by: —
Map: ../map.md · HITL task — the corpus is signed data; only the owner changes a label. Agents prepare the diff
and the evidence; the owner signs. Nothing here changes the pipeline.

## Question

Nothing to decide about the algorithm: seven labels or bindings in the signed development corpora are known to
score a right answer as a miss, or to hold a value no reader can emit, or to belong to another programme. Each
is one line in a gold file. Which of the seven does the owner sign, so the scorer stops hiding answers before
the exit gate (17) is read? Every item moves a number *only* by re-scoring frozen captures — no rule, no run.

| # | item | file | today | proposed |
|---|---|---|---|---|
| Q1 | **NTU Nanyang Global Scholarship** — read correctly in every repetition (`scholarship_exists`, `citizenship_restriction = all`, `international_eligible = true`) but filed `unmapped.*` because the live URL is `/admissions/ug/scholarships/.../nanyang-scholarship` and the bindings hold `/admissions/undergraduate/...` | `identity_bindings.draft2.json` (cohort) | 3 labels / 2 questions missed | add the `/admissions/ug/` spelling as a second source URL of `scholarships.nanyang_global` (ID-1 scorer alias, built, off until signed) |
| Q2 | **NTU SAT key** — pipeline emits `sat.minimum`; gold key is `english_evidence.sat.minimum` | `ground_truth.reviewed10.json` | 1 label unmatchable even when read | map `sat_min_total → english_evidence.sat.minimum` where the corpus uses it (ID-1) |
| Q3 | **Imperial £47,800** — gold tuition label carries no population; FE-2b claims it as `international` (Overseas fee row); the Home £10,050 is never claimed | `dev3.draft1.json` | scored hit by luck of the scope rule | add `population: international` to the label so the Home row can never match it |
| Q4 | **Per-semester tuition** (several dev3/dev4 sites publish a semester fee) | corpus convention + `GLOSSARY.md` | no convention; a reader that annualises would be "wrong value" | label the amount **as published** with `period: semester`; the pipeline never multiplies; the scorer compares amount + period |
| Q5 | **Uppsala deadline** — gold 2027-04-15 (national round, programme page); the pipeline reads 2027-01-15 ("application closes 15 January 2027", the international round, official `/study/bachelors-studies` page) → the one wrong dev2 claim | `dev2.draft1.json` | the only wrong claim on dev2 is a gold dispute | gold `deadline = 2027-01-15` with `population: international`; keep 2027-04-15 as a second label `population: eu_national`; the product serves an international applicant |
| Q6 | **Chula** — english ×3 and scholarship ×2 labels belong to the ISE/ICE programme (`ise.eng.chula.ac.th`), while `programme_urls` lists and we confirm the Faculty of Science BSc page | `dev3.draft1.json` | 3 questions in the denominator that the confirmed programme cannot answer | the case is the Faculty of Science BSc; the five ISE labels → `status: not_applicable` (another programme); if the owner wants ISE measured, it becomes its own case |
| Q7 | **gpa prose labels** — ntu "A in all subjects (NIS Grade 12 …)", um "65% minimum average (SHSC)", ucph "Pass the KU quota 2-test …", msu "Math 60 / Informatics 65 …" | cohort, dev3 | 0/4 everywhere, by construction | `status: unknown` now (leaves the denominator); a structured `{qualification, requirement}` form is a later corpus task |
| Q8 | **Delft TOEFL evidence URL** `…/1-admission-requirements/` vs live `…/admission-requirements` | `ground_truth.reviewed10.json` | hit only through the sibling rule | declare the two URLs twins |

➡️ Recommended: **yes to all eight**. Expected movement on frozen captures (re-score only): cohort +2 questions
(Q1), dev2 wrong claim 1 → 0 (Q5), denominators −3 (Q6) and −3/−4 (Q7); nothing else moves.

## Done when

- The owner has answered per item; the agent applies the signed lines, bumps the dataset version strings
  (`2026-10-17.reviewed11` / `dev2-draft2` / `dev3-draft2`), re-scores `base2-*` and the latest `ap1c-*` captures
  with `python -m evaluation.research.scorecard` and records the before/after rows in the loop report; the
  identity-binding aliases (ID-1) go on by default only for the items signed.
- `scholarship-audit` is run on Q1 (the award's coverage and eligibility are stated by the page, not inferred).

## Evidence

- `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` §2 (ntu D1/D2, chula A7, gpa B7, uppsala B4/D3), §4.
- `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` "Clean baseline 2" (the Uppsala claim), "Evidence on
  found pages" (ID-1 off until signed), "EN-2b and FE-2b reruns" (Imperial £47,800).

## Answer

Owner (Диас), 2026-10-18: «Все да» — Q1–Q8 accepted as recommended. Implementation handed to a worker; resolved when the corrections are committed and the frozen captures re-scored.
