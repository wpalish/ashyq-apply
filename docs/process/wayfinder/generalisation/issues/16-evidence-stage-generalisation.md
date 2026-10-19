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
