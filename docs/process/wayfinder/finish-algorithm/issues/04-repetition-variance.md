# Repetition variance: which cases flip between repetitions, and why

Type: research
Status: resolved
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

## Answer

Gist: 13 of 35 development cases flip across 8 identical repetitions. Only kuleuven (subhost robots.txt reads
time out, 6/8), unibo (7 timeouts in one rep) and toronto's page (403 in every rep, constant) are host. The rest
are ours: provider rank for hku, iitd and unsw; order, lead slots or stage clock for tcd, ctu, rwth, uba, uio,
uppsala and uct. 2 reps per arm costs ≈1.1 false stable items per 4-set cycle; 4 reps costs ≈0.06. Detail:
[`docs/process/REPETITION_VARIANCE_2026-10-18.md`](../../../REPETITION_VARIANCE_2026-10-18.md).

- **The ap1c reps count as defaults for discovery.** `d7cbf8f` differs from base2's `593bd29` only in the
  flag-off AP-1c change in `web_scholarships.py`. `ap1c.on`'s `--nav-link-level-guard` acts only in the funding
  phase, and no label differs because of it.
- **The examples the ticket gave as host flips are not host flips:**
  - tcd's `7/40 failed` (4 `http_error` + 3 `blocked`) is identical in its hit and wrong reps; the flip is a lead
    choice with the gold at rank 1 in every family;
  - uba's `PARTIALLY_BLOCKED` (1 + 2) is identical in all 8 reps; the one miss is the 55 s discovery deadline
    plus a lead slot;
  - uct's timeout is in a rep that still answered; its lost `ielts.overall` comes from the SO-1
    `first_read_rule` firing on one 11.6 s read.
- **No harness kills.** No case reached 115 s; the longest took 110 s, and all 8 × 35 runs ended `complete`.
- **01 Q3:** the host rule removes kuleuven (6 reps), unibo `base2.off#2`, and toronto's page. tcd, uba, uct and
  every other flip stay in the denominator.
- **Owners of the "ours" cases:**
  - ticket 06: hku, iitd, unsw;
  - ticket 05: ctu, rwth, unibo;
  - worker A: tcd, toronto W↔M;
  - worker B: uba, uio, iitd, ctu.
- **Map fog "stage order on slow hosts" is now specifiable:** uppsala, uio and uct, and rwth's inconsistent slow
  flag. The causes are the fixed 55 s deadline, the SO-1 decision made from the first 2 reads, and a sitemap stage
  with no cap of its own (36–51 s).
- **History:** 6 of the 62 historical stable gains and losses sit on items that flip under identical defaults
  (the rwth `programme.exists` "gain" was credited to three different flags).
- **Recommendation:**
  - keep 2 reps per arm for screening;
  - rerun 2 more reps when a flag's only evidence is a flaky item;
  - acceptance baseline 17 uses 4 reps, judged after the host exclusions.
