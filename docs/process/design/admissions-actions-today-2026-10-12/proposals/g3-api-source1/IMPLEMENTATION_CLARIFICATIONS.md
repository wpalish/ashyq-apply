# Immutable wire1 implementation clarification

This note records parent source-authoring instructions; it does not mutate the copied wire/design/native contracts.

- SOURCE-BOUND legacy mark import matches the exact current own task binding and a fresh currently authorized canonical source-preview token for that binding's exact raw occurrences. The old accepted binding digest alone is insufficient. Missing/changed token -> fixed legacy_import_changed; locked new source -> fixed source_locked. Source version remains unknown; unbound personal import/manual reports remain free. Accepted UUID replay precedes mutable current/source/access/plan reads.
- Full export validates all typed row bodies/headers and complete history, then performs a final observed scalar G3 head equality after loading the full event list. No retries, new Session, locks, source joins or reallocation.
- Current/import-preview output revision max2147483647; command expected_revision retains max2147483646.
- Copied typed DB timestamp headers normalize with native ensure_utc(...).astimezone(UTC). Saved JSON/hashes/local dates/native ensure_utc remain unchanged.
- Native term access is observed after its real SELECT and bounded again to terminal Today time without another term query/grant. Research grants do not imply preparation permission.
- Current source metadata is owned and selected before evidence-count metadata; locked roles do not read claims/conflicts/payloads. Changed/revoked roles clear new current digests/links instead of transferring stale authority.
- submission_declarations exports typed accepted submission deltas, including explicit replacement-submission declarations. Planning corrections/withdrawals remain events and do not rewrite the original declaration. The current submission+planning correction test asserts one original declaration; replacement-submission filtering is not claimed as tested.
