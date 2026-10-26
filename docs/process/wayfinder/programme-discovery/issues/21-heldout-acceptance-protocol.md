# Acceptance protocol for the next heldout check

Type: grilling
Status: open
Blocked by: 15, 16
Map: ../map.md · HITL — fixes how, when and how often the nine are run again; the destination names it as part of the design.

## Question

The DoD (`docs/process/SEARCH_DEFINITION_OF_DONE.md`) says the heldout split is run once every three or four
enabled rules and never tuned on; the final check of 2026-10-17 (run 39103386295, four repetitions) read 0–1/9
programme pages. Each further run spends one of the few looks the nine can take before they become a
development set. Once the v3 design is agreed ([Prototype: the discovery plan v3](16-prototype-discovery-plan-v3.md))
and dev4 is signed ([Commission the dev4 programme-page labels](15-commission-dev4-labels.md)), under what
pre-registered conditions are the nine run, what may be read afterwards, and what does "pass" mean for DoD
targets 3 and 6?

❓ **Q1** - **When, and how often**: the nine run at most twice during this effort — once when every approved
rule of the design is on by default and has passed the paired-run bar on all four development sets (the
acceptance run), and once more only if the first fails and a fix with development-set evidence has landed. The
DoD's "every three or four rules" cadence is the ceiling, not the plan.

➡️ Yes — two looks is what the split can afford; the dev4 proxies are where iteration happens.

---

❓ **Q2** - **Pre-registered expectation**, written into the loop report before the run: (a) programme-page
recall on the readable heldout sites, under the identity rule of
[What counts as the programme page found](03-programme-identity-equivalence.md), within 15 pp of the cohort
(target 6's reference), with the pooled recall on the four development sets reported beside it; (b) every site
that refuses the runner reported `unavailable`, no page confirmed on it (target 3); (c) site identity
established through the identity-gate arm on every readable site; (d) no wrong-page confirmation (the
related-programme outcome does not count as wrong).

➡️ Yes.

---

❓ **Q3** - **Two arms, two repetitions**: the acceptance run uses today's harness entry and the
`--through-identity-gate` arm ([Production site-identity gate](05-identity-gate-in-design.md) Q3), two
repetitions each — four columns, as in the final check — so the product path is measured and a
one-repetition fluke cannot pass or fail the design.

➡️ Yes.

---

❓ **Q4** - **What may be read after the run**: the aggregate scorecard lines only — recall n/9, identity
established n/9, unavailable n/9, wrong page n, budget compliance. Per-case traces, logs, captures and rows
stay closed. A failed run is diagnosed on dev4 and the other development sets; opening heldout stage-level
aggregates (stage of loss, counts only, no URLs) is a separate, explicit owner decision, recorded on this map
if taken.

➡️ Yes — `DISCOVERY_ANALYSIS_2026-10-17.md` was written from heldout traces and the map already restricts its
use; a second such reading would make the nine a development set.

---

❓ **Q5** - **What "pass" means**: if (a)–(d) hold, DoD targets 3 and 6 are marked met for the programme page,
this map's destination is reached, and the loop moves on to the evidence stages (STRUCTURAL_ANALYSIS
Changes 2–3); if not, the design returns to the development sets with the aggregate numbers as the only
heldout input, and the second look is spent only as Q1 says.

➡️ Yes.

## Evidence

- `docs/process/SEARCH_DEFINITION_OF_DONE.md` targets 3 and 6 and the heldout cadence (L21, L24, L42);
  `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` "Final check" (four repetitions, aggregate only).
- Evidence policy of this map (`map.md`, Notes) and [Confirm the destination](01-destination.md) Q4.
