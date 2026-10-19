# H-B: registry-seed path vs no-seed path vs identity-gate path — the cohort through three arms

Type: task
Status: open
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
