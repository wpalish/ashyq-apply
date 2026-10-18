# Map — Finish the search algorithm (every DoD target, then the heldout acceptance)

Label: `wayfinder:map` · Tracker: local markdown (`issues/NN-<slug>.md`; `Type:`, `Status:`, `Blocked by:` lines)
· Charted 2026-10-18 by the planner agent at the owner's request. **Extends**
[Programme-page discovery on unseen universities](../programme-discovery/map.md): that map's destination (the
discovery-v3 design) is reached — R1, R2+R2b, R5, R6 are on by default, R3/R4 rejected — and its open tickets
[Commission the dev4 programme-page labels](../programme-discovery/issues/15-commission-dev4-labels.md) and
[Acceptance protocol for the next heldout check](../programme-discovery/issues/21-heldout-acceptance-protocol.md)
(protocol decided by the owner: ≤ 2 looks, two arms × two repetitions, aggregates only) are inherited here, not
re-decided. Owner (Диас) answers every HITL ticket; agents only recommend.

## Destination

**Every target of `docs/process/SEARCH_DEFINITION_OF_DONE.md` met on the four development sets (cohort, dev2,
dev3, dev4) by the scorecard's own rows, then accepted on the heldout split under ticket 21's protocol — as fast
and as cheaply as possible.** "Fast" means parallel AFK tickets with disjoint files, each one flag-off → one paired
run on all four sets → default-on with no stable loss and no new wrong claim, and no ticket ever waiting on the
owner (HITL questions are batched in `OWNER_QUESTIONS.md`). "Cheap" means no rule is attempted on a loss class
the plan has already named unreachable without an access, provider or model change — those are escalated, not
built. The map is done when either the acceptance run passes or the owner has decided what to do with each target
the rules cannot reach.

## Notes

- **Where we stand (clean baseline 2, every rule on, 4 repetitions; `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` tail; scorecards `scratchpad/runs/base2-{cohort,dev2,dev3,dev4}/sc.md`).**
  Targets **1, 2, 5 met** on all four sets (precision 1.00, wrong scope 0, 0 cases over budget). **Target 3**: programme
  page cohort 5–6/10, dev2 2–5/6, dev3 7–9/11, dev4 3–4/5; wrong page in some repetitions toronto, hku, tcd; missed
  toronto (403 on 22/23), kaist (opaque URLs, department host), tsinghua (other registrable domain), kuleuven
  (BLOCKED 12/12), ub (13/18 failed), unibo and ctu (gold returned, never read), flaky uba/uio; aalto BLOCKED.
  **Target 4 — the binding gap**: known core answered cohort 11–12/28, dev2 4–5/21, dev3 8/28 → **23–25 of 77
  (≈31%) against ≥ 80%**; dev4 has no core labels. Found-page-but-unanswered: groningen 3/5, ntu 1/5, warsaw 0/2,
  ethz 0/2, uppsala 2/4, tcd 2/4, unsw 0/3, chula 0/3, auckland 2/4, um 1/2, puc 0/1, ucph 0/1. 12 cases have no
  programme label (tec, kaznu, uct, khalifa, utokyo, ntutw, msu, usp, vut, taltech, boun, itu). **Target 6** is
  unmeasured until the acceptance run.
- **The arithmetic that shapes this map.** `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` puts the losses our own
  code can fix at ~18 questions (readers, classifier order, index budget, one-link-away pages — the in-flight
  workers C and D); 10 questions sit on access-blocked hosts (aalto, toronto, hku admissions, kaist, kaznu); 3–4 gpa
  labels are reviewer prose no reader can emit; 3 chula labels belong to another programme than the one confirmed;
  the rest are on client-rendered lists, other registrable domains, PDFs or non-English evidence pages. Even with
  every code fix landed the pooled rate is ≈55–65% on today's denominator. So **the denominator and corpus decisions
  (tickets 01, 02) are the critical path**, not another rule; they are asked first and in one round.
- **Domain.** Discovery `backend/app/adapters/discovery/live_discovery.py`, search `backend/app/adapters/search/*`
  (`retrieval.py` ranks), classifier `backend/app/adapters/page_classifier.py`, evidence stages
  `backend/app/adapters/{web_requirements,web_scholarships,extraction,structured_extraction}.py`, runner
  `backend/app/pipeline/runner.py` (`CORE_QUESTIONS`), production entry `backend/app/catalogue/discovery.py`.
  Measurement `backend/evaluation/research/{live.py,scorecard.py,metrics.py,identities.py}`; gold
  `backend/evaluation/research/data/{ground_truth.reviewed10,dev2.draft1,dev3.draft1,dev4.draft1}.json` and
  `identity_bindings.*`; the workflow `.github/workflows/benchmark-capture.yml` (`expert_paired`, 2 reps per arm,
  ~25 min wall clock per set, `case_parallelism 5`).
- **Working model (owner, 2026-10-18).** A planner charts and decomposes; parallel workers (each in its own
  worktree, medium effort) execute AFK tickets; each rule flag-off → paired runs on cohort/dev2/dev3/dev4 →
  default-on only with no stable loss and no new wrong claim (owner delegation as in cycle 4c, confirmed in ticket
  01); the loop never waits for the owner. **Disjoint files per parallel ticket** — the file list in each ticket is
  the lock; a worker that needs a file another open ticket names waits for that ticket or lands behind it.
- **In flight right now (tickets 11–15, `Status: claimed`).** A — wrong/missed pages toronto/hku/kaist/tcd;
  B — missed pages tsinghua/kuleuven/ub/iitd/uio/uba/ctu; C — core gaps groningen/ntu/warsaw/ethz/uppsala/tcd;
  D — core gaps unsw/chula/auckland/um/puc/ucph; E — label proposals for the 12 unadjudicated cases. Nothing on
  this map duplicates them; tickets 05–06 and 16 build on what they leave.
- **Standing rules (brief §7.4, AGENTS §6, DoD).** No robots bypass, no UA spoofing, no proxies; no applicant
  attribute in any query; 6 queries / 60 HTTP requests / 120 s per university; nothing sent to an LLM beyond the
  privacy table; `Fetcher` never weakened. Not decisions on this map.
- **Evidence policy.** The heldout nine (`nu metu sabanci charles masaryk tum tartu polimi vilnius`) are never
  opened — no gold, draft, capture, log or per-case row; only ticket 19 runs them, and reads aggregates only.
  Design evidence comes from the four development sets and from code.
- **Skills every session consults.** `grilling` + `domain-modeling` for every HITL ticket (numbered questions, a
  recommended answer each, wait for the owner); `research` for AFK research tickets; `loop-engineering` runs the
  AFK task tickets (flag-off, paired run, bar); `scholarship-audit` on any award label touched in 02 or 09.
- **Tracker conventions.** Claim = `Status: claimed` before any work; resolve = `## Answer`, `Status: resolved`,
  one gist line below. HITL tickets stay `open` until the owner answers through `OWNER_QUESTIONS.md` (Russian).
  Every AFK task ticket proposes its flag name and loop id; the worker registers the final name in HANDOFF §8.

## Decisions so far

<!-- one line per closed ticket: gist, then the link holds the detail -->

- [Destination, denominator, judging](issues/01-destination-denominator-judging.md): owner, all yes — target 4 on `core_known_readable`; per-rep `unavailable` for targets 3/4; stopping rule; ≤5 workers + delegation; one heldout look.
- [Corpus corrections](issues/02-corpus-corrections-round.md): owner, all eight yes — applied: reviewed11 / dev2-draft2 / dev3-draft2, ID-1 aliases on, fee period in the scorer; re-scored cohort known core 11–12/28 → 14–15/27, dev3 8/28 → 8/22, but dev2 4–5/21 → 3–4/21 with **one new wrong claim** (Uppsala: the pipeline now reads the national 15 April, the signed gold is the international 15 January) — a deadline-reader task, not a label.
- [Targets 3 and 4 as scorecard rows](issues/03-targets-3-4-scorecard-rows.md): done — `programme_found_on_readable`, `wrong_programme_pages`, `core_known_readable_rate` judged on the worst repetition with per-repetition `unavailable`; DoD change-log line dated 2026-10-18.
- [Repetition variance](issues/04-repetition-variance.md): 13 of 35 cases flip across 8 identical repetitions; host-caused only kuleuven, unibo (one rep), toronto's page; the rest are provider rank or stage order (ours). 2 reps per arm ≈ 1.1 false stable items per 4-set cycle; 17 uses 4.
- [Returned, never read](issues/05-returned-never-read.md) → [Family-agreement rule](issues/06-retrieval-family-agreement.md): no single rank rule reads the gold on ≥ 2 of unibo/ctu/tcd/unsw/ubc without a predicted loss (ethz 4/4, warsaw, uba); 06 closed "not built"; the five go to the residue.
- [Non-English evidence count](issues/07-non-english-evidence-count.md): 16 of 77 known core questions sit behind non-English pages; 13 are never fetched, the 3 fetched are already English twins — any language route gains 0 today; 08's recommended answer is "build nothing now".
- [Residue ledger](issues/16-residue-ledger.md): **go to 17** — every stable target-3/4 loss is in a named class (not linked / client-rendered 9, non-English 9, other host 4, other domain 3, returned-not-read 3; pages kaist, tsinghua, ctu, unibo); ours-still is 4 questions + ubc's page and flips no target; pooled readable ≈ 0.44 → ≈ 0.49 after DL-6, ceiling ≈ 0.56; Table C for 18 pre-filled; dev4 (target-6 proxy) 0.22.

## Ticket order, parallel groups and the critical path

| group | tickets | runs in parallel with | wall-clock note |
|---|---|---|---|
| **G0 owner round 1 (HITL, batched)** | [01](issues/01-destination-denominator-judging.md), [02](issues/02-corpus-corrections-round.md) | everything below; nothing waits on them except the *reading* of 03's second column | one sitting; the recommended answers are written so that "да" accepts them |
| **G1 measurement (AFK, no pipeline risk)** | [03](issues/03-targets-3-4-scorecard-rows.md), [04](issues/04-repetition-variance.md), [20](issues/20-run-throughput-and-credits.md) | G2, G3, the in-flight workers | 03 is needed before 17 is read; 04 feeds 01-Q3; 20 tells how many workers can run at once |
| **G2 in flight (AFK, claimed)** | [11](issues/11-worker-a-wrong-missed-pages.md), [12](issues/12-worker-b-missed-pages.md), [13](issues/13-worker-c-core-gaps.md), [14](issues/14-worker-d-core-gaps.md), [15](issues/15-worker-e-label-proposals.md) | each other (disjoint cases; files per ticket) | each rule ≈ 25 min × 4 sets; see 20 for concurrency |
| **G3 new AFK research → task** | [05](issues/05-returned-never-read.md) → [06](issues/06-retrieval-family-agreement.md); [07](issues/07-non-english-evidence-count.md) → HITL [08](issues/08-non-english-evidence-route.md); [09](issues/09-dev4-core-labels.md) | G1, G2 | 06 touches `retrieval.py` only (disjoint from A/B); 09's experts run now on the 5 adjudicated dev4 cases |
| **G4 owner round 2 (HITL)** | [10](issues/10-sign-unadjudicated-labels.md) (when E delivers), [08](issues/08-non-english-evidence-route.md) (when 07 delivers), 09's signature | — | one sitting again |
| **G5 exit gate (AFK)** | [16](issues/16-residue-ledger.md) → [17](issues/17-clean-baseline-3-development-exit.md) | — | one defaults run on four sets (~25 min) after the last G2/G3 rule lands |
| **G6 escalation (HITL, only if 17 says a target is not met)** | [18](issues/18-escalation-unreachable-targets.md) | — | the per-target options are pre-written in 16 so the round is one table |
| **G7 acceptance (AFK)** | [19](issues/19-heldout-acceptance-run.md) | — | two arms × two repetitions on the nine (~25 min); aggregates only; DoD change log entry |

**Critical path**: 01 (denominator) → 03 (rows) → [G2 + 06 land] → 02 signed → 16 → 17 → 19. The longest
chain by wall clock is the in-flight evidence work (C, D: several paired runs each) — nothing on this map can
shorten it except *not* adding rules behind it, which is why 16 names the residue before any new evidence rule is
proposed. **Minimal path to the acceptance run**: 01 + 03 + 02 + whatever of G2/06 passes its bar + 17 green → 19.
Tickets 07/08/09/10 improve the *honesty* of targets 4 and 6 but are not on the path unless 17 fails on target 4.

**Stopping rule per target** (detail in [01](issues/01-destination-denominator-judging.md) Q4 and
[16](issues/16-residue-ledger.md)): a target is declared unreachable by rules — and escalated in 18, not retried —
when every remaining loss on the development sets belongs to a named class: **access** (robots unreachable, 403,
challenge, dropped connections, certificate refusals), **other registrable domain**, **SPA / PDF-only**,
**client-rendered list**, **department host the homepage never links / opaque URLs**, **non-English evidence page**
(pending 08), **gold identity / prose label** (pending 02). Two failed paired runs of a rule on the same cause is
also a stop (DoD loop rule; recorded in `hypotheses.json`).

## Not yet specified

<!-- in-scope fog: questions coming, not yet sharp enough to ticket -->

- **A model-based extractor for the six core questions** (D9, proposer-only, priced per university) — only if
  [Decide the route for non-English evidence](issues/08-non-english-evidence-route.md) picks it or
  [Escalation](issues/18-escalation-unreachable-targets.md) opens it; the shape (which pages, which privacy table
  rows, how it is paired-run) is not specifiable before that.
- **Opaque-URL and department-host discovery** (kaist `cs.`, ntutw `csie.`): carried over from the previous map's
  fog; enters only if dev4 or worker A shows the shape on ≥ 2 readable cases.
- **Stage order on slow hosts** (SO-1/SM-1 re-measure after SB-1c): read off 04's variance analysis; ticketed only
  if a flaky case's cause is order, not the host.
- **What "unavailable" and "related" look like in the product payload** — after acceptance; the trace and the
  benchmark `Observation` carry them today.
- **A second development round for dev4 core evidence** — only after 09 shows how many dev4 core labels are known
  and whether the heldout countries' evidence pages are English.

## Out of scope

<!-- ruled beyond the destination; never graduates -->

- **Access bypass of any kind** and **Track E (another runner)** — infrastructure; a site that refuses is
  `unavailable` by definition (previous map, 01 Q5).
- **Changing the budget** 6 / 60 / 120, **the search provider**, **the browser tier** (01 Q6 of the previous map).
- **New DoD targets or raising/lowering a threshold** without the owner's dated entry — this map asks (01, 02, 18),
  it never edits the DoD on its own.
- **Registry seeds or per-institution hardcode** for any development or heldout case.
- **The product UI/payload changes** behind "related", "unavailable", twins, `site_identity.proof`.
- **Document stage / post-approval labels** (13 unmeasurable document labels) — not in the six core questions.
