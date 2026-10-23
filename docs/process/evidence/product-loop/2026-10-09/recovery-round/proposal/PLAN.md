# Product research recovery: external proposal

2026-10-09. Parent owns primary repository, HANDOFF, Git and native gates. Base source hashes are in base-source-pins.json; AGENTS and current HANDOFF §1/§2/§5 were read. Historic full HANDOFF output was truncated and is not claimed as a complete history audit.

Scope: two existing UI files plus their two existing test files. ShortlistScreen reads native run state using the existing Home/Docs attention and active predicates. A run with no returned results directs the user to existing Progress; no run preserves Start research. A nonempty active/attention run adds an informational notice without replacing rows or resetting local state. Callback is optional and is called only on explicit button click. Notice uses total returned results, not filtered rows. No new retry, research, collection, choice, notes, filter reset or absence claim.

ResultDetail Documents hint names programmes chosen or considered in Plan, consistent with native approved/maybe collection. Real checklist display remains unchanged.

Tests append bounded actual-component cases to existing controls: native stop/active/empty states, optional callback, healthy completed or locally filtered-empty state, partial row/filter/compare/note continuity and no research mutations; Documents hint for saved choices and retained checklist. Existing test bodies remain unchanged. Test mocks may add run and result overrides.

Validation: owned frontend copy with installed dependency package symlinks, own cache/logs, denied transport/listen/DNS. Run new controls on base screens for honest RED; same focused files on proposed screens, TypeScript and selected ESLint. No primary execution, backend imports, SQL, ports, network, provider, model, labels, score, new full or seed. Preserve all errors and commands. Parent/A must review exact immutable bytes before application; native full/browser/reload/production remain NOT_RUN by B.
