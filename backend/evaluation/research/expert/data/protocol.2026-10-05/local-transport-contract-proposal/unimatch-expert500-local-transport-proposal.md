# Prospective local transport: established findings

**Status:** source-only auxiliary audit, outside the expert pilot. No runtime implementation, model/provider/source calls, credential reads, label reads or capture replay. V13 helpers, clocks, captures and results remain unchanged. Persistent per-case workers are the **root engineer’s prospective choice**, not an owner instruction. Dependent live work remains paused pending the same-owned Exa credential.

## Fixed method

Retain the same ten public cases, explicit reviewed-62 denominator/40 threshold, Exa identity, algorithm 60 reads/6 searches/120 seconds with its existing reserve, and expert 60 reads/6 searches with an immutable 900-second total guard. Astra uses normal configured/default reasoning effort. Model thinking remains outside source counters but inside that absolute guard. Preserve public requests, isolation mappings, journal/citation gates, shared STOP, original raw records and seal-before-labels. No batching, extra source admission, account/provider substitution or old capture reuse follows from this proposal.

## Minimum changes required before a future trial

1. **Source lifetime:** a distinct persistent case worker can retain the stock Fetcher/provider and call the stock controller executor for each accepted expert action. Strict reads must remain cold; workers/cache state must be separate across cases and algorithm/expert arms. Current `controller.run` constructs and closes Fetcher per invocation (`controller.py:994`). Performance and persistent-worker parity have not been tested.
2. **STOP admission:** parent checks before starting a process do not prove refusal at every tool boundary. Current controller executor has no cross-process STOP hook (`controller.py:470,714–802`). A prospective opt-in admission gate must precede execution/counter increments for both search and fetch, including baseline adapters (`live.py:125–132`). Persist the originating provider/integrity cause before publishing shared STOP; preserve and account for already admitted tails. A case wall guard must not be relabelled a provider failure. Unknown counters or missing originals remain ineligible.
3. **Local provenance:** introduce an explicit local transport receipt variant. Bind unique local session/action IDs, actual process argv, sanitized public environment, canonical workspace, interpreter/dependency/import origins, frozen source identity, plan/resume hashes, process lifecycle and complete original plan/summary/raw files. Do not fabricate GH run IDs, tags, headSha or conclusions. Frozen parent `workflow` and report `verified_controller_completion` currently validate GH identities. Their local variants must retain counter recomputation, accepted-prefix versus spent-tail checks, deadline rules and every raw hash. Freeze/export must include the actual new receipts and executed helpers.
4. **Secret separation:** `network_turn_policy.select` inherits its parent environment (`:325–333`); file isolation does not sanitize it. Settings can load `.env` (`app/config.py:20`), and stock live transport copies the environment (`live.py:873–882`). Keep the Exa key exclusively in the source worker/broker; use a secret-free orchestration/model environment and clean frozen source CWD. Explicitly control proxy/certificate/import variables and temporary data paths. Public receipts must not contain secret values or secret-derived hashes.

## Required proof still absent

Synthetic gates must establish per-tool concurrent STOP, unchanged 60/6 and clock/resume accounting, raw-tail completeness, process termination at the guard, environment/key isolation, import/source identity, tamper refusal and seal-before-labels. A fresh source-free neutral proof and actual ten-workspace isolation proof must bind the future runtime. No local authenticated source behavior, throughput, 900-second feasibility or 40-of-62 outcome is established. Globally serialized short-lived workers with a conservative delay are only an alternative; they do not prove persistent Fetcher state parity.

## Original source references

Repository base: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend`.

- `/tmp/unimatch-expert500-journal-pilot-v13-coherent.py`: SHA256 `c62fb07ec5e8fcf409672136709842867272b88e7194591a151bfe01ac52f395`.
- `/tmp/unimatch-expert500-journal-report-v13.py`: SHA256 `205d2e475dc45ace08a182adfb697f19be75e30ae0faa01b5b1a1368503cc703`.
- Independent source-only runtime audit: `/tmp/unimatch-expert500-local-runtime-audit.md`, SHA256 `23284a381316db7ee7cb328bb4d5729c9d6933bcc27b0e03b05f38fc5955a4ac`.
