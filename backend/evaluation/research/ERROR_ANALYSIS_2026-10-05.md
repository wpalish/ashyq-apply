# Error analysis, 2026-10-05 (plan phase 1)

**Input.** Run 37279746829 (`expert_paired`, cohort of 10, exa), arm `on`
(ER-08, ER-09, ER-10 on), repetition 1, scored with
`python -m evaluation.research.scorecard` against corpus
`2026-09-23.reviewed`. Repetition 2 and the `off` arm give the same label
outcomes. Every miss below was traced to the run's own fetch log (was the
page the reviewer cites requested, and what came back) and, where the page
was read, to what was extracted from it. Prepared by claude-opus-5.

**Totals.** 62 known labels: 16 hit, 46 not. 42 adjudicated claims: 31
right, 11 counted wrong.

## The 46 labels not hit, by cause

| Cause | Labels | Where | What the trace shows |
|---|---|---|---|
| ACCESS from the runner | 17 | KAIST 8, Toronto 4, HKU 3, Aalto 2 | KAIST `admission.kaist.ac.kr`: robots.txt **ConnectTimeout** from GitHub (from another network it loads, and it names only Googlebot); Toronto: HTTP 403 on 21/30 pages; HKU `admissions.hku.hk`: connection reset; Aalto: robots.txt ReadTimeout. RFC 9309 makes an unreachable robots.txt a full disallow, correctly. |
| OTHER_PAGE | 10 | Groningen 9, KAIST 1 | Groningen's documents, NIS-credential and mathematics labels all cite `…/with-non-dutch-diploma/bachelor/bachelor-application-documents`, two links from the programme page (programme page → "bachelor, non-Dutch qualification" → documents); never requested. KAIST admission route on `cs.kaist.ac.kr/content?menu=40`, never requested. |
| EXTRACTOR | 9 | NTU 8, Vienna 1 | NTU Nanyang Scholarship page read (`ok`): coverage of tuition, housing, travel and the essay/referee documents are not extracted. Vienna programme page read: teaching language not extracted. |
| STALE_SOURCE | 6 | NTU 4, Vienna 2 | The cited pages now answer **404**: NTU "other international qualifications" (IELTS 6/6/6, SAT 1250, NIS grades, additional qualification) and Vienna "german-language-proficiency". NTU's current general requirements page states IELTS 6.5/6.5/6.5. Needs re-verification and a new signed corpus version, not a pipeline change. |
| REPRESENTATION | 3 | NTU | Right fact, coarser value: `application_mode` "separate" vs "separate_after_admission_application"; `applicability.degree` {"degree": "bachelor", "applies": "yes"} vs "bachelor_full_time"; `bond` value equal but its population scope reads the page's "Singapore PRs and international students" against the corpus's descriptive "full-time undergraduate scholarship applicants". |
| CLASSIFIER / IDENTITY | 1 | KAIST | `cs.kaist.ac.kr/content?menu=188` read (`ok`) and not confirmed as the programme. |

## The 11 claims counted wrong

| Claims | Cause | Detail |
|---|---|---|
| 1 | SCOPE | Groningen deadline 2027-05-01 recorded with population **EU/EEA**; the label (and this applicant) is **non-EU/EEA**. |
| 1 | IDENTITY | NTU "Bachelor of Science in Mathematical and Computer Sciences" returned as a programme for a computer-science request. |
| 6 | REPRESENTATION | NTU `applicability.degree` and `applicability.application_mode`, three pages each (see above). |
| 3 | SCOPE semantics | NTU `bond` population (see above): both readings are on the page; which dimension the corpus means is a scoring question for the owner. |

No claim states a fact the page does not state. Precision is lost to
scope and representation, not to invented values.

## Other findings

* **Budget.** Five cases send 7 queries without ER-08 (discovery 6 +
  scholarship search 1); the target is 6.
* **Measurement.** The corpus marks most core-question labels `unknown`
  (IELTS 18 critical unknown, SAT 20, tuition 10, deadline 9), so ER-08's
  answers (NTU IELTS, Delft TOEFL, Groningen fee) are unadjudicated and do
  not move recall. Phase 0.2 (corpus draft8) addresses this.
* **Benchmark network ≠ production network.** 17 of 46 misses are hosts the
  GitHub runner cannot reach; production runs elsewhere and may reach them.

## Order of work (largest recoverable value per effort, wrong values first)

1. Precision: population-aware row choice for deadlines (Groningen),
   programme identity for "Mathematical and Computer Sciences" (NTU), the
   finer scholarship vocabulary where the page states it (NTU). Owner
   decision on the `bond` scope semantics.
2. OTHER_PAGE: follow the applicant-situation admission link from the
   programme page (non-domestic / international qualification), two hops,
   inside the read budget — Groningen's 9 labels, then test for generality.
3. EXTRACTOR: scholarship coverage (tuition, housing, travel) and
   scholarship documents (essay, referee) — NTU's 8 labels.
4. STALE_SOURCE: re-verify in corpus draft8 (phase 0.2).
5. ACCESS: measure reachability from the production network before
   treating these 17 as pipeline misses; owner decision.
