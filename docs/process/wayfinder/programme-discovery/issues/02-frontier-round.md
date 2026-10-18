# Frontier round: the open decisions, breadth-first

Type: grilling
Status: open
Blocked by: 01
Map: ../map.md · HITL — one round, every question whose prerequisites the research tickets have settled.

## Question

With the destination fixed, which decisions are open now, and which of the agent's recommended answers does the
owner accept as-is? This is the breadth-first round the wayfinder skill asks for: the whole frontier, not one
thread deep. Each question below is also its own ticket (linked), so a "yes" closes that ticket as its
recommended answers stand, and a "no" or "talk" keeps it open for a deeper round.

❓ **Q1** - **Programme identity**: accept the recommended equivalence rule in
[What counts as the programme page found](03-programme-identity-equivalence.md) — a declared language twin,
a canonical variant (`/2027/`, `?lang=`, trailing slash), and an official sibling detail page of the *same
programme* count as found; a sibling *specialisation*, a *major* page, and another programme of the same
faculty do not count as found but are not wrong-page false positives either (they are reported as "related").

➡️ Yes.

---

❓ **Q2** - **A country-proxy development split (dev4)**: commission 8–10 universities in the heldout
countries, excluding the nine, labelled for the programme page (and its twin) only, as the development set for
local-language rules ([Country-proxy development split (dev4)](04-dev4-country-proxy-split.md)).

➡️ Yes.

---

❓ **Q3** - **The production identity gate is inside this design**, and the benchmark gets a second arm that
goes through `_identify_site` with the seed row, so the gate is measured
([Production site-identity gate: in the design, in the benchmark](05-identity-gate-in-design.md)).

➡️ Yes.

---

❓ **Q4** - **A bounded model as programme-page picker is out of this map** (rules first; the model is a later,
separately priced experiment under D9) ([Bounded model as programme-page picker](06-model-page-picker.md)).

➡️ Yes — out for now.

---

❓ **Q5** - **Query-language probes and the local-language family**: up to 300 Serper credits for the five
query shapes in [Approve a Serper probe budget and the query-language shape](07-serper-probe-and-query-language.md),
run from the GitHub runner once provider results are recorded; a shape that returns the gold (or its twin) in
the top 10 for ≥ 4 of the 6 local-language development cases becomes a flagged family that takes the third
first-pass slot, `programmes` moves to the reserve and `admissions` is dropped (six families stay six).

➡️ Yes.

---

❓ **Q6** - **The sitemap `keep()` rule may keep a URL on subject + level words alone** (no structural
programme word), under a cap ([Sitemap keep rule: evidence sum or structure first](18-keep-rule-evidence-sum.md)).

➡️ Yes.

---

❓ **Q7** - **Programme titles may carry a subtitle, a location or a form word and still name computer
science** ([Subject match on local programme titles](19-subject-title-shapes.md)).

➡️ Yes, with the listed shapes only.

---

❓ **Q8** - **A bounded local-catalogue entry route**: a homepage link may be followed on a study-section label
in the institution's language (two hops), local listing words become URL signals, and the sitemap of a
catalogue host on the same registrable domain may be read (≤ 3 documents)
([Local catalogue entry: section labels and the catalogue host's sitemap](20-local-catalogue-entry.md)).

➡️ Yes.

---

❓ **Q9** - **Research findings accepted as the factual base**: tickets 08–14 (resolved) are read as facts; the
loop takes the two defects they expose (search skipped after an early 33-second trigger — fix in flight as of
2026-10-18; the twin never recorded) as bug fixes needing no decision.

➡️ Yes.

## Notes

A "no" on any question reopens that ticket for its own grilling round; the dependent tickets (15, 16, 21) wait.
