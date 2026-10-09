# First native failure — originals preserved, full NOT RUN

**FAILED CORE / FULL NOT RUN.** Own queue36998 terminated exit1 after doctor/core on source HEAD`08450f71e6bbeadd9a2212fbd6c9f96f5c428755`, selected34pinsSHA`bc960dfdf50a140698ff399c7929cc503f6fee24ef5f050c34d3ef9f72a71dd6`. No source repair, rerun, full, PostgreSQL, E2E, audit, container or production action occurred in this collection task.

| Actual completed unit | Result | Original scope |
|---|---|---|
| Doctor `20261009T041529Z-doctor-03e1638b` |5/5 PASS|Environment/runtime dependency checks only; doctor produces no source snapshot manifest|
| Core `20261009T041531Z-check-d7321524` |7/8 PASS; backend-sqlite FAILED|Ruff/format/mypy and all four frontend steps passed; core overall failed|
| Backend SQLite JUnit |4392 distinct IDs =4391 PASS +1 FAIL;0 errors/0 skipped|One completed run; failures/errors/skips independently counted from exact original XML|
| Backend coverage/warnings |95.27%;32 warnings|Coverage threshold reached, but test gate exit1 remains FAILED|
| Frontend |357 tests/34 files PASS|Existing source frontend count; not additional privacy assertions or quality improvement|
| Static |Ruff/format/mypy exit0; mypy388 source files|Counts different units from pytest and preserved from actual logs|
| Full and additional gates |NOT_RUN|No full queue record: PostgreSQL/demo E2E/auth E2E/pip audit/npm audit/containers all NOT_RUN|

The pytest terminal summary is `1 failed, 4391 passed, 32 warnings in513.31s`; the recorded backend subprocess step is515.8s. These are distinct timings. Core's actual8step list matches the own-child summary and onlybackend-sqlite exits1; the queue stopped before full. Running7individual successful core steps is not core PASS.

## First failed assertion

`tests/test_rejected_diagnostics.py::test_p6_ordinary_source_status_budget_and_controlflow`, frozen source line615:

```python
assert any("Traceback" in log["json"] for log in captured(caplog))
```

The recorded assertion result isFalse. Before this line, the generic ValueError rethrow identity and `audits[0]["detail"]["error"] == "ordinary bounded parse failure"` assertions passed. Assertions later in P6 were not reached. The original full failure text is preserved in both backend-sqlite.log and XML, and reproduced as a derivative in analysis.json. This collector does not determine whether logging capture, fixture state or application behavior explains the failure; it does not reclassify it as harmless, modify the assertion or claim a fix.

## Source/ownership binding

Queue execution.json reports one unique own-child stdout-selected doctor and one core run, with exactly the expected repository, HEAD and selected34 SHA. Actual summary hashes match queue records. Core summary.source equals its original source-manifest exactly. Declared source map has12104paths; canonical sorted-map digest recomputes to`7a07649d1cb38feb22b45d917e03d2d48fab987936b960dacd384e4999358023`. These are declared source paths, **not12104executable files or tests**, and recomputing their map digest is not a new physical inspection of the entire snapshot. The34 selected pins all match that declaration. Applied-head and pending-full application receipt also match HEAD/pins. Existing provider STOP65b5 remains unchanged.

Doctor's environment-only source metadata does not have a snapshot manifest. No such file was invented or borrowed from core. Historical failed/accepted runs or previous source5b48 full proof are not attributed to this changed source.

## Finite originals

`selection-manifest.json` pins exactly23physical files /5,736,311bytes:

- Doctor: summary +five whole logs =6.
- Core: summary +eight whole logs +backend SQLite XML +source-manifest =11.
- Own queue: execution.json +two original console logs =3.
- Source bindings: selected34map +application receipt +applied HEAD =3; these are metadata, not three additional runs.

The first20files are complete actual doctor/core/queue originals. Embedded source maps are duplicated in actual summary and source-manifest and remain byte-for-byte intact; that duplication is not an additional experiment. Every selected source and copy SHA/length was checked before/after copying. No source tree, `.env`, applicant/user database, `.coverage`, ZIP, Playwright profile, dependencies, unsafe reset packet or old runtime was selected. No raw original was scrubbed, normalized or edited. Expected ErrorBoundary test diagnostics in a frontend log are preserved alongside its actual357PASS summary, not promoted to a new failure.

The external collector only reads the finite selected original files and writes this external packet. Root alone may archive it to `privacy-diagnostics/first-core-failed`, update failed relay status, and prepare a separate reviewed repair. No canonical archive or primary/Git/source/test modification was made here. No tests/server/network/containers were rerun. Source-bound local collection is neither CI, full, production, search quality, legal compliance nor competitor security proof.
