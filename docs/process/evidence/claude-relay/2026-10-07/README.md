# Claude relay evidence, 7 October 2026

## Original evidence and method

The two `.tgz` files preserve the downloaded GitHub artifacts in their original layout. No original capture, corpus or binding was changed. `*-audit.json` gives each capture's SHA256, source commit, programme URLs, error, core answers and exact cost counters. Run metadata is saved separately. This is an offline audit of old runs, not a new search score.

## Production access recheck

Unchanged deployed Fetcher, worker machine `8dd627ae93e508`, Amsterdam, original image `deployment-01M49AMVGCRD8P1YRQKRFQYE28`. Command: `cd /app/backend && PYTHONPATH=/app/backend python scripts/probe_access.py --case aalto --case ntu`.

NTU: all three public pages return HTTP 200 (general requirements, BComp Computer Science, Nanyang Scholarship). Aalto: all three refused because robots.txt ReadTimeout; the whole site is conservatively disallowed. No robots bypass, cache, provider call or deployment. Owner independently verified NTU DNS; these results additionally prove page reads at this time. HKU was not rechecked.

## Heldout audit (run 37554279823)

The GitHub job is cancelled. Artifact has **35 of 36 planned captures**. Missing: second **NU-off**, not Masaryk. There are no `CAPTURE_IN_PROGRESS` rows in the downloaded captures; 14 rows are finalized `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED` outcomes.

Four Masaryk captures exceed 120 s by 3.54–6.45 ms. The old scorecard rounds all four to 120.0 and passes them. New scorecard preserves and compares exact telemetry. No budget tolerance was introduced.

The observed aggregate is 5/210, not a completed 5/216. Do not use the absent row as a measured zero. Separately, both on repetitions are complete nine-case samples: **1/54 each (1.85%)**. RL-1 cohort on repetitions are **12/60 each (20%)**; like-arm worst-repetition gap is **18.15 percentage points**, beyond the existing 15-point limit. The coverage failure remains supported by those saved complete on samples, while the full ABBA experiment remains incomplete. Core coverage counts the presence of answers, not their correctness; no signed heldout claim-accuracy score is claimed.

## RL-1 audit (run 37545452839)

All 40 captures exist. New scorecard confirms two stable gains (Delft IELTS overall, UBC deadline), zero stable losses and zero unassessed cases. Both arms have precision 1.0 on the original adjudicated sample, wrong-scope 0 and no exact budget overrun. On core 12/60 twice; off 10/60 twice. One Groningen off row has a finalized budget stop but remains a measured outcome. No new live searches were used to reach this conclusion.

## Groningen proposal

`groningen-g1-proposed.json` is unsigned and changes no gold. Browser table column ancestry confirms BSc Computing Science is in Admissions Level 1, MSc in Level 2. New proposed IELTS value is 6.0 overall and 6.0 in every component for fall 2027 / 2027/28. Official page is archived through unchanged Fetcher, and its current modification date is 7 October 2026, 12:22 p.m. Owner confirmation is pending; preserve reviewed9 and historic scores.

## Next development set

`development-cohort-prepared.json`: Dalian, Nagoya, Witwatersrand, AUT, Caltech, all from frozen DEV, distinct countries, outside both heldout groups. These are seed identity hints only. **Prepared, not run.** Current evaluation CLI selects only the curated 19: opt-in seed-case support is the next step, not a completed feature. Provider failure must stop the whole new batch; do not inherit the paired shell loop's continued dispatch after refusal.
