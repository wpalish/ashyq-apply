# Final preparation binding — saved backend terminal review

**Verdict: SAVED_FINAL_FULL_NATIVE_BACKEND_TERMINAL_VERIFIED. No concrete acceptance blocker found in the bounded saved receipts.**

Run: `evidence/backend-binding-final/20261011T134306725752Z`. Parent reports frozen source HEAD `cdcf89ab`; Git was not queried. This reviewer parsed saved JSON/XML/coverage metadata, recomputed evidence/helper hashes, compared test identities, and read back ordinary current code/config hashes. No tests, application, server, database, browser, Git, provider or LLM was executed; source/helper files were unchanged. Only this external report and its metadata receipt were written.

Authorship qualification: this reviewer authored the evidence-binding proposal. This receipt checks root-executed saved gates and bindings; the separate static source peer review is `audits/evidence-binding-review.md`.

## Actual tests and native retention

| Saved phase | Actual / unique IDs | Failures / errors / skips | Coverage JSON | Coverage floor | Pytest exit |
|---|---:|---:|---:|---:|---:|
| sqlite | 4,682 / 4,682 | 0 / 0 / 0 | 95.4438284585484% | 92% | 0 |
| postgres | 4,682 / 4,682 | 0 / 0 / 0 | 95.43745619065825% | 92% | 0 |

The phase `(classname, name)` identity sets are identical. Sorted compact JSON SHA256: `129716f4c40b296a483e733599f569da6bc9d1589830257a8a4540bdb62c5819`.

- All **4,653** prior accepted identities from `evidence/backend-full/20261011T124000847599Z` remain in each phase; zero are missing.
- Exactly **29** identities were added: **21** pure preparation-domain controls and **8** API controls (four semantic cases across the two existing native database fixtures). The metadata receipt lists their exact IDs.
- Preparation totals are **151** in each phase: **100 API + 51 domain**. The existing 92 API and 30 domain identities are retained. Both full invocations retain the literal native `tests` target and `--cov-fail-under=92`; no selector/skip/count substitution is present.
- JUnit testcase elements and result fields agree. Coverage JSON totals independently match phase receipt fields. Both saved logs report **4,682 passed, 42 warnings**; this acceptance is not warning-free.

## Isolation, probes and cleanup

All **25 recorded evidence hashes per phase** recompute exactly (50/50). There are **13 guard receipts per phase**, zero recorded outside attempts, no guard-startup failure marker, no app preimport, and a main receipt confirming the driver guard and restored IPv6 trait. Allowed private Unix PostgreSQL events total **757 / 758**; every recorded host is under its phase-owned runtime prefix.

Each saved OS parent probe and actual Bash/Python `-I` descendant probe passes all **six** actions (IPv4/IPv6 bind, connect and sendto denied with EPERM). The separately saved child receipt equals the embedded descendant result. Each private PostgreSQL probe records successful `SELECT 1`. Both saved sandbox profiles retain `(deny network*)` and only the owned runtime trailing-slash Unix-socket prefix for inbound/outbound/bind allowances.

Both phase results record `shutdown_confirmed:true`, `runtime_removed:true`, empty cleanup issues and empty active-cluster markers. This verifies saved cleanup evidence without a fresh process/database probe. The root result is PASS and contains both actual completed phase records; its `postgres_if_not_started:NOT_RUN` fallback field does not describe the completed PostgreSQL phase.

## Source and helper binding

Four phase source maps are byte/hash-identical: **595 consumed paths**, SHA256 `c50d877140062290915426c3e7aa4f6107419c008e78ea3936e413db13dd7f17`. Both before/after pairs compare equal.

All **557** expected native path keys and exact final values occur in the terminal maps. Relative to the old accepted map, zero paths were added or dropped; exactly these three values change, while the other **554** expected values remain exact:

| Path | Final SHA256 |
|---|---|
| `backend/app/domain/preparation.py` | `07cf2c70355847b76affbe72564b80841bad9009af671056e6b38c2d098295b4` |
| `backend/tests/test_preparation_api.py` | `fde8e742aabc908f807937241f7480b9a1260e88faa9465045c874b258e79437` |
| `backend/tests/test_preparation_domain.py` | `45c54b4a2dacb4b71e4b400da09c39979fe9df81949110f3aed1366df59e20c2` |

The previously reviewed `BINDING_FORMAT_ONLY` qualification remains: only native parameter-list wrapping changed, AST is equal, and both complete original test prefixes remain byte-exact. No formatter delta is treated as behavioral change.

Expected-map SHA256: `4d9434a121dc96c1893bc0e95fc73ce9df3e86692a661aa33e65dd6db15a871b`. All **17 consumed helper/config hashes** match current helper files. The **other 16** helper/config files are byte-identical to old accepted backend-full, including floors, guards, mocked-endpoint constraints, shared-lock and cleanup logic. Only the exact three source-pin values were rebound in the expected map.

Current-source carry is bounded: **442 ordinary backend-consumed code/config files** (432 Python, three shared TS/TSX, seven named ordinary configs/workflow files) match the terminal map at review. Remaining asset/template/text payloads are bound by saved during-gate 595 maps; their bodies were not reopened. Historical frozen native-fixture replay is not current search-quality measurement.

## Final static/frontend receipt

`evidence/static-frontend-binding-final-v2` has all **seven saved steps exit 0**: Ruff, Ruff format, mypy, frontend typecheck, lint, native units and build. Its **625** before/after maps are byte-identical, SHA256 `f6e406cd7afa9c7459e4b762a0b6f67a62c4e544a40ea6824452a27f7de7e281`. The actual intersection with backend consumed pins is **513 paths**, with zero mismatches.

Frontend JUnit contains **468 unique passing cases in 54 suites**, zero failures/errors/skips. All **465** earlier IDs from `static-frontend-final-v2` remain; the only three additions are saved same-programme request-retention, same-programme evidence-retention and initially closed evidence-details controls. Current readback of **508** ordinary static code/config paths matches this saved map.

Ruff reports all checks passed, format reports 404 files formatted, and mypy reports no issues in 372 files with annotation-unchecked notes. Lint contains **four warnings, zero errors**. Unit logs retain React `act` warnings, jsdom navigation messages and synthetic ErrorBoundary exceptions; actual terminal/JUnit results pass. Build exits 0. No clean-log claim is made.

## Limits retained

The qualification for a real concurrent-HTTP UUID race remains; these gates do not add that test. ORM case-deletion/cascade/export coverage is not a newly executed end-to-end HTTP account-deletion proof. `GLOBAL_PROVIDER_STOP/UNSCORED` remains closed and current search quality is **NOT_MEASURED**. The separate SAT Week 1 content draft is not integrated by these gates. Root ongoing Demo/Auth/UI gates are outside this review and are neither read nor accepted here.

## Primary receipt hashes

| Saved artifact | SHA256 |
|---|---|
| Final backend root result | `2a92fbbf8ec0fce3611cd06ae3e5e118966db0bb386b7f8f83824b8ae92d6a84` |
| SQLite result | `204b89fe3ef7835c3a186eb5c77ada01c5964f6e93173380092f30248bfb8067` |
| PostgreSQL result | `7c448f078156aa7b9021f7813da3d18f7f1e663b13480d8db17c08f8f8c6aa09` |
| SQLite JUnit | `d183ca729dc4452d321102780803a74814c15494ee561d45ed845df081016690` |
| PostgreSQL JUnit | `46fa638def7e2328b82d7c82f2f4db9c3b646de697e799ff4ed6178fe0d3f44e` |
| SQLite coverage JSON | `88850d60850b921865b7803a854029ba3e96f27e3bebdd49986641719453cce1` |
| PostgreSQL coverage JSON | `1b781d26ad7e442f5178825d51345218f14ed2b01736721ee7325d8eddca76f9` |
| Saved helper-pins map | `03662fe6a9bd0f50b253224d18e56b540382178acbadeae43a2b882888d18219` |
| Saved preflight | `78b870695d6aaf85a06115f803440c346f1338df978ab0b37c2069f67af93c76` |
| Final static/frontend result | `e293e70d610fad2ccf09e7a22570d58ec67c0bfb47996bd9030cecc728e3e9df` |
| Final frontend JUnit | `469b860980a1cf5a7a2246cb896363e01d7dcd3b7f42a088585923ce25475bd7` |

Metadata receipt: `audits/backend-binding-final-terminal-review.json`, SHA256 `6755749be468d40f3b8475f2fa9fc4f837818d2cb1321ea759f09781541b3811`.
