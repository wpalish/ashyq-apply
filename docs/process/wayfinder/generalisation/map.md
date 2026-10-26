# Map — Generalisation: why the development sets did not predict the heldout, and how to make them

Label: `wayfinder:map` · Tracker: local markdown (`issues/NN-<slug>.md`; `Type:`, `Status:`, `Blocked by:` lines)
· Charted 2026-10-19 by the planner agent after the heldout acceptance run (finish-algorithm ticket
[19](../finish-algorithm/issues/19-heldout-acceptance-run.md)) read far outside every pre-registered range.
**Extends** [Finish the search algorithm](../finish-algorithm/map.md) (targets 1, 2, 5 met on development; 3, 4
recorded "not met" with residue; acceptance failed) and [Programme-page discovery](../programme-discovery/map.md)
(the v3 design, on by default). Owner (Диас) answers every HITL ticket through `OWNER_QUESTIONS.md` (Russian); agents
only recommend.

## Destination

**A pipeline and a development procedure such that the pooled country-proxy sets dev4 + dev5 predict the heldout
nine within 15 pp** — on target 6's row (`core_known_readable_rate`) and on `programme_found_on_readable` /
`wrong_programme_pages` — **under the path the product actually takes for an unseen university, and a credible
second look under programme-discovery 21-Q1** (a fix with development-set evidence landed and passed its paired bar on
every development set, pre-registered again before dispatch), **without any rule tuned on the nine.** "Predict" means:
before the second look, a leave-one-country-out reading of dev4 + dev5 gives a range, and the nine's aggregate falls
inside it. The map is done when (a) dev5 is signed, baselined design-blind and in CI; (b) each of the six hypotheses
below has a development-side verdict with numbers; (c) the confirmed causes have flagged rules that passed the paired
bar on all five sets *and* the seen-site guard (ticket 13); (d) the second-look pre-registration is written from
dev4 + dev5 — or the owner has decided that target 6 cannot be predicted by any development set and redrawn it.

## Notes

- **What the heldout read (aggregates only; `HELDOUT_PREREGISTRATION_2026-10-18.md` §8 and §10, the owner-approved
  H-1 stage table `HELDOUT_STAGE_SUMMARY_2026-10-19.md`).** Worst column: precision 0/3, wrong scope 3/3 (one on the
  degree dimension; two are wrong values), programme page on readable 1/9 with **4 wrong pages** and 4 missed,
  readable core 0/23 (any-answer 10–11/54), 0 unavailable (8 REACHED, 1 PARTIALLY_BLOCKED), budget met. Stage
  table: the gold programme page is **never returned by search in 4–6 of 9**; identity recovery confirms 5 pages,
  **4 wrong**; all nine run on the **registry-seed path** (19 seeds, identity gate not exercised); discovery sends
  only **2.3–3.0 queries per case** (three families; `courses`/`programmes`/`undergraduate` 0–1 in total) while
  dev4 sends 3.7–4.0 with every family; `read_refused:subject_mismatch` 16–18 and `reads_as:unknown` 5–17 per
  column; 37–44 claims, 3 matched to a label, 2–7 `unmapped.scholarship_exists`; costs pages fetched ok 1–2 of
  16–19. **These numbers order the hypotheses and tests below; no rule is designed against them.**
- **The development reference (`STAGE_SUMMARY_DEV_2026-10-19.md`, base3).** Gold never returned: cohort 0/10, dev2
  1/10, dev3 2–3/14, **dev4 0/5** (4 dev4 cases have no gold — related only). Confirmed pages wrong: cohort 3–5 of
  9–11 pages (masked: the gold is confirmed beside them, so the *case* reads hit), dev2 0–2, dev3 0–1, dev4 0.
  Matched claims ≈ all correct on every set. dev4's gold was returned by the `local_language` family in 5/5 and
  dev4 sends all six families. **dev4 — the country proxy — looks nothing like the nine on the same countries.**
  What separates them without opening the nine: the harness path (no-seed vs registry seeds), the label conventions
  (dev4 draft3 of 2026-10-18 lists twins and `related`; heldout.reviewed1 was signed 2026-10-17, before tickets 03/09/10
  and corpus round 02), and the fact that R1/R5/LX-1/subject shapes were tuned while dev4 was in view.
- **Two things in flight, not re-decided here.** H-1 is read (above). **H-2**: a worker who never sees pipeline output
  audits heldout.reviewed1 against the eight signed conventions (02-Q1…Q8) and the scorer changes since 2026-10-17;
  its proposals go to the owner as heldout.reviewed2 and the frozen run is re-scored once. Ticket 05 tells H-2 which
  conventions move numbers on development; nothing here reads heldout labels.
- **The six hypotheses, each with its development-side test** (the ticket holds the detail):

  | # | hypothesis | would explain | development-side test (confirms / refutes) | ticket |
  |---|---|---|---|---|
  | H-A | **measurement / corpus drift** — heldout.reviewed1 predates the twin / canonical-variant / related / alias / period conventions and the 15 scorer commits since 2026-10-17; dev labels were reconciled against pipeline output three times, the nine never | part of "gold never returned" (a twin is counted on dev, not on the nine), unmapped award claims, the 3 matched claims | 2×2 re-score of the frozen base3 development captures: {today's corpora, oldest drafts} × {today's scorer, scorer at `72ff9b15`}; strip twins/variants/related from dev4 labels and re-count `gold_returned_by_search` and page recall | [05](issues/05-label-convention-ablation.md) |
  | H-B | **registry-seed path vs no-seed / identity-gate path** — the nine and the cohort take the registry path (seeds fill slots, sitemap stage reads thousands of URLs, search sends fewer families); dev2–dev4 take the no-seed path the rules were tuned on; production's 481 non-registry universities take the identity-gate path nobody measures on these countries | fewer discovery queries per case, sitemap-heavy reads, confirm of a seed sibling | the cohort through three harness arms: registry seeds (today) / homepage-only no-seed entry / `--through-identity-gate`; compare the stage funnel and the scorecard per arm; a seed-perturbation arm if the first is inconclusive | [06](issues/06-registry-path-vs-no-seed-cohort.md) |
  | H-C | **local-language discovery** — the local-language family and the subject-title shapes carry words memorised from development cases; on an unseen site in the same language the gold is never returned and leads are refused `subject_mismatch` | gold never returned 4–6/9, `read_refused:subject_mismatch` 16–18 | leave-one-country-out on the lexicons: rebuild R5 / LX-1 / subject shapes without country X's development words and measure gold-returned and confirm on X (dev4 + dev5); offline classifier audit of dev5 gold pages | [08](issues/08-local-language-reach-loco.md), [10](issues/10-dev5-gold-page-audit.md) |
  | H-D | **scope readers on non-English pages** — degree level and population read from local words are wrong | 1 wrong-scope claim (degree) of 3 | wrong-scope by dimension on dev4 + dev5 baselines; offline degree-level reader on dev5 pages' local level words | [16](issues/16-evidence-stage-generalisation.md) (minor) |
  | H-E | **university-name aliasing** — native-script or short names fail the identity gate, the confirm step's institution check and the award bindings | identity gate (not exercised on the nine — a production risk), `unmapped.scholarship_exists`, 4 wrong confirms if the institution check passes a sibling faculty page | identity-gate offline check on the 13 dev5 homepages; native-name vs seed-name table; bindings coverage of dev5 awards (expressibility) | [11](issues/11-identity-gate-native-names-dev5.md) |
  | H-F | **overfitting of rules to seen sites** — 20+ default-on flags, each motivated by named development cases; gains measured on the same cases that motivated them | dev improving while the nine stayed at 0–1/9 on both looks (2026-10-17 and 2026-10-19) | the seen-site ledger (flag → motivating cases → gains elsewhere); the design-blind dev5 protocol and the leave-one-country-out gate for every future rule | [12](issues/12-seen-site-rule-ledger.md), [13](issues/13-design-blind-dev5-and-loco-gate.md) |

  **Failure 2 of the stage table — a wrong page confirmed when the gold is absent — is reproduced on development by
  the gold-knockout arm** ([07](issues/07-gold-knockout-arm.md)): the benchmark fetcher refuses the case's own gold
  URLs and twins, and the stage summary says whether confirm abstains (`unresolved`, the DoD's "never a guess") or
  confirms a sibling. The guard rule that follows is [09](issues/09-confirm-abstention-guard.md).
- **dev5 — the clean proxy.** Thirteen candidates in the nine's countries, none of the nine, none sharing a
  registrable domain or parent with them: kbtu, satbayev, aitu (Kazakhstan), hacettepe, bilkent, ytu (Türkiye),
  upol, zcu (Czechia), tud, lmu (Germany), unipd, sapienza (Italy), vilniustech (Lithuania; a different institution
  from Vilnius University — `vilniustech.lt` vs `vu.lt`, checked in 02). Estonia has no proxy left (TalTech is dev4;
  the top-500 seed has one Estonian row). kbtu and satbayev refused TLS to the agent's container on 2026-10-18 (a
  missing intermediate certificate); the runner-side probe decides. **dev5 is design-blind** (ticket 13): rules are
  designed on cohort/dev2/dev3/dev4, dev5 is read per paired run at aggregate level, and its per-case rows open only
  when the owner says so. That is what makes dev5 a predictor instead of a fifth tuning set.
- **Domain.** Harness `backend/evaluation/research/live.py` (`COHORT`, `DEV2`, `DEV4_DOMAINS`, `DEV4_SEEDS`,
  `DEV4_OFF_SEED`, `DEV4_HOSTS`, `CASE_DOMAINS`, `NO_REGISTRY_CASES`, `dev2_entry`, `seed_entry`, `capture_one`,
  the `--case` choices), `backend/scripts/canary_discovery.py` (`run_canary`: registry selector vs `entries`),
  registry `backend/app/adapters/discovery/institution_registry.json` (19 entries: `seeds` with
  `program_catalog`/`admissions`/`costs`/`scholarships`, `seeds_verified_on` 2026-08-28 / 2026-09-05), production
  entry `backend/app/catalogue/discovery.py` (`_identify_site`, R6), discovery `live_discovery.py` (`_confirm_programs`,
  `_recover_search_pages`, `LOCALIZED_IDENTITY`, `FRONT_PAGE_NOT_PROGRAMME`, the R5 local-language family in
  `app/adapters/search/intent.py`), scorer `metrics.py` (`dimension_matches`, `same_programme_page`,
  `adjudicate_programme_pages`), `scorecard.py`, `stage_summary.py` (leak guard), `identities.py`, `expressibility.py`,
  labelling `expert/{core_drafts,core_drafts_dev4}.py`, `scripts/verify_evidence.py` (`OFFICIAL_DOMAINS`),
  `scripts/probe_access.py`, workflow `.github/workflows/benchmark-capture.yml` (`expert_paired`, `verify_evidence`,
  `query_probe`; `MEASUREMENT_BINDINGS`). Gold `evaluation/research/data/{ground_truth.reviewed11,dev2.draft3,
  dev3.draft3,dev4.draft3}.json` and `identity_bindings.*`.
- **Working model (owner, 2026-10-18/19).** A planner charts; parallel workers (own worktree, medium effort) run AFK
  tickets and commit locally; the main session cherry-picks, runs the gates, pushes, dispatches paired runs on cohort /
  dev2 / dev3 / dev4 (+ dev5 once signed), checks in ≈ 15 min later, never idles. **Maximum subagents for 15 hours
  are authorised.** Disjoint files per ticket are the lock; a ticket that needs a file another open ticket names lands
  behind it. Every AFK ticket proposes its flag name and loop id; the worker registers the final name in HANDOFF §8.
- **Standing rules (brief §7.4, AGENTS §6, DoD, LOOP_PROTOCOL).** No robots bypass, UA spoofing or proxies; no applicant
  attribute in any query; 6 / 60 / 120 s; `Fetcher` never weakened; nothing sent to a model beyond the privacy table;
  no model identifier in the repository; no pull request unless the owner asks. Not decisions here.
- **Evidence policy — absolute.** The nine (`nu metu sabanci charles masaryk tum tartu polimi vilnius`) are never
  opened: no gold, draft, binding row, registry row, capture, log or per-case row; `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN`
  is never listed. The only heldout inputs to this map are the two owner-approved aggregate documents named above.
  Every test is run on cohort / dev2 / dev3 / dev4 / dev5 captures, gold files and code. A worker that needs a
  number about the nine asks the owner through `OWNER_QUESTIONS.md`; it never computes one.
- **Skills every session consults.** `grilling` + `domain-modeling` for 01, 13, 15; `research` for 05, 08, 10, 11, 12,
  16, 17; `loop-engineering` runs 06, 07, 09, 14 (flag-off → one paired run per set → default-on with no stable loss,
  no new wrong claim, and the guard of 13); `university-admissions-research` for the dev5 experts (03, 04);
  `scholarship-audit` on every dev5 award label.
- **Tracker conventions.** Claim = `Status: claimed` before any work; resolve = `## Answer`, `Status: resolved`, one
  gist line below. HITL tickets stay `open` until the owner answers through `OWNER_QUESTIONS.md`.

## Decisions so far

<!-- one line per closed ticket: gist, then the link holds the detail -->

(none yet — round 1 is open with the owner: tickets 01 and 13)
- [05](issues/05-label-convention-ablation.md) H-A **confirmed** on development: twin / department-page / `related`
  conventions move page recall 20–42 pp (dev3, dev4), the acronym scope rule claim precision up to 60 pp (dev2), draft
  award bindings known core 7–10 pp; H-2 audits URL forms, `related`, university-name form, populations, bindings.

## Ticket order, parallel groups and the critical path

| group | tickets | runs in parallel with | wall-clock note |
|---|---|---|---|
| **G0 owner round 1 (HITL, batched)** | [01](issues/01-destination-and-proxy-reference.md), [13](issues/13-design-blind-dev5-and-loco-gate.md) | everything below; nothing waits on them except the *signing* of dev5 and the *reading* of dev5 per-case rows | one sitting; «да» accepts the recommended answers |
| **G1 now (AFK, ≈ 10 workers at once, disjoint files)** | [02](issues/02-dev5-harness-ids-and-access-probe.md) harness ids + runner probe; [03](issues/03-dev5-programme-page-labels.md) programme-page experts ×4 (KZ / TR / CZ+DE / IT+LT); [05](issues/05-label-convention-ablation.md) 2×2 re-score; [06](issues/06-registry-path-vs-no-seed-cohort.md) harness arms; [07](issues/07-gold-knockout-arm.md) knockout arm; [11](issues/11-identity-gate-native-names-dev5.md) offline gate; [12](issues/12-seen-site-rule-ledger.md) ledger | each other | 05, 11, 12 are offline (1–3 h, no run); 02 ≈ 2 h + one CI probe; 03 ≈ 1–2 h per expert + one `verify_evidence` CI job; 06 and 07 ≈ 2 h of harness code each, then one paired run per set (≈ 25 min, parallel) |
| **G2 after drafts (AFK)** | [04](issues/04-dev5-core-labels.md) core experts ×4 (from 03's pages); [08](issues/08-local-language-reach-loco.md) LOCO lexicon; [10](issues/10-dev5-gold-page-audit.md) classifier audit on dev5 gold pages | G1's runs | 04 ≈ 1 h per case, parallel; 08 ≈ 3 h offline + an optional ≤ 300-credit probe (owner, Q6); 10 ≈ 2 h offline |
| **G3 after the owner signs dev5 (AFK)** | [14](issues/14-dev4-dev5-baseline.md) defaults baseline on dev4 + dev5 (design-blind: pre-registered, aggregates only on dev5); [09](issues/09-confirm-abstention-guard.md) after 07's verdict; LQ-2 (from 08) if H-C confirms | each other | 14 is two runs (≈ 25 min); 09 ≈ 4 h + five paired runs |
| **G4 synthesis (AFK → HITL)** | [16](issues/16-evidence-stage-generalisation.md); 13's LOCO computation; [15](issues/15-loco-prediction-and-second-look-prereg.md) | — | 15 is written only when every hypothesis has a verdict |
| **G5 exit** | [17](issues/17-residue-and-stop.md) | — | the stop rule below |

**Critical path**: 02 → 03 (owner signs dev5.draft1) → 14 (dev5 baseline, design-blind) → 13's LOCO prediction → 15
(second-look pre-registration). The longest chain by wall clock is 07 → 09 → five paired runs → verdict (≈ 8–10 h);
nothing shortens it except starting 07 in the first hour. **Minimal path to a credible second look**: 02 + 03 + 14 +
one confirmed cause with a rule that passes 13's guard + 15.

**Ordered by expected gain per hour** (gain = pp of the development-to-heldout gap explained or closed, per worker hour):

1. [05](issues/05-label-convention-ablation.md) — 1–2 h offline; can explain a large share of "gold never returned" and
   tells H-2 exactly which conventions to audit. No run.
2. [06](issues/06-registry-path-vs-no-seed-cohort.md) — 2 h + one run; the path is the one structural fact true of all
   nine and of no development set but the cohort.
3. [07](issues/07-gold-knockout-arm.md) — 2 h + four runs; reproduces failure 2 (wrong page confirmed when the gold is
   absent) on 44 development cases and sets the bar for 09.
4. [02](issues/02-dev5-harness-ids-and-access-probe.md) + [03](issues/03-dev5-programme-page-labels.md) — the only
   way to a clean predictor; 2 h + 1–2 h per expert in parallel.
5. [11](issues/11-identity-gate-native-names-dev5.md), [12](issues/12-seen-site-rule-ledger.md) — offline, 2 h each;
   11 decides the second look's identity-gate arm, 12 decides which default-on rules are suspect.
6. [10](issues/10-dev5-gold-page-audit.md), [08](issues/08-local-language-reach-loco.md) — offline 2–3 h each; H-C's verdict.
7. [14](issues/14-dev4-dev5-baseline.md) — two runs once dev5 is signed.
8. [09](issues/09-confirm-abstention-guard.md) — the one rule this map expects to build; 4 h + five runs.
9. [04](issues/04-dev5-core-labels.md) — needed for target 6's row on dev5; ≈ 13 expert hours in parallel.
10. [16](issues/16-evidence-stage-generalisation.md), [13](issues/13-design-blind-dev5-and-loco-gate.md) computation,
    [15](issues/15-loco-prediction-and-second-look-prereg.md), [17](issues/17-residue-and-stop.md).

**Stopping rule.** The map hands over to a second-look pre-registration when **all** of: (a) dev5 is signed and its
baseline was read design-blind; (b) each hypothesis H-A…H-F has a verdict with numbers (confirmed / refuted / not
testable on development, and why); (c) on the gold-knockout arm, wrong confirms are 0 on every set with no hit lost on
the normal arm (the DoD's "never a guess" holds when the gold is absent); (d) every rule turned on since 2026-10-17
passes the seen-site guard, or is turned off; (e) the leave-one-country-out spread of dev4 + dev5 on target 6's row is
itself ≤ 15 pp — if the development countries disagree with each other by more than that, no development set can
predict the nine within 15 pp and the owner redraws target 6 or the proxy set ([17](issues/17-residue-and-stop.md)).
The map stops short and escalates when the authorised 15 worker-hours are spent, or a rule fails its paired run twice
on the same cause (DoD loop rule). **No heldout look is spent by this map**; it writes the pre-registration for one.

## Not yet specified

<!-- in-scope fog: questions coming, not yet sharp enough to ticket -->

- **A general local-language query construction** (LQ-2: the query built from the site's own words — `<html lang>`,
  the catalogue's section labels, the seed row's native name — not from a lexicon of development words). Sharp only
  after 08 says whether the lexicon is memorised.
- **Seeds as hints, not slot-fillers, on the registry path** (registry institutions run the same discovery as unseen
  ones, seeds joining as extra leads). Sharp only after 06 says the path matters; it is a product change the owner
  decides (Q5), measured on the cohort's three arms.
- **The second look's arms**: registry path (as today) vs no-seed / identity-gate path (production's path for unseen
  universities) — a harness change decided *before* dispatch (Q4), never after a result. Enters 15 once 06 and 11 report.
- **The evidence stages on a found page in the nine's countries** (costs pages fetched ok ≈ 0 on every set, unmapped
  award claims): after discovery predicts, a separate round on dev4 + dev5 evidence pages; ticket 16 sizes it.
- **A Kazakhstan proxy** if kbtu and satbayev refuse TLS from the runner too (aitu alone, or none): decided by 02's probe.

## Out of scope

<!-- ruled beyond the destination; never graduates -->

- **Any look at the nine beyond the two approved aggregate documents** — including a stage aggregate of a new kind,
  a seed-URL check or a bindings count on the nine. Each would be a third H-1 decision for the owner, not a ticket.
- **Designing or ranking a rule by what the heldout aggregates suggest.** They order *tests*; the rules come from
  development evidence only.
- **Access bypass, the browser tier, another runner, a provider change, the 6 / 60 / 120 budget** (previous maps).
- **Per-institution seeds or hardcode for any development or heldout case**; dev5 enters through the no-seed path.
- **The model-based extractor and the PDF route** (their own maps / escalations).
- **Changing DoD thresholds** without the owner's dated entry; this map asks (01, 13, 15), never edits.
