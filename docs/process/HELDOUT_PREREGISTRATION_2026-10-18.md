# Pre-registration of the heldout acceptance run (finish-algorithm ticket 19, step 1)

Date 2026-10-18 · planner, written **before** any heldout run of this map · ticket
[19](wayfinder/finish-algorithm/issues/19-heldout-acceptance-run.md) · protocol: programme-discovery ticket
[21](wayfinder/programme-discovery/issues/21-heldout-acceptance-protocol.md) (owner: ≤ 2 looks, two arms × two
repetitions, aggregates only) · owner decisions of round 3: ticket [18](wayfinder/finish-algorithm/issues/18-escalation-unreachable-targets.md)
(targets 3 and 4 recorded "not met", the run proceeds, target 6 against the pooled development sets, both readings
pre-registered) · DoD change log entries dated 2026-10-18 in `SEARCH_DEFINITION_OF_DONE.md`.

**What this file is.** The expectation the heldout result is judged against, fixed before the dispatch, so that nothing
read afterwards can move it. Every number below comes from the four development sets (clean baseline 3, ticket 17) or the
residue ledger; no heldout file, capture, log, label or per-case row was opened to write it. The nine stay closed: `nu metu
sabanci charles masaryk tum tartu polimi vilnius`.

## 1. The one run — exact dispatch inputs

Workflow `.github/workflows/benchmark-capture.yml` (`workflow_dispatch`), one run, on the commit that carries today's defaults
(DL-6, SC-2, FP-1, QH-1, AN-1 + AN-1b on; everything rejected in the loop report off). Record the run id and the commit SHA
in LOOP_REPORT the moment it is dispatched.

| input | value | why |
|---|---|---|
| `mode` | `expert_paired` | two arms × two repetitions (`off`, `on`, `on`, `off` per case) — 21-Q3 |
| `case` | `nu metu sabanci charles masaryk tum tartu polimi vilnius` | `expert_paired` takes a **space-separated list of case ids**; the word `heldout` names the set only in the input's description and is not a value `live.py --case` accepts (`choices=[*COHORT, *HELDOUT, *DEV2, *DEV4_DOMAINS]` — ids only). Ticket 19's shorthand `case=heldout` means this list |
| `extra_args` | `--through-identity-gate` | the protocol's second arm (21-Q3): `off` = today's harness entry, `on` = production's site-identity gate — see §1.1 |
| `base_args` | *(empty)* | nothing else differs between the arms; both run today's defaults |
| `seconds_per_case` | `120` (default) | the budget |
| `max_pages` | `60` (default) | the budget |
| `case_parallelism` | `5` (default) | nine universities, each ABBA on its own; no site sees more requests |
| `runner` | `ubuntu-latest` (default) | the same machine class as every development run |
| `search_provider` | *(default — decided by the workflow)* | unchanged from the development runs |
| `run_tag` | `heldout-acceptance-19` | so the run name says what it is |
| `search_first`, `plan`, `resume_run_id` | defaults | not part of this mode |

Four columns come back: `off#1`, `off#2`, `on#1`, `on#2`. Every target is judged on its **worst** column (DoD), with 01-Q3's
per-repetition `unavailable` applied to targets 3 and 4.

**No other heldout run** happens in this map. A second look is governed by 21-Q1 alone (see §6).

### 1.1 What the `--through-identity-gate` arm does on the nine — read before the run, so it is not a surprise after it

`evaluation/research/live.py` applies the gate arm only to a seed-only case (`gated = through_identity_gate and case_id in
DEV2`, where `DEV2` holds the dev2 and dev3 ids; `NO_REGISTRY_CASES = DEV2 ∪ DEV4`). The nine are **registry institutions**
(`HELDOUT` in `live.py`, `CASE_DOMAINS` entries), so on both arms they take the registry path
(`canary.run_canary(CASE_DOMAINS[case_id], False)`), exactly as the cohort does. Consequences, pre-registered:

- the `on` columns are **not a different configuration** on the nine: the run yields four repetitions of today's defaults,
  as the 2026-10-17 look did (run 39103386295) and as clean baseline 3 did on the development sets;
- the `identity established` row of the summary reads **0/0** on every column (no `site_identity` is recorded for a registry
  case); 21-Q2 (c) "identity established on every readable site" is therefore **not measurable by this run as the harness
  stands** and is recorded as *not measured*, neither met nor failed;
- for a registry institution the registry selector *is* the production path, so the four columns do measure the path the
  product takes for these nine. The dispatch keeps the flag exactly as the protocol wrote it; this file says in advance what
  the flag will and will not do. Changing the harness so that registry cases go through the gate would be a harness change,
  not a rule — it is **not** made here, and if the owner wants it, it is a question in `OWNER_QUESTIONS.md` *before* dispatch,
  never after the result is seen.

## 2. Scoring — aggregates only

```bash
cd backend
.venv/bin/python -m evaluation.research.scorecard <unpacked artifact dir> \
  --dataset evaluation/research/data/heldout.reviewed1.json --summary-only --out <quarantine>/summary.json
```

- The artifact is unpacked into the session scratchpad's `HELDOUT_QUARANTINE_DO_NOT_OPEN/<run id>/` and that folder is never
  listed, `cat`-ed, grepped or opened by any agent; its path is passed to the scorecard and nothing else.
- The corpus file is the scorecard's input only. **Nobody opens it**: not for its labels, its evidence URLs, its programme
  URLs or its version string beyond what the summary's first line prints. If the scorecard refuses the file (schema or
  draft status), the refusal text is the only thing read, and the question goes to the owner; `--allow-drafts` is **not**
  added without the owner's word, because it changes what "signed" means for the heldout split.
- What is read: the `--summary-only` stdout and `summary.json` **only** — per arm and repetition the metric ratios
  (`programme_page_recall`, `claim_precision`, `claim_recall`, `wrong_scope_claim_rate`, `other_scope_claim_rate`,
  `partial_claim_rate`, `critical_field_coverage`, `unsupported_claim_rate`), `core questions answered`, `known core answered`,
  the readable rows (`known core answered (readable)` = `core_known_readable_rate`, `programme page on readable` =
  `programme_found_on_readable`, `wrong programme pages`), `unavailable cases`, `excluded cases`, `excluded core questions`
  by reason, programme pages `hit/wrong/related/missed` as counts, `identity established`, reads, `cases_over_budget`,
  `wrong_claims` as a count, known labels by outcome as counts, access states as counts, stable gains / losses / unstable as
  counts, and the targets table (`backend/tests/test_scorecard_summary.py` pins that no case id, URL, university, claim
  value, label or gain/loss item appears).
- What is **never** read: the per-case table, `capture.json`, traces, `out/log-*.txt`, the artifact's captures, any heldout
  corpus or bindings file, the full scorecard (`scorecard` without `--summary-only`), and any stage-level aggregate (21-Q4:
  a separate, explicit owner decision, asked in `OWNER_QUESTIONS.md`, never taken here).
- The summary's numbers are copied into LOOP_REPORT and the DoD status table **as the rows print them**, with their
  denominators; no number is typed by hand.

## 3. Denominators — each target as 01-Q2 / 01-Q3 and the DoD change log define it

| # | row | numerator ÷ denominator | judged on | cases that leave the denominator |
|---|---|---|---|---|
| 1 | `claim_precision` | right claims ÷ all claims stated | worst column | none — every case, readable or not |
| 2 | `wrong_scope_claim_rate` | claims about the wrong population, year or programme ÷ all claims | worst column | none |
| 3a | `programme_found_on_readable` | programme hits (a declared twin counts, a *related* programme does not) ÷ cases whose programme is `known` in the signed corpus **and** readable in that column | worst column | a case `unavailable` in that column: `access` `BLOCKED`, or half or more of its requests on the wire failed (cache hits, our privacy refusals and 404s on robots.txt / sitemap probes are not the site failing); a case with no programme label (`unlabelled`) |
| 3b | `wrong_programme_pages` | cases whose returned page is a wrong programme | worst column | none (a related page is not wrong; an `unavailable` case confirms no page, so it adds none) |
| 4 | `core_known_readable_rate` | core questions answered ÷ known core questions (of the six: English test minimum, GPA, deadline, tuition or total cost, a scholarship exists, open to an international applicant) on readable cases where at least one known label's evidence is an HTML page on a host that answered in that column | worst column | the case's `unavailable` questions (`access`); questions whose every evidence page is a PDF (`pdf`) or sits on a host whose every request failed (`host_failed`). **Stay in**: a non-English evidence page, another registrable domain of the same university, a case whose programme page was not found, and a label without an evidence URL (the scorer treats it as readable) |
| 5 | `cases_over_budget` | cases over 6 queries, 60 HTTP requests on the wire (redirect hops, retries and robots.txt count) or 120 s, a wall-clock-ended case included | worst column | none |
| 6 | `core_known_readable_rate` on the nine (row 4) against a reference | worst column of the nine vs the reference in §5 | as row 4 |

`known core answered` (the old `core_known_rate`, all known questions) is printed beside row 4 and recorded, but it judges
nothing: 01-Q2 fixed the readable denominator.

## 4. The development reference — clean baseline 3, recomputed from the four scorecards

Source: `scratchpad/runs/base3-{cohort,dev2,dev3,dev4}/sc.json` (runs 39172483236 / 39172484697 / 39172486984 / 39172488858;
pipeline `1093faaa`; corpora `2026-10-17.reviewed11`, `2026-10-17.dev2-draft2`, `2026-10-17.dev3-draft2`,
`2026-10-18.dev4-draft2`), pooled by summing numerators and denominators across the four sets per column, then over all
sixteen columns. Script: `scratchpad/prereg19/pool_base3.py` (read-only; asserts no heldout id is in any card).

| pooled column | precision | wrong scope | over budget | programme page on readable | wrong pages | core readable | core all | unavailable / cases |
|---|---|---|---|---|---|---|---|---|
| off#1 | 75/75 = 1.000 | 0/75 | 0 | 20/29 = 0.690 | 3 | 30/63 = 0.476 | 30/79 | 4 / 44 |
| off#2 | 77/77 = 1.000 | 0/77 | 0 | 21/27 = 0.778 | 0 | 32/64 = 0.500 | 32/79 | 6 / 44 |
| on#1 | 76/76 = 1.000 | 0/76 | 0 | 22/28 = 0.786 | 2 | 30/64 = 0.469 | 30/79 | 5 / 44 |
| on#2 | 79/79 = 1.000 | 0/79 | 0 | 22/28 = 0.786 | 1 | 32/64 = 0.500 | 32/79 | 5 / 44 |
| **all 16** | **307/307 = 1.000** | **0/307** | **0** | **85/112 = 0.759** | 6 (0–3 per column) | **124/255 = 0.486** | 124/316 = 0.392 | 20 / 176 = 11 % |

Per set (four columns each): cohort core readable 13–14/19 (0.68–0.74), page 5/8 (0.625) in every column, wrong pages 0–2,
unavailable 2; dev2 6–7/18 (0.35–0.39), page 4–5/6, wrong 0–1, unavailable 1; dev3 8–9/18 (0.44–0.50), page 8/9–10, wrong
0–1, unavailable 1–2; dev4 2/9 (0.22), page 3–4/4–5, wrong 0, unavailable 0–1.

**Adjustment the nine will run with.** AN-1 + AN-1b went on by default after baseline 3 (runs 39173608793…613552): one stable
gain on dev2 (an award `exists`, scoped bachelor), no loss, 0 wrong claims on any set. The defaults the nine run on therefore
read, on the development sets, **core readable 31/63, 33/64, 31/64, 33/64 per column (0.48–0.52); all sixteen 128/255 =
0.502**. Nothing else changed between baseline 3 and the dispatch commit (if something does, this file is amended *before*
the dispatch, never after).

## 5. Pre-registered expectations — the run is judged against these

| # | row | expected on the nine (worst column) | development reference it comes from | reading |
|---|---|---|---|---|
| 1 | `claim_precision` | **≥ 0.95** | 1.00 on all 16 development columns (307/307) | met / not met as the DoD says |
| 2 | `wrong_scope_claim_rate` | **≤ 0.03** | 0/307 | met / not met |
| 5 | `cases_over_budget` | **0** | 0 on all 16 columns | met / not met |
| 3a | `programme_found_on_readable` | **≈ 0.71–0.78** expected (ticket 18 / ledger §8); the DoD target itself is 1.0 and is expected **not met** | pooled 0.69–0.79 per column, 0.76 over all; cohort 0.625 | the DoD row reads met only at 1.0. 21-Q2 (a) "within 15 pp" of the reference is read in addition: vs pooled 0.759 → ≥ 0.609; vs cohort 0.625 → ≥ 0.475 |
| 3b | `wrong_programme_pages` | **0** (a *related* page is not wrong) | 0–3 per pooled column; 0–2 on the cohort | 0 → met; ≥ 1 → not met, recorded as a count only (no case, no URL) |
| 3c | `unavailable` sites | **≈ 2–3 of 9** (ledger §8, ticket 18); every one of them with **0 pages confirmed** (21-Q2 (b)) | development share 4–6 of 44 per column (≈ 11 %, ≈ 1 of 9); the 2026-10-17 look reached all nine | a count, not a target; with fewer than 5 readable sites the target-3/4 rows rest on ≤ 4 cases — the reading is still recorded as the rows print it, with the denominator beside it |
| 3d | `identity established` | **0/0 on every column** (§1.1) | — | *not measured by this run*; neither met nor failed |
| 4 | `core_known_readable_rate` | expected **not met** against 0.80; the nine's own value is what §5-6 reads | pooled development **0.486 measured / 0.502 with AN-1 + AN-1b**, range 0.47–0.52 per column | met only at ≥ 0.80 |
| 4′ | dev4 as the country proxy | **0.22–0.38** | dev4 2/9 = 0.22 on every baseline-3 column; 2/8 → 3/8 = 0.25–0.38 once ticket 09's corpus lines (ktu gpa `unknown`, rwth second source URL) are in the scored file | context for target 6, not a target |
| **6 primary** | the nine's `core_known_readable_rate` (worst column) vs the **pooled development sets** | **met if ≥ 0.352** (= 0.502 − 0.150; the measured-only reference 0.486 gives 0.336 — the higher bar applies, since AN-1 + AN-1b are on for the nine) | pooled 128/255 = 0.502 (adjusted), 124/255 = 0.486 (measured) | **the criterion** (owner, 18-Q4). Sensitivity, recorded not judged: against the worst pooled column (31/64 = 0.484) the bar would be 0.334 |
| **6 secondary** | the same value vs the **cohort** | **met if ≥ 0.534** (= cohort's worst baseline-3 column 13/19 = 0.684 − 0.150); typical cohort column 14/19 = 0.737 → 0.587 | cohort 13–14/19 | the DoD table's original wording; reported beside the primary reading, decides nothing |
| 6‴ | expectation | the dev4 proxy (0.22–0.38) says the primary reading is **expected borderline-to-not-met** (0.22 is 13 pp under the 0.352 bar; 0.38 clears it) and the secondary reading **expected not met** (36–60 pp gap) | ledger Table C row 6 | written here so a borderline result is read against a stated expectation |

**Residue expected on the nine, by class only** (no counts can be pre-registered without opening labels; development counts
beside each): returned-not-read (dev: 3 questions, 4 pages), non-English evidence without a route (dev: 9), unnamed award on
a read page (dev: 2, ktu), no exact CS programme / related only (dev: vut, taltech, boun, itu), other host never linked (dev:
4), other registrable domain (dev: 3), client-rendered / not linked (dev: 9), PDF-only evidence outside the denominator (dev:
6). The summary's `excluded core questions` row gives the `pdf` / `host_failed` counts on the nine; nothing else about the
residue is read.

## 6. Stop and no-retune rule

1. **Nothing in this map changes in response to the heldout result.** No rule, flag default, threshold, scorer line, denominator,
   corpus label, binding or workflow input is added, removed or re-tuned because of what the nine read; the DoD's "rules are
   never tuned on it" and 01-Q6's "one heldout look" hold. The result is recorded as the rows print it (LOOP_REPORT, the DoD
   status table with run id and date, the map's Decisions so far), met or not met per target, with this file as the yardstick.
2. **If it fails**, the design returns to the development sets with the summary's aggregate numbers as the *only* heldout input
   (21-Q5). A second look is spent only after a fix with development-set evidence has landed and passed its paired-run bar on
   all four sets (21-Q1) — and it is pre-registered again, in a dated file like this one, before dispatch.
3. **If it passes** on targets 1, 2, 5 and the primary reading of 6, those are marked met on the heldout split; targets 3 and 4
   keep the owner's "not met; residue" status unless their own rows read met on the nine.
4. **The per-case level stays closed** whatever the outcome. Opening a heldout stage-level aggregate (counts of loss stages, no
   URLs) is 21-Q4: a separate, explicit owner decision asked in `OWNER_QUESTIONS.md`, never taken by an agent, and never taken
   to explain a number already seen.
5. **Amendments** to this file are allowed only before the dispatch and are dated; after dispatch it is frozen — a correction
   found later is written as a note *under* the recorded result, not into the expectation.

## 7. Record to keep when the run is dispatched (filled by the main session)

| field | value |
|---|---|
| dispatched (UTC) | |
| run id | |
| commit SHA the run checked out | |
| inputs as entered (copy of §1) | |
| summary read on (UTC) | |
| summary.json path (inside the quarantine folder) | |

## Amendment A1 (before dispatch, 2026-10-18): signed labels from tickets 09 and 10

The owner signed tickets 09 and 10 before dispatch, which changes the dev4 core denominator. dev4.draft3 sets ktu gpa to `unknown`, so dev4 readable core is now 2/8 per column instead of 2/9. Re-scored on the same base3 captures (LOOP_REPORT "Signed labels: tickets 09 and 10"):

- **Pooled development reference, readable core.** Measured: 124/251 = 0.494. Adjusted for AN-1 + AN-1b: 128/251 = 0.510.
- **Target 6 primary bar.** It becomes **≥ 0.360** (= 0.510 − 0.150), replacing 0.352. Measured-only sensitivity: 0.344.
- **dev4 proxy.** 2/8 = 0.25, against 0.22 before.
- **Target 3 denominators.** They grow on dev2 (6 → 9) and dev3 (9–10 → 12–13). The pooled page-on-readable reference is read from the t0910-after scorecards. The "within 15 pp" reading in 21-Q2(a) uses that value, and the ranges in §4 stay as stated.

Nothing else changes, and every rule in §6 still applies.
