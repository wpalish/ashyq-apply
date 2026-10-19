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
