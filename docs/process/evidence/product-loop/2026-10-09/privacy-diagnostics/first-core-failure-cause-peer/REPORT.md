# First core failed — test capture state

Core failed7/8:4391PASS/1FAIL,32warnings,95.27% coverage; fullNOT_RUN. Exact source08450f71 remains frozen. Sole assertion tests/test_rejected_diagnostics.py615 depends on a captured JSONTraceback; ordinary rethrow/audit assertions passed.

Source identifies Alembic fileConfig default disable_existing_loggers=True as a native-suite confounder absent from the isolated targeted proof. This disables named pipeline/fetch/worker loggers; merely caplog.set_level cannot restore disabled flags. Actual logger.disabled value was not logged, so cause is source-backed with native prior fixture order, not a directly observed runtime boolean. Existing absence-only captured-log controls can be vacuous.

Support narrow test-only stronger capture fixtures/positive emitted-record checks in the two new tests, preserving all privacy/SQL/status/control assertions and unchanged app/env.py. Root is preparing the actual synthetic-predisabled OFF/ON replay; this saved-only packet neither reruns it nor claims repair success. Original failuretext/log and exact metadata/source hashes retained; no source/Git/DB/test/live/reset actions. See source-explanation.md for line-cited path and qualifications.
