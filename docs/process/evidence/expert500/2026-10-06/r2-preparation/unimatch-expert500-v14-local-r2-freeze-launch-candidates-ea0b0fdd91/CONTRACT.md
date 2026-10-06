# V14-local-r2 freezer / launcher candidates

Offline prospective candidates; no actual neutral, isolation, source, model, provider, freeze or launch invocation was performed. Original V14 files and failed proof originals remain unchanged.

## Exact entry points

- `/tmp/unimatch-expert500-freeze-v14-local-r2-candidate.py`: `prepare_freeze(configuration, *, repo: Path, destination: Path) -> dict`; CLI `--configuration --repo --out`.
- `/tmp/unimatch-expert500-launch-v14-local-r2-candidate.py`: `prepare_trial(manifest_path, *, repo: Path, root: Path, temp_root: Path) -> dict`; `launch_stage(*, repo, root, stage, source_key_fd) -> int`.
- `/tmp/test_unimatch_expert500_freeze_launch_v14_local_r2_candidate.py`: 75 synthetic filesystem/proof/process mocks; no real helper runner or source call.

## Narrow r2 change

All helper, test, result and neutral archive coordinates point only to r2. The worker remains the original frozen local-worker-v1. Protocol stays `journal-v14-local`, transport stays `local_process_v1`, normal CLI default reasoning is unchanged, baseline60/6/120000ms with119000ms source deadline plus1000ms reserve, expert60/6 and immutable900000ms hang guard, fixed62/40 remain unchanged.

The selector PATH is exactly the bundled CLI parent followed by `/usr/bin:/bin:/usr/sbin:/sbin`. The source worker public environment is bound separately. Extra PATH prefixes/suffixes or ambient inheritance fail. The direct neutral replay default is the five-key public environment emitted by the r2 neutral helper; configure_proofs still binds the actual supplied public environment exactly.

Fresh neutral and OS receipts must contain `cli_discovery` with exactly `path`, `codex_executable`, `sandbox_executable` and boolean `path_matches_public_model_environment=true`, plus `cli_discovery_sha256`. The expected executables are the pinned bundled CLI and `/usr/bin/sandbox-exec`. Freezer and launcher replay both hashes, exact executable identities and the configured selector PATH. This is a proof replay; these candidates do not themselves run discovery or claim actual CLI availability. Root must invoke r2 proof helpers with the same exact outer PATH.

## Existing gates retained

Selected cleanHEAD/source/runtime manifests and canonical import roots; all dependency files/interpreter target/venvcfg; exact22modules including admission; private baseline registry metadata only from originalsource e327498d605d3dbe14da177a8a535c664818ce9b; actual default DOC2/DOC3/form states plus document_seconds0; actual completed successful selected-source release-gates metadata from `.github/workflows/ci.yml`; current local gates; fresh three-phase default-effort neutral with all original streams and before/after runtime hashes; fresh current-parent ten-case240-cat OS proof; exact public selector environment at every request/phase; exclusive byte freeze and once-only trial/stage claims; original pending source-tail proof and provider STOP policy. No private registry bytes are read/copied and no GH IDs are fabricated.

## Remaining actual prerequisites

Actual selected clean source/runtime configuration, original registry pointer/hash, successful selected-source CI originals, current gates, fresh r2 neutral archive and fresh r2 OS result remain operator-supplied. Neutral manifest SHA is intentionally unresolved. A separate key-free declared-interpreter/import-origin proof before any private descriptor remains required; the frozen worker's prepare_imports requires a key and is not that preflight. No old successful or failed proof is accepted as a new execution.

## Original offline gates

75 passed in0.38s; Ruff, formatter and mypy3files pass. Pytest ran from a clean temporary cwd with explicit HOME/PATH/LANG/LC_ALL/TMPDIR/PYTHONPATH/MYPYPATH and no secret environment names. Static checks used backend cwd and its configs. Exact argv/env/cwd and before/after hashes are in commands-stable-original.json. The nine owned and relevant companion inputs were unchanged through the final gate. Initial test-style failures are preserved as original logs. No source calls were performed.
