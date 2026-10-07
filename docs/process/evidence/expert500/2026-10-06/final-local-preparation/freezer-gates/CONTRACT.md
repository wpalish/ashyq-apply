# V14 local freezer and launcher candidates

Status: offline candidates; 60 synthetic tests and three-file quality checks pass. No actual neutral/OS/source/model/provider/CI invocation, registry read, freeze, or launch has occurred in this work.

## Files and entry points

- `/tmp/unimatch-expert500-freeze-v14-local-candidate.py`: `prepare_freeze(configuration, *, repo: Path, destination: Path) -> dict`; CLI `--configuration PATH --repo PATH --out PATH`.
- `/tmp/unimatch-expert500-launch-v14-local-candidate.py`: `prepare_trial(manifest_path, *, repo: Path, root: Path, temp_root: Path) -> dict`; `launch_stage(*, repo: Path, root: Path, stage: 'baseline'|'experts', source_key_fd: int) -> int`.
- `/tmp/test_unimatch_expert500_freeze_launch_v14_local_candidate.py`: synthetic filesystem/subprocess/proof tests only.

Launcher preparation uses `--repo --root --manifest --temp-root`, with no credential descriptor. An actual stage uses `--repo --root --stage --source-key-fd`; it requires an existing FIFO FD >2, never reads its bytes, and passes that FD only to the new local parent. Source/model requests are never made by preparation.

## Required configuration (no successful placeholders)

- `protocol_version: journal-v14-local`; `transport_kind: local_process_v1`.
- `harness_sha`: exact selected 40-character clean HEAD; `frozen_ref`: existing exact matching ref. The repo and source_cwd must be clean and stay unchanged through launch. There is no reset, checkout, retry, installation, or mutation command in either helper.
- `search_provider`, `algorithm_provider`, `expert_provider`: `exa`.
- `local_runtime`: exactly `source_cwd`, `source_manifest`, `interpreter`, `runtime_files`, `runtime_import_roots`, `public_environment`.
  - Source directory and all import roots must be canonical. Every application/evaluation Python file is independently pinned in confined relative source_manifest entries. The actual seven merged algorithm defaults are parsed as literals.
  - Interpreter invocation and resolved target are bound; venv `pyvenv.cfg`, if present, is required. Every file under the canonical dependency roots must be pinned; dependency symlinks and unmanifested files fail. The prospective operator configuration should use the exact existing canonical stdlib, lib-dynload, and venv site-packages roots verified by trace, with no install/copy workaround.
  - Public environments explicitly contain HOME/PATH/TMPDIR and optionally LANG/LC_ALL; no credential/PYTHONPATH/ambient extension is accepted. The source-worker base environment and selector_environment are frozen separately.
- `selector_environment`: exact public map used by the fresh neutral and parent; digest is recomputed.
- `public_cases`: original ordered ten, exact `{id, university, domain, request}` shape with the existing eight public request fields; bachelor/computer science/fall2027, unknown programme/population/qualification/year remain null. No registry values are consulted.
- `baseline_identity_registry`: `{path, sha256}` metadata only, outside source/repo/import roots; `baseline_identity_registry_source_sha: e327498d605d3dbe14da177a8a535c664818ce9b`. Freezer/launcher never read registry bytes; binding_registry is the same pointer.
- `ci_source_proof`: `{path, sha256}` for original completed successful selected-source GitHub REST metadata, repository wpalish/ashyq-apply, exact run ID/head/URL and `.github/workflows/ci.yml`. Actual nonempty workflow name is recorded (`release-gates` in root's original metadata); it is never invented as `CI`.
- `local_gates`: `{path, sha256}` for original current gate JSON and separately hashed original logs; coverage>=92, required backend/frontend/quality/parent/launcher/default-provider/OS/demo/alembic gates.
- `neutral_originals`: `{path, sha256}` for an exclusive fresh original archive manifest. Manifest kind is `fresh_source_free_v14_local_neutral_originals`, schema1/protocol journal-v14-local, completed three default-effort Astra phases, zero source/university/tool requests, original result/helper/raw copies and actual 15 module + 3 helper before/after hashes. The archive is supplied only after the fresh root invocation; no old proof/hash is reused.
- `os_preflight`: `{path, sha256}` for the fresh original `/tmp/unimatch-expert500-v14-local-isolation-preflight-result.json`. Replay requires exact current parent hash, ten workspaces/240 harmless-cat processes, and zero model/source/network requests.

The fresh neutral result retains top-level `public_model_environment`/SHA. Each original request and phase result additionally requires the exact `selector_environment`/SHA now emitted by root's prepared helper. The freezer replays every canonical completed stream/schema/prompt/command/window/output. No partial text or failed turn is admitted.

## Frozen and once-only contracts

- Exact 22 public protocol modules, installed admission module, actual helper/test/probe/worker/exporter bytes and bundled CLI bytes are hashed. Actual `/tmp` invocation coordinates are preserved as script-map keys because parent/report use those literal keys. Canonical evidence pointers are checked against canonical OS result coordinates without rewriting recorded neutral invocation strings.
- Original neutral raw byte copies, OS artifact tree, CI/local gate result/logs, and helper bytes are copied exclusively into the freeze. Private registry contents are not copied.
- New trial directory claim precedes every workspace mutation. Durable launch-start and stage-start receipts survive failures; reentry/concurrency cannot allocate or dispatch twice. There is no deletion/reset/retry.
- Parent argv uses the declared interpreter `-B -E -S -s`, only declared public source/runtime import roots, the exact new parent/ref/stage/FD, and explicit selector public environment. There are no synthetic GH IDs or source dispatches.
- Original network caps remain expert60/6 with immutable900s per-case hang guard/default CLI effort, baseline60/6/120000ms with119000 source deadline+1000 reserve, reviewed denominator62/threshold40. No separate documents clock or optional capture experiments are enabled; actual merged DOC2/DOC3/form and other stock defaults are truthfully bound.
- STOP markers and incomplete/provider-failed baseline stages refuse subsequent stage launch. Unknown source tails remain an independent report/preseal rejection; the launcher cannot declare them zero.

## Remaining genuine prerequisites

Root must supply an actual clean selected source/runtime config, exact original registry pointer/hash, completed selected-source release-gates proof, current original local gate/log bundle, fresh neutral archive and fresh OS result. Exporter and its test are required inventory entries; their final bytes are supplied by catalogue. Root's secret-free interpreter/import-origin preflight before passing any private descriptor remains an operator prerequisite; these candidates do not claim it has run. No runtime/config/proof JSON with fabricated successful hashes is included.

Commands actually run (backend cwd, synthetic only):

```
UNIMATCH_EXA_API_KEY='' PYTHONPATH=. ./.venv/bin/python -m pytest -q --no-cov /tmp/test_unimatch_expert500_freeze_launch_v14_local_candidate.py
MYPYPATH=. ./.venv/bin/python -m mypy --config-file mypy.ini --follow-imports=skip /tmp/unimatch-expert500-freeze-v14-local-candidate.py /tmp/unimatch-expert500-launch-v14-local-candidate.py /tmp/test_unimatch_expert500_freeze_launch_v14_local_candidate.py
./.venv/bin/ruff check --config ruff.toml --ignore E501,B023 /tmp/unimatch-expert500-freeze-v14-local-candidate.py /tmp/unimatch-expert500-launch-v14-local-candidate.py /tmp/test_unimatch_expert500_freeze_launch_v14_local_candidate.py
./.venv/bin/ruff format --config ruff.toml --check /tmp/unimatch-expert500-freeze-v14-local-candidate.py /tmp/unimatch-expert500-launch-v14-local-candidate.py /tmp/test_unimatch_expert500_freeze_launch_v14_local_candidate.py
```

Preserved raw logs include initial43green, initial genuine four-error static failure, expanded60green/one-test-annotation failure, and final60green/quality success. No prior helper bytes were edited.
