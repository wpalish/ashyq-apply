# Confirm the destination, the target-4 denominator and the judging rule

Type: grilling
Status: open
Blocked by: —
Map: ../map.md · HITL — owner round 1. Every other ticket can start; only the *reading* of ticket 03's second
column and the exit gate (17) wait on these answers.

## Question

The DoD (`docs/process/SEARCH_DEFINITION_OF_DONE.md`) says target 4 counts core answers "wherever the official
site publishes the answer and lets us read it", judged on the **worst** repetition, and target 3 counts the page
"on every site the run can read". The scorecard today puts every `known` core label of every case in the
denominator (77 on cohort+dev2+dev3; `scorecard.core_known`), reads 23–25 of them, and has no row for targets 3
or 4 at all (`TARGETS` holds precision, wrong scope, budget). `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md`
shows ~18 of the 52–54 missing questions are ours to fix in code; 10 sit on hosts that refuse the runner, 3–4 are
prose gpa labels, 3 are chula labels of another programme, the rest are client-rendered lists, other registrable
domains, PDFs and non-English pages. What exactly is the destination, how is target 4's denominator defined,
and how is a flaky repetition judged — so that the exit gate (17) is mechanical and no rule is built against a
denominator the DoD never meant?

❓ **Q1 — Destination as written on the map**: every DoD target met on the four development sets by scorecard
rows (03), then one acceptance run on the nine under ticket 21's protocol; a planner decomposes, parallel workers
execute flag-off → paired run → default-on under the cycle-4c delegation (no stable loss, no new wrong claim),
with no ticket waiting on you; losses in a named unreachable class are escalated (18), not built against.

➡️ Yes.

---

❓ **Q2 — Target 4 denominator = `core_known_readable`**: a known core label counts in the denominator only when
its evidence page is on a host the run could read in that repetition (the case's `access` is not `BLOCKED`, and
the label's evidence URL host is not among the hosts whose every request failed in the capture) **and** the
evidence is an HTML page, not a PDF (browser tier and PDFs are outside the design, previous map 01 Q6).
**Stays in the denominator**: a non-English evidence page (the site publishes it and lets us read it), a label on a
case whose programme page we failed to find, a label on another registrable domain of the same university. The
scorecard prints both denominators (today's and `readable`) until this is answered; the DoD gets a dated entry.

➡️ Yes. This is the DoD's own wording made mechanical. It removes ≈10 access questions (aalto, toronto, hku
admissions host, kaist, kaznu) and the PDF labels (warsaw PDF, uba/utokyo study plans); it keeps the honest
hard cases (non-English pages, other domains, pages we did not find) so the 80% still means something.

---

❓ **Q3 — Judging a flaky repetition**: targets 1, 2, 5 stay on the worst repetition. For targets 3 and 4, a case
whose host stalled or refused *in that repetition* (timeouts/failed requests ≥ 50% of its pages, as `access`
already classifies) is reported `unavailable` for that repetition and leaves that repetition's denominator; a
case that flips for any other reason (provider rank, order) stays and counts against the worst repetition.
Ticket 04 names which flaky cases fall on which side before this is read.

➡️ Yes. Worst-of-four with 2 reps per arm already fails dev2 on tcd's host timeouts alone (programme page 2–5/6
across the four base2 repetitions); access is per repetition in reality and should be in the measure.

---

❓ **Q4 — Stopping rule per target** (the map's list): a target is declared unreachable by rules when every
remaining development loss is in a named class — access; other registrable domain; SPA/PDF; client-rendered list;
department host / opaque URLs; non-English evidence (until 08 decides); gold identity or prose label (until 02
decides) — or when a rule fails its paired run twice on the same cause. Then 16 writes the residue, 18 brings you
the options (denominator, model extractor under D9, accept-and-record), and no further rule is attempted on it.

➡️ Yes.

---

❓ **Q5 — Delegation and parallelism**: up to five workers at once, each one ticket, each flag-off → one paired run
on all four sets (`expert_paired`, 2 reps per arm) → default-on by the cycle-4c delegation without a per-rule
question to you; a rule that gains nothing stable but adds reads is rejected, not kept "for later"; every
default-on is one line in the loop report and HANDOFF §8.

➡️ Yes — this is the working model you set on 2026-10-18, written down so the workers can cite it.

---

❓ **Q6 — The heldout look**: exactly one acceptance run (19) when 17 is green, under ticket 21's protocol (two
arms × two repetitions, aggregates only, pre-registered expectation); a second look only per 21-Q1; targets 3, 4
and 6 are read with the same denominators as Q2–Q3.

➡️ Yes.

## Evidence

- `backend/evaluation/research/scorecard.py` `TARGETS` (L45), `core_known` (L286–305), `_access` (L423);
  `scratchpad/runs/base2-{cohort,dev2,dev3}/sc.md` per-case "core known" column (28 + 21 + 28 = 77).
- `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` §0–§1 (cause × question tables), §4 (labels that look wrong).
- `docs/process/SEARCH_DEFINITION_OF_DONE.md` targets 3, 4, 6 and "judges each target on the worst repetition".
