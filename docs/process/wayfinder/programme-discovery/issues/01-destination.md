# Confirm the destination and its boundaries

Type: grilling
Status: resolved
Blocked by: —
Map: ../map.md · HITL — the owner (Диас) answers; the recommended answers below are the agent's, not decisions.

## Question

What is this map finding its way to? The destination fixes the scope of every other ticket, so it is settled
first. Three readings of "solve: for unseen universities the programme page itself is not found" are possible,
and they lead to different maps.

❓ **Q1** - **The destination is a design, not a build**: this map ends with an owner-approved
*programme-discovery v3 design* — the ordered list of flagged rules (each with its precision guard and the
development case that motivates it), the measurement changes needed first, and the acceptance protocol for the
next heldout run — and the loop (`loop-engineering`, paired runs, one rule at a time, owner approval per rule)
then builds it outside this map. Alternatives: (a) the map carries execution too (every rule built and
measured inside wayfinder tickets); (b) the destination is only a *decision*, e.g. "accept partial coverage
and change DoD target 3".

➡️ Yes — a design handed to the loop. The loop already exists and is good at the build; what is missing is
the decision layer (which pages count, which language rules, which measurement first). Execution inside the
map would re-create the loop with worse tooling. Option (b) is premature: the research tickets found concrete,
fixable mechanisms (a stage-order defect, a lexicon gate, an identity gate), so the DoD does not need redrawing
yet.

---

❓ **Q2** - **"Unseen university" means the production path, not just the benchmark**: the design must work
for a university outside the 19-entry registry *as the product sees it* — through `CatalogueDiscoveryAdapter`
(site identity from the seed row, no seeds, 481 of 500 seed rows) — not only for the harness's `dev2_entry`
shortcut that hands discovery a verified homepage. Research found the production identity gate fails on 8 of
15 conclusive development homepages
([Production site-identity gate on development homepages](12-identity-gate-offline.md)).

➡️ Yes. Otherwise the heldout check can pass while the product still never starts discovery for a university
whose homepage title is in Czech, German, Turkish or Kazakh — which describes the heldout countries.

---

❓ **Q3** - **Target: DoD targets 3 and 6 for the programme page only.** This map stops at "a confirmed
programme page (or an honest *unavailable*)"; core-question coverage (target 4), extraction, awards, and the
precision of claims read *after* the page is found stay with STRUCTURAL_ANALYSIS Changes 2–3 and are out of
scope here.

➡️ Yes. The final heldout check says the page itself is the binding gap; mixing the evidence stages in would
make every ticket twice as large and every paired run twice as hard to read.

---

❓ **Q4** - **The heldout quarantine stays absolute for this effort**: no ticket opens heldout gold, drafts,
captures, logs or per-case rows; design evidence is the three development sets and the code; the nine are run
again only under the acceptance protocol (fog item) and only a few times.

➡️ Yes. Tuning on the nine would make target 6 unmeasurable for good; the country-proxy split
([Country-proxy development split (dev4)](04-dev4-country-proxy-split.md)) is the lawful way to learn about
those sites.

---

❓ **Q5** - **Out of scope, confirmed**: access-blocked hosts (robots unreachable, 403, Cloudflare, dropped
connections — "unavailable" by definition, no bypass), the 6/60/120 budget, the production 300 s limit,
provider replacement, registry seeds or any per-institution hardcode for the nine.

➡️ Yes to all five. Each is either an invariant (brief §7.4), an owner decision already taken (Serper,
2026-10-17), or infrastructure (Track E).

---

❓ **Q6** - **The browser tier is outside this design**: every rule is specified for the HTTP tier the
benchmark runs (`UNIMATCH_ENABLE_BROWSER_TIER=false`); JS-rendered catalogues (tec's SPA) and PDF-only study
plans (uba, utokyo) are reported *unavailable* or *unresolved* by this design, never guessed, and a browser-tier
arm is a later, separately measured effort.

➡️ Yes. DoD target 3 is measured on the HTTP tier; a tier that is off in every capture would make the paired
runs unreadable, and the development misses are not browser problems (tec's English programme page *was*
returned and read — [Where the programme page is lost today](08-loss-stages-today.md), classifier note).

## Notes for the owner

"Yes" to every question accepts the Destination as written on the map (and moves Q6's tier to the map's Out of
scope). A "no" on Q1 or Q2 redraws the map before any other ticket is taken.

## Answer

2026-10-18, the owner (Диас): **yes to all six as recommended** (01-Q1 … 01-Q6).

- Q1: the destination is the programme-discovery v3 **design**, handed to the loop; the map builds nothing.
- Q2: "unseen university" means the production path (`CatalogueDiscoveryAdapter`, no seeds), identity gate included.
- Q3: scope is DoD targets 3 and 6 for the programme page only; evidence stages stay in STRUCTURAL_ANALYSIS Changes 2–3.
- Q4: the heldout quarantine is absolute; the nine run only under the acceptance protocol (ticket 21).
- Q5: out of scope: access-blocked hosts, the 6/60/120 budget, the 300 s limit, a provider change, seeds or hardcoding for the nine.
- Q6: the browser tier is outside this design; SPA and PDF catalogues are marked unavailable/unresolved.
