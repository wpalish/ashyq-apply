# Independent native OFF explicit-rate-limit proof review

Verdict: CONFIRMED TWO NATIVE STOP-CONDITION DEFECTS; proof only, no source/design acceptance. A manifest4da306202513a298c28fd6b188c634cf9a1f283286964b755d84289ecd28db91 and receipt1906daa095e0bc18e23fec9c5cf99c3e63d746584d0ccedffe9b58023127a217 match.49 selected files/338,279bytes copied unchanged before analysis;8 current source hashes match. This is exact selected dependency proof, not a fresh full repository gate or Git/source-head verification.

Actual normal factory get_search_provider -> _ThrottleLatch -> ExaMcpSearchProvider.search/_search_once/_post/_initialize and native discover_candidates are unmodified. HTTPX constructor supplies MockTransport; actual parser consumes synthetic JSON-RPC initialize/notification/tools HTTP replies. DNS resolver is synthetic and socket connections forbidden. No provider search method replaced; original file/method identities and client closure checked. Each scenario is a fresh subprocess with empty process latch and query pacer state; reset_search_throttle never called and no persisted STOP touched.

B copied the corrected filesystem-only replay seam and repeated five bounded scenarios, not all75 author assertions. Own28 assertions:16PASS/12RED, all case statuses equal preserved author rows. These12 RED are repeated proofs of two seams, not12 distinct bugs.

| Scenario | Query attempts | Mock initialize/notification/tool dispatches | Latch |
|---|---:|---|---|
| Factory meta native retryTrue, first/repeat/other-before-refusal-created instance |3|2/2/6|empty|
| Factory meta isolated retryFalse |3|2/2/3|empty|
| Retrieval meta native retryTrue |6families|1/1/12|empty|
| Retrieval meta isolated retryFalse |6families|1/1/6|empty|
| Factory new instance created after escaped meta-refusal, native retryTrue |2|2/2/4|empty|

Native RATE_LIMIT_RETRY=True remains source-default and restored even in the isolatedFalse control. It makes two _search_once tools before each search exception escapes (first cold search includes initialize+notification). The post-refusal-created adapter proves this is not merely an object-created-before-refusal effect: first search4 MockHTTP, new later instance sends4 more. Future outer latch repair must stop later query families/adapters AFTER that escaped explicit refusal. It does not by itself stop the first internal retry after first vendor response; this proof never asserts global first-response stopping.

Every meta tool returns HTTP200 with exact boolean _meta.ai.exa/rateLimited=True and valid structured rows. Native client correctly declines those rows and raises SearchUnavailable(reason=SearchFailureReason.RATE_LIMITED,http_status=None). This None is real native metadata, not missing HTTP429. Factory currently only stores suppression on http_status429, and suppressed local errors are always synthetic429. Retrieval only breaks its query loop on429. Therefore typed reasonNone-status refusal bypasses both; actual retrieval reports6 failed families, fixed rate-limited diagnostic without HTTP429 and throttled=False. Search seam attempts are not tool/HTTP dispatch counts; all dispatches here are mocks, not vendor/network calls.

Read-only comparator inspection: HTTP429 factory suppresses same/other/new-after-refusal instance before any further initialize/notification/tools; retrieval breaks after1family. Ordinary success/transport/ReadTimeout and corrected exact metaFalse have no quota latch or added native retry. Their verified raw source pre/post hashes match, clients close. B did not repeat these already unambiguous comparators, and does not call that independent re-execution. Original benign fixture selector error remains4PASS/1RED; corrected fresh metaFalse is separately5PASS. All14 raw scenarios75=62PASS/13RED; excluding only five malformed-fixture assertions yields qualified70=58PASS/12RED, exactly reported. No original expectations or red outputs changed.

Current native diagnostic is honest rate-limited/statusNone, but no family stop. Future proposal must preserve typed original metadata for local repeats/new instances, avoid stale-origin/legacy-float fallback inventing429 for current meta, and make caller throttle texts appropriate to both explicit causes. Ordinary transport/timeouts remain unchanged. Existing approved client retry flags are outside that source task and strict capture first-refusal/STOP remains a separate authoritative boundary. Design and mutable proposal are NOT approved by this review; exact sealed proposal required for new peer controls, including cooldown/expiry/provenance.

No source application, flag/default edits, app/Git/STOP/reset/scoring/gold/labels/model/live/network calls. Only own external mock files created; all processes and mock clients close; source8 hashes unchanged. No quota availability, university fact, quality/recall gain, production wall-clock or launch readiness conclusion follows.
