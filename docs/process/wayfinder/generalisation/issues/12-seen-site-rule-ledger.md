# H-F: the seen-site ledger — which default-on rules ever helped a case that did not motivate them?

Type: research
Status: resolved
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

## Answer

Ledger: [`SEEN_SITE_LEDGER_2026-10-19.md`](../../../SEEN_SITE_LEDGER_2026-10-19.md). It covers the 51 rules on by
default since 2026-10-17: 42 rule rows plus 9 bug fixes. The sources are the flag comments, the loop report, git log
and 54 scored set-runs in `scratchpad/runs/*/sc.json`.

- **Counts:** **general 23**, **seen-site 17**, **unmeasured 11**.
  - General: 18 of the 23 are guards by construction, and 5 are recall rules with a gain in another set.
    Three of those 5 are weak: LI-1, CL-1 and R1 each rest on one 2-rep gain.
  - Seen-site: 15 pipeline rules and 2 scorer rules.
  - Unmeasured: FI-1, IM-1 and 9 bug fixes.
- **Seen-site rules:** R5, R6, ALIAS_AWARE_PROGRAM_MATCH, SB-1, QR-1, SC-2, DL-6, EN-2, FE-2, DL-5, QR-2, QP-1,
  AP-1, AN-1 and SQ-1, plus the ID-1 and acronym scorer matches. **Every evidence-stage rule turned on since
  2026-10-18 is seen-site.**
- **Discovery recall rules:** only QB-1 (auckland, D3) and R2 (kit, D4) have an out-of-set gain seen in more
  than one run.
- **Noise floor:** 1 of the 8 A/A set-runs shows a 2-rep "stable gain" (ctu, base3-dev4). A single-label 2-rep
  gain is therefore weak evidence.
- **Register gap:** `hypotheses.json` has no entry for any of the 51 rules. Its 10 entries are all cohort-era.
- **Award route:** it is not on (`AWARD_ROUTE = False`).
- **Lexicon (feeds 08):** 19 entries come from a single development case: LX-1 11, R2 6, CG-1 2. R1's table
  and R5's family carry no case words, but R5's query shape was fitted on six development cases.
- **Re-measure order for 13:** R5 → R6 → ALIAS_AWARE → SB-1 → QR-1 → SC-2 → DL-6 → EN-2 → FE-2 → DL-5 → QR-2 →
  QP-1 → AP-1 → AN-1 → SQ-1, then scorer re-scores. FI-1 and IM-1 are measured once. No flag has a negative
  form today: the worker adds `--no-<flag>` for each.

Gist: 17 of 51 default-on rules have gains only where they were designed, all ten evidence rules of 2026-10-18 among them; dev5 off/on decides, R5 first.
