# Next cycles plan, 2026-10-26: cycles 25–27 — the $0 queue after FRH, and the key track armed

Planner, 2026-10-25 evening, for the cycles that start 2026-10-26. Read: `LOOP_PROTOCOL.md` (the four harness rules of
2026-10-25), HANDOFF §1–§2, §5–§9 and every §8 line since 2026-10-23, `NEXT_CYCLES_2026-10-23.md` (what closed, §0–§7),
`NO_SEARCH_FLOOR_2026-10-21.md` §8–§8.6 (FRH step 2 and its amendment), `LOOP_REPORT.md` 2026-10-25 18:00 and 19:00,
`RELEASE_CHECKLIST.md` as **RC-2** left it (`d0f58c3d`, counted on `56d4e9c9`), `SEARCH_DEFINITION_OF_DONE.md`,
`KB_REFRESH_2026-10-23.md`, `RECORD_RUN_2026-10-19.md` (R1's pre-registered inputs), the free-search map with tickets 02,
03 and 10 and its `OWNER_QUESTIONS.md`, `benchmark-capture.yml`, `ci.yml`, the three Playwright configs, the hooks and
scripts under `.claude/hooks/` and `scripts/`, `git log` to `d0f58c3d`, the branch's CI and `benchmark-capture` run lists
(`gh`, ids, names, failing job names and conclusions only), and the two finished `verify_evidence` artifacts (development
KB universities only; §0.3). Development data only: **no heldout file, capture, log or label was opened; no dev5 per-case
row was read; no other scratchpad was read; no provider was called; no credit was spent.** The one number computed here
that is not in a committed file is the backend test count (`pytest --collect-only`, 7 720 at `56d4e9c9`; RC-2 counts the
same on CI).

Constraints, unchanged: paid search frozen; no free key yet (01-Q3, "later"); dev5 design-blind (13-Q1); a rule goes on
by default only under 13-Q2; the 6 / 60 / 120 budget; no PR unless the owner asks; model identifiers stay out; the nine
heldout universities are never opened. New since 2026-10-25 (owner): **at most 4 workers at once** — nine spent the
weekly model limit in three hours — so this plan is budgeted for four worktrees (RC-2's is merged and removed, so all
four start now); a pipeline ticket that runs the full suite repeatedly counts double, and none is proposed. The main
session's own rule from the same evening: **nothing is pushed before the gate script passes** (GATE-1, #1).

## 0. Where we stand after cycles 22–24

| row | cohort | dev2 | dev3 | dev4 | all |
|---|---|---|---|---|---|
| recorded replay (base3 Serper lists), today's defaults; last full four-set read 2026-10-20 (`aw2-*`), guards since | 5/0/0/5 (10-20); **4/1/0/5 in all four columns of `rp-frh2-cohort`** (10-25) | 6/0/1/3 | 10/0–1/0/3–4 | 5/0/1/3 (10-20); 4/0/1/4 off in `rp-frh2-dev4` (unibo's host stalled, §8.6.3) | **26/39** (10-20 composite), wrong 0; on 10-25 one cohort case reads **wrong** on identical lists → **WP-1** |
| **no search provider**, today's defaults (**FRH on**, LOOP_REPORT 10-25 19:00) | 4/0/0/6 | **3**/0/0/7 (khalifa) | **6**/0/0/8 (auckland) | 1/0/0/8 (kit: hit in `frh2-dev4`, missed in `sg1b-dev4` and `frh-dev4` the same afternoon) | **14/39**, wrong 0 (13 when kit misses) |
| own-index ceiling (`INDEX_CEILING`, IC-2b committed) | 3 | 1 | 6 | 1 | 11/39 |
| knockout guesses (gold hidden) | 0 | 1 (khalifa) | 1 (uio) + flake | 1 (ctu) | 3 + flake; `frh-ko-*` identical to off |
| precision · wrong scope · over budget | 1.0 · 0 · 0 | same | same; unsw still ends at 115–119 s but **keeps 8–15 predictions** (HC-1/HC-1b) | same | targets 1, 2, 5 met |
| dev5 no-search floor, aggregates only (D-F5) | — | — | — | — | unchanged: found 1/6 readable, 0 wrong pages, 0 over budget, 2 of 3 claims wrong-scope |
| **the product in kb mode** | KB **v23** `2026-10-25.kb-cs-bachelor.23`: 813 built facts, 871 in the merged view, **95** entries with verified data, 998 re-checkable records, 58 under `review` (43 robots-unreachable, 4 HTTP 405, 11 Incapsula — §0.3 clears the 11 and adds one TCD drift); ledger **RC-2** (`d0f58c3d`, counted on `56d4e9c9`): **97 PASS, 3 PARTIAL (3, 87, 92), 2 BLOCKED (29, 94)** over gates 1–102; 101 (compose kb run) and 102 (kb axe) PASS on CI output; gate 3 PARTIAL on the head's `ruff format --check` (fixed `ae676340`, its run in progress) | | | | |
| **tests** (RC-2, run 40222180992 on `781a4905`) | pytest **7 720** on SQLite and PostgreSQL, coverage 95.87 %; vitest **371**; `e2e` 79 + 1 skipped, `e2e:auth` 6, `e2e:kb` **21** | | | | the next recount is RC-3's |

What closed since the 2026-10-23 plan — every one of its fourteen rows, plus six it did not list:

| item | outcome |
|---|---|
| **FRH-2** | built (`c8c7b727`), replayed (12 runs, 10-25 18:00): both predicted gains, 0 wrong, knockout identical, **but groningen lost** (no search) and unibo lost (recorded) → §8.6 diagnosis: groningen was the follow (two non-hubs passing the trigger on the word "science", one hub followed twice), unibo was the host; amended (`8ecf06df`: whole-phrase URL test, one follow per hub), re-run (6 runs, 19:00): groningen kept, khalifa and auckland gained, 0 wrong → **on by default** (`2156b46c`); no-search floor **12/39 → 14/39** |
| **HC-1 / HC-1b** | a clock-killed case keeps its claims (`f5d317ba`); the per-case file now carries the parent's finalisation too (`15b7c42b`); DoD change-log line 2026-10-20; unsw keeps 8–15 predictions in every column of `hc1-dev3` / `rp-hc1-dev3` |
| **SG-1** | re-run under HC-1 (`sg1b-dev3`, `sg1b-dev4`): labels identical, reads **not** down on dev4 (200/189 → 202/208) → **off for good**; `hypotheses.json` row `rejected` |
| **I18N-3** | `DocumentItem.name_message` / `notes_messages` (served, never stored), `msg.document.*` ×22 in en/ru/kk (`147a2b27`) |
| **Explore menu** (I18N nav, owner request 10-25) | `JourneyMenu.tsx`, `topbar.explore`, the six navigation words in ru/kk **provisional** (`GLOSSARY.md` "Provisional — navigation") — the owner confirms the words (§7) |
| **A11Y-KB** + follow-up | `kb-accessibility.spec.ts` in `e2e:kb` (`875c6b56`); the Documents contrast fix (`797d1832`) — the spec excuses nothing; gate 102 text ready for RC-2 |
| **CS-1** | compose stack ships kb mode; the `compose-stack` CI job proves a kb run reads no page (`07bdd3dc`); gate 101 text ready |
| **MODE-1** | a demo server configured for kb shows the kb notice when demo is unticked (`16071924`); merged after `e2e:kb` alone, it turned the **demo** suite red on CI for six runs, 17:51–18:25 (§0.1) |
| **EX-1**, **SEC-3**, **DOC-1**, **LG-1**, **CM-1**, **IC-2b**, **KB-2** (v23) | all landed (`efd203dd`, `18da4147`, `c3a41f2a`, `b634d81e`, `109b1605`, `0e0af6b4`, `10be8d8c`) |
| **FLAKE-3** | three load-sensitive tests on an injected clock (`8460d8c9`) |
| moderator entry, vite 6.4.5, **E2E-LOCAL** | `e5730e5f`; `f7f6576b`; the demo suite runs the same locally as on CI — fonts from a worktree's linked `node_modules`, a favicon, a pinned never-adopted API (`56d4e9c9`) |
| **harness rules** (owner, 10-25) | `.claude/hooks/worker-cap.sh` (≤ 4 worktrees), `scripts/run_suite.sh` (two slots, 3 GB floor, own temp dir), `scripts/link_worktree_env.sh`, the session-start hook, the three-suites rule and the artefact-cleanup rule in `LOOP_PROTOCOL.md` (`e3faac33`) |
| **RC-2** | **landed** (`d0f58c3d`): 97 / 3 / 2 over 1–102; gate 2 records three red stretches since 10-20 with cause, fix and first green run; gate 3 PARTIAL; gate 92's still-English shell keys down to **5**; one new KB quote drift found (TCD, §0.3) |
| `ruff format` of the FRH test | `ae676340`: backend CI was red on `2156b46c` and `56d4e9c9` because the default flip was pushed without `ruff format --check` (§0.1) |
| two `verify_evidence` runs | **finished** 18:12–18:16 (runs 40220078860, 40220076931); read in §0.3; no ticket has consumed them → **KB-3** |

### 0.1 CI was red three times on 2026-10-25, and not once was it a flake

Each red was a CI gate that exists, was not run before the push, and failed on the first run after it:

| red | runs | failing job and gate | cause | fix, first green |
|---|---|---|---|---|
| 17:27 | 40216521401 (`f5d317ba`) | `security-and-containers`, `npm audit --audit-level=high` | vite 6.4.3 advisories GHSA-9jrq-w75r-8gcw / GHSA-rq7h-c2jc-7f22 | `f7f6576b` (vite 6.4.5) |
| 17:51 → 18:25 | 40218485400, 40219478885, 40220057742, 40220780546, 40220879459, 40221152011 (`f7f6576b` … `572e2392`) | `frontend`, `npm run e2e` | `journey.spec.ts` expected the **live** warning after unticking demo; MODE-1 (`16071924`) made a kb-configured demo server show the **kb** notice there — right, asserted by the kb suite, and merged after `e2e:kb` alone | `781a4905`; green run **40222180992** (all five jobs) |
| 18:49 → 18:50 | 40223065559, 40223159698 (`2156b46c`, `56d4e9c9`) | `backend (sqlite)`, `ruff format --check` | the FRH default-flip commit left `tests/test_follow_refused_hub_link.py` unformatted; the main session's merge ran neither `ruff format --check` nor the suite runner's lint step | `ae676340`; run 40225019401 on `d0f58c3d` in progress at writing; gate 3 is PARTIAL until it is green |

The owner's rules of the same day (all three browser suites for a frontend change; `run_suite.sh`) are policy, and
the main session has now asked for the mechanism: **one script, run before every push, that executes exactly the CI
gates of the touched areas and exits non-zero on the first failure** — that is **GATE-1** (§3, #1). RC-3 records the
third stretch under gate 2 and moves gate 3 back to PASS on `ae676340`'s green run.

### 0.2 The harness after 2026-10-25: four rules, and the gap each still has

| rule (LOOP_PROTOCOL) | mechanism today | what is still manual, and the ticket |
|---|---|---|
| ≤ 4 workers | `PreToolUse` hook refuses a fifth worktree | nothing; the plan itself is budgeted for 4 (§6) |
| the full suite through `run_suite.sh` | two flock slots, 3 GB floor, own temp dir, cluster cleanup | the *rest* of the merge gate (ruff/mypy over `evaluation` as CI does, the frontend four, the golden demo, the trailer check) is typed by hand each time → **GATE-1** |
| all three browser suites for a frontend change | a sentence in the protocol | nothing decides *which* changes need them or runs them in CI's order; and nothing checks that the three configs stay disjoint and never adopt a server — a fourth config, or a `reuseExistingServer: true` pasted from a tutorial, would pass CI → **E2E-CFG-1**; the demo and auth suites still run on the checkout's grown `backend/data` database, which CI never has (HANDOFF §9's 2026-09-06 trap) → **E2E-DB-1** |
| artefact cleanup (`git checkout -- docs/screenshots`, delete `playwright-report*`, `test-results*`) | a sentence in the protocol | every local run overwrites 38 tracked PNGs and leaves report folders → **E2E-HYG-1** makes the rule a no-op |

### 0.3 The two evidence checks that were in flight: read

Both ran on GitHub runners with the production `Fetcher` (no robots override), 2026-10-25, development KB universities
only:

| run | drafts | known rows | quote found | not found |
|---|---|---|---|---|
| 40220078860 (`evidence-check-40220078860`) | `kb_drafts.2026-10-19/topup_documents4` (the 11 NUS / CityUHK PDF rows and their batch) | 87 | **82** — NUS (qs2027-010) **6/6**, CityUHK (qs2027-052) **5/5**: the PDFs read from the runner, the quotes are there; the sandbox's Incapsula stub was access, not drift | **5**: UQ (qs2027-041) documents ×5, `HTTP 403` from the runner — access from this vantage point too |
| 40220076931 (`evidence-check-40220076931`) | `kb_drafts.2026-10-23/batch1` (KB-2's re-quotes) | 2 | **2/2**: NTU deadline 2027-01-20, Auckland tuition range | — |

So KB-2's two CI items both close the way the better case predicted: the 11 Incapsula rows stand as verified and their
`review: quote_gone` marks come off; the 2 re-quotes are CI-verified; UQ's five rows are recorded as blocked.

RC-2 added one row the same evening: `verify_evidence --from-kb` from the sandbox on v23 read **checked=998 verified=908,
12 not found** — the 11 NUS / CityUHK rows above (access, now CI-verified) and **one real drift**: TCD (qs2027-075)
`scholarships.e3_balanced_solutions_better.exists`, quoted from `https://www.tcd.ie/e3/education/scholarships/` on
2026-10-20, whose quote the page no longer prints. Its sibling `…applicability.international` on the same page is
checked with it. That row needs a re-read, not bookkeeping. Both go into **KB-3** (§3): a data rebuild, one re-draft, no
code change.

**Three benches and the product, where each is.** The recorded replay is exhausted for rule gains (§2.1) and shows one
new wrong page on the cohort to name (WP-1). The **no-search bench is at its $0 ceiling**: FRH was the last two-set rule
and it landed; what remains is 25 cases in classes no $0 rule reaches (§2.2) — NS-RES-1 writes the residue down and
declares the bench. The **product in kb mode** is launch-ready as far as a repository can make it: the kb journey, its
accessibility, the compose stack's kb run and the ledger's gates 97–102 are CI jobs; what launch still needs is the
owner's (merge to `main`, deployment, a lawyer, a payment account, the glossary words — §7). The **harness** is the one
place where $0 work is still worth a worker: the owner's four new rules of 2026-10-25 are policy, and §0.2 names the
script, the config test, the scratch database and the screenshot fix that make them mechanical. After that, and after
KB-3 and the residue entry, the $0 queue is **empty** (§2.7), and this plan says so rather than inventing a cycle. The
**key track** (§4) is written so the main session fires it the minute `UNIMATCH_EXA_API_KEY` lands: a 1-query smoke,
R1 (44 cases, one column, 264-query cap), the `recorded-search/2` store, the re-baseline — with the exact inputs and a
query budget. Its one $0 prerequisite, the smoke mode, is a one-hour ticket in the harness lane, right after the gate
script.

## 1. The ranked list

Ranking = expected movement (a red CI avoided, a measurement that can start, a fact served correctly, a declared
bench) per worker hour. Dispatches cost no worker time (§5). Effort `medium` throughout; no pipeline ticket. File
ownership in §3 and §4.5; the four worker lanes in §6.

| # | item | track | kind | worker h | runs | what it moves | why it pays | expected outcome |
|---|---|---|---|---|---|---|---|---|
| 1 | **GATE-1** `scripts/pre_merge.sh` — exactly the CI gates of the touched areas, one command, non-zero on the first failure | A | harness | 2.5 | 0 | the merge gate becomes mechanical: backend → `ruff check`, `ruff format --check`, `mypy` (over `evaluation` as CI does) and the suite through `run_suite.sh`; frontend → `tsc`, `eslint`, vitest, build, **all three Playwright suites** and the artefact cleanup; the golden demo; the `Agent:` trailer; a test holds the script to `ci.yml` | **three red CI stretches on 10-25** (§0.1), each a gate that exists and was not run before the push — the last one by the main session itself; it will run this script before every push | a red local gate instead of a red CI |
| 2 | **SM-1** a 1-query smoke mode in `benchmark-capture.yml` | B (prereq, $0) | harness | 1 | 0 | the key track's first step costs **1** query instead of a 6-query capture, prints the provider's answer and lets the dashboard cost be read before 264 are spent | the owner says "later" for the key; when it lands, the main session should not be building a workflow step with the clock running | `mode=preflight`; the job's first real run is the smoke itself |
| 3 | **E2E-CFG-1** a CI check over the three Playwright configs | A | harness (test) | 1 | 0 | `reuseExistingServer` is `false` everywhere, the two ports, the stated mode, a **disjoint spec partition** (a new `kb-*.spec.ts` today runs in both the demo and the kb suite), and the auth config enters `tsconfig`'s `include` (it is type-checked by nobody today) | E2E-LOCAL fixed the configs by hand; nothing stops the next hand | a vitest in the `frontend` CI job |
| 4 | **E2E-DB-1** the demo and auth suites on a scratch database, like the kb suite | A | harness | 1.5 | 0 | a local run of `npm run e2e` is the CI run: CI has an empty `backend/data`, a developer's has every earlier run and `seed_demo.py` (HANDOFF §9, 2026-09-06: 5 failed / 64 did not run on a clean `main`) | E2E-LOCAL's title says "runs the same locally as on CI"; the database is the difference that is left | each suite wipes and migrates its own `backend/data/e2e-<suite>` |
| 5 | **KB-3** the two CI evidence checks folded in, the TCD scholarship quote re-read: v24 | A | KB data (+ one re-draft) | 2 | 1 (`verify_evidence`) | 11 facts the product serves lose a `review` mark they never deserved; **one fact the product serves whose quote is gone** (TCD) is re-quoted or becomes `unverified_quote`; UQ ×5 recorded as access; the KB refresh doc says what CI and RC-2 found | gate 99 counts "re-verifiable"; the 11 were re-verified on 10-25 and the committed file still says `quote_gone`, and RC-2's own check found a twelfth row that is real drift | KB v24, `has_verified_data` 95 (or 94 with the reason named), nine journey universities untouched |
| 6 | **FLAKE-4** the community e2e tag per project | A | e2e fix | 0.5 | 0 | gate 2's recorded intermittent red (`community.spec.ts:48`, run 39386144462): one `RUN` tag for two projects on one API | "a fix is queued" since 10-20; still at l.16 | gate 2 PASS without a caveat (RC-3) |
| 7 | **E2E-HYG-1** screenshots to a gitignored root unless asked; ignore globs | A | harness | 1 | 0 | the cleanup rule becomes a no-op: no tracked file changes on a local run | 38 tracked PNGs are rewritten by every run of the demo suite, and every worker is told to `git checkout` them | `git status` clean after all three suites, no command |
| 8 | **WP-1 → NS-RES-1** the cohort recorded wrong page named; the no-search residue by class; the ledger rows | A | measurement + docs | 2 | 0 (base4, §5) | `rp-frh2-cohort` reads 4/1/0/5 in every column where 10-20 read 5/0/0/5 — the same recorded lists; and the bench's 25 residue cases are named only in a plan, not in LOOP_REPORT or `hypotheses.json` | a wrong page in all four columns is a regression or a site change, not noise; a bench is declared in the report, not in prose | one LOOP_REPORT entry each; FRH / CO-1 / SG-1 rows current; free-search ticket 10's no-search row |
| 9 | **RC-3** the ledger after this cycle | A | docs | 1 | 0 (CI) | gate 3 PARTIAL → PASS on `ae676340`'s green run; gate 2's third stretch and FLAKE-4; 99 (v24, the TCD row); the summary | RC-2 counted on `56d4e9c9` with gate 3 red on purpose; the cycle's head fixes it | counted on the cycle's head; last |
| 10 | **STORE-1** commit the `recorded-search/2` store R1 builds; tests over both stores | B (after R1) | harness data | 1.5 | 4 (`base5-*`) | the recorded bench gets Exa's lists beside Serper's; `recorded_search_misses` tells whether the store is complete | the bench has replayed one provider's lists since 10-19 | `recorded_search.r1.json`, HANDOFF §8 |
| 11 | **FPR-1** `FREE_PROVIDER_REPLAY_2026-10-xx.md` — ticket 03's table | B (after R1) | docs | 1.5 | 0 | the free-search map's first measured provider row against the Serper control and 01-Q2's bar; the per-query cost read off the dashboard | the owner chooses a `live` default from a table with numbers, not from the last outage | ticket 03 resolved; ticket 10's Exa row |
| 12 | **PROBE-1** (optional) `query_probe` accepts a keyed provider other than Serper | B | harness | 0.5 | 1 (15 queries) | LQ-2a's 15 pre-registered phrases can run on the same key | the probe job today refuses without `UNIMATCH_SERPER_API_KEY` | only if the budget after R1 allows (§4.3) |

Not on the list, and why: §2 (what is exhausted) and §8 (what is not built).

## 2. What is exhausted, honestly

### 2.1 The recorded-search replay, for rule gains: exhausted (unchanged)

No rule since AW-2 has had a plausible gain on it and none is proposed. It runs guard arms only. The one thing it
*does* show today is a cohort case that turned **wrong** between 10-20 and 10-25 on identical lists (`rp-frh2-cohort`
4/1/0/5 in both off and both on columns, so not FRH, which made no follow on cohort recorded, §8.6). WP-1 names it; it is
a 1-hour read of a committed artifact, not a rule.

### 2.2 The no-search bench: at its $0 ceiling, 14/39

FRH was the last cause with two development sets behind it (NO_SEARCH_FLOOR §4, §7.5, §8.3); it landed with 0 wrong pages
and both gains. The 25 misses that remain are, by class (NEXT_CYCLES_2026-10-23 §2.2's list, to be re-counted by NS-RES-1
from the `frh2-*` on columns — that list names 28 cases for 25 misses, so three of its names are hits, groningen among
them):

| class | what it needs | $0 rule? |
|---|---|---|
| access from every vantage point we have (aalto, toronto, hku, kaznu, ub, kuleuven) | the owner's computer as a runner (01-Q4) tells whether it is the datacenter or us; a robots refusal stays a refusal | no |
| the gold on a department or catalogue host the homepage never links and no sitemap we read lists (kaist, ntutw, msu, um, unibo, ktu, chula, usp, warsaw) | a search provider (the key) | no |
| another registrable domain (tsinghua) | a provider, or a signed extra domain | no |
| no usable sitemap and a gold deeper than two hops (ethz, tcd, delft, …) | a provider | no |
| catalogue picks without the programme (tec, uba, uct, rwth) | a provider, or a product decision about related programmes | no |
| the four clock cases (uio, ctu, ubc, uppsala) — all unreachable golds | nothing a rule changes; SG-1 saved 6 s, not 20–30 | no |

NS-RES-1 writes this table with the exact 25 names into LOOP_REPORT and declares the bench; the next movement on it is
the key (§4) or the vantage point (§7), not a worker.

### 2.3 KB manual rounds: still stopped — KB-3 is bookkeeping, not a round

KB-3 adds no fact from a new page; it records what CI verified. The pool (60 not published, 63 access, 47 not researched)
and the two owner flags (`--yearless-deadlines-with-caveat`, `--standing-fee-policy-current`) are unchanged (§7).

### 2.4 Product hygiene for the kb launch: one item left, and it is a flake

The 2026-10-23 list (I18N-3, CS-1, A11Y-KB, EX-1, DOC-1, MODE-1, CM-1) is done, and RC-2 counts 97 PASS over 102 gates.
What this plan can still do for the product without the owner is FLAKE-4 and the gate-3 recount (RC-3). Launch itself
waits on the owner: merge to `main` (`kb-refresh.yml` reads the default branch; gates 97–102 hold on the branch only),
an external deployment, gate 87 (a lawyer), gate 94 (a payment account and a price), gate 29 (the tag), gate 92 — whose
still-English shell list is now exactly **five keys**: `topbar.newCase`, `topbar.demoData`, `topbar.liveSources`,
`brand.tagline`, `brand.disclaimer` (11 on 10-20), plus the six provisional navigation words and I18N-3's document terms
awaiting a person's review. None of these is a worker ticket, and no ticket here pretends to move them.

### 2.5 Localisation: at its $0 floor

After I18N-3 and the Explore menu, what stays English is the page's own words, parameters as the university wrote them,
and glossary terms a person must choose (I18N_RESULTS §"Still English"). The provisional navigation words are the owner's
to confirm (§7).

### 2.6 Rules and research with nothing left to do at $0

LQ-2a (built; needs the key — §4.2 B5). LOCO-1 / NN-1 / IG-2 (the overlay signature). S4, AI-1, AW-1, SH-1, LL-1 (recorded,
triggers written). CO-1 V1 / V2 (superseded: FRH reached both their cases; NS-RES-1 closes the rows). SG-1 (off for good).
D-D ablations, G-16a, CX-1 / FR-3 (closed). The twin checks (signatures). The own index as a provider, Common Crawl, the
model hint (as before).

### 2.7 The harness: after cycle 25, empty too

GATE-1, E2E-CFG-1, E2E-DB-1, E2E-HYG-1, FLAKE-4 and SM-1 are the whole list the owner's 2026-10-25 rules and the 10-25 red
runs open. Nothing else in `scripts/`, `.claude/hooks/` or the workflows is known to be manual, drifting or wrong. When
they land, the next harness change comes from a verdict, not from this plan.

## 3. Track A — worker tickets ($0, no owner)

Common to every ticket: no dev5 or heldout page, label, capture or row; no pipeline flag (nothing under `app/pipeline`,
`app/adapters/discovery` or `scoring.py` is touched by any ticket here); golden demo byte-identical
(`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`, brief §5.7 order); gates green
(AGENTS §5, plus `evaluation` in ruff/mypy as CI runs them); commit locally with the `Agent:` trailer; a HANDOFF §8 line
for any contract change (append-only; the main session resolves the mechanical conflict). **A ticket that touches a
Playwright config, spec or helper runs all three browser suites before it is handed over**, and only one worker runs
them at a time on this machine (ports 5173/8099; the configs refuse to adopt a server) — in cycle 25 that is W2 alone.
`RELEASE_CHECKLIST.md` belongs to RC-3, last. LOOP_REPORT is appended by WP-1/NS-RES-1 and by the main session at
verdict time; the conflict is mechanical. Until GATE-1 lands, the main session types its gate before every push:
`ruff check` + `ruff format --check` + `mypy` over `app tests evaluation`, `scripts/run_suite.sh`, the frontend four,
and all three browser suites when any frontend file changed.

### GATE-1 — `scripts/pre_merge.sh`: exactly the CI gates of the touched areas, one command (harness worker, ≈ 2.5 h; first)

- **Why.** §0.1: three reds in one afternoon, each a gate that exists in `ci.yml` and was not run before the push —
  `npm audit`, the demo suite, `ruff format --check`. The main session will run this script before every push; a red
  here is a red CI that did not happen.
- **Change.** New `scripts/pre_merge.sh [--base REF] [--scope auto|backend|frontend|all] [--pg] [--e2e auto|always|never] [--dry-run]`,
  run from any worktree (`git rev-parse --show-toplevel`; the venv and `node_modules` symlinks are what
  `link_worktree_env.sh` made). `--base` defaults to `origin/claude/greeting-16wj2z`. It stops at the first failure
  (exit 1) except for the cleanup, which always runs:
  1. **Preconditions.** `git status --porcelain` empty; when the browser suites are in scope, ports 5173 and 8099 free
     (`ss -ltn` or `lsof -i`, whichever exists) — a busy port names its process and stops, since the configs refuse to
     adopt a server (HANDOFF §9, E2E-LOCAL); `scripts/clean_test_tmp.sh` once.
  2. **Scope**, from `git diff --name-only "$BASE...HEAD"` (`--scope auto`): a path under `backend/` → the backend
     gates (3) and the golden demo (4); under `frontend/` → the frontend gates (5), suites included; under
     `.github/workflows/` or `scripts/` → the YAML parse and `bash -n` of the changed files plus
     `pytest tests/test_workflow_runners.py tests/test_expert_workflow.py`; docs only → step 7 alone, and the summary
     says so. `--scope all` runs everything; a push that bundles several cherry-picks is `all` unless every commit is
     docs.
  3. **Backend, exactly CI's `backend` job** (`ci.yml` l.31–34): `ruff check app tests evaluation`,
     `ruff format --check app tests evaluation`, `mypy app tests evaluation`, then the suite through the two-slot
     runner with coverage passed explicitly because `run_suite.sh` clears `addopts`:
     `scripts/run_suite.sh --cov=app --cov-fail-under=92 -n 4 tests`. `--pg` adds CI's PostgreSQL job
     (`./.venv/bin/python scripts/pg.py .venv/bin/pytest -q -n 4 tests`); off by default locally, CI runs it anyway.
     (AGENTS §5 names `app tests` only; CI and this script include `evaluation`. The script follows CI; the main
     session shows the owner the one-line AGENTS §5 correction — AGENTS.md is not edited by a worker.)
  4. **Golden demo.** On a throwaway database (`UNIMATCH_DATABASE_URL=sqlite:///$RUN_TMP/demo.db`,
     `UNIMATCH_DEMO_MODE=true ./.venv/bin/alembic upgrade head`),
     `UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false ./.venv/bin/python seed_demo.py` and the brief §5.7
     assertions on its output: Groningen first, UBC in `OUT_OF_BUDGET` (the exact strings `seed_demo.py` prints; the
     worker reads them, never guesses).
  5. **Frontend, exactly CI's `frontend` job** (`ci.yml` l.53–66): `npm run typecheck`, `npm run lint`,
     `npm test -- --run`, `npm run build` (the bundle budget is inside `build`), then **all three** browser suites in
     CI's order — `npm run e2e`, `npm run e2e:auth`, `npm run e2e:kb` — sequential, the port check repeated before each.
     `--e2e never` is for a worker whose ports are taken (it prints that the suites were skipped and exits 1 unless
     `--scope backend`); `always` forces them for a docs-only diff.
  6. **Cleanup, on `trap EXIT`.** `git checkout -- docs/screenshots` (a no-op once E2E-HYG-1 lands),
     `rm -rf frontend/playwright-report* frontend/test-results*`; then `git status --porcelain` must be empty again, or
     the gate is red with the list.
  7. **Commits.** Every commit in `$BASE..HEAD` carries an `Agent:` trailer (`git log --format=%B "$BASE..HEAD"` —
     the count of `^Agent: ` lines equals `git rev-list --count`) and none has a `wip:` subject.
  8. **Summary.** A table step → exit code → seconds; exit 1 on any red. `--dry-run` prints every command and runs
     none.
- **Tests.** New `backend/tests/test_pre_merge_script.py`: (a) `bash -n`; (b) **the mirror**: every `run:` command of
  `ci.yml`'s `backend` and `frontend` jobs (YAML-parsed as in `test_workflow_runners.py`; `npm … --prefix frontend`
  normalised to the script's form; checkout / setup / venv / pip / `playwright install` lines on an allow-list) appears
  in the script, so the gate cannot drift from CI without a red test; (c) the script's e2e commands are exactly the
  three `e2e*` scripts of `frontend/package.json`; (d) the scope table is pinned on three synthetic diffs (docs only →
  step 7 alone; `backend/` → the four backend commands and the demo; `frontend/` → the four frontend commands and the
  three suites) through `--dry-run`; (e) `shellcheck` when installed, else a skip whose message says so (gate 26's
  rule).
- **Bar.** `--dry-run` reviewed; steps 1–4 and 7–8 run green in the worker's worktree with `--e2e never` (the ports
  belong to W2 in cycle 25); the main session runs the full gate once, with the suites, on the cycle's first frontend
  cherry-pick, and its output goes to HANDOFF §6; **from then on nothing is pushed without it.**
  `docs/process/ONBOARDING.md`'s first-session list gains the one command. The protocol's own wording is the owner's;
  the main session tells him the script exists.
- **Owns.** `scripts/pre_merge.sh` (new), `backend/tests/test_pre_merge_script.py` (new), `docs/process/ONBOARDING.md`
  (one paragraph).

### SM-1 — a 1-query smoke mode (harness worker, ≈ 1 h; after GATE-1, same worker; Track B's prerequisite)

- **Why.** The expert job skips its pre-flight for every provider but Serper (`benchmark-capture.yml` l.805–812:
  `search pre-flight skipped: provider is $UNIMATCH_SEARCH_PROVIDER`), and the smallest capture is a one-case
  `columns=1` record run of 6 queries. The key track's first step should cost one query and print the provider's
  answer, so the dashboard's per-query cost can be read before R1's 264.
- **Change.** `.github/workflows/benchmark-capture.yml`: `mode` gains the option `preflight`; a new job `preflight`
  (`if: inputs.mode == 'preflight'`, `runs-on: ${{ inputs.runner || 'ubuntu-latest' }}`, `timeout-minutes: 10`, the
  checkout / Python / venv steps of the expert job) that: (1) reuses the expert job's "Select the search layer" step
  verbatim, and refuses `none`, `recorded` and `auto` (an explicit keyed or keyless provider only — the point is to
  test *that* key); (2) runs the "Search query cap" step with `planned=1` (a `preflight` branch beside the
  `expert_paired` one; `max_search_queries` required, ≥ 1); (3) runs
  `.venv/bin/python -m evaluation.research.search_preflight --max-search-queries "$CAP" --search-ledger out/search_ledger.json`
  (one query, `max_results=1`, the adapter's key-masked error excerpt on failure, exit 1 → job red); (4) writes
  `out/config.txt` (provider, `decided_by`, cap, the ledger) and uploads `preflight-<run id>` (config, ledger, stdout,
  stderr). No key is ever printed; the adapter masks it in the body excerpt and nothing else about the request is
  logged.
- **Not changed.** The expert job's pre-flight stays Serper-only: widening it to Exa/Tavily would make R1's plan 265
  and break RECORD_RUN §2's pre-registered 264 (`test_record_run.py::test_a_record_run_of_the_44_ids_plans_264_and_263_is_refused`)
  for no gain once the standalone smoke exists.
- **Tests.** `backend/tests/test_expert_workflow.py` (one new class) or new `test_preflight_mode.py`, reading the YAML
  as `test_workflow_runners.py` does: the job exists and is gated to `mode == 'preflight'`; its run block names
  `search_preflight` with both cap flags; no step runs `evaluation.research.live`; the provider step refuses
  `none`/`recorded`/`auto` (assert the `case` arms); `test_workflow_runners.py` stays green by construction (the
  `runner` choice is the existing hosted-only one). `python -c "import yaml, sys; yaml.safe_load(open(sys.argv[1]))"`
  and `bash -n` over the extracted run blocks.
- **Docs.** `docs/process/RECORD_RUN_2026-10-19.md` gains "§0 Smoke before R1" with the inputs of §4.2 B1.
- **Bar.** YAML parses; the tests pass; the job cannot be dry-run without a key by design — its first real run is the
  smoke. The main session cherry-picks it as soon as it lands (right after GATE-1), so the branch head carries it on
  the day the key lands.
- **Owns.** `.github/workflows/benchmark-capture.yml`, `backend/tests/test_expert_workflow.py` (or the new test file),
  `docs/process/RECORD_RUN_2026-10-19.md` (one section).

### E2E-CFG-1 — a CI check over the three Playwright configs (e2e worker, ≈ 1 h)

- **Change.** New `frontend/src/e2e-configs.test.ts` (vitest's `include` is `src/**/*.test.{ts,tsx}`), reading
  `playwright.config.ts`, `playwright.auth.config.ts`, `playwright.kb.config.ts` and `e2e/kb-env/serve-api.sh` as text
  (no import of `@playwright/test`):
  1. every `reuseExistingServer:` is `false`, exactly two per config (API, Vite);
  2. the API server's `url` is `127.0.0.1:8099/api/health` and Vite's `127.0.0.1:5173` in all three (the proxy
     hard-codes 8099);
  3. **the partition**: for every `e2e/*.spec.ts`, exactly one config claims it — demo = `testDir` minus `testIgnore`,
     auth = `testMatch` `**/auth-journey.spec.ts`, kb = `testMatch` `**/kb-*.spec.ts`. Today the demo config ignores
     `kb-journey` and `kb-accessibility` **by name**, so a third `kb-*.spec.ts` would run in both suites: the ticket
     changes the demo `testIgnore` to the glob `**/kb-*.spec.ts` and the test holds the partition from then on;
  4. **the stated mode**: the demo config's API `env` carries `UNIMATCH_DEMO_MODE: 'true'` and
     `UNIMATCH_KNOWLEDGE_MODE: 'kb'`; the auth config's API entry states both too (add them if absent — same worker as
     E2E-DB-1); `kb-env/serve-api.sh` exports `UNIMATCH_KNOWLEDGE_MODE` and `UNIMATCH_DEMO_MODE` (the worker reads the
     script; if it inherits one, it states it);
  5. `tsconfig.json` `include` names all three config files — `playwright.auth.config.ts` is missing today, so
     `npm run typecheck` has never read it; add it and fix whatever it surfaces inside that file only.
- **Bar.** vitest green locally and in the `frontend` CI job; `npm run typecheck` clean with the auth config included;
  the demo suite (`npm run e2e`) still runs the same files (the glob changes nothing today).
- **Owns.** `frontend/src/e2e-configs.test.ts` (new), `frontend/tsconfig.json`, `frontend/playwright.config.ts` (the
  `testIgnore` line), `frontend/playwright.auth.config.ts` (the two env rows, if absent).

### E2E-DB-1 — the demo and auth suites on a scratch database (e2e worker, ≈ 1.5 h; after E2E-CFG-1, same worker)

- **The gap.** `playwright.config.ts` and `playwright.auth.config.ts` start `bash ../backend/run.sh --with-worker` with
  no database URL, so a local run reads the checkout's `backend/data` database — grown by every earlier run and by
  `seed_demo.py`. HANDOFF §9 (2026-09-06) records the symptom: the journey's first assertion fails because the app
  restores the organisation's latest case instead of a blank profile, and five spec files' `beforeAll` fall with it
  (5 failed / 64 did not run on a clean `main`). CI has an empty checkout, so CI never sees it; a developer does. The kb
  suite already does this right: `e2e/kb-env/serve-api.sh` takes a scratch directory whose name must be `e2e-kb*`
  (refusing to wipe anything else), wipes it, and sets `UNIMATCH_DATABASE_URL`, `UNIMATCH_CACHE_DIR` and
  `UNIMATCH_EXPORT_DIR` inside it.
- **Change.** New `frontend/e2e/demo-env/serve-api.sh` modelled on kb-env's (no network guard — the demo and auth
  suites read fixtures): `E2E_SCRATCH_DIR` must be named `e2e-demo*` or `e2e-auth*` under `backend/data/`; wipe,
  `mkdir`, export the three paths, then exactly what `run.sh --with-worker` does today (the worker reads `run.sh`
  first: if it migrates, the script only sets the env; if not, `alembic upgrade head` precedes it). Both configs'
  API `command` points at the script with its directory in `env` (`frontend/e2e/kb-env/paths.ts` shows the pattern;
  add `demo-env/paths.ts` rather than widening kb-env's). The configs keep their stated mode rows (E2E-CFG-1's test
  reads them there). Nothing is seeded: CI runs the suites on an empty database and is green, and the journey starts
  its own demo run; the auth suite's persistence is within one run.
- **Tests.** E2E-CFG-1's vitest gains: each API `command` names a `serve-api.sh` under `e2e/*-env/`, and that script
  sets `UNIMATCH_DATABASE_URL` under its scratch directory and name-checks the directory before `rm -rf`.
  `backend/tests/test_e2e_kb_harness.py` holds the kb script; mirror its shell assertions for the new one
  (`bash -n`, the name guard).
- **Bar.** All three suites green in the worktree, and green again right after `seed_demo.py` has written the
  checkout's own database (the trap's recipe); green on CI; HANDOFF §9's 2026-09-06 entry gets one "fixed by" line
  (the "restore by latest" product note stays as the owner's product question — this ticket fixes the harness, not the
  restore rule).
- **Owns.** `frontend/e2e/demo-env/serve-api.sh` and `paths.ts` (new), `frontend/playwright.config.ts`,
  `frontend/playwright.auth.config.ts`, `frontend/src/e2e-configs.test.ts` (shared with E2E-CFG-1, same worker),
  `.github/workflows/ci.yml` only to add the new scratch directories to the failure artifact (optional),
  `docs/process/HANDOFF.md` §9 (one line).

### FLAKE-4 — the community e2e tag per project (e2e worker, ≈ 0.5 h; same worker)

- **The defect.** `frontend/e2e/community.spec.ts` l.16 `const RUN = \`e2e${Date.now()…}\`` is one tag for the desktop
  and mobile projects, which run the same file against one API, so the feed holds two posts with the same tag and
  `page.getByText(\`#${RUN}\`)` / `.post.filter({ hasText: RUN })` meet two (gate 2's recorded red, run 39386144462,
  `[mobile] community.spec.ts:48`, "the per-run tag is not unique per project"). The queued fix never landed.
- **Change.** The tag carries the project: `test.info()` is available inside hooks and tests, not at module level, so
  compute it in `beforeAll` (or a `tag()` helper) as `e2e<d|m><digits>` from `test.info().project.name`; every
  locator that reads it is unchanged.
- **Tests.** The spec itself; run the demo suite twice locally (both projects) with no strict-mode violation.
- **Bar.** Green on CI on two consecutive runs; RC-3 moves gate 2's "recorded intermittent red" to "fixed by <hash>".
- **Owns.** `frontend/e2e/community.spec.ts`.

### E2E-HYG-1 — screenshots to a gitignored root unless asked; ignore globs (e2e worker, ≈ 1 h; same worker, last)

- **Change.** `frontend/e2e/helpers.ts`: `shot()` writes under `test-results/screenshots/<project>/` (gitignored)
  unless `E2E_SCREENSHOTS=docs` is set, in which case it writes to `../docs/screenshots` exactly as today — the
  deliberate regeneration for the README; CI sets nothing and never committed a screenshot. `.gitignore`:
  `/frontend/playwright-report*/` and `/frontend/test-results*/` (today the three report folders, `test-results/` and
  `test-results-kb/` are named one by one; a new config's output folder would be untracked noise). `ci.yml`'s
  failure-artifact paths are unchanged.
- **Tests.** In `frontend/src/e2e-configs.test.ts`: `helpers.ts`'s default root is under `test-results/` and the
  `docs/screenshots` root appears only behind the env var; `.gitignore` carries both globs. One local run of all three
  suites: `git status --porcelain` is empty afterwards with no cleanup command.
- **Bar.** The protocol's cleanup rule becomes a no-op; GATE-1's step 6 stays as belt and braces; the main session
  tells the owner the sentence can go (his file).
- **Owns.** `frontend/e2e/helpers.ts`, `.gitignore`, `frontend/src/e2e-configs.test.ts` (shared, same worker).

### KB-3 — the two CI evidence checks folded in, the TCD quote re-read: v24 (KB worker, ≈ 2 h, 1 CI run)

- **Inputs.** The artifacts of runs 40220078860 (`topup_documents4`: 87 known rows, 82 found; NUS 6/6, CityUHK 5/5; UQ
  qs2027-041 ×5 `HTTP 403`) and 40220076931 (`batch1`: NTU deadline, Auckland tuition, 2/2) — §0.3. Download them into
  the worker's own scratchpad; copy `report.json` beside each drafts folder as `evidence_check.ci-2026-10-25.json`.
  And RC-2's finding: TCD (qs2027-075) `scholarships.e3_balanced_solutions_better.exists`, `quote_gone` on
  `https://www.tcd.ie/e3/education/scholarships/` (verified 2026-10-20; the sibling
  `…applicability.international` quotes the same page).
- **Do.** Generalise `kb_drafts.2026-10-23/build_v23.py` to take a version and build date and any number of evidence
  reports (`build_v24.py`, or the same script with `--version 2026-10-26.kb-cs-bachelor.24 --built-at 2026-10-26`),
  composing the two existing `kb_build` functions as before (nothing under `app/` or `kb_build.py` changes). Effect, by
  record: the 11 NUS / CityUHK document facts lose `review` (CI found the quote: `verified_on` 2026-10-25,
  `verified_by: ci`, value unchanged); the 2 batch1 facts carry the CI check beside the sandbox's; UQ's 5 document facts
  keep value and date with `review: {needed, class: fetch_error, status_code: 403, checked_on: 2026-10-25}` — access
  from a runner, not drift — and `KB_REFRESH_2026-10-23.md`'s blocked list names them. `review_queue` shrinks by the
  11 (the UQ rows either change class or join it; the number is reported either way).
  **The TCD row** (real drift): read `https://www.tcd.ie/e3/education/scholarships/` as it stands through the
  production `Fetcher` from the sandbox (`--trust-env-proxy`, robots honoured, no override) with the
  `university-admissions-research` skill: a verbatim quote that still states that the award exists and who may apply
  (both facts share the page), or each fact becomes `unknown`, kind `unverified_quote`, dated — never a retyped value.
  Draft into `kb_drafts.2026-10-26/batch1/` in the dev5 formats; the main session dispatches `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-26/batch1` (§5); the build takes that report too, and
  a CI-found quote wins over the sandbox read. A `--from-kb` check of the committed v24 must then read the TCD rows as
  verified or `unknown`, never `quote_gone`.
- **Docs.** `KB_REFRESH_2026-10-23.md`: the "CI, not dispatched by the worker" items get their results and run ids, and
  a dated section for RC-2's twelfth row; `KNOWLEDGE_BASE.md`'s version line → v24.
- **Tests.** `tests/test_knowledge_base.py` green (the merge loses no verified fact; the unknown-kinds table; the REL-1
  pins; the unknown-kinds table gains the TCD rows if they go `unknown`); `has_verified_data` **95**, or 94 with TCD
  named as the reason if the award was its only verified fact; the kb journey's nine universities (Edinburgh, ETH,
  Kyoto, Stanford, Fudan, Oxford, KTH, Sheffield, Groningen) have no row among the ≈ 20 touched, so `e2e:kb` is
  unchanged and this ticket, having no frontend change, does not run it; `seed_demo.py` unchanged (demo mode never
  reads the KB).
- **Bar.** Every fact whose mark comes off was found by the CI checker on the committed URL; no value changes except
  the TCD re-quote or `unknown`; v24's `diff` against v23 over facts is exactly the 18 records' metadata plus the TCD
  rows; gate 99 text for RC-3: "998 records; 908 verified from the sandbox on 10-25, +11 from the runner; TCD re-quoted
  (or unknown, dated); 5 UQ rows blocked from both vantage points".
- **Owns.** `backend/app/knowledge/kb_cs_bachelor.json`, `backend/evaluation/research/expert/data/kb_drafts.2026-10-23/batch1/evidence_check.ci-2026-10-25.json`
  (new), `backend/evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents4/evidence_check.ci-2026-10-25.json`
  (new), `backend/evaluation/research/expert/data/kb_drafts.2026-10-26/batch1/` (new, the TCD re-draft),
  `backend/evaluation/research/expert/data/kb_drafts.2026-10-19/unknown_kinds.json` (rows only if TCD goes `unknown`),
  `backend/evaluation/research/expert/data/kb_drafts.2026-10-23/build_v23.py` (or `build_v24.py` beside it),
  `docs/process/KB_REFRESH_2026-10-23.md`, `docs/process/KNOWLEDGE_BASE.md` (the version line).

### WP-1 — the cohort recorded wrong page, named (measurement worker, ≈ 1 h; starts now)

- **Do.** Download `expert-recovery-40220881831` (`rp-frh2-cohort`) into the worker's own scratchpad (development set,
  cohort); `python -m evaluation.research.scorecard <dir> --dataset evaluation/research/data/ground_truth.reviewed11.json`
  → the case that reads `wrong` in all four columns and the page it confirmed. Classify: (a) a known residue class
  (RESIDUE_LEDGER Table A: ubc's degree word, kaist's department host — `wrong_programme_pages` was 0–2 per repetition
  at baseline 3) that `aw2-cohort` happened to read 0 on 10-20 → a LOOP_REPORT line, no ticket; (b) a page confirmed
  only since a default flip (NS-1b / PC-1 on 10-20 09:15, after `aw2`'s 05:20; FRH on 10-25, which made no cohort
  follow on recorded) → a diagnosis ticket with the mechanism, written for the next plan; (c) the site changed (the
  gold moved or a twin appeared) → a twin note for the owner's signature queue. `base4-cohort` (§5), when it lands,
  adds four columns to the same question.
- **Bar.** The case and the URL named with the column rows; no heldout, no dev5.
- **Owns.** `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` (one appended entry).

### NS-RES-1 — the no-search bench declared at 14/39; the ledgers current (same worker, ≈ 1 h; after WP-1)

- **Do.** LOOP_REPORT: one entry "the no-search bench at its $0 ceiling" — 14/39 and 0 wrong (kit's flake noted), the
  §2.2 table with the exact 25 names read from the `frh2-*` on columns and what each class needs; the DoD is untouched
  (targets and denominators stay). `hypotheses.json` (its own row shape): **FRH** `tested`, on by default 2026-10-25,
  the §8.6 narrowing and the groningen / unibo diagnosis, cited; **CO-1-V1** and **CO-1-V2** `candidate` → closed with
  the reason (FRH reached auckland and khalifa, so the one-set re-open trigger cannot fire); **SG-1** gains the 10-25
  re-run under HC-1 (final). Free-search ticket 10: the "no search at all" row filled from this (the per-set floor and
  the residue classes); the Exa row stays for FPR-1.
- **Bar.** The JSON parses; `python -m evaluation.research.scorecard --help` unaffected; every row cites a document and
  section; no case outside the 44.
- **Owns.** `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` (append), `backend/evaluation/research/expert/data/hypotheses.json`,
  `docs/process/wayfinder/free-search/issues/10-residue-and-stop.md` (one row).

### RC-3 — the ledger after this cycle (docs worker, ≈ 1 h; `RELEASE_CHECKLIST.md` only; last)

- **Do.** On the cycle's head, after every other ticket is cherry-picked: gate 3 — PARTIAL → PASS on `ae676340`'s
  green `release-gates` run (40225019401 if it is the one; `ruff format --check` output shown) with the sizes from
  `npm run build`; gate 2 — the third red stretch of 10-25 (40223065559, 40223159698, the unformatted FRH test, the
  fix, the first green run) beside RC-2's three, and FLAKE-4's hash against the recorded intermittent red; gate 1 —
  the counts if the green run's differ from RC-2's (7 720 / 371 / 79+1 / 6 / 21); gate 99 — KB v24 (§3 KB-3's bar
  text); gate 16 — the secret grep re-dated; the summary recounted (97 → 98 PASS when gate 3 is green). Gates 101–102
  are RC-2's and are only re-cited.
- **Bar.** `PASS` only with output shown; the owner-dependent rows (87, 94, 29) and gate 92 PARTIAL unchanged.
- **Owns.** `RELEASE_CHECKLIST.md`.

## 4. Track B — the key track, ready to fire

### 4.1 What arrives and where it goes

The owner adds the repository secret **`UNIMATCH_EXA_API_KEY`** (and, if he opens Tavily too, **`UNIMATCH_TAVILY_API_KEY`**).
Nothing else is configured: `benchmark-capture.yml` already reads both (`env:` of the `capture` and `expert` jobs),
`search_provider=exa` / `tavily` stops before any capture when its secret is missing (`::error::exa requires
UNIMATCH_EXA_API_KEY; no capture started`), the cap step refuses a keyed run without `max_search_queries`, and the
`(N+1)`th query is refused unsent. The product's default stays `UNIMATCH_SEARCH_PROVIDER=none` / kb mode; nothing in this
track changes a product setting.

**Timing rule.** Fire B1 the hour the key lands. Fire B2 the same day — **except on the 31st**: a run that straddles the
1st does not match the monthly figure (ledger §9; RECORD_RUN §2), so a key that lands on 2026-10-31 waits for 11-01.

### 4.2 The firing sequence

| step | dispatch (`benchmark-capture.yml`, `runner=ubuntu-latest`) | queries (cap) | read | go / stop |
|---|---|---|---|---|
| **B1 smoke** | `mode=preflight`, `search_provider=exa`, `max_search_queries=1`, `run_tag=smoke-exa` (SM-1). **Fallback if SM-1 has not landed:** `mode=expert_paired`, `columns=1`, `case=groningen`, `search_provider=exa`, `max_search_queries=6`, `extra_args` and `base_args` empty, `run_tag=smoke-exa` — one capture, ≤ 6 queries, and it exercises `make_v2_store` on one case | 1 (or ≤ 6) | the job log: `search pre-flight ok: exa answered with 1 result(s)` (or the capture's `search_calls`); **the dashboard balance before and after**, read by the owner or the main session, written into LOOP_REPORT as the per-query cost | **stop** if the provider answers an error (402 = credit spent; the adapter maps it to `SearchUnavailable`): ask the owner, spend nothing more. **Stop** if cost × 264 > **$5** (half the monthly credit): ask before R1 |
| **B2 R1** | **RECORD_RUN_2026-10-19 §2 verbatim**: `mode=expert_paired`, `columns=1`, `case=groningen delft aalto vienna warsaw ubc toronto hku ntu kaist ethz psaclay uppsala tcd tsinghua tec uba kaznu uct khalifa imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula ctu vut rwth kit unibo taltech ktu boun itu`, `search_provider=exa`, `max_search_queries=264`, `base_args` and `extra_args` empty, `case_parallelism=5`, `seconds_per_case=120`, `max_pages=60`, `search_first=false`, `run_tag=r1` | 264 planned (44 × 1 × 6 + 0: Exa has no pre-flight), **≈ 205 expected** (4.66 per case per column, ledger) | `out/config.txt` (`search query cap: 264 for exa (planned 264)`, the ledger count), the artifact `expert-recovery-<run>` with `out/<case>-on/…`, every `<case>.search.json`, and `out/recorded_search.r1.json`; scored per set (§4.4) | a cap of 263 is refused before any query (`test_record_run.py`); the job's 55-minute limit holds 44 cases at parallelism 5 (≈ 18 min of captures) |
| **B3 store** | none — the run built `out/recorded_search.r1.json`; if the step failed (`continue-on-error`), rebuild locally per RECORD_RUN §3 (`--record-run <run> <created_at> <head_sha> <dir> --cases …`) | 0 | `<set>: N cases, M requests` for cohort 10, dev2 10, dev3 15, dev4 9; schema `recorded-search/2` | **STORE-1** commits it (§4.5) |
| **B4 re-baseline** | 4 runs: `mode=expert_paired`, `columns=4`, `search_provider=recorded`, `base_args=--recorded-store evaluation/research/data/recorded_search.r1.json`, `extra_args` empty, `case=<set>`, `run_tag=base5-<set>` | 0 | per set: hit / wrong / related / missed on Exa's lists in four columns; `recorded_search_misses_discovery` **= 0** and `recorded_search_misses_topic_scholarship` **= 0** (the v2 target) — a miss means the store lacks a request (a case whose live search failed is left out by the builder) and names it | the default-store decision (§4.4) |
| **B5 optional, same key** | (a) **R1′ Tavily**: the B2 inputs with `search_provider=tavily`, `run_tag=r1t` — only with `UNIMATCH_TAVILY_API_KEY`, charged to Tavily's 1 000 credits; (b) **LQ-2a's 15 phrases** through `mode=query_probe` once PROBE-1 widens its provider gate (today it needs `UNIMATCH_SERPER_API_KEY`) | 264 (Tavily); 15 (Exa) | ticket 03's second row; LQ-2a's pre-registered table | only if §4.3's budget line allows |
| **B6 gated** | **R2** (dev5, `columns=4`, cap 312, aggregates only) | 312 | 13-Q2 (b) for the flipped rules | **not before 13-Q1…Q5 are signed**; not in this plan's firing sequence |

### 4.3 Query budget (Exa, the month the key lands)

Exa's free credit is $10 a month ≈ 2 500 instant searches at $4 per 1 000 (`provider-survey-2026-10-19.md`); the
adapter asks for `contents.highlights`, which Exa bills as contents on top — so the smoke's dashboard delta, not the
list price, is the number. Tavily: 1 000 credits a month, 1 per basic search.

| step | planned (cap) | expected sent | cumulative Exa |
|---|---:|---:|---:|
| B1 smoke | 1 (fallback 6) | 1 (≈ 5) | 1–6 |
| B2 R1 | 264 | ≈ 205 | ≤ 270 |
| B3 store, B4 re-baseline (`recorded`) | 0 | 0 | ≤ 270 |
| B5 (b) LQ-2a probe | 15 | 15 | ≤ 285 |
| B6 R2 (gated) | 312 | ≈ 243 | ≤ 597 |
| **month total, everything fired** | **≤ 597** | **≈ 464** | **≈ 24 %** of 2 500 at list price |
| B5 (a) R1′ Tavily | 264 | ≈ 205 | Tavily's own 1 000 |

Stop rules: B1's cost × 264 > $5 → ask before B2; any `search_budget_exhausted` in a capture → the scorecard marks the
repetition unhealthy and the run is read as such, never re-dispatched the same day; a 402 anywhere → stop, nothing is
retried (the adapter never retries; the cap refuses the next query unsent).

### 4.4 Reading R1 and the store, and the bars

1. **Health** (`out/config.txt`, `capture.json`): the ledger count ≤ 264; no `search_budget_exhausted`; `search_failures`
   0 or the codes named; every case has `<case>.search.json`; `cases_over_budget` as today's defaults (the four clock
   cases).
2. **Ticket 03's row** — `python -m evaluation.research.stage_summary <dir> --dataset <gold>` per set (cohort
   `ground_truth.reviewed11.json`; dev2/dev3/dev4 `draft3`): `gold_returned_by_search` and `returned_by_family:*`
   against the Serper base3 control **8/10 · 9/10 · 11–12/14 · 5/5**. **Bar (01-Q2, recommended, unanswered): no
   worse by more than one case on any set.** FPR-1 writes the table either way.
3. **Programme outcome on a live Exa column** — the scorecard per set: hit / wrong / related / missed beside the
   recorded (Serper) row of §0. One column, so no stability claim; **a wrong page confirmed on the Exa arm is a stop**
   (diagnose before the store is replayed as a default).
4. **Store** (STORE-1): schema `recorded-search/2`; `test_the_committed_store_holds_the_four_development_sets_only` and
   `test_the_committed_store_keys_are_todays_discovery_requests` pass over it as over base3.
5. **Re-baseline** (`base5-<set>`): both miss counters 0; hits per set vs the base3 replay row. **Decision:** Exa's
   lists hit ≥ Serper's − 1 per set with 0 wrong → `DEFAULT_RECORDED_STORE` moves to `recorded_search.r1.json` (one
   HANDOFF §8 line; the base3 store stays committed as history, `--recorded-store` selects it); worse → base3 stays the
   default and ticket 10's Exa row says so with the numbers. Either way LOOP_REPORT gets the "where we stand" row on
   the new store beside the base3 one.

### 4.5 Worker tickets of the key track

**STORE-1** (harness data worker, ≈ 1.5 h, after B2). Commit `backend/evaluation/research/data/recorded_search.r1.json`
from the artifact (or the local rebuild), with the run id, `created_at` and head sha the builder stamps; `sha256` in
the commit message. `backend/tests/test_recorded_search.py`: the two committed-store tests parametrised over both
stores; `test_search_capture_log.py` l.109 unchanged (base3). `DEFAULT_RECORDED_STORE` unchanged until §4.4 (5); the
`--recorded-store` path in `base_args` selects the new one. HANDOFF §8: the store, its run, its schema. Owns: the store
file, `backend/tests/test_recorded_search.py`, HANDOFF §8 (one line).

**FPR-1** (docs worker, ≈ 1.5 h, after B2 is scored). `docs/process/FREE_PROVIDER_REPLAY_2026-10-xx.md` as ticket 03's
deliverable: provider × set `gold_returned_by_search` vs the Serper control, per family, the gold's rank where returned,
the per-query cost from the dashboard delta (relayed by the main session; never estimated), one terms row quoting the
provider's page (`assets/provider-survey-2026-10-19.md`), the verdict against 01-Q2's bar; ticket 03 → `resolved` with
its gist; ticket 10's Exa row. Owns: the new doc, `issues/03-free-tier-provider-replay.md`, `issues/10-residue-and-stop.md`
(the Exa row; NS-RES-1 owns the no-search row — sequential if one worker).

**PROBE-1** (optional, ≈ 0.5 h, before B5 (b)). `benchmark-capture.yml`'s `query_probe` job accepts `search_provider`
like the expert job (the key check per provider; the 300-query cap stays); `search_probe.py` unchanged if it already
takes the configured provider (the worker reads it). Owns: `.github/workflows/benchmark-capture.yml` (the one job; after
SM-1 has landed, same file — same worker or sequential).

## 5. Dispatch table (main session, 0 worker hours)

Common inputs as NEXT_CYCLES_2026-10-23 §4 (`runner=ubuntu-latest`, `mode=expert_paired`, `seconds_per_case=120`,
`max_pages=60`, `case_parallelism=5`). Score cohort on `reviewed11`, dev2/dev3/dev4 on `draft3` with `--allow-drafts`;
dev5 never, except `--summary-only` on a pre-registered run.

| run | set(s) | inputs that differ | `run_tag` | read |
|---|---|---|---|---|
| **release-gates** on `d0f58c3d` (run 40225019401, in progress at writing; the first run after `ae676340`) | — | — | — | green → gate 3 PASS for RC-3 (`781a4905`'s run 40222180992 is already the green run gate 2 cites); red → the job name back to the main session the same hour |
| **release-gates** of every cycle-25 cherry-pick (GATE-1, SM-1, E2E-*, KB-3) | — | — | — | the `frontend` job now runs E2E-CFG-1's test; `compose-stack` unchanged |
| **KB-3 TCD batch check** | — | `mode=verify_evidence`, `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-26/batch1` | — | the `evidence-check-<run>` artifact beside the drafts; a quote CI finds wins over the sandbox read; a `quote_gone` on CI too → `unknown`, dated |
| **Clean baseline 4** ($0; 8 runs) | 4 sets recorded; 4 sets no-search | `search_provider=recorded` / `none`, `columns=4`, `extra_args` empty | `base4-<set>`, `ns-base4-<set>` | one "where we stand" row per bench with every default on (LV-1, AW-2, NS-1b, PC-1, **FRH**); replaces §0's composite; `base4-cohort` adds four columns to WP-1's question; `ns-base4-dev4` says whether kit is a hit or a flake |
| **D-D interaction check** (optional, idle runners) | 4 sets | `extra_args=--no-<rule>` for `abstain-on-unreadable-entry`, `confirm-head-identity`, `reject-combination-head`, `reject-subpage-head`; knockout too | `rp-abl-<rule>-<set>` | identical → absorbed (ledger note); a stable loss → load-bearing; no default change from this alone |
| **B1 smoke** (key) | — | `mode=preflight`, `search_provider=exa`, `max_search_queries=1` (fallback §4.2) | `smoke-exa` | §4.2; the dashboard delta → LOOP_REPORT |
| **B2 R1** (key) | the 44 | RECORD_RUN §2 verbatim; `max_search_queries=264` | `r1` | §4.4 (1)–(3); artifact → STORE-1, FPR-1 |
| **B4 re-baseline** (key, after STORE-1) | 4 sets | `search_provider=recorded`, `base_args=--recorded-store evaluation/research/data/recorded_search.r1.json`, `columns=4` | `base5-<set>` | §4.4 (5) |
| **B5** (key, optional) | the 44 / — | `search_provider=tavily`, cap 264 / `mode=query_probe` after PROBE-1, cap 15 | `r1t` / `lq2a-probe` | ticket 03's second row / LQ-2a's table |

The KB refresh workflow is still **not** dispatchable from the branch (`kb-refresh.yml` reads the default branch); §7.

## 6. The cycles — four lanes, never a fifth

RC-2 is merged and its worktree removed, so cycle 25 starts all **four** lanes (the hook refuses a fifth). Only W2
runs browser suites in cycle 25 (ports). No ticket runs the full suite repeatedly.

| lane | cycle 25 (now) | cycle 26 | cycle 27 |
|---|---|---|---|
| **W1** harness, scripts and workflows | **GATE-1** (2.5 h; `--e2e never` in the worktree; cherry-picked first) → **SM-1** (1 h) | follow-ups from GATE-1's first real run by the main session; **PROBE-1** if B5 (b) is wanted | **STORE-1** when R1 lands; otherwise idle |
| **W2** e2e harness (the only browser-suite runner) | **E2E-CFG-1** → **E2E-DB-1** → **FLAKE-4** → **E2E-HYG-1** (4 h; all three suites once per ticket that touches a config, spec or helper) | follow-ups from CI (a partition the test finds, an auth-config type error) | idle |
| **W3** KB | **KB-3** (2 h; the TCD re-draft first, so its batch check is dispatched early) | — | **FPR-1** when R1 is scored |
| **W4** measurement and docs | **WP-1 → NS-RES-1** (2 h) | **RC-3** (1 h) once the cycle's tickets are cherry-picked and `ae676340`'s run is read | idle, or the follow-up WP-1 names |
| **main session** | type the gate by hand until GATE-1 lands, then `scripts/pre_merge.sh` **before every push** (its first full run, suites included, on the first frontend cherry-pick); cherry-pick GATE-1, SM-1, then the rest as they land; dispatch base4 / ns-base4 (8) and KB-3's batch check; read run 40225019401 | read base4 → LOOP_REPORT "where we stand"; owner batch (§7) once, with the AGENTS §5 / LOOP_PROTOCOL notes | the key: B1 the hour it lands, B2 the day (not the 31st), B4 after STORE-1, the default-store decision; no key: RC-3 closes the cycle and **the $0 queue is empty** — the main session says so to the owner with §7 instead of inventing work |

Expected after cycles 25–27 without the owner: CI green and held green by a local gate that runs what CI runs; the three
browser suites disjoint, pinned and on scratch databases; a local run that leaves no tracked file changed; KB v24 with
the 11 runner-verified facts unmarked; the cohort recorded wrong page named; the no-search bench declared at 14/39 with
its 25 residue cases by class; the ledgers current; the ledger recounted. **With the key:** a 1-query smoke with a cost
reading, R1's 44 live Exa captures, the second recorded-search store, the re-baseline on it, and ticket 03's first
measured row — within one day of the secret appearing.

## 7. What each pending owner answer unlocks

| answer | unlocks (one line) |
|---|---|
| **Exa key** (`UNIMATCH_EXA_API_KEY`; 01-Q3 / Q6) | §4: B1 the same hour, R1 the same day (not the 31st), the `recorded-search/2` store, the re-baseline, ticket 03's row; ≈ 205 queries of ≈ 2 500; **Tavily** beside it (`UNIMATCH_TAVILY_API_KEY`) → R1′ for a second row |
| **Merge to `main`** | `kb-refresh.yml` runs at all (schedule and dispatch read the default branch) and the 60-day clock starts; gates 97–102 hold on `main`; ledger "Order of work remaining" item 10 closes |
| **Native-name overlay signature** (`catalogue_native_names.proposed.json`) | production `native_name` for the signed rows; the identity gate reads dev5 7/13 → 9/13 (IG-2); LQ-2a's `native_name` branch stops being inert |
| **Three twin signatures** (Q1 uct keep; Q2 kuleuven "(b) without the credits clause"; Q3 tcd) | `dev2.draft4` / `dev3.draft4` after a CI `verify_evidence`: knockout dev2 1 → 0, dev3 kuleuven wrong → hit in readable repetitions; recorded hits 26 → 27–28/39 by re-score, 0 code |
| **U7** (deadline variant A or B) | the Fudan-type row stops reading GAP for a window the applicant never had; `eligibility.evaluate` is shared with live mode, so `seed_demo.py` is re-checked; ≈ 1.5 h |
| **KFUPM** (two official pages disagree on the waived tuition) | one held-back fact enters the next KB build, or stays `unknown` with the disagreement as its kind |
| **Self-hosted runner** (01-Q4; SR2-03's setup rules first) | one `read_pages` dispatch of RP-1's 105 rows on 28 universities; the 43 robots-unreachable and 4 HTTP-405 KB rows, UQ's 5 and the access six of the development misses re-probed from a home IP; the kb-refresh workflow's self-hosted input |
| **Osaka / IP Paris** (Q7, `--standing-fee-policy-current`: ETH, EPFL, FU Berlin, Heidelberg, UZH, KTH, Lund, IP Paris, Osaka, Nanjing, Kyoto, ISCT) and the yearless-deadline flag | 12 fees shown current with the "fee policy page; no academic year printed" caveat; yearless deadlines become facts with `year_inferred`; one `kb_build`, 0 code |
| **Melbourne** (SR2-05: the related route with `verified: false`) | whether a REL-1 route whose quote failed is offered at all; one KB statement served or withheld |
| **The glossary person** (gate 92): the six provisional navigation words (`GLOSSARY.md` "Provisional — navigation"), I18N-3's document terms, and the **five** shell keys still English on purpose — `topbar.newCase`, `topbar.demoData`, `topbar.liveSources`, `brand.tagline`, `brand.disclaimer` | each answer is one `i18n` edit; all of them together, gate 92 PASS |
| **A lawyer (87), an ApiPay account and price (94), the release tag (29)**, an external deployment | the rows that need a person, not a cycle |
| **AGENTS §5** one line (`evaluation` in the ruff/mypy gate, as CI runs it) and **LOOP_PROTOCOL**'s cleanup sentence after E2E-HYG-1 | the rulebook matches the gate script; both are the owner's files |
| **13-Q1…Q5** (the second look) | R2 on dev5 (cap 312, aggregates) → 13-Q2 (b) for the flipped rules and a reading of D-F5's two wrong-scope claims beside a search arm |

## 8. What this plan does not build, and why

| item | why not now | re-opens when |
|---|---|---|
| **CO-1 V1 / V2** | FRH reached auckland (dev3) and khalifa (dev2) with 0 wrong; the one-set trigger cannot fire; NS-RES-1 closes the rows | a new development case loses a gold to the confirm-queue tie |
| **SG-1** | off for good (10-25: reads not down on dev4 under HC-1); 2026-10-23 §7: no further re-open | — |
| the kaist catalogue-role refusal; the 25 no-search residue cases | §2.2: every class needs a key, a vantage point or a product decision | the key (§4) or 01-Q4 |
| widening the expert job's pre-flight to Exa / Tavily | it would make R1's plan 265 against the pre-registered 264 (`test_record_run.py`); the standalone smoke (SM-1) does the job at 1 query | never needed |
| any provider run before B1's cost is read | the ledger's rule: nothing may cost money by accident; highlights are billed as contents | B1 |
| R2 (dev5) | design-blind until 13-Q1…Q5 are signed; the budget line exists (312) | the signatures |
| a product change for the "restore by latest" note (HANDOFF §9) | E2E-DB-1 removes the harness symptom; the product rule is a decision about which case a browser restores — the owner's | a user report, or the owner |
| FR-3 / CX-1 step 2, R4 default-on, the 300 s product deadline, AW-3, PD-1, CA-1, IB-1, AI-1, AW-1, SH-1, LL-1, SP-2 | as NEXT_CYCLES_2026-10-23 §7 and 2026-10-21 §7: gain 0 on every bench today | the triggers written there |
| a KB manual round for new facts; I18N-4; U7, U9, B7, D7, P3, P4, Q7, the Melbourne route | §2.3, §2.5, owner decisions | the answers |
| a fifth worker, a pipeline ticket, a second e2e runner | the owner's rules of 2026-10-25 | — |
| the own index as a provider, Common Crawl discovery, model extraction, any heldout look, DoD targets or denominators, the 6 / 60 / 120 budget | as before | — |
