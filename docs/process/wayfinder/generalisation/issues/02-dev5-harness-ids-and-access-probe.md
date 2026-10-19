# dev5 in the harness: case ids, domains, runner-side access probe, CI wiring

Type: task
Status: open
Blocked by: —
Map: ../map.md · AFK — one worker; measurement code only, no discovery or product change.

## Goal

Make the thirteen dev5 candidates capturable and scorable exactly like dev4, through the **no-seed path**, before
their labels exist: `kbtu satbayev aitu hacettepe bilkent ytu upol zcu tud lmu unipd sapienza vilniustech`. Drop
any host the GitHub runner cannot read (robots unreachable, 403, challenge, TLS refusal) — an unreadable proxy
teaches nothing — and record the probe.

## Steps

1. **Leakage check first** (ticket 04 of the programme-discovery map, Q4): for each candidate, the official
   registrable domain and the parent institution; none may equal or be a subdomain of a heldout domain. Record
   the table in the ticket's Answer (candidate, domain, parent, verdict). `vilniustech.lt` is Vilnius Gediminas
   Technical University — a different institution from Vilnius University; `uni-muenchen.de` / `tu-dresden.de`
   are not TUM. Do this from public knowledge and the top-500 seed (`backend/app/catalogue/unimatch_top500_seed.json`:
   KZ 3, TR 6, CZ 3, DE 27, IT 15, LT 1 rows) — **never from a heldout file or registry row**.
2. **Runner-side access probe**: a `probe_access` step is not a workflow mode today. Add `mode=probe_access` to
   `.github/workflows/benchmark-capture.yml` (one job: `scripts/probe_access.py --urls <file>` with the production
   `Fetcher`, robots honoured, no retries), with the thirteen homepages, robots.txt and one catalogue page each in
   `backend/scripts/probe_access_urls.txt` (dev5 section). The main session dispatches it; the worker reads the
   artifact. kbtu and satbayev refused TLS to the agent's container on 2026-10-18 (`SIGN_DEV4_2026-10-18.md`: the
   server sends only its leaf certificate); if the runner sees the same, they are `unavailable` by definition and
   leave dev5 — no bypass, no CA tweak.
3. **Harness ids** in `backend/evaluation/research/live.py`, mirroring dev4: `DEV5_DOMAINS` (case → official
   domain), `DEV5_SEEDS` (case → `seed_id` of the top-500 row where one exists), `DEV5_OFF_SEED` (name, country,
   city for rows outside the seed), `DEV5_HOSTS` (homepage host when not `www.`), `CASE_DOMAINS` and
   `NO_REGISTRY_CASES` extended, `--case` choices extended, `dev2_entry` / `with_off_seed_rows` covering dev5;
   `DEV5_IDS` for the scorecard's set labels if `DEV3_IDS` has a counterpart. Update `backend/tests/test_research_benchmark.py`
   (case lists), and the LOOP_PROTOCOL case table (`docs/process/LOOP_PROTOCOL.md`: add a `dev5` row).
4. **Evidence check domains**: `backend/scripts/verify_evidence.py` `OFFICIAL_DOMAINS` gets the thirteen (or the
   survivors), one line each.
5. **Bindings**: an empty `identity_bindings.dev5-draft1.json` (`version: 2026-10-19.dev5-draft1`, `bindings: []`)
   and the workflow's `MEASUREMENT_BINDINGS` line for it — so that award claims on dev5 can land once 04 binds them.
6. **Workflow case help text**: add dev5 to the `case` input description.

## Files the worker holds

`backend/evaluation/research/live.py` (the id tables and `dev2_entry` only), `backend/scripts/probe_access.py`,
`backend/scripts/probe_access_urls.txt`, `backend/scripts/verify_evidence.py` (`OFFICIAL_DOMAINS` only),
`.github/workflows/benchmark-capture.yml` (the `case` description, `MEASUREMENT_BINDINGS`, the new
`probe_access` job), `backend/evaluation/research/data/identity_bindings.dev5-draft1.json`,
`backend/tests/test_research_benchmark.py`, `docs/process/LOOP_PROTOCOL.md` (case table row). Nothing under
`app/`. Ticket 06 also edits `live.py` (`capture_one`, `seed_entry`): 02 lands first; 06 rebases on it.

## Evidence

- `live.py` L146–215 (`DEV4_*`, `dev2_entry`, `with_off_seed_rows`); programme-discovery ticket 15 step 6 (how dev4
  entered the harness); `SIGN_DEV4_2026-10-18.md` «Отброшены (проба доступа)».
- `scripts/probe_access.py` docstring (production `Fetcher`, no cache, no proxy).

## Done when

Gates green; `python -m evaluation.research.live --help` lists the dev5 ids; the probe artifact is read and the
survivors table is in the Answer; `test_research_benchmark.py` pins the dev5 list and that no dev5 id is a heldout
id or domain. Flag: none (measurement). Loop id: **G-02**.

## Harness defect 2026-10-19

Symptom (run 39203214600, aggregates only): `discovery_queries = 0`, `identity_recovery_leads_checked = 0`,
`seeds = 0` in all four columns, with `search_calls_total = 65` (5 per case), `sitemaps_read = 37`,
`programme_candidates_read = 10` and about 28 s per case. dev4 on the same path sends about 4 discovery
queries per case at about 60 s.

**Root cause: not in the harness's dev5 wiring, and not reproduced offline.** No dev5 capture, log or row
was opened. The comparison was made from code and synthetic runs:

- `dev2_entry`, `with_off_seed_rows`, `canary._install_identified_sites`, `NO_REGISTRY_CASES`,
  `GATED_CASES` and the `capture_one` branch treat every dev4 and dev5 id the same way. All 22 proxy
  entries install as an established `site_identity_checked` row with the right registrable domain. The
  seven off-seed dev5 rows get their catalogue row, as dev4's three do.
- Nothing else in `live.py`, `canary_discovery.py`, the workflow's `expert_paired` step, the search
  seam or discovery is keyed by case id or by set membership. The profile is the canary's fixed one,
  the query budget is per institution, and the stage budget does not depend on the domain.
- The real child path (`capture_one`, then the canary, the runner and discovery), run offline with a
  mocked provider and synthetic pages, sends the same six discovery queries, from the same families and
  in the same stage order, for `rwth`, `lmu`, `upol`, `kbtu`, `tud` and `sapienza`. That holds both when
  every read fails and when every read answers. Each query is restricted to the case's own domain, and
  each lands in `trace.search_results`, the rows the stage summary counts.

`tests/test_dev5_discovery_search.py` now pins this: a dev5 case (`lmu` on-seed, `kbtu` off-seed with
a bare host) and the dev4 case `rwth` reach discovery search with the same families. **It passes on
the current code, so it does not fail first**, because no harness defect was found to fix. It guards
the path from now on.

The open explanation is live-only, and it is consistent with every aggregate. `scorecard._trace` reads
the trace from `*.raw.json`. When a repetition has no raw report, it falls back to `*.trace.json`, the
checkpoint `capture_one` writes at the confirm and walker stages. That checkpoint is written *before*
the post-walker search stage, and it is deleted only once the raw report is written. So a child that
stops after the walker but before `.raw.json` is written leaves a trace that has sitemaps and
candidate reads but no `search_results` rows. Meanwhile the observation's `search_calls` (counted by
the harness's provider wrapper) still records the queries that were sent. To test this without
breaking blindness, count `*.raw.json` files against `capture.json` files per repetition in the run
artefact (a file count, not a content read). Also read `cases_with_trace` and the scorecard's error
counts from `--summary-only`. A second live-only candidate: every discovery query failed at the provider
(a `SearchUnavailable` records no row). The aggregate `search_failures` is not in the stage summary, so
the main session should decide whether to add it as an aggregate row before the next dev5 run. No fix
was made to the harness or to product code.
