# Measurement gaps that hide discovery outcomes

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5 from the harness, scorer and captures.

## Question

Which facts about programme-page discovery does the benchmark *not* record or *mis-score* today, so that a
design decision would be made blind or a correct page would be scored as a miss?

## Answer

| gap | where | consequence | fix shape (for the loop; a task, not a decision) |
|---|---|---|---|
| **Provider result lists are not recorded** | `retrieval.discover_candidates` returns ranked candidates; the trace keeps only `rejected_sample` (capped at 40, mostly sitemap rejections), `rejection_counts` and the URLs identity recovery *read* | "gold never seen" cannot be split into "not returned" and "returned at rank > 8"; the query-language decision has no evidence | record the top-10 URLs per query family per institution (public URLs only, consistent with `QueryAuditRecord`'s redaction — no query text) |
| **A killed capture writes no trace** | `live.py`: the child's `.raw.json` is written after discovery; `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED` at 115 s leaves `programme_urls = []`, `access = unknown (0/0 failed)` | ubc and imperial had confirmed a page and score 0 (`bundle5-cohort/x/ubc-on`, `bundle5-dev3/x/imperial-on`: `.json` only, no `.raw.json`) | persist `DiscoveryTrace` and `programme_urls` at the confirm checkpoint (STRUCTURAL §4.2) |
| **Twins and variants score as misses** | `metrics.canonical_url` keeps scheme/host/path (trailing slash stripped) and the query; `programme_page_recall` is `bool(expected & returned)` (L304–308) | a declared English twin (ucph before relabelling, psaclay today), `/2027/computing-beng`, `?lang=en` vs none (groningen listed both by hand) are misses unless the gold lists every form | discovery records `programme_url_aliases` (declared hreflang twins) and the scorer accepts a hit on any alias; the identity rule of [What counts as the programme page found](03-programme-identity-equivalence.md) decides what else |
| **No "related programme" outcome** | the scorer has hit / miss and a precision denominator (`programme_page_precision` over cases whose status is not unknown) | a sibling specialisation or a CS-major page counts as a wrong page in precision | a third outcome once ticket 03 is answered |
| **Stage seconds end at discovery** | `stage_budget.stage_seconds` covers sitemap/navigation/walker/confirm/search/recovery; `telemetry.stage_seconds` is `None` in the bundle5 `.json` | the evidence stages' share of the clock on killed cases is read from the `.log` by hand | harness-side per-stage seconds including verify/costs/scholarships (STRUCTURAL §4.1) |
| **The identity gate is not measured** | `live.dev2_entry` bypasses `_identify_site` | see [Production site-identity gate on development homepages](12-identity-gate-offline.md) | a `--through-identity-gate` arm |
| **Link-text leads are invisible in the scorecard** | `trace.kept_by_link_text` and `walker.candidates` (capped at 200) exist in `.raw.json` but no scorecard line reports "gold URL seen as a link, dropped as `short_label`" | the KAIST-type loss (gold seen, never read) looks like "never seen" | a scorecard column "gold seen at stage" from the trace — `scratchpad/funnel_tools/funnel.py` is the prototype |

None of these needs an owner decision except the identity rule (ticket 03); they are the content of
[Record provider results and persist the trace at checkpoints](17-record-provider-results.md), which must
land before the query-language probes are read.

### Sources

- `backend/evaluation/research/metrics.py` L19–25, L283–312; `backend/evaluation/research/live.py` L150–165,
  L1457–1463, L1600–1660; `backend/evaluation/research/scorecard.py` L36–60.
- `backend/app/adapters/discovery/live_discovery.py` L1700–1800 (`DiscoveryTrace`), L1918–2047 (`StageBudget`).
- Captures: `scratchpad/runs/bundle5-*/x/{ubc,imperial}-on/*/` (no `.raw.json`), `bundle5-dev2/x/tcd-on/*/tcd.json` (`telemetry.stage_seconds: null`).
