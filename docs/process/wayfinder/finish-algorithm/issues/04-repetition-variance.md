# Repetition variance: which cases flip between repetitions, and why

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK research — read-only on development captures; feeds ticket 01 Q3 and names the flaky hosts
every paired run must discount. Output: `docs/process/REPETITION_VARIANCE_2026-10-18.md`.

## Question

Under identical defaults, the programme page is found on dev2 in 5/6, 5/6, 4/6 and 2/6 of the four base2
repetitions, on cohort 5–6/10, dev3 7–9/11, dev4 3–4/5, and known core answers move by one or two per set. With
"worst repetition" as the judge, a target can be failed by a host that stalled once. For every development case
that differs between any two of the **eight** identical-config repetitions available (`base2-*` four, `ap1c-*`
four — same defaults), what flipped (page hit/wrong/miss, core answers, reads, seconds), and what is the cause
class per case: (a) host — timeouts, dropped connections, certificate or robots refusals in that repetition
(`.log` fetch outcomes, `access` fields); (b) provider — the gold URL's rank in `search_results` differs between
repetitions; (c) order — same inputs, a different page confirmed first (stage clock, 33 s rule, slots); (d)
harness — wall-clock kill at 115 s, checkpoint trace vs raw trace?

## Done when

- One table per set: case · outcome per repetition (8 columns) · cause class · the evidence line (log excerpt
  path, rank numbers). Cases that never flip are listed once at the bottom.
- A verdict per flaky case: **host** (leaves the denominator for that repetition under 01 Q3 — e.g. tcd 7/40
  failed, uct timeouts, uba PARTIALLY_BLOCKED) or **ours** (provider rank / order — stays in; names the ticket that
  owns it: 05/06 for rank, worker A/B for the case).
- Expected cost of a paired run in false signals: how many "stable" gains/losses in the loop report's history
  would have flipped on a third repetition (read from the `*-cohort/-dev2/-dev3` directories with 4 columns);
  recommend whether 2 reps per arm stays (cheap) or the acceptance baseline (17) uses 4.
- No heldout directory is opened (`heldout-final` excluded by name in every script).

## Files

Read-only: `scratchpad/runs/{base2,ap1c}-{cohort,dev2,dev3,dev4}/{sc.json,x/}`; the loop report. Writes only the
analysis file above (and scripts under `scratchpad/variance_tools/`, run with `python3 -I`).

## Evidence

`scratchpad/runs/base2-dev2/sc.md` (recall 5/6, 5/6, 4/6, 2/6; tcd `REACHED (7/40 failed)`), `base2-cohort/sc.md`
(hku unstable `programme.exists`), `base2-dev4/sc.md` (ctu unstable); LOOP_REPORT "Clean baseline 2" ranges.
