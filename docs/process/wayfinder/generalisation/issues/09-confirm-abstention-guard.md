# The guard rule: when the gold is absent, confirm abstains instead of confirming a sibling (CA-1)

Type: task
Status: open
Blocked by: 07
Map: ../map.md · AFK — the one product rule this map expects to build; flag off → one paired run per set (five once dev5
is baselined) → default-on only with no stable loss, no new wrong claim, and the seen-site guard of 13. Effort: high
(a hard pipeline rule, LOOP_PROTOCOL).

## Goal

DoD target 3: "the programme page is found on every site the run can read; a site that refuses us says *unavailable*,
never a guess." Ticket 07 measures how often identity recovery confirms a sibling when the gold is unreachable; its
refusal-rule table says which signal would have refused each wrong confirm. This ticket turns the signals that catch
≥ 2 development wrong confirms — and cost no hit — into one flagged rule.

## Shape (to be fixed by 07's table; the candidates, from the stage rows)

Identity recovery (`_recover_search_pages`) and the confirm predicate (`_confirm_programs`) confirm a candidate only
when the page *itself* carries the identity — not its URL slug, not the lead's family:
1. the page's title or `h1` names the subject (English or a local shape the page's own `<html lang>` admits) **and**
   the degree level; a URL-only subject match is a lead, not a confirmation;
2. a candidate that only one lead family returned, at rank > 3, is not confirmed on its own: it needs a second
   independent signal (a second family, the sitemap, a catalogue listing that links it, or a declared twin);
3. a catalogue hub, faculty or department page (`reads_as:program_catalog`, `navigation_lead_no_subject`) is never
   confirmed as the programme page, however good the subject words (FP-1 did this for the front page);
4. when nothing passes, discovery ends with `programme unresolved` and the evidence stages run on the admissions and
   fees hosts without a programme scope — claims then carry no programme and the scorer's `other_scope` /
   `unlabelled` reading applies, which is honest, instead of claims scoped to a wrong programme.

Flag `CONFIRM_REQUIRES_PAGE_IDENTITY = False` (`--confirm-requires-page-identity`), loop id **CA-1**; one flag, the
sub-rules on by the flag together (07's table decides which of 1–3 are in).

## Bar

- Knockout arm (07's flag) **plus** CA-1 on every set: wrong confirms → 0 with the gold refused (`case_outcome:wrong`
  0, the cases read `missed`), no case over budget.
- Normal arm with CA-1 on: no stable loss of a hit on cohort / dev2 / dev3 / dev4 (and dev5 aggregate not worse), no
  new wrong claim; `confirmed_pages_wrong` on the cohort (3–5 today, beside the gold) goes down.
- The golden demo (`seed_demo.py`, brief §5.7 order) unchanged.
- Seen-site guard (13): the gain is a *precision* gain on cases that did not motivate it — by construction it is
  measured on all 44 development cases under knockout; record which sets improved.

## Files the worker holds

`backend/app/adapters/discovery/live_discovery.py` (`_confirm_programs`, `_recover_search_pages`, the new flag; nothing
else in the file), its tests (`tests/test_recovery_lead_order.py`, a new `tests/test_confirm_page_identity.py`),
HANDOFF §8 line. Does not touch `intent.py` (08/LQ-2), `page_classifier.py`, the evidence stages or the scorer.

## Evidence

- 07's deliverable `GOLD_KNOCKOUT_2026-10-19.md` (the refusal-rule table); `HELDOUT_STAGE_SUMMARY_2026-10-19.md`
  (`lead_rejected_sample:navigation_lead_no_subject 40`, `degree_level_other 45–47`, `confirmed_url_hint:en 3–4` of 5
  confirmed — the confirmed pages were English pages); `live_discovery.py` L2007 (`FRONT_PAGE_NOT_PROGRAMME`, the
  precedent for a confirm guard), L3994 / L4832.

## Done when

Paired runs on every set with CA-1 off/on, both normal and knockout arms, read by the bar above; `LOOP_REPORT` line;
HANDOFF §8 line; default-on or rejected with the cause recorded in `hypotheses.json`. Loop id: **CA-1**.
