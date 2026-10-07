# Local worker candidate: frozen offline delivery

Protocol: `journal-v14-local`. Transport: `local_process_v1`.

Candidate: `/tmp/unimatch-expert500-local-worker-v1-candidate.py`

Tests: `/tmp/test_unimatch_expert500_local_worker_v1_candidate.py`

Worker SHA256: `8fbede0eaa700e7268367000705f111846835ac368a8e46ef80e7f1ad735195d`

Test SHA256: `85f83f298fe2999ded4318836da15e0dad1aaa95d0ee8999579913194a240d34`

## Callable client

`SessionConfig` is a frozen dataclass. Its complete public mapping contains:

- `case_id`, `stage` (`expert` or `baseline`), full `source_sha`, `protocol_version`.
- Canonical `source_cwd`, public relative `source_manifest` (path to SHA256).
- Exact `interpreter` invocation, absolute `runtime_files` (path to SHA256), `runtime_import_roots`.
- Canonical private `session_root`, explicit `public_environment`.
- Canonical `admission_root`, immutable UUID `admission_run_id`, canonical `delivery_root`.
- `wall_guard`: expert's original UTC start/deadline plus integer `wall_guard_ms=900000`; baseline null.
- `baseline_identity_registry`: baseline-only `{path, sha256}` for the approved original producer input; expert null.

`SessionConfig.as_dict()` returns JSON-safe complete config; `from_dict()` strictly validates it.

`start_session(config, private_key=..., process_factory=..., clock=..., monotonic=..., kill_group=...)`
returns `LocalSession`:

- `execute(plan, destination, wall_guard=..., prior_delivery=None) -> LocalDelivery`
- `baseline(capture_request, destination) -> LocalDelivery`
- `close() -> dict`: bounded cleanup and original `session-final.json`.

`LocalDelivery` holds `receipt`, `receipt_path`, `receipt_sha256`, `summary`, `capture`, `source_counters`, `raw_logs`;
`.as_dict()` is JSON-safe. Counter keys are exactly `fetcher_calls`, `search_queries`, `elapsed_ms`.

Pure stored-byte validators:

- `validate_local_delivery(destination, expected_case_id=..., expected_stage=..., expected_source_sha=..., expected_wall_guard=None, prior_delivery=None) -> LocalDelivery`
- `validate_unavailable_delivery(...) -> LocalDelivery`, same keywords: original unknown terminal evidence only, always `source_counters=None`, known false, no facts/summary/capture.
- `validate_session_final(session_root, expected_session_id=..., expected_source_sha=..., expected_case_id=..., expected_stage=...) -> dict`

The unavailable validator never makes a tail primary eligible. It verifies original request/config/start/final/streams/partial hashes and actual preceding delivery. A 900-second ending requires the saved terminal clock to reach the same immutable deadline; an earlier timeout remains an integrity failure.

## Execution and original artifacts

One expert process owns one persistent stock Fetcher, provider and admission gate. Fetches are cold;
the same Fetcher's robots/pacing state and provider/controller latch survive between actions.
Each execute call permits one original action, exact 60/6/900000 policy and complete prior-summary
projection. Model waiting never contributes to the controller source ledger.

Worker argv: exact interpreter `-B -E -S -s` candidate `--worker session-bootstrap.json`.
The verified bootstrap installs only the frozen clean source and dependency import roots. Startup and
action receipts bind actual Python flags, interpreter invocation/target, PID/PGID, config, source/runtime
file device/inode/hash, module origins and bytecode origins, environment and algorithm defaults.

The baseline wrapper has the same Python flags and calls stock `live.main --child` with exactly:
60 pages, 120 seconds, strict mode, Exa, 1000 ms finalization reserve, original shared admission root/run.
It relocates only stock `live.REVIEWED_BINDINGS` to the approved baseline-only pointer. It preserves
original observation/budget/stdout/stderr, actual wrapper argv and stock argv, child-runtime/default/input
proof, child import proof, actual child PGID, process result and genuine Capture packaging.
The child shares the worker PGID; outer cleanup reaches it. Inner cleanup uses child terminate/kill/reap.

Current defaults are parsed from pinned public source constants and recorded as actual values,
including document rules/leads/form headings and `DOCUMENT_SECONDS=0.0`; optional CLI flags are absent.
Baseline execution records and immutable admission permits are independently reconciled: persisted
permission with `executed=false` has zero counter delta. Permission count is never a read count.

Session files: `session-bootstrap.json`, `session-start.json`, original worker stdin/stdout/stderr,
`session-final.json`. Each delivery binds request, original worker receipt/response, startup hash,
original response stream range and all artifact hashes/identities. Later mutable stream growth cannot
invalidate or silently replace earlier response ranges. Session final binds complete streams.

Expert outputs remain `artifact/dispatch.json`, `artifact/summary.json`, `artifact/logs/<original>` and
source streams. Baseline outputs include `artifact/capture/local/capture.json`. The parent creates the
public packet separately; the worker does not read a reviewed dataset or generate scoring facts.

Expert destination is `delivery_root/controller-{turn:02d}` (numeric positive turns including 100+).
Baseline destination is its initially absent `delivery_root`. The client exclusively creates deliveries.
Private sessions live outside delivery directories. No original artifact is overwritten.

## Secret and producer-input boundary

The client never reads ambient credentials or `.env` contents. The key is an explicit private argument
passed only to the source worker's explicit environment. It is absent from public configs, argv,
prompts, proof values and secret-derived hashes. Selector public environment is a copied allowlist:
HOME, PATH, LANG, LC_ALL, TMPDIR; source credentials/proxy/CA/Python/import injections are absent.

Source environment pins robots, delay, timeout, browser disabled and private cache/database paths.
Baseline private producer input must be a canonical regular original file outside every public
source/import root; only pointer/hash and before/after file identity are exposed. Expert rejects it.
Root must mechanically provide the authorized original V13 producer input; no real registry was read
while building or testing this candidate.

## Offline gates and remaining integration

105 tests passed in 2.78 seconds against the installed opt-in controller/admission modules, with fake
tools, clocks, source artifacts and source processes. One expressly authorized source-free Python
interpreter probe imports synthetic `app.config`, proves `-S` skips an ambient synthetic site hook,
and executes no stock source tool, credential, model or network call.

Ruff check, Ruff format check and isolated mypy (2 files) pass. Original intermediate negative logs
remain in `/tmp`; they distinguish fixture/API corrections from the final result.

Final logs:

- `/tmp/unimatch-expert500-local-worker-v1-unknown-binding-original.log`
- `/tmp/unimatch-expert500-local-worker-v1-ruff-final-v2-original.log`
- `/tmp/unimatch-expert500-local-worker-v1-format-check-final-v2-original.log`
- `/tmp/unimatch-expert500-local-worker-v1-mypy-final-v2-original.log`

The root still owns integration, complete real dependency/import manifests, private input relocation,
source-session isolation, parent/report binding, model/OS/runtime preflights and freeze. This candidate
has no live source/model/provider result. Unknown source counters or forced unknown tails remain
preseal ineligible. This delivery does not claim launch readiness.
