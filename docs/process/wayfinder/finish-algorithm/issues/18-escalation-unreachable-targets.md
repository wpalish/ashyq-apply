# Escalation: targets the rules cannot reach — the owner chooses per target

Type: grilling
Status: resolved
Gist: owner (a), (a), yes, pooled — targets 3 and 4 recorded "not met" in the DoD change log (2026-10-18) with the residue by class (3: kaist, tsinghua, returned-not-read 4, flaky 6; 4: pooled readable 124/255 ≈ 0.49, residue 9 / 9 / 4 / 3 / 3 + ours 4), no measure change; the model extractor only as a separate map paired with a reach rule; the acceptance run (19) proceeds; target 6 reads the nine against the pooled development sets (primary) and the cohort (secondary) — both pre-registered in `docs/process/HELDOUT_PREREGISTRATION_2026-10-18.md`.
Blocked by: 17
Map: ../map.md · HITL — opened **only if** ticket 17 reports a target not met. The option table is pre-filled by
ticket 16 (Table C) so this round is one sitting; the questions below are the shape, the numbers come from 16.

## Question

For each target 17 marks "not met", every remaining development loss is in a named class the map has already
declared unreachable by a rule (01 Q4). The owner picks, per target, one of: (a) **accept and record** — the DoD
status table says "not met; residue: <classes with counts>" and the map proceeds to the acceptance run with that
residue pre-registered; (b) **redefine the measure** — a dated DoD change-log line with the exact wording 16
proposes (e.g. "target 4 excludes labels whose evidence page is in a language the readers have no table for");
(c) **one non-rule change** — the model extractor experiment (D9, priced in 07/16), a Track E runner for the access
class, or a provider parameter — as a new effort with its own map, not a resumption of this one.

❓ **Q1 — Target 3 (programme page on readable sites)**: expected residue classes — department host / opaque URLs
(kaist), other registrable domain (tsinghua), host flakiness. Recommended: **(a)** for kaist/tsinghua (the DoD's
"never a guess" is kept; the residue is named), **01 Q3** already handles flakiness.

➡️ (a).

---

❓ **Q2 — Target 4 (≥ 80% known core answered)**: expected residue classes — client-rendered lists (groningen,
ethz), other host (unsw, warsaw), non-English evidence without a route (08), prose/identity labels (02).
Recommended: **(a)** if the readable rate is ≥ 70% with the residue named; **(c) model extractor** as a *separate*
priced effort only if non-English evidence alone is ≥ 20% of the readable denominator; never (b) beyond 01 Q2.

➡️ (a), with (c) opened as its own map if 16's numbers say so.

---

❓ **Q3 — Does the acceptance run (19) go ahead with a target recorded "not met"?** Recommended: yes — target 6
(heldout within 15 pp of the cohort) is measurable regardless, and the heldout look is the only way to learn
whether the residue classes are the same on unseen sites; the pre-registration states the development numbers
*with* the residue.

➡️ Yes.

## Evidence

Ticket 16 Table C; DoD "Changing a target needs the owner's approval and is recorded here with the date".

## Answer

Owner (Диас), 2026-10-18: «Раунд 2 и 3: все как рекомендовано» — 18-Q1 (a) record target 3 not met with the residue by class; 18-Q2 (a) record target 4 not met (≈48 % readable, residue by class), no measure redefinition, model extractor only as a separate map with a reach rule; 18-Q3 yes, the acceptance run proceeds; 18-Q4 target 6 compares the nine with the pooled development sets, both readings pre-registered.
