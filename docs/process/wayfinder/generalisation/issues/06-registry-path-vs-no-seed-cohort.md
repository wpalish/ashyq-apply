# H-B: registry-seed path vs no-seed path vs identity-gate path — the cohort through three arms

Type: task
Status: resolved (harness built 2026-10-19; the H-B verdict waits on the two paired runs in the Answer, main session dispatches)
Blocked by: —
Map: ../map.md · AFK — harness code (measurement only), then paired runs on the cohort; `loop-engineering`.

## Question

All nine heldout cases and the ten cohort cases run `canary.run_canary(CASE_DOMAINS[case_id], False)`: the registry
selector, `institution_registry.json` seeds (`program_catalog`, `admissions`, `costs`, `scholarships`; cohort
verified 2026-08-28, the nine 2026-09-05, KAIST re-verified 2026-09-22), slots pre-filled, sitemaps of the seed hosts
read. dev2 / dev3 / dev4 run `entries=[dev2_entry(case)]`: homepage only, empty seeds — the path every rule since
2026-10-17 was tuned on. Production's 481 non-registry universities run a third path: `_identify_site` first, then the
no-seed discovery. On the nine the stage table shows 2.3–3.0 discovery queries per case (three families) against dev4's
3.7–4.0 (six families), 9 000–10 000 sitemap URLs seen, 4 wrong confirms of 5. **Does the path itself change the
funnel?** The only development set that can answer is the cohort, because only it has registry seeds.

## Build (measurement only, `live.py` + `canary_discovery.py`)

- `--no-registry-seeds`: a cohort case is captured through `run_canary(None, False, entries=[cohort_entry(case)])`
  where `cohort_entry` builds `{"name","country","city","homepage"}` from the registry row *without its seeds*
  (same shape as `dev2_entry`). The capture records `config.entry_path = "no_seed"`.
- `--through-identity-gate` extended to the cohort: `seed_entry` today reads `DEV2[case_id]`; add a cohort → top-500
  `seed_id` table (`COHORT_SEEDS`; rows exist for the ten) so the gate arm runs `_identify_site` on the cohort too.
  `gated = through_identity_gate and case_id in (DEV2 ∪ COHORT)`.
- `--perturb-seeds <kind>` (only if the first run is inconclusive, owner-free): the registry seeds are kept but
  `program_catalog` is replaced by the homepage's first navigation link of the same host — a deliberately imperfect
  seed, to see what confirm does with a wrong lead. Record `config.entry_path = "perturbed"`.
- The stage summary and scorecard read `entry_path` from `config` and print it in the arm header.

## Runs (main session dispatches; worker reads artifacts)

1. cohort, `expert_paired`, `extra_args=--no-registry-seeds` (off = registry, on = no-seed), parallelism 5.
2. cohort, `extra_args=--through-identity-gate` (off = registry, on = gate path).
3. only if 1 is inconclusive: `extra_args=--perturb-seeds nav`.

## Read

Per arm: `discovery_queries` total and by family, `seeds`, `sitemaps_read` / `sitemap_urls_seen` / `kept`,
`reads_by_kind:sitemap`, `identity_recovery_leads_confirmed`, `confirmed_pages_{hit,related,wrong}`,
`gold_returned_by_search` / `gold_read` / `gold_confirmed`, `page_outcome:*`; scorecard: programme page
hit/wrong/related/missed, readable core, precision, reads per case. **H-B confirmed** if the registry arm sends fewer
families, reads more sitemap URLs, confirms more wrong pages or reaches the gold less than the no-seed arm on the
same ten sites (≥ 2 cases moving in the same direction, both repetitions); **refuted** if the three arms agree
within repetition noise (ticket 04 of the finish map: ≈ 1 flip per set per cycle).

## Files the worker holds

`backend/evaluation/research/live.py` (`capture_one`'s path selection, `seed_entry`, a `cohort_entry`, the two flags;
lands *after* 02's id tables), `backend/scripts/canary_discovery.py` (only if `run_canary` needs a `seeds=` override),
`backend/evaluation/research/stage_summary.py` / `scorecard.py` (the `entry_path` header line only — ticket 07 edits
the same two files for its own header; land in order 06 → 07), `backend/tests/test_research_benchmark.py`.

## Evidence

- `live.py` L1040–1053 (the three-way path selection), L226–248 (`seed_entry`); `canary_discovery.py` L395–430
  (`run_canary`, `_install_identified_sites`); `institution_registry.json` field set (`seeds`, `seeds_verified_on`);
  `HELDOUT_STAGE_SUMMARY_2026-10-19.md` rows `seeds`, `discovery_queries:*`, `sitemap_urls_seen`,
  `confirmed_pages_wrong`; `STAGE_SUMMARY_DEV_2026-10-19.md` cohort section (`seeds 36`, six families).

## Done when

The two (or three) runs are scored, the per-arm table is in `LOOP_REPORT` and the Answer with the H-B verdict; if
confirmed, the Answer names the product change for the owner's Q5 (seeds as extra leads: flag proposal
`REGISTRY_SEEDS_AS_LEADS`, `--registry-seeds-as-leads`, loop id **RS-1**) and the file it would touch
(`live_discovery.py` seed intake). Harness flags here carry no product behaviour. Loop id: **G-06**.

## Answer

Claimed and built 2026-10-19 by a worker. The harness part is finished. **The H-B verdict is not given yet:**
no paired run has been dispatched (worker rule). The main session dispatches the two runs below, scores them and
appends the per-arm table and the verdict here and in `LOOP_REPORT`.

### What was built (measurement only, no product behaviour)

| arm | flag | what the cohort case runs | `config.entry_path` |
|---|---|---|---|
| registry (today) | none | `run_canary(CASE_DOMAINS[case], False)`: registry selector, curated seeds, slots pre-filled | absent, shown as `default` |
| no-seed | `--no-registry-seeds` | `run_canary(None, False, entries=[cohort_entry(case)], drop_registry_entry=True)`: the registry row's name, country, city and homepage **without** `seeds`, `seeds_verified_on` or `campuses`, installed as an established site, the dev2 shape | `no_seed` |
| identity gate | `--through-identity-gate` (now also cohort) | `run_canary(None, False, entries=[seed_entry(case)], through_identity_gate=True, drop_registry_entry=True)`: the curated entry and curated domain are dropped, the row keeps the seed record's domain (`seed`, or `unknown` for vienna, ntu, kaist, whose seed rows have none), and production's `_identify_site` decides | `identity_gate` |

- `live.py`: `COHORT_SEEDS` (case → top-500 `seed_id`, with the same identity key as the registry row for all ten),
  `cohort_entry`, `seed_entry` reading `COHORT_SEEDS` for a cohort case, `GATED_CASES = DEV2 ∪ COHORT`. The
  `capture_one(no_registry_seeds=…)` path selection, then the flag, forwarded to the child and recorded in `config`.
  `--no-registry-seeds` refuses `--through-identity-gate` and any `--case` outside the cohort.
- `canary_discovery.py`: `drop_registry_entry=` on `run_canary` / `_install_identified_sites`. The registry entry
  that `import_catalogue` attached is forgotten in the throwaway canary DB only.
- `scorecard.py` (full and summary render) and `stage_summary.py`: an `entry path` row or line in the arm header,
  shown only when an arm left the default path. Ticket 07 adds its own header line next to it.
- `--perturb-seeds nav` was **not built**. The ticket makes it conditional on run 1 being inconclusive. Build it
  only then.
- Tests: `backend/tests/test_benchmark_entry_paths.py` (15), `test_benchmark_identity_gate.py`: the old
  "registry case has no gate" test now uses a dev4 case, because the cohort is gated.

**The no-seed arm still has some registry knowledge.** It is not quite dev2's path. Three readers still look up the
registry file by domain whatever the entry says, so the no-seed arm keeps:
- `live_discovery._registry_hosts_by_domain` / `is_seed_host`: the seed-host allowlist, e.g. Toronto's `future.utoronto.ca`;
- `registry_campuses`: the campus hosts;
- `registry_identities`: identities and aliases for entity resolution.

A difference between the arms is therefore a lower bound on the path effect. Read it that way. If H-B comes out
refuted, a third, stricter arm would have to blank those three as well before "the path does not matter" is
claimed.

### Dispatch inputs (main session)

Both runs: `benchmark-capture.yml`, `mode=expert_paired`,
`case=groningen delft aalto vienna warsaw ubc toronto hku ntu kaist` (space-separated ids), `base_args` empty,
`seconds_per_case=120`, `max_pages=60`, `case_parallelism=5`, `runner=ubuntu-latest`, `search_provider=auto`.

| run | `extra_args` | off arm | on arm | `run_tag` |
|---|---|---|---|---|
| 1 | `--no-registry-seeds` | registry | no-seed | `g06-no-seed` |
| 2 | `--through-identity-gate` | registry | identity gate (scorecard adds `identity established n/10`) | `g06-gate` |
| 3 (only if 1 is inconclusive) | `--perturb-seeds nav` (build first) | registry | perturbed | `g06-perturbed` |

### How to read the runs

1. Run `stage_summary.py <artifact> --dataset <cohort corpus>` and `scorecard.py` on each artifact.
2. Check that the arm header shows `entry path | default | no_seed` (run 1) or `default | identity_gate` (run 2).
3. Read the ticket's §Read rows per arm.
4. Apply the bar as written: **confirmed** if, on the same ten sites, the registry arm does one of these, with ≥ 2
   cases moving in the same direction in both repetitions:
   - it sends fewer families;
   - it reads more sitemap URLs;
   - it confirms more wrong pages;
   - it reaches the gold less often.

   **Refuted** if the arms agree within ≈ 1 flip per set.
5. If H-B is confirmed: propose `REGISTRY_SEEDS_AS_LEADS` / `--registry-seeds-as-leads`, loop id **RS-1**, in the
   seed intake of `live_discovery.py`, for the owner's Q5.

### Also landed with this ticket (for ticket 13's re-measure)

Every default-on rule now has a `--no-<flag>` form in `live.py` (`NEGATABLE_RULES`). The form:
- sets the module constant False in the child;
- is forwarded by the parent;
- refuses its on-form;
- is recorded as `config.rules_off`.

The forms are the fifteen seen-site rules in the ledger's order, every other default-on rule with an on-form, and
`--no-integrated-masters-level` (IM-1, which has no on-form).
