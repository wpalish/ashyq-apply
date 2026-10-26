# Record provider results and persist the trace at checkpoints

Type: task
Status: resolved
Blocked by: —
Map: ../map.md · AFK task — measurement only; it unblocks the query-language decision and makes killed captures readable.

## Question

Nothing to decide: [Measurement gaps that hide discovery outcomes](14-measurement-gaps.md) lists what the
trace and the scorer do not record, and [Approve a Serper probe budget](07-serper-probe-and-query-language.md)
cannot be answered from evidence until the provider's result lists are kept. Scope of the work (harness and
trace only; no discovery rule changes; the paired-run protocol still applies because the trace feeds the
scorecard):

1. `DiscoveryTrace.search_results`: per institution, per query family, the top-10 URLs the provider returned
   (public URLs only; no query text, consistent with `QueryAuditRecord`).
2. Persist `DiscoveryTrace` and `programme_urls` at the confirm checkpoint in `live.py`, so a child killed at
   115 s still reports what discovery confirmed and when.
3. `programme_url_aliases` on the candidate: declared hreflang twins of every confirmed page, both directions.
4. Scorecard: "gold seen at stage" per case (sitemap / link text / search result / read / confirmed), from the
   trace, so "never seen" is split into "not returned", "returned not read", "seen as link, dropped".
5. Tests: trace shape, checkpoint persistence under a simulated kill, redaction (no query text, no applicant
   word in the recorded URLs list).

## Answer

Landed 2026-10-18 by claude-opus-5: `4c6d9e8` (code + tests), the confirm checkpoint itself in `1184f66`
(earlier). No flag: every addition is recording; no discovery rule, read or query changed, the golden demo
(`TestDemoRunIsByteIdentical`) and the frozen replays (`test_research_benchmark.py`) pass unchanged.
No capture carries the new fields yet; the first paired run after this commit is the first.

1. **Provider result lists.** `RetrievalReport.results_by_family` → `DiscoveryTrace.search_results`: one
   row per query sent, `{"family", "urls"}`, top 10 in rank order, http(s) only, fragment and credentials
   dropped, **no query text** (consistent with `QueryAuditRecord`; the scope note asking for the text was
   overruled by this ticket). Capped at 24 rows. Recorded at all three discovery call sites (one-pass,
   QB-1 two passes, multi-field).
2. **Checkpoint.** Already in `1184f66` (`<case>.trace.json` at confirm/walker/timeout; removed on a
   completed run). Extended: the checkpoint and timeout paths now also write
   `Observation.programme_url_aliases`, and the trace carries the new fields, so a killed case keeps its
   result lists.
3. **Twins.** `declared_alternates()` (every `hreflang` other than `x-default`, same registrable domain,
   any page language) is noted for every page read by confirm, confirm-added and identity recovery
   (`DiscoveryTrace.note_read`, which also records `pages_read` with the verdict) and for every page the
   walker confirms (`CatalogWalk.alternates`). `DiscoveryTrace.programme_url_aliases` holds both
   directions. **Deviation:** the aliases live on the trace and on the benchmark `Observation`, not on the
   product `Candidate`, so no product payload moves a byte.
4. **Scorer.** `metrics.returned_matching_gold`: a returned page counts when it or a recorded twin is in
   the gold (recall and precision numerator); precision's denominator is unchanged. This applies ticket 03
   Q1's *recommended* answer; ticket 03 is still open, and if the owner answers no, this is the one rule to
   revert. **No published number moved** (no frozen capture records twins).
5. **Scorecard.** `scorecard.gold_seen` per case and repetition (`rep["gold_seen"]`), and a "gold seen"
   column in the per-case table once a case carries a trace: `confirmed` (scored hit, twin included) /
   `rejected` (refused when read, or dropped unread — the reason is kept) / `read` / `listed` (selected,
   link text, walker candidate, unresolved) / `returned` (only in a provider list) / `never`, plus
   `seen_as` with every way it was seen. Read from `.raw.json`, else the checkpoint `.trace.json`.
   Limits: unread rejections come from `rejected_sample` (first 40 of at most 200); walker reads appear as
   `walker:<outcome>` tags.
6. **Tests.** `backend/tests/test_benchmark_provider_results.py` (15): result-list shape, rank order and
   redaction (no query text, no `site:`, no credentials, no applicant attribute), bounds, empty trace
   serialises as before, twins both directions and from the walker, aliases persisted under a simulated
   kill at 0.3 s, twin scoring (and no borrowed hit), every gold-seen stage, raw vs checkpoint trace,
   unchanged table shape without traces.
