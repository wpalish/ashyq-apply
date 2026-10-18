# Record provider results and persist the trace at checkpoints

Type: task
Status: open
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

(open — recorded when merged: commit, flags, the first capture that carries the new fields)
