# Existing backend golden failure

The frontend work does not change any tracked backend file: `git diff --quiet c2565ad6 -- backend` exits0. No baseline/golden was changed.

Full backend gate on the UI checkout:

-5870 passed,1 failed,49 warnings in985.80s.
- Coverage94.19%, required92%.
- Ruff check, Ruff format and mypy passed (420 files).

Failing test:

`tests/test_freshness_regressions.py::TestDemoRunIsByteIdentical::test_the_demo_pipeline_payload_is_byte_identical_to_baseline`

Expected SHA256:

`d1403ce29ee2e0f710a034b78afe222cc42b40059a6730a60fa5041490333c53`

Actual SHA256:

`c2d4688c3822c4ce05a43b0188104c9fe610f14dd377c6592deb2af7b01a0daf`

The same target was run from a clean archived copy of the untouched product base `c2565ad6` and produced the same actual hash. This establishes that the failure is inherited; it does not establish its underlying cause. Do not update the golden merely to obtain a green gate.

Raw evidence:

- [Full current gate](evidence/logs/ui-backend-tests.log)
- [Untouched base reproduction](evidence/base-c2565ad6-golden.log)
- [Static backend gate](evidence/logs/ui-backend-static.log)

The branch remains WIP, unmerged and undeployed. Repair/qualify this baseline in its owning workstream before release.
