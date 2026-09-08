# T34 A1 — QA TEST_AUTHOR report (campaign c3, SECURITY payments fail-closed)

- ROLE_PHASE: ashyq-qa / TEST_AUTHOR
- STATUS: TESTS_READY
- Baseline SHA (verified `git rev-parse HEAD` before work): `edf546de9f998c0909337d0abe6f8e1c9c4a0be5`
- Branch: `ai/c3/t34/qa`, worktree `/Users/wpalish/ashyq-worktrees/c3-t34-qa`, tree clean at start and after commit
- QA commit: `dc04fc387c4ab605dbed4cacde915105384db1e8` (parent = baseline; only the two test files, +125/-0; trailer `Agent: ashyq-qa`; not pushed)

## Files modified (append-only)

- `/Users/wpalish/ashyq-worktrees/c3-t34-qa/backend/tests/test_apipay_adapter.py` (+47): R1, R2, R3
- `/Users/wpalish/ashyq-worktrees/c3-t34-qa/backend/tests/test_payments_config.py` (+78): R4, R5 (parametrized x2), R6, 2 green guards; import block gained `pytest` and `typing.Any`

No production files touched. T33/T35/T37 files untouched. No conftest.py / test_payment_webhook.py edits. Synthetic key material only (`"a"*20`, `"b"*32`, `"whsec"`-style placeholders).

## Commands and exit codes

| Command (cwd `/Users/wpalish/ashyq-worktrees/c3-t34-qa/backend`) | Exit | Result |
|---|---|---|
| `./.venv/bin/python -m pytest tests/test_apipay_adapter.py tests/test_payments_config.py` (final) | 1 | 7 failed, 21 passed in 0.62s |
| same command (first run, before base-dict fix) | 1 | 8 failed, 20 passed — R6/guard were masked by the UNIMATCH_METRICS_TOKEN check, fixed (see Deviations) |
| `./.venv/bin/python -m ruff check tests/test_apipay_adapter.py tests/test_payments_config.py` | 0 | All checks passed |
| `./.venv/bin/python -m ruff format --check ...` | 0 | 2 files already formatted |
| `./.venv/bin/python -m mypy tests/test_apipay_adapter.py tests/test_payments_config.py` | 0 | no issues |
| `./.venv/bin/python -m pytest tests/test_payments_config.py::test_a_valid_production_apipay_configuration_starts tests/test_payments_config.py::test_development_keeps_the_fake_provider_available -v` | 0 | 2 passed |
| `./.venv/bin/python -m pytest` (full-suite baseline sanity, single run) | see note | 7 failed, 1360 passed, 1 warning in 175.34s |

Note on full-suite exit code: the run was piped to `tail`; the `EXIT=$?` echo captured `tail`'s status (zsh has `pipestatus`, not bash `PIPESTATUS`), so no direct pytest exit code was captured. The summary line `7 failed, 1360 passed` is the recorded evidence; pytest exits 1 with failures. The 7 failures are exactly the 7 new RED test items; 1360 passed = 1358 pre-existing green + 2 new green guards. No pre-existing test regressed.

## RED results (per scenario, on baseline edf546d)

- R1 `test_webhook_signature_computed_with_an_empty_secret_is_rejected` — `assert True is False` : forged `sha256=49503cb4...` computed with key `b""` verifies as True through `verify_webhook` (S3a exploit: `hmac.new(b"", ...)` is deterministic and matches; only guard is `if not signature`).
- R2 `test_an_empty_api_key_is_rejected_at_construction` — `Failed: DID NOT RAISE ValueError` (match "non-empty api_key").
- R3 `test_an_empty_webhook_secret_is_rejected_at_construction` — `Failed: DID NOT RAISE ValueError` (match "non-empty webhook_secret").
- R4 `test_an_unknown_provider_name_is_refused_at_startup` (provider="apipy") — `Failed: DID NOT RAISE RuntimeError` (match "UNIMATCH_PAYMENTS_PROVIDER").
- R5 `test_apipay_with_short_credentials_is_refused_at_startup[api_key 19 chars]` — `DID NOT RAISE RuntimeError` (match "UNIMATCH_APIPAY_API_KEY").
- R5 `test_apipay_with_short_credentials_is_refused_at_startup[webhook_secret 31 chars]` — `DID NOT RAISE RuntimeError` (match "UNIMATCH_APIPAY_WEBHOOK_SECRET").
- R6 `test_production_never_takes_payments_through_the_fake_provider` (prod base + payments_enabled=True + provider="fake") — `DID NOT RAISE RuntimeError` (match "fake provider").

All REDs are genuine reproductions (assertion/raise failures inside the scenario), not import or environment errors.

## GREEN results (pass on baseline AND must stay green after the fix)

- `test_a_valid_production_apipay_configuration_starts` — prod base + apipay + key `"a"*20` + secret `"b"*32` passes `validate_runtime()`.
- `test_development_keeps_the_fake_provider_available` — dev + `payments_enabled=True` + `provider="fake"` passes `validate_runtime()`.
- All 19 pre-existing tests in the two files still pass (15 adapter + 4 config).

## Deviations / notes for Developer

1. `_PRODUCTION_BASE` = verbatim `test_metrics.py:250-259` dict PLUS `"metrics_enabled": False, "metrics_token": ""` (the `:263` closed-metrics variant). Reason: with metrics defaults (`metrics_enabled=True`, empty token) the pre-existing UNIMATCH_METRICS_TOKEN check fires before any payments check — first run showed R6 and the prod guard failing for that unrelated reason. With metrics closed, the failures isolate exactly the frozen payments semantics.
2. R5 was parametrized over explicit kwargs (`api_key`, `webhook_secret`) rather than `**dict` field override so the annotated test bodies stay mypy-clean (mypy.ini has `files = app`; explicit-path checks would otherwise flag `**dict[str, str]` into the pydantic Settings constructor).
3. R1 constructs with a valid secret then forces `provider._secret = b""`, so it remains valid after C2 makes construction reject empty credentials; a sanity `assert provider._secret == b"whsec"` precedes the force.
4. Match substrings are exactly the contract-frozen ones: `UNIMATCH_PAYMENTS_PROVIDER`, `UNIMATCH_APIPAY_API_KEY`, `UNIMATCH_APIPAY_WEBHOOK_SECRET`, `fake provider`, plus `non-empty api_key` / `non-empty webhook_secret` from frozen C2 message text.

## Scope confirmation

- allowed_paths respected: no edits to `app/config.py`, `app/payments/apipay.py`, `app/payments/provider.py`, or any T33/T35/T37 file.
- Read-only regression files (`test_payment_webhook.py`, paywall/billing suites) were only run inside the full-suite sanity run: all passed.
- No push, no deploy, no real secret material, offline.
