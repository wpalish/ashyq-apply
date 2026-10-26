# Core labels for dev4: the only development proxy for target 6

Type: task
Status: resolved
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

## Progress (2026-10-18)

Expert drafts for all nine cases in `backend/evaluation/research/expert/data/core_drafts_dev4.2026-10-18/`
(converter `backend/evaluation/research/expert/core_drafts_dev4.py`); `dev4.draft2.json` and
`identity_bindings.dev4-draft2.json` written; signing table `docs/process/SIGN_DEV4_CORE_2026-10-18.md`.
25 quotes offered; `verify_evidence.py` in the agent container verified 0/25 (robots.txt unreachable from the
container, ConnectError), so every core label is `unknown` until the `verify_evidence` workflow runs on the
drafts directory and the converter is re-run with `--evidence`.

## Answer

Owner (Диас), 2026-10-18: «Раунд 2 и 3: все как рекомендовано» — accept all dev4 core labels as drafted after the CI evidence check (25/25), except ktu gpa → `unknown` (02-Q7); rwth: add the Deutschlandstipendium award page as a second source URL; SIGN_DEV4 Q1 yes, Q2 unknown, Q3 as 02-Q4.

## Done

- `dev4.draft3.json` (`2026-10-18.dev4-draft3`) is signed: every case `human_verified`, reviewer Диас, with a
  CERTIFIED note (as `heldout.reviewed1` marks it). All drafted core labels accepted (CI evidence check 25/25);
  ktu `gpa` → `unknown` (prose, 02-Q7; value and URL kept in the note). `identity_bindings.dev4-draft3.json`
  binds the RWTH Deutschlandstipendium award page (`…/Bildungsfonds-Deutschlandstipendium/~goap/…`) as a second
  source URL of `scholarships.deutschlandstipendium`; it is now the workflow's dev4 extra-bindings file.
  dev4-draft2 stays frozen; VERSIONS.md entry; test `tests/test_signed_labels_09_10.py`.
- Re-scored base3-dev4 and an1b-dev4 (read-only): known core answered (readable) 2/9 → 2/8 on every rep
  (0.22 → 0.25; ktu gpa leaves the denominator). Award claims were not re-mapped: the captures hold no claim
  from the RWTH award page (it is classifier-rejected). Row in LOOP_REPORT, "Signed labels: tickets 09 and 10".
