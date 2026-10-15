# G3 API route-only mypy repair1

Status: **NOT_APPLIED / NOT_IMPORTED / NOT_FORMATTED / NOT_TYPECHECKED / NOT_RUN**. This external packet contains one application postimage only; root owns application and all later native gates.

## Authorized finite delta

Root HANDOFF §5 write-ahead `2026-10-12T17:56:07.451075+00:00` grants only `backend/app/api/routes_admissions_actions.py`. Current exact preimage is `6fc7ff0875fe496307bd0cf1d8964f85a5151c9b6a11f1b35e57a3aba6727040`.

The retained native staticAPI2 result reports Ruff/format exit 0, mypy exit 1 with two diagnostics in this route (406 checked source files), before/after source equality. Copied raw source maps are independently byte-equal. Those are predecessor results, not qualification of this proposed postimage.

1. After `_load_current`'s unchanged `row is None` return, explicitly reject `latest_revision is None` with the existing `saved_unreadable` error. `_current_pair` already rejects a present row whose revision differs from the latest event revision, so the explicit guard narrows the returned optional integer without a zero fallback, cast, coercion, ignore, reset or changed receipt.
2. Add the existing native `DocumentAction` and `ProgrammeProjection` imports and type the existing `[programme, *actions]` list as `list[ProgrammeProjection | DocumentAction]`. Iterate that named list. Both existing native classes declare `unresolved_reasons: list[ReasonCode]`; list membership, predicates, order, mapping and reason deduplication remain identical.

Diff: `diffs/backend/app/api/routes_admissions_actions.py.diff`, exactly three hunks. Postimage SHA256: `31c445bb51eabc2e51f3e9d5f4a8114a748432af33a4f9a6a3b0e03b5329d983`.

## Source-only preservation

A textual inverse replacing precisely the one import line, the explicit two-line guard and the typed-list/two-line iteration returned the complete original SHA256 `6fc7ff0875fe496307bd0cf1d8964f85a5151c9b6a11f1b35e57a3aba6727040`. Exact-one occurrences were checked. No AST, source import, lint, formatter, type checker, collection or test runner was executed by this producer.

All other bytes, including ownership/replay/CAS order, dirty-session handling, history/export, source/access checks, Today adapters, error codes, scopes and route DTOs are preserved. No tests, native schema/configuration/guard, source/lab/primary, Git, HANDOFF or runtime helper was modified.

## Exact retained source/evidence references

- Native preparation graph schema: `backend/app/schemas/preparation_graph.py`, SHA256 `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249`; `DocumentAction` lines219–231, `ProgrammeProjection` lines234–248.
- Root AGENTS at read: SHA256 `a28ea0f3c275f54e431169082e27aec5f156d048d30ad617c8a21d0021cc2f69`.
- Root HANDOFF at read: SHA256 `cd88517d23b051889ce1eb08654e915ca3986801392dee3d984c70fb55589050`, finite authorization at line2493.
- Preserved predecessor evidence directory: `raw/backend-static-api2/` contains complete Ruff/format/mypy logs, result and source-before/source-after maps. Raw mypy SHA256 `9cdadd5693738616f65271de21194707cbc5dc3a43572e1f0d695368fac891ab`; raw result SHA256 `da0f8c4d48675b362fa90a011cfb33119cf26030338fc084e40433b522bd7ee2`.

Next authorized root step is ordinary source review followed by narrow installed-native route import/format, route-only application and new source/helper pins. This packet asserts no new gate pass, runtime acceptance, release, CI or deployment.
