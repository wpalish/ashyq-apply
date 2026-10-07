# Prospective year-context V2 candidate

This is a `/tmp` delta from the preserved V1 candidate. This agent has not applied it to the repository. The five original copies remain the exact V1 bytes. `candidate.patch` includes all changes; `source.patch` contains only DocumentIR/models changes; `regression-draft.patch` contains only tests. `citations.py` is retained byte-identically because its existing `asdict` proof and original-question feedback already consume the new metadata. `manifest.json` records every path and SHA256.

## Scope and provenance

- `SectionYearLabel.container_dom_path` and `EvidenceBlock.semantic_container_dom_path` bind the label and cited block to the same nearest explicit `main`, `article`, `section`, or `body`. A labelled section cannot supply the year to a different unheaded section. Equal heading text is insufficient. Nested ordinary div wrappers in the same semantic container remain valid.
- Original coordinates are assigned in one traversal before source tags are removed. This avoids the previous per-cell scan over earlier siblings. Paths retain the existing tag/ordinal syntax.
- Labels, Year cells and Year headers check hidden, navigation, footer, masthead, form/control ancestry and descendants. Explicit `hidden`, `aria-hidden`, known hidden classes and inline `display:none`/`visibility:hidden` are rejected. No external stylesheet or browser rendering is inferred.
- Year header references accept the actual BeautifulSoup list-valued `headers` attribute. Presence is authoritative: empty, unresolved, duplicate-ID, duplicate-reference and non-Year references cannot revert to positional Year classification. These failures remain recorded as `RowYearCell.blocked_reason`, so a matching page label cannot rescue them.
- Year source text and visibility are captured before dropped forms/control content can erase an unusable original Year header. Original text is retained for provenance; the blocked reference is never admitted as support.
- `RowYearCell` adds source kind/tag/scope, header origin, exact header DOM paths and blocked reason. A real Year `<th scope=row>` has no value-block ID by design. It is supported through its original row/header coordinates; an implicit row header additionally has to occur in the selected fee's existing row-header context. Ordinary Year value cells still require the exact same-table/same-row value block. Nontrivial Year-value rowspan/colspan and multiple competing Year sources remain rejected.

The join remains academic-year-only. It does not fill or change programme, campus, applicant, qualification, degree, intake, value or quote. The existing scope reader, default-off capture flags, raw source authority and exact quotation constraints are unchanged. The root's two test phrase corrections are included verbatim (`Domestic applicants in a bachelor programme tuition`, `International applicants in a master programme tuition`); no new prose parsing rule was added.

## Verification and red/green application

There are 48 additional parameterized cases in 16 new test functions beyond the V1 synthetic regressions. The manifest contains the exact per-file inventory. Root should first apply the added negative/positive tests to the initial actual candidate, preserve that red, then apply the V2 source copies and run the full citation/DocumentIR gates plus transitive typing. Existing V1 tests and root fixture corrections must remain.

Candidate-only checks passed 48 DocumentIR cases (one unrelated extraction-import test deselected) and 13 year-helper scenarios using an isolated fake `app` import, BeautifulSoup, and AST-extracted helper functions. They never import the actual repository runtime. Five candidate files pass AST and Ruff. DocumentIR passes isolated mypy with dependency imports skipped. These checks are not a claim that the full actual citation/runtime gate or transitive typing has passed; root owns those.

Preserved logs include the initial isolated-harness AST setup failure and first mypy variable-shadowing failure, plus their final green logs. No university data, labels, models or network requests were used.

## Deliberate limits

This candidate constrains the new year-provenance join. It does not redesign the legacy textual `section_path` stack or general HTML rendering. A body without semantic boundaries is treated as one container; missing structural provenance is never repaired by target-year inference. Year-value spans stay conservative. No prospective improvement is added to V12 primary facts, diagnosis or score.
