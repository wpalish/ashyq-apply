# H-F: the seen-site ledger — which default-on rules ever helped a case that did not motivate them?

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK, offline, from the loop reports, HANDOFF §8 and `hypotheses.json`; no run.

## Question

Since 2026-10-05 the loop turned on, by paired runs, at least: CU-1, CL-1, QB-1/QB-1b, FS-1, FS-2, the award route,
ENGLISH_READERS_V2 / FEE_READERS_V2, CG-1, R1 (`LOCALIZED_IDENTITY`), R2/R2b (LX-1 + subject shapes), R5
(local-language family), R6, `FEE_SUBPAGE_EXCLUSION`, `LOCAL_TWIN_ON_IDENTITY_REFUSAL`, `ALIAS_AWARE_PROGRAM_MATCH`,
FP-1, QH-1, AN-1 + AN-1b, DL-6, SC-2, SB-1/TB-1, ID-1 (scorer), and the acronym / brand-name scorer matches. Each was
motivated by named development cases and judged "stable gain, no stable loss" on the same sets. The nine read 0–1/9
programme pages on 2026-10-17 **and** on 2026-10-19 while dev4 rose. **Which rules have evidence of helping a case
outside the set that motivated them?** A rule with none is a seen-site rule until dev5 says otherwise.

## Method

For every flag on by default (`grep -n ' = True' live_discovery.py extraction.py web_*.py intent.py retrieval.py
page_classifier.py metrics.py identities.py`, plus HANDOFF §8 lines), one row:

| flag / loop id | on since (run id) | motivating cases (set) | stable gains recorded, by case (set) | gains outside the motivating set? | precision guard or recall rule? | verdict |

Sources: `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` cycle tables (gains/losses columns),
`docs/process/LOOP_REPORT.md`, `expert/data/hypotheses.json` (status, `case_ids`), programme-discovery tickets 08–11,
16. Verdict vocabulary: **general** (a gain on ≥ 1 case in another set, or a precision guard that adds no reads and
fires on unseen pages by construction), **seen-site** (gains only on motivating cases), **unmeasured** (on without a
paired run — e.g. bug fixes merged on). Also count how many of the words/shapes/lexicon entries added by R2, R5, LX-1
and ticket 19 came from a single development case (feeds 08).

## Deliverable

`docs/process/SEEN_SITE_LEDGER_2026-10-19.md` with the table and three counts (general / seen-site / unmeasured),
and the list of seen-site rules in the order they should be re-measured by 13's protocol (dev5 aggregate off/on —
one `expert_paired` run per rule on dev5 only, `extra_args=--no-<flag>` where a negative form exists, else the worker
adds it). A seen-site rule that shows a *loss* on dev5 is proposed for default-off in 15; a rule with no effect on
dev5 keeps its default and its label.

## Files the worker holds

`scratchpad/g12/*`, the new doc. No code change.

## Evidence

- Loop report cycle tables; `hypotheses.json` (10 entries: 3 candidate, 3 rejected, 4 tested — the register is
  incomplete relative to the flags on by default, which is itself a finding); `current_rules.json` (CR-01…).

## Done when

The doc is committed; the Answer gives the three counts and the re-measure order; 13 and 15 read it. Loop id: **G-12**.
