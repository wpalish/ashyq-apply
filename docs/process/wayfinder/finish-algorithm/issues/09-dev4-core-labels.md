# Core labels for dev4: the only development proxy for target 6

Type: task
Status: open
Blocked by: —
Map: ../map.md · AFK task with a HITL signature — agents run the experts and the checks; the owner signs the
table (round 2). Starts now on the five adjudicated cases (kit, ktu, rwth, ctu, unibo); the four unadjudicated
(vut, taltech, boun, itu) follow ticket 10.

## Goal

Target 6 compares **core coverage** on the heldout nine with the cohort; dev4 is the development set in the nine's
countries, and it has **no core labels** (`known core answered —` on every base2 repetition), so nothing today
predicts what the acceptance run will read on Czech, German, Turkish, Estonian, Italian or Lithuanian pages. Label
the six core questions (English test minimum, GPA/entry requirement, deadline, tuition, a scholarship exists, open
to an international applicant) for each dev4 case, with a source URL, a verbatim quote and the page language, in
the `Case` schema (`labels[]` with `status: known|unknown|not_applicable`, `evidence_url`, `population`, `period`
per ticket 02 Q4), plus the identity bindings for award pages.

## Protocol

1. One expert sub-agent per university (Track A, `SEARCH_FINISH_PLAN_V2.md` §4): official domains only, no bypass,
   no heldout artefact in its context, no applicant attribute in any query; `university-admissions-research` and
   `scholarship-audit` skills; a value without a quote is `unknown`.
2. `scripts/verify_evidence.py` on every quote with the production fetcher (workflow mode `verify_evidence`); a
   failed quote stays `unknown`; PDF-only evidence is labelled with its URL and flagged `pdf` (leaves the readable
   denominator under 01 Q2 but stays on record).
3. The agent writes `dev4.draft2.json` (labels added, programme rows unchanged) and `identity_bindings.dev4-draft2.json`;
   the scorecard's dev4 column then shows `known core answered n/N` on a re-score of base2-dev4 (no run needed).
4. **Owner signs** the table in round 2 (`OWNER_QUESTIONS.md`), per case: accept / edit / unknown.

## Files (the lock)

`backend/evaluation/research/data/dev4.draft2.json`, `identity_bindings.dev4-draft2.json`, `live.py` (dataset
version string only). No pipeline file.

## Done when

- Signed `dev4.draft2.json` with ≤ 9 rows × 6 questions, every `known` label quote verified; the loop report gets
  the dev4 "known core answered" row on base2 and on the latest defaults run; the languages of the evidence pages
  are reported to ticket 07.

## Evidence

`scratchpad/runs/base2-dev4/sc.md` (`known core answered 0/0`); previous map
[Commission the dev4 programme-page labels](../../programme-discovery/issues/15-commission-dev4-labels.md) (the
programme-page protocol this extends); DoD target 6.
