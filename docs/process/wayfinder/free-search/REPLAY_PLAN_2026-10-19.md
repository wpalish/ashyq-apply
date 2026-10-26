# Replay experiment plan — the algorithm after search, on recorded Serper lists, for $0 (2026-10-19)

Map: [free-search](map.md) (owner decision 2026-10-19: no scraping; offline replay of the saved Serper lists for the
work after search) · inherits the guards of [generalisation](../generalisation/map.md) (design-blind dev5, 13-Q2's
default-on bar, the seen-site ledger) and the residue classes of [finish-algorithm](../finish-algorithm/map.md).
Planner, 2026-10-19, from the A/A replay runs 39236948934 / 39236953817 / 39236958339 / 39236924796, the store
`evaluation/research/data/recorded_search.base3.json`, the harness (`live.py`, `scorecard.py`, `stage_summary.py`,
`recorded.py`) and the loop report. **No heldout file, capture, log or label was opened; dev5 has no recorded lists and
is not part of any replay.** Every number below is from the four development sets.

## 0. The ranked list (next 1–2 loop cycles)

Ranking = DoD progress per worker-hour. A dispatch costs no worker time (public-repo runner minutes are free); a
worker ticket costs the hours shown. One paired run ≈ 12–16 min per set, four sets in parallel.

| # | what | kind | worker h | runs | DoD row it moves | why this rank |
|---|---|---|---|---|---|---|
| 1 | **G-07 gold-knockout arm on all four sets** (`--knockout-gold <set file>`) | dispatch, harness exists | 0 (+1 h reading) | 4 | none directly; it is the specification of #2 and the development reproduction of the heldout's "4 wrong of 5 confirmed" | fetcher-level refusal, queries unchanged → fully replayable; deterministic on replay; the generalisation map's longest chain starts here |
| 2 | **CH-1 — confirm requires head identity** (CA-1's sub-rules 1 and 3; generalisation ticket 09) | worker ticket (§5.1) | ≈ 4 | 4 normal + 4 knockout | target 3 `wrong_programme_pages`: dev2 1 → 0 (uct, 4/4 repetitions), dev4 1 → 0 (unibo, 1/4); knockout guess rate | the only stable development wrong pages on the signed corpora are unit pages confirmed from body text; the rule is a guard, so it fires on unseen pages by construction |
| 3 | **UA-1 — no confirmation when the institution's own entry points were unreadable** (CA-1 sub-rule 4, the "unavailable, never a guess" half) | worker ticket (§5.2) | ≈ 2 | 4 | target 3 `wrong_programme_pages`: cohort 1 → 0 (toronto, 4/4) | toronto reads 0 pages on its main host (robots http_error, 4 sitemap probes 403, both navigation fallbacks unreachable) and still confirms a satellite-campus page from one search lead |
| 4 | **CL-2 — a programme page whose head and URL carry the identity is not `unknown`** | worker ticket (§5.3), conditional on a 20-minute page check | ≈ 3 | 4 normal + 4 knockout | target 3 `programme_found_on_readable`: dev4 unibo (gold read and refused 4/4), dev2 tec (English twin read and refused 4/4) | the inverse failure of #2; the dev5 page audit says `reads_as:unknown` is the dominant refusal on unseen sites (13 of 22) — but it is a recall rule, so it runs only together with #2 and under knockout |
| 5 | **Ablations of default-on rules that touch confirm or stop** (`--no-integrated-masters-level`, `--no-alias-aware-program-match`, `--no-stage-budgets`) | dispatch | 0 | 12 | none directly; says whether a default-on rule causes a wrong or missed page on development (H-F) | deterministic replay makes a 2+2 read decisive; IM-1 and FI-1 have never had a paired run |
| 6 | **G-06 no-seed arm on the cohort** (`--no-registry-seeds`) | dispatch (partially measurable, §1.4) | 0 | 1 | none directly; H-B | the one structural fact about the nine that the cohort can test; read the misses count first |
| 7 | **H-1 — misses counted per search kind in the scorecard's replay target** | harness ticket (§5.4) | ≈ 1.5 | 0 | measurement honesty of every replay run | the A/A already trips the "queries changed" warning on dev3 (24 → 26) from scholarship/topic query counts that vary with reads, not from a changed discovery query |
| 8 | Ablations of the ten seen-site evidence rules (`--no-english-readers-v2`, …) | dispatch, fills idle runners | 0 | ≤ 40 | none; H-F evidence | topic search is dead on replay, so these read in a degraded regime (§1.3); aggregate read only |

Not on the list, and why, in §7. Paid credits: §6 — at most one live paired run on dev4 + dev5 (≈ 450 queries) after #2
passes, and the second heldout look after the generalisation map's ticket 15; nothing else.

## 1. What the replay measures, and what it cannot (facts, not assumptions)

### 1.1 The store

`recorded_search.base3.json`: 174 request keys from the base3 runs (2026-10-18 22:30, head `1093faaa`), 141 keyed on a
domain filter and 33 localized (`hl`/`gl`, one per non-English development case). Per domain the store holds the
families base3 actually sent: **2 entries** (`field_and_degree`, `natural_language`, plus the localized family) for the
cases where base3 never sent QB-1's second pass — a page, gold or not, was confirmed in the first pass, or the stage
budget ended discovery — in any repetition (rug.nl, tudelft.nl, univie.ac.at, uw.edu.pl,
ethz.ch, uu.se, uba.ar, uc.cl, uio.no, usp.br, kit.edu, ktu.edu, rwth-aachen.de, taltech.ee, unibo.it, ku.dk, kaznu.kz,
bogazici.edu.tr, chula.ac.th, universite-paris-saclay.fr); **3** where the reserve pass sometimes started (auckland,
imperial, tcd, ubc, uct, um, unsw, ku.ac.ae); **5–6** where the second pass ran (aalto, hku, kaist, utoronto, cvut, vut,
itu, iitd, kuleuven, msu, ntu.edu.tw, tec, tsinghua, u-tokyo, ub); **none** for ntu.edu.sg, whose base3 repetitions
confirmed the page from the registry seeds and sitemaps before any discovery query was sent (its one recorded call is
the scholarship query, which misses). A request outside this set returns nothing and counts as a miss. **Consequence:** any arm that makes a case send its second pass where base3 never did (a rule that refuses the
first confirmed page, the knockout arm, SB-1 or QB-1 off, the no-seed path) will raise `recorded_search_misses` on that
case by up to 3. That is structural to the experiment, not "the rule changed the queries"; §1.4 says how to read it.

### 1.2 The A/A noise floor, re-scored on the signed corpora

The loop report's A/A table scored the cohort on `ground_truth.draft10` (`scorecard` prints the corpus version in its
header). On the signed `reviewed11` (the scorecard default) the cohort reads **claim precision 28/28 = 1.00, wrong scope
0/28, wrong programme pages 1 (toronto)** in all four columns. The six draft10 "wrong-scope" claims are NTU's SAT 1250 on
the population dimension (corpus round 02-Q2 signed `population: international`), and draft10's second wrong page is ubc's
BA page, which `reviewed11` labels `related`. **The cohort's "precision 0.79, wrong scope 6/28, wrong pages 2" in the
A/A section is a corpus-version artefact; the LOOP_REPORT line should be corrected and every cohort replay scored with
`--dataset evaluation/research/data/ground_truth.reviewed11.json`.** dev2/dev3/dev4 were scored on draft3 and stand.

Noise floor on the signed corpora, off#1/off#2/on#1/on#2: cohort pages 4/4/4/4 of 10, wrong 1/1/1/1, claims 28/28 ×4;
dev2 pages 6/6/5/6, wrong 1/1/1/1 (uct), wrong claims 1 ×4 (uppsala, §1.3); dev3 pages 8 ×4, wrong 1/0/1/0 (kuleuven,
host-flaky); dev4 pages 4 ×4, wrong 0/0/0/1 (unibo). Misses per column: cohort 9 ×4, dev2 23/23/22/23, dev3 24/23/26/23,
dev4 19 ×4. Stable gains/losses: none on any set. **A single-column flip (uba dev2 on#1, kuleuven dev3, unibo dev4 on#2)
is within the floor; a 2+2 stable change is attributable to the flag.**

### 1.3 Three regimes a rule can fall into on replay

| regime | rules | how the replay reads them |
|---|---|---|
| **A. query-neutral, pages reached** — confirm predicate, read order under the same leads, classifier verdicts, readers on pages reached from the programme/admissions page or by link | FP-1, EF-1, PL-1, CG-1, R1, R2, LI-1, IM-1, ALIAS_AWARE, PG-1, CL-1, SM-2, the fetch savers, the deadline/fee/English readers on linked pages, award rules on linked pages, `--knockout-gold` | **fully measurable**; deterministic to ±1 case |
| **B. query-neutral in text but changes which queries are sent** — stop-on-confirm and reserve logic, the no-seed path, the knockout arm | SB-1, QB-1, `--no-registry-seeds`, `--knockout-gold` on first-pass-confirmed cases | **measurable with a visible cost**: the extra pass misses; read the per-case misses before the outcome rows; the result is a lower bound on what live would find in the extra pass |
| **C. changes query text or depends on a search the store never recorded** — topic, scholarship, identity-gate and award queries, R5 off, QA-1, LQ-2, `--through-identity-gate` (R6 sends an identity query), TS-2, SQ-1, AR-1's filtered award query | `--no-local-language-queries`, `--alias-queries`, `--topic-search*`, `--no-scholarship-index-query`, `--through-identity-gate`, `--award-route` | **not measurable**: the on arm is scored on empty searches it would not have had live |

Two artefacts of regime C sit in the replay *baseline* and must not be read as pipeline faults: **uppsala's deadline
2027-04-15** is a wrong value in every replay column (the DL-6 page `/en/study/bachelors-studies/…` is never read on
replay — the log shows the programme page, four PDFs and the fees page only — because the question-routed topic query
that reaches it misses), while live base3 reads 2027-01-15; and **core answers are below live on every set** (dev4
0/8 on replay vs 2/8 live). Compare arms, never absolutes, and judge "no new wrong claim" against the off arm.

### 1.4 How to read a replay run

1. Score with the signed corpus: `python -m evaluation.research.scorecard <artifact> --dataset
   evaluation/research/data/<ground_truth.reviewed11|dev2.draft3|dev3.draft3|dev4.draft3>.json` (`--allow-drafts` for
   dev2–dev4); `python -m evaluation.research.stage_summary <artifact> --dataset <same file>`.
2. Read `recorded_search_misses` per column first. Baseline = the off arm's worst repetition (cohort 9, dev2 23, dev3
   23–24, dev4 19). An on-arm excess of ≤ 2 on dev3 is A/A noise (the scholarship/topic query count varies with reads).
   An excess of up to 3 × (cases whose first confirmed page the rule refused, or knockout cases) is regime B — expected,
   and stated in the plan line for that run. Anything else means the rule changed a discovery query: stop reading.
3. Then the DoD rows: `wrong_programme_pages`, `programme_found_on_readable`, `claim_precision`, `wrong_scope_claim_rate`,
   `cases_over_budget`, reads; stable gains/losses (2+2); for a knockout arm the `knockout_*` funnel rows (`knockout_cases_gold_refused`,
   `knockout_guess_cases_wrong`, `knockout_abstained`, `knockout_leaked_hits` must be 0).
4. Default-on bar (finish-algorithm 01-Q5 + generalisation 13-Q2): no stable loss on any set, no new wrong claim, no new
   wrong page, 0 over budget, **and** a stable gain on a set that did not motivate the rule or a precision gain under
   knockout on ≥ 2 sets, **and** the dev5 aggregate not worse — which replay cannot give (dev5 is not in the store), so
   a replay-passing rule goes on by default only after the one live dev4 + dev5 run of §6, or stays flag-off with its
   replay table recorded in HANDOFF §8 and `hypotheses.json`.

## 2. What the A/A shows after search, by name (development sets, signed corpora)

| set | case | A/A outcome (4 columns) | what discovery did | class | reachable by a replay rule? |
|---|---|---|---|---|---|
| cohort | **toronto** | wrong ×4 | main host unreadable (robots `http_error`, sitemap probes 403 ×4, navigation fallback unreachable ×2; 20/24 requests failed); identity recovery checked 7 leads, confirmed `www.utm.utoronto.ca/math-cs-stats/…/programs/computer-science` (a satellite campus's department programme page); gold `future.utoronto.ca/program/computer-science` returned by `programmes`, unresolved (http_error) | access + guess | **yes — UA-1** (#3): abstain when nothing on the institution's own entry hosts was readable |
| cohort | ubc | related ×4 | BA Computer Science confirmed; BSc gold returned by two families, never read (degree word) | rank / degree word | no (EF-1 rejected on this cause; RA-1 found no rule) |
| cohort | warsaw | missed ×4 | gold returned by `local_language` only, never read; PDF scholarship label | rank (returned, not read) | no (RA-1 "local_language rank 1 first" rejected before build: predicted loss on warsaw itself and ctu) |
| cohort | aalto, hku | missed ×4 | robots unreachable; unresolved leads | access | no |
| cohort | kaist | missed ×4 | gold only as a walker link dropped `short_label` | opaque URL / department host | no |
| dev2 | **uct** | wrong ×4 | identity recovery read two real programme pages and refused both as related (BBusSc specialising in CS, BCom IS & CS — R2, correct), then confirmed `sit.uct.ac.za/department-computer-science` (a department page) because its body states a bachelor level and its subject is computer science; QB-1 then skipped the second pass; the gold `sit.uct.ac.za/bsc-degrees` was returned by two families and never read | **unit page confirmed from body text** | **yes — CH-1** (#2): the head ("Department of …") names a unit, not a degree; refusing it lets recovery read on |
| dev2 | uppsala | hit; one wrong claim ×4 | deadline 2027-04-15 (national round) — the DL-6 page is reached by a topic query live, never on replay | replay artefact (§1.3) | not a rule target on replay |
| dev2 | tec | missed ×4 | gold's English twin read and refused "reads as irrelevant" | classifier | **maybe — CL-2** (#4), after a page check |
| dev2 | tsinghua, kaznu | missed ×4 | gold never seen (other registrable domain; site refuses) | other domain / access | no |
| dev3 | kuleuven | wrong 2, missed 2 | sitemaps 401/404; `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` confirmed; gold is the `onderwijsaanbod.` catalogue entry | host-flaky; **possibly an undeclared twin** | not a rule: a worker should check whether the confirmed page declares the gold as an alternate or redirects to it (dev case; hand-fetch allowed) and propose the twin to the owner if so |
| dev3 | unsw | related ×4 | — | label convention | no |
| dev3 | ntutw, msu, iitd, ub | missed ×4 | never returned / access | residue classes | no |
| dev4 | **unibo** | missed 3, wrong 1 | gold `corsi.unibo.it/laurea/informatica` **read and refused** "reads as unknown, not a programme page" in every column (and its `/insegnamenti` sibling refused on subject); in on#2 identity recovery confirmed `site.unibo.it/digital-sustainability-lab/en/teachings/courses` (a lab's courses list) → `programme.exists` wrong-scope | classifier miss + **unit page confirmed** | **yes — CH-1 refuses the lab page; CL-2 may accept the gold if its head carries "Informatica" and the URL's `laurea` slug is read as the level** |
| dev4 | vut, boun, itu | missed ×4 | related-only labels; nothing confirmed | no gold | no |

Other-scope (not wrong) claims on the cohort: groningen tuition and deadline, delft tuition — the statutory EU fee
(€ 2 771) claimed with its population beside the international label. Honest under the scorer; nothing to build.

**What this says about the heldout's two failures, without opening the nine.** "Gold never returned" has no
development analogue the replay can create except the knockout arm — which is why #1 is first. "Wrong page confirmed"
has exactly two stable development instances (toronto, uct) plus one flaky (unibo), and all three are confirmations
from a page's *body* (degree word somewhere in the text) when its *head* names a unit, a campus or a list. That shape
is generic: it needs no site word, and the dev5 page audit (generalisation ticket 10) found 3 refusals of the same
family on pages nobody tuned on.

## 3. Cycle 1 — dispatch now (no code)

Common inputs for every run: workflow `benchmark-capture.yml`, `runner=ubuntu-latest`, `mode=expert_paired`,
`seconds_per_case=120`, `max_pages=60`, `case_parallelism=5`, **`search_provider=recorded`**, `base_args` empty
unless stated. Case lists:

- cohort: `groningen delft aalto vienna warsaw ubc toronto hku ntu kaist`
- dev2: `ethz psaclay uppsala tcd tsinghua tec uba kaznu uct khalifa`
- dev3: `imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula`
- dev4: `ctu vut rwth kit unibo taltech ktu boun itu`

| run | set | `extra_args` | `run_tag` | expected misses | read |
|---|---|---|---|---|---|
| 1a | cohort | `--knockout-gold evaluation/research/data/ground_truth.reviewed11.json` | `rp-ko-cohort` | off 9; on up to +3 per knocked-out case with two recorded families (delft, groningen, vienna) and up to +6 for ntu (no discovery query recorded) → ≤ +15 | `knockout_*` rows; `case_outcome:wrong` on the on arm = the guess list; claims on the on arm by verdict |
| 1b | dev2 | `--knockout-gold evaluation/research/data/dev2.draft3.json` | `rp-ko-dev2` | off 23; on ≤ +3 × 6 | same |
| 1c | dev3 | `--knockout-gold evaluation/research/data/dev3.draft3.json` | `rp-ko-dev3` | off 24; on ≤ +3 × 8 | same |
| 1d | dev4 | `--knockout-gold evaluation/research/data/dev4.draft3.json` | `rp-ko-dev4` | off 19; on ≤ +3 × 4 | same |
| 2a–d | all four | `--no-integrated-masters-level` | `rp-abl-im1-<set>` | off = on | IM-1 is unmeasured (ledger row 13); it refuses pages by level; a stable page gain on its off arm means it costs a hit, a wrong-page rise means it is load-bearing |
| 3a–d | all four | `--no-alias-aware-program-match` | `rp-abl-alias-<set>` | off = on | the verify-stage programme match (seen-site, kit/rwth); read `programme.exists` claims and wrong scope |
| 4a–d | all four | `--no-stage-budgets` | `rp-abl-sb1-<set>` | on arm may rise (regime B: discovery no longer stops at the first confirmation) | does "first confirmation wins" cause the unit-page confirms (uct) — or does reading on add wrong pages? |
| 5 | cohort | `--no-registry-seeds` | `rp-g06-noseed` | on arm may rise (regime B) | H-B: families per case, `confirmed_pages_wrong`, gold reached; read misses first; the `--through-identity-gate` arm is regime C (R6's identity query) and is **not** dispatched on replay |

Deliverable of cycle 1 (main session, ≈ 1 h): `docs/process/GOLD_KNOCKOUT_2026-10-19.md` as generalisation ticket 07
specifies — per set the on-arm funnel against the off arm, the **guess rate** = `knockout_guess_cases_wrong` ÷
`knockout_cases_gold_refused`, and the table *case → page confirmed instead → which signal would have refused it* (head
names a unit / no level in head or URL / list page / single family at rank > 3 / entry hosts unreadable). That table is
CH-1's and UA-1's test list; the workers start on §5's shape while it is being written and align the tests to it.

## 4. Cycle 2 — the rules (after the §5 workers land, cherry-picked and gated)

| run | set | `base_args` | `extra_args` | `run_tag` | bar |
|---|---|---|---|---|---|
| 6a–d | all four | — | `--confirm-head-identity` | `rp-ch1-<set>` | dev2 `wrong_programme_pages` 1 → 0 (uct) in both on reps; dev4 unibo wrong 0; **no hit lost** on any set (groningen, delft, vienna, ntu; ethz, psaclay, uppsala, tcd, uba, khalifa; imperial, um, auckland, ucph, puc, uio, usp, chula; ctu, rwth, kit, ktu); 0 new wrong claim; reads not up by more than the reads the refused page freed |
| 7a–d | all four | `--knockout-gold <set file>` | `--confirm-head-identity` | `rp-ch1-ko-<set>` | both arms knocked out, the on arm adds CH-1: `knockout_guess_cases_wrong` on → 0, or down on ≥ 2 sets with `knockout_abstained` up by the same count; `knockout_leaked_hits` 0 |
| 8a–d | all four | — | `--confirm-head-identity --abstain-on-unreadable-entry` | `rp-ch1-ua1-<set>` | cohort `wrong_programme_pages` 1 → 0 (toronto reads `missed`/unresolved with an access note); nothing else moves vs 6a–d |
| 9a–d | all four | `--confirm-head-identity` | `--classify-head-and-slug-identity` | `rp-cl2-<set>` | CL-2 on top of CH-1: dev4 unibo `missed` → `hit` or unchanged; dev2 tec unchanged or hit; **0 new wrong page on any set**; then 9e–h = the same pair under `--knockout-gold` in `base_args`: guess cases not up |
| 10 | all four, as runners idle | — | one of `--no-coordinated-degree-scope`, `--no-international-round-deadline`, `--no-english-readers-v2`, `--no-fee-readers-v2`, `--no-intake-section-deadline`, `--no-parent-degree-link`, `--no-question-page-order`, `--no-award-page-evidence`, `--no-award-name-qualifier`, `--no-funding-identity-scope` | `rp-abl-<rule>-<set>` | aggregate read only (`--summary-only` is enough): a rule whose off arm is identical on all four sets in a deterministic replay has no development evidence left; record in the seen-site ledger, change no default from a replay alone |

Default-on decisions from cycle 2: a rule that passes its bar on the four sets is **ready for the one live dev4 + dev5
run of §6** (13-Q2(b)); it stays flag-off until then. Rejections go to `hypotheses.json` with the replay table.

## 5. Worker tickets

Common to every ticket (the design-blind guard, generalisation 13 and the seen-site ledger): rules are designed on the
cohort/dev2/dev3/dev4 captures named here and on code; **no dev5 or heldout page, label, capture or row is opened**; every
word table is dictionary-grade for every language in `languages.json` at once (16-Q5) and no entry comes from a single
development page; tests use synthetic pages in at least three languages plus one hand-fetched development page per
motivating case (dev only; production User-Agent after a robots.txt check, as tickets 10/11 did); the rule's gain must
appear on a set that did not motivate it (CH-1: cohort/dev3 under knockout; UA-1: any set under knockout where entry
hosts fail; CL-2: dev3 or cohort) or it is recorded `seen_site`. Flag off by default; harness `store_true` flag plus its
`NEGATABLE_RULES` entry; HANDOFF §8 line; golden demo byte-identical (`UNIMATCH_DEMO_MODE=true
UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`, brief §5.7 order); gates green; worker effort `medium`
except CH-1 (`high`: it changes `profile_rejects`, which the confirm stage and the catalogue walker share).

### 5.1 CH-1 — confirm requires head identity (`CONFIRM_REQUIRES_HEAD_IDENTITY`, `--confirm-head-identity`, loop id CA-1a)

**Change** (`backend/app/adapters/discovery/live_discovery.py`: `profile_rejects` and a helper beside
`_integrated_master_page`; `backend/app/adapters/page_classifier.py`: `PageClassification` carries `title` today but
no `h1` — add a `heading: str` field filled from the first `h1` of the main content, change no verdict). With the flag
on, a candidate page passes `profile_rejects` only when its **head** — `<title>` or first `h1` — carries the identity:

1. the head names the requested subject (today's predicate `matches_field_text` / `subject_head_verdict` on the head
   text, not on `page.subject` derived from anywhere on the page);
2. the requested degree level is named in the head, **or** in the URL's degree slug (`_DEGREE_SLUGS`, which already
   holds the Bologna forms for every level), **or** in a labelled field of the page ("Degree: BSc", `_LANGUAGE_LABEL`-style
   label reading) — a level word found only in running body text is not enough;
3. a head that names an organisational unit and no degree (department, faculty, school, institute, lab/laboratory,
   centre, group, chair — and their `languages.json` equivalents, dictionary-grade) is refused with a new pinned verdict
   `"page head names a unit (<word>), not a programme"`; FP-1's `FRONT_PAGE_VERDICT` is the precedent.

The new verdict's prefix is added to `_IDENTITY_REFUSAL_PREFIXES`, so it counts as an identity refusal (R1's local-twin
read and R2b's sibling queue still apply) and it frees the slot: identity recovery reads on and QB-1's second pass runs when nothing is confirmed — which is
what reaches uct's `bsc-degrees`. Nothing changes off.

**Tests** (`tests/test_confirm_page_identity.py`, new; `tests/test_recovery_lead_order.py` unchanged): synthetic pages —
a department page with "Bachelor" in the body only → refused with the unit verdict; the same page with "BSc Computer
Science" as `h1` → confirmed; a programme page whose head is "Computer Science" and whose URL has `/bachelor/` →
confirmed; a lab's "Courses" page → refused (no subject in head); German/Italian/Czech variants from the dictionary table;
the hand-fetched uct department page and the unibo lab courses page → refused; the hand-fetched groningen and delft gold
pages → still confirmed; off → every verdict byte-identical to today.

**Acceptance on replay** (runs 6a–d, 7a–d): §4's bars. Reject if any set loses a hit in both on repetitions, or if the
knockout guess rate does not fall on at least two sets.

**Overfitting guard**: the unit-word table is written from a dictionary before any page is read, committed in the first
commit of the branch; no English or local word from uct's or unibo's pages beyond the generic unit nouns; LOCO: remove
English from the table and the uct test must still refuse on rule 2 (no level in head or URL); the gain is counted on
cohort/dev3 under knockout (sets that did not motivate it).

### 5.2 UA-1 — no confirmation when the institution's own entry points were unreadable (`ABSTAIN_ON_UNREADABLE_ENTRY`, `--abstain-on-unreadable-entry`, loop id CA-1b)

**Change** (`live_discovery.py`: `_recover_search_pages` and the stage that records entry reads; `DiscoveryTrace` gains
`entry_unreadable: bool`, serialised only when true). When the homepage read, the robots.txt read and every sitemap probe
on the institution's registrable domain failed (any outcome but `ok`, cache hits excepted) **and** the navigation
fallback reached nothing, identity recovery may still read leads but confirms none of them as *the* programme page: an
accepted lead is kept on the trace as `unresolved_access` (so the evidence stages can read it without a programme scope
and the product can show it as a lead), discovery ends `programme unresolved`, and `trace.errors` carries one line
`"entry hosts unreadable: no programme page confirmed"`. A site where any entry read succeeded is unaffected (kuleuven in the
repetitions that confirmed: robots.txt and the later entry reads `ok`, only the sitemap probes 401/404 → unaffected;
khalifa when it answers → unaffected).

**Tests** (`tests/test_live_discovery.py`, a new class): a fake fetcher that fails robots, homepage and probes but serves
one sub-host page → off: confirmed; on: unresolved, lead recorded, trace line present; one entry read ok → confirmed on
both arms; the scorecard's `case_readable` is untouched (the case stays `unavailable` in the readable denominator; only
`wrong_programme_pages` moves).

**Acceptance on replay** (runs 8a–d): cohort `wrong_programme_pages` 1 → 0 in both on repetitions; no other case changes
outcome on any set; reads not up. Under knockout (fold into 7a–d's reading): no change expected unless a set has a case
with unreadable entry hosts.

**Overfitting guard**: no host, path or word; the condition is "zero successful entry reads", a count. It cannot fire on a
site that answers, so it cannot be tuned to a site. Recorded as a guard (general by construction) only if it loses no hit.

### 5.3 CL-2 — a page whose head and URL carry the identity is not `unknown` (`CLASSIFY_HEAD_AND_SLUG_IDENTITY`, `--classify-head-and-slug-identity`, loop id CL-2)

**Precondition (20 minutes, before any code)**: hand-fetch `corsi.unibo.it/laurea/informatica` and tec's English twin
(both dev cases) through the sandbox egress with the production User-Agent after a robots.txt check; record `<title>`,
first `h1`, `<html lang>`, whether the main content is a script shell. If the head carries neither the subject alias nor
a level word, close the ticket "SPA / thin shell — residue" and build nothing.

**Change** (`page_classifier.py` only): with the flag on, a page that would classify `UNKNOWN` or `IRRELEVANT` is
classified `PROGRAM_DETAIL` when (a) its head names the requested-field alias (ontology strong/localized aliases, as
R1 reads them), (b) the level is named in the head or in the URL's degree slug, and (c) the page has no listing
structure (fewer than N programme-like links, N from the existing catalogue heuristics). CH-1's head identity then
judges it like any candidate; CL-2 never runs without CH-1 on (the flag checks it and logs a trace line otherwise).

**Tests** (`tests/test_page_classifier.py`): synthetic `unknown` pages in Italian/Spanish/English with head alias + slug
level → `PROGRAM_DETAIL`; the same page with a programme-list body → still a catalogue; a news page with "Bachelor"
in the URL and a subject in the head → refused by (c) or by the existing NEWS rule; off → byte-identical.

**Acceptance on replay** (runs 9a–h): dev4 unibo `missed` → `hit` or unchanged; dev2 tec unchanged or `hit`; **0 new wrong
page on any set in both on repetitions**, and under knockout `knockout_guess_cases_wrong` not above the CH-1-only arm.
Reject on the first new wrong page: a recall rule on the classifier is the kind that produced the heldout's wrong confirms.

**Overfitting guard**: only existing tables (`_DEGREE_SLUGS`, the ontology aliases) — no new slug or alias may be added in
this ticket; motivating cases from two sets (dev4, dev2); the gain must also show on cohort or dev3 under knockout (a page
the old classifier refused and the new one accepts, counted as `knockout_abstained` → confirmed-related, never a wrong).

### 5.4 H-1 — replay misses per search kind (`scorecard.py`, `live.py` telemetry; measurement only)

**Change**: the recorded provider's counters are already read into `recorded_search_hits/misses`; add
`recorded_search_misses_discovery` by counting misses while discovery is the active stage (the harness wraps the provider
per stage: `trace.search_results` rows are discovery's), and judge the replay target on the discovery count only; print
both. Expected: dev3's A/A reads 0 excess on discovery (its 24 → 26 came from scholarship/topic queries), the knockout
arm's excess reads as discovery misses with a note `knockout: second pass unrecorded on n cases`. Tests in
`tests/test_scorecard.py` on synthetic captures; `--summary-only` unchanged. ≈ 1.5 h; lands before cycle 2 is read.

## 6. What would justify paid credits later, and how few

Replay cannot measure two things: a rule that changes queries, and dev5 (never recorded). The plan spends credits only
for the second, and only after a rule has passed on replay:

- **One live `expert_paired` run on dev4 + dev5 with the passing bundle** (`--confirm-head-identity
  [--abstain-on-unreadable-entry] [--classify-head-and-slug-identity]`), dev5 read at aggregate level only (13-Q1): ≈ 9 + 11
  cases × 4 columns × ≈ 5 queries ≈ **450 queries**. On the free allowances first (Tavily 1 000 / Exa ≈ 2 500 a month,
  under ticket 02's per-run cap); on Serper only if the owner tops up (≈ 450 credits ≈ $0.45). Justified when: CH-1
  passes §4's bar on all four sets normal and knockout, and the knockout guess rate falls on ≥ 2 sets. Not justified
  for an ablation result, for UA-1 alone, or for a rule that failed on replay. Its lists are recorded by WF-17 and
  extend the store, so the next replay includes dev5 for free.
- **The second heldout look** (≈ 9 × 4 × 5 ≈ 180 queries), only after generalisation ticket 15's pre-registration —
  not this plan's decision.

Total ≤ ≈ 650 queries for the whole programme above; zero if the free keys exist. Nothing else in this plan needs a
provider call. No credit buys information the replay already gives (confirm behaviour, read order, readers on linked
pages), and no credit is spent to re-measure a rejected rule.

## 7. Not on this plan

- **Rejected rules, not retried without new evidence** (DoD loop rule; `hypotheses.json` to be completed with these
  entries by the H-1 worker): RK-2, RA-1 (never built), R3 `--sitemap-keep-evidence-sum`, R4 `--local-catalogue-entry`,
  PL-1, DI-1, EF-1 (4 reps: wrong pages up on the cohort), SO-1, SM-1, LX-1 as a whole, EU-1, TS-2, HL-1/UC-1/EX-2 (no
  effect), PD-2 (neutral). PD-1's boun loss stays with the PDF map; a replay re-measure is cheap but moves no DoD row
  today (PDF labels are outside the readable denominator), so it waits for that map's ticket.
- **Regime C flags** (§1.3): `--no-local-language-queries`, `--no-discovery-query-reserve`, `--no-shared-query-budget`,
  `--alias-queries`, `--through-identity-gate`, `--topic-search-continue`, `--no-topic-search`, `--no-scholarship-index-query`,
  `--award-route`, `--search-first`: unmeasurable or meaningless on replay; the seen-site re-measure of R5/R6/SQ-1 is live-only
  (13-Q4) and waits for free keys.
- **Wrong-scope rules**: on the signed corpora the development sets have 0 stable wrong-scope claims (unibo's one is a
  wrong page's claim and goes with CH-1). The heldout's degree-dimension wrong scope has no development instance to design
  from; the knockout arm's claim table (cycle 1) is where one would appear. No ticket until it does.
- **Rank rules for returned-not-read** (ubc, warsaw, hku): RA-1's offline replay rejected every shape; nothing new here.
- **A model-chosen page, the browser tier, access bypass, a provider change**: other maps / out of scope.
