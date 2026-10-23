# Backend terminal acceptance review — 2026-10-11

**Verdict: SAVED_FULL_NATIVE_BACKEND_ACCEPTANCE_VERIFIED, with the scoped current-source carry qualification below. No concrete terminal acceptance blocker found.**

Saved run: `evidence/backend-full/20261011T124000847599Z`. Root acceptance receipt reports HEAD `777e9e23`; Git was not invoked by this reviewer. File hashes bind the review. The reviewer parsed saved metadata/JUnit/coverage/guard/probe receipts and checked ordinary current-source hashes; no tests, server, database, browser, provider, LLM, Git or runtime process was launched. No source was changed; only this external report was written.

## Counts, identities and native floor

| Saved phase | Unique passing test IDs | Failures / errors / skips | Coverage over app | Covered / executable lines | Guard receipts | Allowed private-PG events |
|---|---:|---|---:|---:|---:|---:|
| sqlite | 4653 | 0 / 0 / 0 | 95.435393258427% | 14949 / 15664 | 13 | 745 |
| postgres | 4653 | 0 / 0 / 0 | 95.429009193054% | 14948 / 15664 | 13 | 746 |

- Both JUnit files contain exactly 4,653 testcase nodes and 4,653 unique `(classname, name)` identities. Their identity sets are identical. Deterministic sorted identity-set JSON SHA256: `7f867f0d4f3d2c850f9926798b39f430b93f59800b9930e1dd8aa664c9dd77ff` (UTF-8 JSON with compact separators).
- Independently compared the prior qualified continuation run `20261011T080840328906Z`: all **4,531** prior SQLite and PostgreSQL unique identities remain. **Zero prior IDs are missing**; the only 122 additions are `tests.test_preparation_api` (92) and `tests.test_preparation_domain` (30). Existing native test paths/values were also retained by the previously reviewed 547→557 pin rebinding; no old native test file hash was changed.
- Each phase includes 92 preparation API cases and 30 preparation domain cases. The API module retains both explicit SQLite and PostgreSQL fixture variants (46 each); full-run phase changes the default Settings database. This is not a claim that every unit test uses its phase database.
- Search controls remain present: 45 cases from `test_search_audit_regressions` and 3 from `test_search_audit_html_links` in each phase. Their retention is included in the prior-ID subset check.
- Saved pytest argv retains the literal `tests` selector, `--cov=app`, `--cov-fail-under=92`, explicit coverage/JUnit outputs and native fixtures. Both pytest commands exited0 without timeout.
- Both saved log summaries report **4,653 passed, 42 warnings**. Acceptance is not warning-free.

## Isolation and cleanup evidence

Both saved OS probe receipts passed before pytest: parent Python and actual Bash→Python `-I` descendant each refused IPv4/IPv6 bind, connect and sendto (six checks per process, errno1). Both phase profiles deny `network*`, allowing only Unix sockets under the exact owned runtime prefix including its trailing slash. These are bounded tested transport controls, not a universal assertion about every possible syscall.

Each phase’s saved private PostgreSQL positive probe passed `SELECT 1`. All 13 guard receipts per phase report zero outside attempts, no app preimport and restored IPv6; saved results report no guard startup failures. Main receipts report 745/746 allowed private PostgreSQL events and installed driver guarding. No real provider endpoint is admitted by this result. All hashes listed by both phase result receipts independently match their saved files.

Both phase results record no cleanup issues or active cluster markers, `shutdown_confirmed:true` and `runtime_removed:true`. This is a review of saved cleanup evidence, without launching a new process or probing a database. The saved native/helper code retains the existing shared nonblocking lock and both-phase cleanup contract; all 17 consumed helper/metadata hashes match current helper files.

## Source bindings and post-mobile carry

- The four native source maps (SQLite before/after, PostgreSQL before/after) are byte/hash-identical: **595 consumed paths**, map SHA256 `57848f5d6e29dfac2d4842153f875853840da2dd7a6317f6cb1449ea0ca107ab`. The two before/after pairs independently compare equal.
- All 557 expected source pins are present with exact values; the consumed maps also include 38 fixed historical native fixture dependencies. Payload bodies/labels were not inspected or scored by this reviewer. Historical unit-fixture replay is not current search-quality measurement.
- Root applied the three mobile paths only after terminal backend acceptance. The recorded/current after hashes of App, CSS and preparation E2E are exact. All three paths are absent from the consumed595 map and expected557 map.
- The saved post-mobile frontend source-before snapshot contains the same 625 path set as the prior static/frontend receipt and differs in exactly those three mobile paths. Consequently its 510 backend snapshot paths and the 511 paths shared with expected native source stay unchanged.
- Independently checked **442 current ordinary code/config consumed files** (432 Python files, shared TS/TSX and selected ordinary configuration files): zero mismatch against the terminal595 map. The remaining asset/template/text payload current carry is qualified by root’s sealed `MOBILE_APPLICATION.json` receipt (`backend_consumed_pin_count:595`, `backend_consumed_pins_unchanged:true`); their contents were not reopened for an independent current readback. This distinction is deliberate.

Backend runtime acceptance therefore carries across this exact mobile-only application under the stated receipt/source qualification. The earlier Ruff/format/mypy backend inputs are unchanged. The old frontend static/unit/build receipt applies to its earlier frontend source; the changed App/CSS/E2E require fresh frontend and native UI acceptance. Those later outcomes are outside this report and remain PENDING here.

## Existing proof limits retained

Passing the preparation controls does not add a real concurrent-HTTP UUID race test. The source has UUID/unique-constraint handling and the reviewed sequential/idempotency controls; the prior static race qualification remains. The new deletion/cascade control verifies ORM case deletion and export/history behavior, not a newly executed end-to-end HTTP account-deletion path for this feature. The prior HTTP-delete qualification remains.

The review does not establish primary-branch integration, deployment, paid-provider operation, comprehensive curriculum coverage, admission score predictions or live programme-requirement accuracy. **Search quality remains NOT_MEASURED; GLOBAL_PROVIDER_STOP/UNSCORED remains closed.**

## Exact receipts and phase hashes

| Path | SHA256 |
|---|---|
| `harness/FULL_BACKEND_ACCEPTANCE.json` | `51cf1a59debccf581d5737b1692ec358e304207d392ec3b1f92434776ac6c887` |
| `harness/MOBILE_APPLICATION.json` | `d9418ed2ea4f57e3ba95e0c0e679c9d016b2685952296317aa26bac064415c07` |
| `audits/gate-binding-review.md` | `2aa1795a0fe91475518787d676561ff9ebfa17ea1e2daeb3d0be7deb8617e3ab` |
| `audits/backend-contract-review.md` | `9d7a84c587715b7937d6b0105a175e97852a68f7e6eb1fdedfac1cb5b88ba5af` |
| `evidence/backend-full/20261011T124000847599Z/result.json` | `80eccef81587c1ab9e9e1ffbdb56a625809af0ff9dd70d49ea5163c69247a88a` |
| `evidence/backend-full/20261011T124000847599Z/preflight.json` | `78b870695d6aaf85a06115f803440c346f1338df978ab0b37c2069f67af93c76` |
| `evidence/backend-full/20261011T124000847599Z/helper-pins.json` | `ad8e22c15f41d6e261f4f1f0e69491882e1df8d4205332e10e40f439da0e3b9d` |
| `backend-full/expected-native-source-pins.json` | `98c41a1c8c83a892ff50d5762df0cc88330c1e2d2c35ff9c53fa77c4f722abec` |
| `evidence/frontend-mobile-final/source-before.json` | `a366a95f119ca2daa376e39d2dae97564ea9779298aef063b1bfe89e1c812cfb` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/result.json` | `cc78037edaec4549515422d69913e65ed95de629763413897a01872133ecf975` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/junit.xml` | `79998a27ce47de0f40dda0b73db4f58adddd8f662f866e9dab6174170dd76594` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/coverage.json` | `34c9150d00089778862046db176a95815558150ef599a8755790f65f34601c8b` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/source-before.json` | `57848f5d6e29dfac2d4842153f875853840da2dd7a6317f6cb1449ea0ca107ab` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/source-after.json` | `57848f5d6e29dfac2d4842153f875853840da2dd7a6317f6cb1449ea0ca107ab` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/os-network-probe.json` | `c08320054f42f592fc092494d7fa405f0e00c31fe4cb31d36b7a8885d3e8b429` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/os-network-child-probe.json` | `00ab0a3e2a868f716c4500ba6ddb25be09553622fa68b446f3a7774acdbf25cd` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/private-pg-probe.json` | `1ec521483461e069d4a143048c48abca32ca9dbbbf79ea6997207457c34fba08` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/pytest.log` | `4e67b6e39fddaebc25735f995722ebd1fe7eaf1a3757b9e3c7ffc1b29327efec` |
| `evidence/backend-full/20261011T124000847599Z/sqlite/network.sb` | `0905567f6ccd992e73b558fc7220dc1dfd996131579b07c00d452c2573f9f7fa` |
| `evidence/backend-full/20261011T124000847599Z/postgres/result.json` | `d527ba5e98c9e21638321009cdc5a9bb107b173709b7bd8acef3b41f15529316` |
| `evidence/backend-full/20261011T124000847599Z/postgres/junit.xml` | `135f44d655feb19aa68680483b045f9f688242cb48a328d77dc0065332b5a849` |
| `evidence/backend-full/20261011T124000847599Z/postgres/coverage.json` | `26ae62ac2b32dbbb880d81001d6e9e828f0fb734be4fb86e0cea940cfbad35da` |
| `evidence/backend-full/20261011T124000847599Z/postgres/source-before.json` | `57848f5d6e29dfac2d4842153f875853840da2dd7a6317f6cb1449ea0ca107ab` |
| `evidence/backend-full/20261011T124000847599Z/postgres/source-after.json` | `57848f5d6e29dfac2d4842153f875853840da2dd7a6317f6cb1449ea0ca107ab` |
| `evidence/backend-full/20261011T124000847599Z/postgres/os-network-probe.json` | `c08320054f42f592fc092494d7fa405f0e00c31fe4cb31d36b7a8885d3e8b429` |
| `evidence/backend-full/20261011T124000847599Z/postgres/os-network-child-probe.json` | `00ab0a3e2a868f716c4500ba6ddb25be09553622fa68b446f3a7774acdbf25cd` |
| `evidence/backend-full/20261011T124000847599Z/postgres/private-pg-probe.json` | `11d50c5480cd6d37a2843cc5d5f6cecb239ee2552a81ce6734b077a4af674880` |
| `evidence/backend-full/20261011T124000847599Z/postgres/pytest.log` | `3edef66fd2e7e9dbe38b3b3f19672f520ab3cb9be22bfaddeed9ed0d8937cf97` |
| `evidence/backend-full/20261011T124000847599Z/postgres/network.sb` | `2ba6eb140e1635756df31414149eb508c9ef97ad19bb8c78a771d1bb1589e19a` |

### Prior identity-floor sources

| Source relative to files-mentioned-by-the-user-2026 | SHA256 |
|---|---|
| `continuation-2026-10-11/evidence/backend-full/20261011T080840328906Z/sqlite/junit.xml` | `a64f78652a850fd3a4406244eea872ccb909e898d6ca2f214e3b93d5f604e86d` |
| `continuation-2026-10-11/evidence/backend-full/20261011T080840328906Z/postgres/junit.xml` | `40605597fa491dd87441ef823394e79300d0e601d6540a6a9e7c949e18c4e2fd` |

The earlier interrupted 07:49 SQLite receipt was also checked for identity retention: its 4,530 IDs are a subset, with the expected additional canary control plus the 122 preparation cases. Its partial-run status was not substituted for the later qualified two-phase identity floor.

## Append-only post-mobile map confirmation

Root supplied `harness/POST_MOBILE_BACKEND_CONSUMED_PINS.json`. This reviewer parsed its metadata only: exactly 595 paths, byte/hash-identical to all four accepted native source maps, SHA256 `57848f5d6e29dfac2d4842153f875853840da2dd7a6317f6cb1449ea0ca107ab`. Zero added/dropped/changed values. This strengthens current carry from the prior receipt-only qualification to independent equality of the saved full current595 map. Underlying payload bodies were not reopened. The earlier review text and original report version/hash remain preserved in the parent receipt; no source, Git, runtime or gate execution occurred.
