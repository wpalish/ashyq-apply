# H-C (offline half): does today's confirm predicate accept the dev5 gold pages? Classifier and subject audit

Type: research
Status: open
Blocked by: 03
Map: ../map.md · AFK, offline; the dev5 drafts' pages as 03 lands them (hand-fetched through the agent's egress with the
production User-Agent after a robots.txt check, 1 s per host, as `NON_ENGLISH_EVIDENCE_2026-10-18.md` did). No run.

## Question

Programme-discovery ticket 10 found that 10 of 20 testable development gold pages were accepted by the confirm
predicate and named the refusal of each other one (lexicon gaps, subject-title shapes, structural labels, identity not
in the text). Those gaps were then closed on *those* pages. **On thirteen pages nobody has tuned on, how many does the
predicate accept today, and what refuses the rest?** This is the offline half of H-C and the pre-baseline prediction
13 needs: a page the predicate refuses cannot be confirmed whatever search returns.

## Test

For each dev5 gold page (local and twin) and each `related` page from 03's drafts:
1. fetch and save (`scratchpad/g10/pages/`); record `<html lang>`, `<title>`, `h1`, hreflang alternates;
2. run `page_classifier.classify_page(url, html, text)` and the confirm predicate's subject / degree checks as
   `scratchpad/wf_tools/` did for ticket 10 (reuse that script; `python3 -I`), with today's defaults
   (`LOCALIZED_IDENTITY` on, LX-1, subject shapes of ticket 19);
3. record the verdict: accepted / `subject_mismatch` / `degree_level_other` / `reads_as:<type>` / identity not in text
   / front page; and whether the English twin alone would be accepted;
4. run the production identity check the confirm step uses for "names another institution" (R6,
   `catalogue/discovery.py` `_names_other_institution`) with the seed row's name against each page.

## Deliverable

`docs/process/DEV5_PAGE_AUDIT_2026-10-19.md`: a table per case (local / twin / related × verdict × reason), totals per
reason, and the **predicted dev5 ceiling for programme-page confirmation** (cases with at least one acceptable page).
That ceiling is written down *before* 14's baseline runs and compared with it afterwards — the first test of whether
offline audits predict a run on unseen sites.

## Files the worker holds

`scratchpad/g10/*`, the new doc. No code change.

## Evidence

- programme-discovery [10](../../programme-discovery/issues/10-classifier-audit.md) (method and the ten refusals),
  [19](../../programme-discovery/issues/19-subject-title-shapes.md) (listed shapes only); `page_classifier.py`;
  `HELDOUT_STAGE_SUMMARY_2026-10-19.md` `read_refused:subject_mismatch 16–18`, `reads_as:unknown 5–17`.

## Done when

The doc is committed with the ceiling; the Answer gives accepted / refused counts by reason and which refusals are
shapes already listed for another language (a lexicon gap) versus new shapes (a rule gap). Loop id: **G-10**.
