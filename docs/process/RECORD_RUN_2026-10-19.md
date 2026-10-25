# Record run R1, 2026-10-19: dispatch inputs, the v2 store and its replay target

Ticket W4 / WF-03a in [NEXT_CYCLES_2026-10-19.md](NEXT_CYCLES_2026-10-19.md) §2.1 and §4. The ledger is
[SEARCH_VOLUME_LEDGER_2026-10-19.md](SEARCH_VOLUME_LEDGER_2026-10-19.md). **R1 has not been dispatched.** It needs
the owner's Exa key in the repository secrets (owner question Q6). Nothing in this document has called a provider.

R1 captures each of the 44 development cases once on Exa. The run produces three things. First, a
`recorded-search/2` store with titles and snippets, which also covers the topic, scholarship and identity searches.
Second, ticket 03's `gold_returned_by_search` row for each query family. Third, the 51-query miss probe from
MISS_STAGES §4, which is a subset of the run.

## 0. Smoke before R1 (SM-1, added 2026-10-26)

Before R1 spends 264 queries, one query checks that the key answers and lets the per-query cost be read off the
provider's dashboard (NEXT_CYCLES_2026-10-26 §4.2 B1). Dispatch `benchmark-capture.yml` with:

| input | value |
|---|---|
| `runner` | `ubuntu-latest` |
| `mode` | `preflight` |
| `search_provider` | `exa` (the job refuses `auto`, `none` and `recorded`: the smoke tests *that* key) |
| `max_search_queries` | `1` (required, ≥ 1; the job plans exactly 1) |
| `run_tag` | `smoke-exa` |
| everything else | default (`case`, `base_args`, `extra_args` empty) |

The `preflight` job runs the expert job's "Select the search layer" and "Search query cap" steps verbatim, then
`python -m evaluation.research.search_preflight --max-search-queries "$CAP" --search-ledger out/search_ledger.json`:
one public query with `max_results=1` through the product client, charged to the ledger before it is sent. Nothing
is captured. The artifact `preflight-<run id>` holds `out/config.txt` (provider, `decided_by`, cap, the ledger),
`search_ledger.json`, and the step's stdout and stderr. No key is printed; the adapter masks it in the error excerpt.

- **Go:** the log says `search pre-flight ok: exa answered with 1 result(s)`. Read the dashboard balance before and
  after and write the per-query cost into LOOP_REPORT.
- **Stop** if the provider answers an error (402 = credit spent; the job is red with `::error::search pre-flight
  FAILED: exa answered http …`): ask the owner and spend nothing more. **Stop** if cost × 264 > $5: ask before R1.
- The expert job's own pre-flight stays Serper-only, so R1's plan stays 264 (§2).
- **Fallback** if the `preflight` mode is not on the branch: `mode=expert_paired`, `columns=1`, `case=groningen`,
  `search_provider=exa`, `max_search_queries=6`, `base_args` and `extra_args` empty, `run_tag=smoke-exa`. That is
  one capture and at most 6 queries.

## 1. What W4 changed in the harness

| piece | before | after W4 |
|---|---|---|
| `benchmark-capture.yml` input `columns` | did not exist: `expert_paired` always ran four captures per case (off/on/on/off) | `4` (default, unchanged) or `1`. With `1`, a record run makes one `on` capture per case in the list and has no `off` arm. The `on` arm runs `base_args` plus `extra_args`, so leave both empty to capture the default pipeline. |
| "Search query cap" step | the plan was 6 × cases × 4 for `expert_paired` | the plan is 6 × cases × `columns`, plus 1 for the Serper pre-flight. A `columns` value other than 1 or 4 is refused. With `none` or `recorded` **and** a cap, the step checks the plan against the cap as a dry run and passes no ledger. Without a cap, those two providers start uncapped, as before. |
| `search_provider` choice | auto / exa / exa_mcp / none / recorded | adds **tavily** and **brave**. The adapters already exist in `app/adapters/search/`. An explicit choice reads only its own secret, `UNIMATCH_TAVILY_API_KEY` or `UNIMATCH_BRAVE_API_KEY`. If that secret is missing, the job stops with `::error::<provider> requires UNIMATCH_<PROVIDER>_API_KEY; no capture started`. Only the provider's name is printed, never a key. |
| step "Build the recorded-search v2 store (make_v2_store)" | did not exist | runs only when `columns` is `1` and the provider is a keyed one. It writes `out/recorded_search.<run_tag or record>.json` into the artifact. The step is `continue-on-error`, so a failed build never costs the captures. |
| `python -m evaluation.research.recorded_search` | `--source SET RUN_ID CREATED_AT HEAD_SHA DIR`, given once per set | also takes `--record-run RUN_ID CREATED_AT HEAD_SHA DIR --cases ID …`, which reads the single artifact for every development set the case list touches. It refuses any heldout or dev5 id before reading anything. It writes nothing unless the store comes out as `recorded-search/2` (exit status 1). |
| scorecard | the replay target was judged on discovery misses only | if a repetition replayed a `recorded-search/2` store, each arm gets one more row: `recorded_search_misses_topic_scholarship`, target `== 0 (v2 store)`. A v1 replay keeps its old targets. So does a replay captured before `capture.json.config.recorded_search_store.schema` existed. |

## 2. R1 dispatch inputs (Exa, all four development sets, 264-query cap)

Dispatch `benchmark-capture` on a ref that contains W4.

| input | value |
|---|---|
| `mode` | `expert_paired` |
| `columns` | `1` |
| `case` | `groningen delft aalto vienna warsaw ubc toronto hku ntu kaist ethz psaclay uppsala tcd tsinghua tec uba kaznu uct khalifa imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula ctu vut rwth kit unibo taltech ktu boun itu` |
| `search_provider` | `exa` (needs the secret `UNIMATCH_EXA_API_KEY`) |
| `max_search_queries` | `264` |
| `base_args` | *(empty)* |
| `extra_args` | *(empty)* |
| `case_parallelism` | `5` |
| `seconds_per_case` | `120` |
| `max_pages` | `60` |
| `search_first` | `false` |
| `runner` | `ubuntu-latest` |
| `run_tag` | `r1` (this names the store `out/recorded_search.r1.json`) |
| `plan`, `resume_run_id` | *(empty)* |

The 44 cases break down as cohort 10, dev2 10, dev3 15 and dev4 9. The cap step prints
`search query cap: 264 for exa (planned 264)`: 44 cases × 1 capture × 6 queries, plus 0 because Exa has no pre-flight.
A cap of 263 is refused before any capture starts. `test_record_run.py::test_a_record_run_of_the_44_ids_plans_264_and_263_is_refused`
checks this. A dry dispatch with `search_provider=none` and `max_search_queries=263` fails the same way and sends
nothing. With `264` it captures without search and without a ledger.

Before dispatch:
- Read the remaining Exa credit off the dashboard **that day** (ledger §8). Exa bills `highlights` as contents.
- R1 must run before 2026-10-31, because a run that straddles the 1st does not match the monthly figure.
- Expect about 205 queries sent. The ledger's measured mean is 4.66 per case per column.
- No heldout id and no dev5 id appears in the list. The builder never lists their files.

**R1′ (Tavily comparison).** Use the same inputs with `search_provider=tavily` (secret `UNIMATCH_TAVILY_API_KEY`) and
`run_tag=r1t`. The cap stays at 264 and is charged to Tavily's own 1 000 credits.

## 3. After the run: `make_v2_store`

The run builds the store itself. If that step failed, or if you want to rebuild it against the run's own timestamp,
rebuild it locally from the artifact:

```bash
RUN=<run id>
gh api repos/wpalish/ashyq-apply/actions/runs/$RUN --jq '.created_at, .head_sha'   # CREATED_AT, HEAD_SHA
# download artifact expert-recovery-$RUN and unzip it into /tmp/r1 (it holds out/<case>-on/<stamp>/…)
cd backend
./.venv/bin/python -m evaluation.research.recorded_search \
  --record-run "$RUN" <CREATED_AT> <HEAD_SHA> /tmp/r1 \
  --cases groningen delft aalto vienna warsaw ubc toronto hku ntu kaist ethz psaclay uppsala tcd tsinghua tec uba kaznu uct khalifa imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula ctu vut rwth kit unibo taltech ktu boun itu \
  --out evaluation/research/data/recorded_search.r1.json
```

The command prints `<set>: N cases, M requests` for each of the four sets. Exit status 1 with the message "no
capture kept a search log" means no capture wrote `<case>.search.json`. In that case the store is not v2 and nothing
is written. In the in-run step, the date passed as `CREATED_AT` is the step's own time, not the run's creation time,
so use the local rebuild above when provenance must match the API.

**Known limit (Exa and Tavily).** Discovery sends the `local_language` family through `search_localized` only when the
provider has that method. Serper and `recorded` have it; Exa and Tavily do not. The store keys that family's traced
list with the rebuilt `hl`/`gl` request, so a replay still finds its URLs. The titles and snippets, however, sit on a
second entry keyed by the request that was actually sent, which has no `hl`/`gl`. A replay therefore ranks
`local_language` lists on URL words alone, as on base3. That family is not a miss, and the scorecard row in §4 does
not count it.

## 4. Re-baseline the replay on the v2 store ($0)

Run four `expert_paired` runs, one per development set. Use `columns=4` and `search_provider=recorded`, with
`base_args=--recorded-store evaluation/research/data/recorded_search.r1.json` and `extra_args` empty. Leave
`max_search_queries` empty: `recorded` sends nothing. Then read `scorecard` on each run:

- `recorded_search_misses` (discovery) stays `<= baseline`, as it always has.
- **New target row.** `recorded_search_misses_topic_scholarship` must be `== 0 (v2 store)` in every arm. A row that
  reads `NO` means the replay asked a topic or scholarship search the record run never sent. That happens when the
  pipeline's query text changed after R1 or when a case was unavailable during R1. That rule or case is then not
  measurable on the store until it is re-recorded. Expectations from NEXT_CYCLES §2.2: warsaw goes from `missed` to
  `hit`, and the ten regime-C labels become measurable.

## 5. Tests (offline, no provider called)

`backend/tests/test_record_run.py` covers the following:
- the 44-id plan, with 264 accepted and 263 refused, for exa, tavily and brave;
- Serper's +1 pre-flight;
- the paired default of 4 columns;
- refusal of any `columns` value other than 1 or 4;
- the dry `none`/`recorded` plan check;
- tavily and brave failing fast without their own secret in both jobs, with no key printed;
- the single-column loop, which makes one `out/<case>-on` capture per case and passes the cap through;
- `make_v2_store`: its sources, its refusal of heldout and dev5 ids, writing v2 and refusing v1, and the workflow
  step's arguments;
- the scorecard row on v2 and its absence on v1 or unlabelled replays;
- `schema` in the capture config.
