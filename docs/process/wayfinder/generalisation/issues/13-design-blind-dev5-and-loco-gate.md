# The guard: design-blind dev5 and a leave-one-country-out gate for every rule

Type: grilling
Status: open
Blocked by: —
Map: ../map.md · HITL — the owner fixes the protocol that stops rules helping only sites already seen. Asked in round 1
beside 01, because dev5's first baseline (14) must already run under it.

## Question

Every rule since 2026-10-05 was designed on cases whose captures the author had open, and judged on the same sets.
dev4 was built as the country proxy and then used to tune R1, R2, LX-1 and the subject shapes — so by 2026-10-19 it
predicted nothing (dev4 gold returned 5/5; the nine 3–5/9). **How does dev5 stay a predictor, and what must a rule show
before it is called general?**

❓ **Q1** — **dev5 is design-blind for this map.** Rules are designed on cohort / dev2 / dev3 / dev4 captures. dev5
runs in every paired cycle, but its result is read **only through `scorecard --summary-only` and `stage_summary`**
(aggregates); its per-case rows, captures and logs are not opened by any worker or by the main session until the
owner says so (a dated line in this ticket's Answer), at the earliest after 15 is written. The first baseline (14) is
pre-registered: the offline ceilings of 10 and 11 are written down before it runs.

➡️ **Yes.** A fifth tuning set adds nothing; a blind set is the only honest predictor we can build without spending
a heldout look. Labels (03, 04) are made by experts who never see pipeline output, so labelling does not break blindness.

---

❓ **Q2** — **Default-on bar for every rule from now on** (adds to "no stable loss, no new wrong claim" and the
cycle-4c delegation): (a) a stable gain on at least one case **outside the set that motivated the rule**, or a
precision guard that fires on unseen pages by construction (its gain is measured under 07's knockout arm); (b) the dev5
aggregate (page hit/wrong/missed counts, readable core, precision) **not worse** on the on arm; (c) the rule's words,
shapes or thresholds are not copied from a single development page (12's count). A rule that fails (a) stays off and is
recorded `seen_site` in `hypotheses.json`; it may be re-tried only with a second motivating case from another set.

➡️ **Yes.** (a) is the guard the loop lacked; (b) is what dev5 is for; (c) is what makes R2/R5-style lexicons honest.

---

❓ **Q3** — **Leave-one-country-out as the prediction.** Before the second look, 15 computes, on the pooled
dev4 + dev5 baseline (14), target 6's row and the programme-page rows **leaving out each country in turn**
(Kazakhstan, Türkiye, Czechia, Germany, Italy, Lithuania; Estonia has one dev4 case only). The pre-registered
expectation for the nine is the **range** [min fold, max fold], not one number, and the second look reads "within
15 pp" against the pooled value *and* records whether the nine fall inside the fold range. If the fold spread itself
exceeds 15 pp, the map stops and the owner redraws target 6 or the proxy set (17).

➡️ **Yes.** A single pooled number hid that dev4 (0.22–0.25) and the cohort (0.74) disagreed by 50 pp; the fold range
makes the uncertainty visible before the look, not after.

---

❓ **Q4** — **Re-measuring the seen-site rules** (12's list) on dev5: one `expert_paired` run per rule on dev5 only
(aggregates), negative flag as `extra_args`; a rule with a dev5 loss is proposed default-off in 15; a rule with no
effect keeps its default. Budget: ≤ 12 runs (≈ 25 min each, in parallel with everything else).

➡️ **Yes, within the 15 hours.**

---

❓ **Q5** — **When dev5 stops being blind**: after 15 is written and the second look is dispatched (or the owner
stops the map), dev5's per-case rows open and it becomes the fifth development set; a dev6 is not commissioned by
this map.

➡️ **Yes.**

## Evidence

- `STAGE_SUMMARY_DEV_2026-10-19.md` dev4 section vs `HELDOUT_PREREGISTRATION_2026-10-18.md` §5 row 4′ (dev4 proxy
  0.22–0.38) and §8 (0/23); loop report R1 / R2 / R5 lines (motivating cases rwth, uba, iitd); finish-algorithm
  [01](../../finish-algorithm/issues/01-destination-denominator-judging.md) Q5 (the delegation this ticket extends).
- 12's ledger when it lands (counts of general / seen-site / unmeasured rules).

## Answer

(open — recorded when the owner answers; Q1's blindness line is dated here)
