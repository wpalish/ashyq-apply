# Decide the route for non-English evidence pages

Type: grilling
Status: open
Blocked by: 01, 07
Map: ../map.md · HITL — owner round 2. Opens when ticket 07's table exists; the recommended answer below is
rewritten with 07's numbers before it is put to the owner.

## Question

Ticket 07 counts the known core questions whose evidence is published only in the institution's language and
sorts them by route: (i) the page's declared English twin, (ii) per-language keyword tables for the six
questions, (iii) a model extractor under D9, or none. Under 01 Q2 these questions **stay in the target-4
denominator** (the site publishes and lets us read them). Which routes does the owner approve, in which order,
and what is the stop for each?

❓ **Q1 — Route (i) first, as one flag**: the evidence stage follows a question page's or award page's declared
`hreflang="en"` twin on the same registrable domain, one read, and reads the twin with today's readers; the trace
records `evidence_twin`. Flag proposal `EVIDENCE_TWIN_FOLLOW` (`--evidence-twin-follow`, loop id ET-1); files
`web_requirements.py`, `web_scholarships.py`, tests. Bar: stable gain ≥ 1 question, no stable loss, 0 new wrong
claims, reads not above the off arm by more than one per followed twin.

➡️ Yes if 07 shows ≥ 2 questions reachable this way; otherwise skip (i).

---

❓ **Q2 — Route (ii) second, as one commit for every language** (16-Q5 rule): the six questions' label words per
language in one `languages.json`-style table, dictionary-grade, the heldout countries' languages included as
translations and checked on dev4 only; month names and decimal commas handled in the date/number readers for all
languages at once; flag `LOCALIZED_EVIDENCE_READERS` (`--localized-evidence-readers`, LE-1); files `extraction.py`,
`structured_extraction.py`, `web_requirements.py` (question-link words), tests on the hand-fetched pages from 07.
Bar as Q1 plus: no new wrong value on any English page (the readers must not loosen for English).

➡️ Yes if 07 shows ≥ 3 questions reachable this way; it is the only route that also helps target 6 on the heldout
countries' pages without opening them.

---

❓ **Q3 — Route (iii), the model extractor**: not in this map unless Q1 + Q2 leave ≥ 20% of the readable target-4
denominator behind non-English evidence after 17; then it opens as its own priced experiment (proposer-only, the
verifier confirms every value against the page text, privacy table unchanged), on the development sets only.

➡️ Yes — rules first; the model is the escalation option in 18, with its price written down there.

---

❓ **Q4 — Stop**: a question whose evidence page has no English twin and whose language has no entry in (ii)'s
table after the one commit is **residue**, named in 16 by case and class (`non_english_no_route`); it is not
removed from the denominator, and the map does not add a per-case word for it.

➡️ Yes.

## Evidence

Ticket 07's table; `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` §1 A6 rows; previous map
[Prototype the discovery v3 plan](../../programme-discovery/issues/16-prototype-discovery-plan-v3.md) 16-Q5
(one table, every language at once).
