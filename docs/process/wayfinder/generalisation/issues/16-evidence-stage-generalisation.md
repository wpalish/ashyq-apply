# H-D and the evidence stages on unseen sites: unlabelled claims, unmapped awards, costs pages, local scope words

Type: research
Status: open
Blocked by: 14
Map: ../map.md · AFK, offline on the dev4 + dev5 baseline captures (dev5 at aggregate level only — 13-Q1); no run.
Lower priority: discovery decides the gap; this ticket sizes what is left once a page is found.

## Question

On the nine, 37–44 claims were emitted and 3 matched a label (2 wrong value, 1 wrong scope on **degree**); 2–7
scholarship claims per column were `unmapped`; costs pages were fetched ok in 1–2 of 16–19. On development the same
rows read: cohort 52–53 matched of 113–128 (75 unlabelled), dev2 11–12 of 33–41, dev3 11–13 of 75–80 (36–38
`unmapped.scholarship_exists`), dev4 8–9 of 13–17; costs pages fetched ok 1–2 of 28 on the cohort and ≈ 0 elsewhere.
**Which of these are heldout-specific and which are dev-wide weaknesses that only looked fine because dev precision is
judged on matched claims?**

## Test (dev4 + dev5 baseline, stage summary rows; dev4 per-case where needed)

1. **Unlabelled share**: claims unlabelled ÷ claims, per set; which claim types dominate (`unmapped.*`,
   `programme.exists`, english tests); for dev4 per case, whether unlabelled claims come from the confirmed programme
   page, a related page or an unconfirmed page (the knockout arm of 07 gives the "wrong page" shape).
2. **Wrong scope by dimension** on dev4 + dev5 (expected 0 today); offline: the degree-level reader on the local level
   words of the dev5 pages (Bc., bakalářský, Bachelor/Lisans, Laurea/L-31, bakalauras, бакалавриат) — does
   `INTEGRATED_MASTERS_LEVEL` / the coordinated-degree scope (SC-2, AN-1b) read them, or leave the degree unset (fine)
   or wrong (H-D confirmed)?
3. **Costs pages**: `pages:costs` vs `pages_fetched_ok:costs` per set; the refusal reason distribution
   (`budget_refused`, `reads_as:costs` refused, fetch failed, PII guard); whether the fee is on the programme page
   itself on dev4 (FE-2b reads it there) — i.e. is "costs page" a stage that works anywhere?
4. **Bindings**: `expressibility` on dev4 draft3 + dev5 draft2 (from 11 step 3): the share of known award labels no
   claim could ever map to.

## Deliverable

`docs/process/EVIDENCE_GENERALISATION_2026-10-19.md`: the four tables; a verdict per item — *dev-wide* (same on
every set; a finish-algorithm residue line, not a generalisation cause) or *country-dependent* (dev4 + dev5 differ
from cohort/dev2/dev3 by ≥ 15 pp — a candidate cause with its mechanism). H-D verdict from item 2.

## Files the worker holds

`scratchpad/g16/*`, the new doc. No code change.

## Evidence

- `HELDOUT_STAGE_SUMMARY_2026-10-19.md` claims and evidence sections; `STAGE_SUMMARY_DEV_2026-10-19.md` claims rows
  per set; `metrics.py` `adjudicate` (what `unlabelled` and `other_scope` mean); `RESIDUE_LEDGER_2026-10-18.md` Table B.

## Done when

The doc is committed; the Answer names each item dev-wide or country-dependent with numbers; 15 and 17 read it.
Loop id: **G-16**.

## Answer — item 2, H-D on the level dimension (LV-1, 2026-10-20)

Source: `backend/tests/test_lexicon_language_coverage.py` (NEXT_CYCLES_2026-10-20 §LV-1). One synthetic programme
page per language of `languages.json` (25), every word from a dictionary or a degree law cited per row; no page was
fetched, no dev5 page read, no heldout file, capture, log or label opened. Each page went through `classify_page` +
`profile_rejects(page, "bachelor", ["computer science"], url, country)`.

| what was read | result before LV-1's rows (the tables at f0d1830e) |
|---|---|
| bachelor's title `<CS alias> — <bachelor word>` | read **bachelor** in 25/25; accepted in 24/25 (ja "情報科学 学士課程": level right, subject unmatched) |
| master's title | read **master** and refused `degree_level_other` in 24/25; sk "Inžiniersky študijný program" read no level (refused as no programme page) |
| integrated master's (it, pl, pt, no/nb/nn: read master; lt, ru, sv: no level, refused — fine) | **et "Bakalaureuse- ja magistriõppe integreeritud õpe" read bachelor and was accepted for a bachelor applicant** |
| item 2's dev5 words, as words (bakalářský, Lisans, Laurea, bakalauras, бакалавриат) | bachelor, right; Bc. and the Italian class codes (L-31, LM-18) read no level (unset, fine; DA-2 keeps Bc. out) |

**Verdict: H-D confirmed for the level dimension, narrowly, on development (dictionary) evidence** — one wrong level
read in 25 languages, of one shape: an integrated degree whose statutory name opens on the bachelor's word, read
first-by-position. Every other local level word reads right or reads nothing. No development case is known to show it
(no dev case's gold is an Estonian integrated programme), so the verdict says the readers can be wrong on unseen
countries in this shape, not that they were wrong on the nine.

Closed (rows cite their source in the table comment): et integrated study → master (`_LV1_DEGREE_WORDS`, behind
`LEXICON_LANGUAGE_COVERAGE`, default off until the 4+4 replay); sk "inžiniersky" → master (unflagged, sk only). Also
found and closed, not level misreads: ca had no R5 query word (`"grau en"`, unflagged); nb/nn had no ontology alias of
computer science (flagged); ja "学士課程" in a head left the subject unmatched (flagged); local level words in URL slugs
for fi, pl, pt, es, da, sv and the de/nl/da/no/sv compounds (flagged), ca `grau-en` and sk `inziniersk…` (unflagged).
Left open: Swedish "kandidatprogram" in a slug on a Finnish (`.fi`) host still reads no level (only `.se` reads it).
