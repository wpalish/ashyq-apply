# H-C (offline half): does today's confirm predicate accept the dev5 gold pages? Classifier and subject audit

Type: research
Status: resolved
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

## Answer

Full table: [`DEV5_PAGE_AUDIT_2026-10-19.md`](../../../DEV5_PAGE_AUDIT_2026-10-19.md). 29 programme-role URLs from the 13
dev5 drafts (local, twin, department, site, related), hand-fetched with the production User-Agent after robots.txt;
25 fetched, 4 not (kbtu, satbayev ×3: TLS chain incomplete, as on the runner). Today's defaults; `LEXICON_V2` on top
changes no verdict.

**Accepted 3 of 25:** lmu department page ("Informatik Bachelor"), tud English twin, unipd local ("INFORMATICA").
**Refused 22:** `reads_as:unknown` 13 (aitu ×6, zcu ×2, vilniustech ×2, hacettepe ×2, bilkent tr),
`reads_as:program_catalog` 3 (sapienza ×2, bilkent catalogue), `subject_mismatch` 6 (lmu local, tud local, unipd site
and twin, upol, ytu); `degree_level_other` 0, front page 0, R6 "names another institution" 0 of 25.

**Lexicon gaps (shape already listed):** 2 pages — form/status words not filler in German (`akkreditiert`;
`Hauptfach`, `Nebenfach`, `ECTS`; ticket 19 Q2's shape); plus 2 pages of the listed structural-label shape (h1 is
the degree only, unipd's course site). **Rule gaps (new shapes):** no level word in title or h1 (aitu, zcu,
vilniustech: 10 pages), a thin script shell read as a catalogue (sapienza ×2), an ASP.NET page whose content region
is emptied (hacettepe ×2), a unit name before the dash (upol). 3 refusals are correct (ytu's related form by name,
bilkent's department catalogue and prospective-students page).

**Predicted ceiling, written before 14's baseline:** **3 of 8** exact cases (tud, unipd, lmu; 2 / 8 if lmu's
department page is not a gold variant in dev5.draft1), and **0 wrong confirms** from the five related-only cases'
pages. aitu, sapienza, upol and zcu cannot be confirmed whatever search returns; satbayev and kbtu cannot be
fetched. H-C's offline half: on unseen sites the predicate loses mostly to **rule** gaps, not to a memorised lexicon.

Gist: dev5 gold pages — 3/25 accepted, ceiling 3/8 exact cases; refusals mostly new shapes (level absent from the head), not lexicon.
