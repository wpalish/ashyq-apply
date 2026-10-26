# Destination, the proxy reference and the rules of this map

Type: grilling
Status: open
Blocked by: —
Map: ../map.md · HITL — the owner confirms the destination and the measure the map aims at.

## Question

The heldout acceptance run read precision 0/3, programme page 1/9 (4 wrong), readable core 0/23, while every
development set reads precision 1.00 and page 3–8 of 5–10. The owner-approved stage aggregates say the loss is
reach (gold never returned 4–6/9) and confirm precision (4 wrong of 5 confirmed), on the registry-seed path. The
previous map's target-6 proxy (dev4) read nothing like the nine on the same countries. What is this map finding
its way to, and what does it measure itself against?

❓ **Q1** — **Destination as the map states it**: dev4 + dev5 predict the nine within 15 pp on target 6's row and on
the programme-page rows, under the production path for an unseen university, with a second look under 21-Q1 and no
rule tuned on the nine; done when dev5 is signed and baselined design-blind, each hypothesis has a development
verdict, confirmed causes have rules that pass the paired bar on five sets *and* the seen-site guard, and the
second-look pre-registration is written from dev4 + dev5.

➡️ **Yes.** The alternative — another round of rules on the four sets and a third look — is what produced two
failed looks; the destination makes *prediction* the deliverable, and a rule only counts when a set that did not
motivate it moves.

---

❓ **Q2** — **Target 6's reference for the second look = pooled dev4 + dev5** (the country proxies), with the pooled
five-set rate reported beside it. Today's DoD line (18-Q4) says "pooled cohort + dev2 + dev3 + dev4". A dated DoD
change-log line is needed.

➡️ **Yes.** The cohort and dev2/dev3 are English, Spanish, Nordic and Asian sites; the nine's countries are
represented only by dev4 and dev5. Predicting within 15 pp of a reference that does not share the nine's
languages is not a prediction. The five-set pooled rate stays as the secondary reading so the two DoD readings stay
comparable with 2026-10-19.

---

❓ **Q3** — **The map's own evidence policy**: only the two approved aggregate documents (§8/§10 of the
pre-registration, the H-1 stage table) are heldout inputs; they order tests, never design rules; any further number
about the nine is an owner decision asked in `OWNER_QUESTIONS.md`, never computed by a worker (no seed-URL check, no
bindings count, no registry-row read for the nine).

➡️ **Yes.** H-1 was granted for one read; stretching it would make the nine a development set.

---

❓ **Q4** — **The second look's two arms** are decided *now*, before any result: `off` = the registry path as today;
`on` = the nine entered as no-seed cases through production's identity gate (the path 481 of 500 catalogue
universities take). It is a harness change (`live.py`: the nine join `NO_REGISTRY_CASES` on the `on` arm with
`seed_entry` built from their top-500 rows), not a rule, and it is pre-registered in 15.

➡️ **Yes, pre-register both arms now; dispatch nothing.** The pre-registration of 2026-10-18 §1.1 already recorded that
the gate arm did nothing on the nine and asked for this decision *before* the next run. Deciding it before 06 and 11
report is what keeps it from being tuned on their results.

---

❓ **Q5** — **Seeds on the registry path.** If 06 shows the cohort's registry arm sends fewer discovery queries, confirms
more wrong pages or reaches the gold less than its no-seed arm, the product change "seeds are extra leads, never
slot-fillers; a registry institution runs the same discovery as an unseen one" is built behind a flag and measured on
the cohort's three arms. If 06 shows no difference, nothing is built.

➡️ **Yes, conditional on 06.** The registry is 19 rows; the product's generality lives in the no-seed path.

---

❓ **Q6** — **Serper probe budget for 08**: ≤ 300 credits, development cases only (dev4 + dev5 drafts), the LOCO
lexicon test's live arm. Without it, 08 is offline-only (lexicon ablation on recorded provider result lists).

➡️ **Yes, ≤ 300.** The 2026-10-18 probe (M5) cost the same and decided R5.

---

❓ **Q7** — **Stopping rule and time box**: the map hands over to a second-look pre-registration only when (a)–(e) of
the map's stopping rule hold; it stops short and escalates after the authorised 15 worker-hours, or after a rule
fails twice on the same cause; it spends no heldout look itself.

➡️ **Yes.**

## Evidence

- `docs/process/HELDOUT_PREREGISTRATION_2026-10-18.md` §8, §9, §10; `docs/process/HELDOUT_STAGE_SUMMARY_2026-10-19.md`;
  `docs/process/STAGE_SUMMARY_DEV_2026-10-19.md` (per-set funnel; dev4 gold returned 5/5, wrong confirms 0).
- `backend/evaluation/research/live.py` L190–215 (`CASE_DOMAINS`, `NO_REGISTRY_CASES`, the registry path for the
  nine and the cohort); `docs/process/wayfinder/programme-discovery/issues/12-identity-gate-offline.md` (the gate
  fails 8 of 15 development homepages; the benchmark bypasses it).
- `docs/process/SEARCH_DEFINITION_OF_DONE.md` target 6 and its 2026-10-18 change-log line (pooled reference).
