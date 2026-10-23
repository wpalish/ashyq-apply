# G1 finite-v2 — sealed narrow proposal

12.10.2026. External ordinary source only. Base `04830101` is parent-reported; actual preimages were checked by SHA-256 before authoring. This packet was not imported, installed, executed, applied to the active checkout or committed by its author.

## Purpose and exact scope

Three paths only:

- `backend/app/api/routes_preparation_graph.py`
- `backend/app/schemas/preparation_graph_loader.py`
- `backend/tests/test_preparation_graph_api.py`

The application patch checks raw claim/conflict/checklist JSON before Pydantic parsing. A single reusable `assert_finite_floats` helper checks native typed float leaves in dictionary keys/values, lists and tuples before JSON-mode serialization; date/datetime/enum leaves are allowed. Existing raw finite JSON validation and post-serialization exact snapshot checks are retained. Legacy schema defaults, v1 handlers, DB codecs, ownership/entitlement/scope checks, failure precedence, full-suite guards and all other paths remain byte-exact by proposal scope.

## Two separate stages for the parent

1. After terminal owned cleanup and the parent's fresh writeahead, verify the `TESTS_FIRST_RECEIPT.json` preimages. Apply **only `TESTS_ONLY_PATCH.diff`**, or append `TEST_FRAGMENT.py` to the current API test file. This patch has no application changes or new imports. Preserve old test bodies and update the execution namespace/source pins under the parent's approved procedure.
2. Run the approved focused diagnostic on the old application and save its real terminal result. Expected regression failures are **unproved before this run**; do not label the source hypothesis a reproduced bug merely because tests exist. The primary cases exercise numeric-string NaN/±Infinity in optional document size, through both the authoritative column and payload fallback. Direct raw claim/conflict controls use transient synthetic ORM envelopes; no nonfinite JSON is written to PostgreSQL or SQLite.
3. Inspect the trace. If the diagnosed reason supports this fix, apply **only `APPLICATION_ONLY_PATCH.diff`** after another preimage check. Existing test additions are already present; do not reapply the full packet. Bind new actual hashes and rerun the authorized focused/full/native gates. Retain the first failure as evidence; this package does not supply any PASS.

`FULL_PROPOSAL_PATCH.diff` is a review convenience, not the tests-first application instruction. The complete `proposed/` test file uses the old application's exact test module as an unchanged AST prefix plus the appended fragment.

## Meaningful controls

7 new test functions, **33 statically enumerated parametrized cases**, never a passed-test count:

- Nested raw NaN/+Inf/-Inf in claim normalized values and conflict values must produce a failed read. A finite neighbouring envelope is retained and the failure flag is not lost.
- Authoritative column raw nonfinite document size is refused for admission, scholarship and school projections.
- Strings NaN/Infinity/-Infinity coerced into `DocumentItem.max_file_size_mb` are refused for both column and payload fallback.
- Explicit None, finite nested numbers, literal text NaN in Any quote, finite tuple values and finite coercible size remain accepted.
- Valid controls retain programme/scope identity, aware accessed/generated timestamps, dates/enums and authoritative claim status/type/url/specificity rather than copied payload metadata. Valid conflict type/unresolved columns still override copied payload values.

No new test imports the proposed helper by name: the tests-first fragment can run against the old application without an import failure due to the missing helper. Existing HTTP tenant, locked minimization, partition, unavailable-slice and legacy regressions are unchanged and remain required gates.

## Static validation and limitations

- All 3 proposed files and the test fragment passed stdlib AST parsing only.
- Every old test AST top-level node is an exact prefix of the proposed module. No test body, fixture, assertion or guard was removed or weakened.
- The old loader's raw before-validator and duplicate-award check remain. API authoritative metadata overrides and failure branches remain.
- SHA receipts cover saved originals, proposed files, patches and the test fragment.
- Ruff/mypy/pytest/app imports/actual serializer behavior, SQLite/PostgreSQL/native and search quality were **NOT RUN** by the author. Formatting and runtime acceptance belong to the parent's approved gates.
- The helper intentionally examines numeric leaves only; it does not replace the existing JSON serializability check, parse arbitrary objects, change semantic evidence levels or record any completion/accepted route/shared score target.

Originals and the tests-first seal are preserved. New application files are external proposals, not an integrated repair or deployment. No providers, labels, stopped security/collector workflows, secrets, user databases, Git or HANDOFF were read/changed by the authoring step.
