# Prospective year-context repair candidate — unapplied

[Unified source and regression patch](/tmp/unimatch-expert500-v12-year-context-candidate.patch) · [Regression-only draft](/tmp/unimatch-expert500-v12-year-context-regression-draft.patch) · [Hash manifest and test inventory](/tmp/unimatch-expert500-v12-year-context-candidate/manifest.json)

The live V12 source, helpers, workspaces, stage artifacts, original completed-case audits and labels are unchanged. Five exact source/test originals and independent candidate copies are under `/tmp/unimatch-expert500-v12-year-context-candidate`. No provider/model/source calls, scoring, changed-runtime tests, Git or HANDOFF changes occurred.

## Intended behavior

1. `DocumentIR.EvidenceBlock` gains two dedicated optional provenance tuples. `section_year_labels` records literal **Academic year** labels immediately following the same content heading, with both original DOM tag paths and the original heading section path. `row_year_cells` records only the selected table row's explicitly headed Year column, including its DOM path, table/row/column, spans, headers and exact IR block ID. Blank and ambiguous cells remain visible as failure evidence. No extra quotation block is inserted and existing block IDs/text/section paths stay unchanged.
2. `_evidence_scope` consumes those references **only for the academic-year predicate**. Programme, degree, applicant population and intake checks continue using the same original selected-block/heading text. Row Year support is more local than a caption/page label: an empty, conflicting, multiple or merged Year cell cannot be rescued by another row, table or a matching page year. An explicit different local quotation year still rejects before broader context. Multiple labels/columns are rejected rather than unioned or resolved by last-wins.
3. `validate_fact_citations` keeps successful same-policy exact-source, raw/payload hash, final-URL, quote, location, all-fact and scope checks. Successful new year support appears in an optional `academic_year_support` proof entry under the existing source-step/raw-hash proof. A typed internal year failure is described with the **original** Q/OTHER, fact ID, `academic_year`, observed markers, source step and location; the temporary Q4 implementation label no longer calls a Q2 qualification note a fee claim.

## Compatibility and limits

- `SourceEvidence`, compact/journal model output schemas, action counters, wall guard, search/page/provider policy and captured claim values are unchanged. Every eight-dimensional scope is still explicitly supplied; no scope field or target year is filled from the request.
- The existing default-off `FORM_LABEL_HEADINGS` flag remains false. No capture flag/default, Fetcher/browser/robots code or source request is changed.
- New dataclass fields have empty defaults; old construction callers remain valid. However, dataclass `asdict` serialization adds provenance keys (even empty), and genuine year locations change future evidence acceptance. This is a **new prospective source/manifest contract**, never a reason to mutate or rerun frozen V12 receipts under changed code. Future protocol snapshots must pin these source bytes; retain old snapshots for old replay.
- The academic year must be explicitly published at the cited structural location. A real 2026/2027 year remains 2026/2027; the patch does not establish fall-2027 applicability, negate the public applicant-year comparison, or omit inconvenient dates.
- It offers no remedy for Aalto's saved robots-disallowed empty reads. Search snippets and inaccessible payloads remain non-citable.
- DOM paths refer to the deterministic parsed original HTML tree, before dropped tags; they are structural coordinates, not invented raw-byte offsets. The original source hash and rendered literal text remain necessary to verify them.

## Synthetic regression draft

The two test-copy changes add **19 test functions / 39 parametrized cases**, all using synthetic HTML/controller payloads. Required cases cover:

- Explicit adjacent year label with exact source coordinates and unchanged quote/block ID; separate heading scopes; no navigation/control/hidden/unrelated/intake-derived label or footer inheritance.
- Exact same-row fee/year proof, including repeated equal amounts in different years; no join from another table or campus row.
- Blank, unknown, wrong, duplicate and merged Year cells; conflicting caption/page year; multiple adjacent year labels; no union or last-wins.
- Domestic/bachelor/master/programme/intake contradictions remain rejected despite matching year support.
- A literal wrong quotation year cannot be masked by a correct section label; no year is silently filled from the request; absent declared-year context still rejects.
- Q2/OTHER/Q4 failure messages retain original fact/question/source identity. Existing citation tests expecting the old generic fee-year wording are narrowly updated to the academic-year dimension; direct trace messages remain compatible ValueErrors.

Static-only evidence: AST parsing and Ruff check passed on the five `/tmp` candidate copies; original source hashes and all three completed audit hashes still match. **No pytest or type/runtime gate has been run**, so these are reviewable candidate/regression drafts, not a validated deployed repair.

Before applying after original V12 seal/export, run the candidate synthetic tests, unchanged catalogue-trace/public-question/applicant-intake tests, source-wide Ruff/mypy and app/evaluation gates in the prospective source. In particular, `test_found_question_scope_must_match_the_public_applicant_and_intake`, `test_found_answers_cannot_omit_their_required_scope`, `test_scope_cannot_be_copied_from_the_request_onto_contradicting_source_words`, and all existing literal-quote and ambiguous-HTML tests remain mandatory. Preserve raw source bytes and per-fact provenance; no threshold-driven semantic exception is proposed.
