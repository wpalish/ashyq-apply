# G3 API mypy repair1 — независимое конечное чтение

Статус: **SOURCE_ONLY_QUALIFIED_FINITE_DELTA — NO_CONCRETE_BLOCKER — NO_RUNTIME_EXECUTION_BY_REVIEWER**.

Проверены только три разрешённых route hunks и их нативные зависимости. Приложение, AST, formatter, type checker, тесты и DB этим reviewer не запускались; source/lab/helper/Git/HANDOFF не изменялись. Это не полная повторная проверка API и не full/focused/native/product acceptance.

## Неизменные входы

- [Repair1 SEAL](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-mypy-repair1/SEAL.json): `5a04249a61128e56140e248fc054f3cd0a5afeeaafe5a0d23571a1f77dddcb3b`, все 11 членов сверены по SHA и размеру.
- [Format1 SEAL](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-mypy-format1/SEAL.json): `f9b68ccec0e4b2fafcdc44d66e6120c6f87b09a4beca90d9943871355a40a769`, все 7 членов сверены по SHA и размеру.
- Полный оригинал route: `6fc7ff0875fe496307bd0cf1d8964f85a5151c9b6a11f1b35e57a3aba6727040`.
- Полный postimage: `31c445bb51eabc2e51f3e9d5f4a8114a748432af33a4f9a6a3b0e03b5329d983`, 96 501 байт.
- Нативная preparation graph schema: `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249`.

Полностью прочитаны diff, manifest, README, сохранённый mypy output и formatter metadata; отдельно прочитаны `_current_pair`, `_load_current`, затронутый reason loop и две named native classes. Textual inverse трёх exact-one replacements восстанавливает **весь** оригинал по SHA; никаких AST сравнений или application imports для этой проверки не делалось.

## Три hunks

| Изменение | Проверка источника | Заключение |
|---|---|---|
| Импорт `DocumentAction`, `ProgrammeProjection` рядом с прежним `PreparationGraph` | Обе существующие native classes имеют `unresolved_reasons: list[ReasonCode]`, schema строки 219–248. Ни schema, ни defaults/validator не изменены. | Named imports соответствуют фактическим типам. |
| `_load_current`: `latest_revision is None` → прежний `saved_unreadable` | Guard стоит **после** неизменного absent-row return и **до** чтения state/head. `_current_pair` уже отказывает при current/history disagreement (237–269); новый guard явно сужает `int | None` перед `validate_current_snapshot`. | Fail-closed narrowing без cast/ignore/zero fallback/repair/reset. Отсутствующее состояние не превращается в искусственное current. |
| `observations: list[ProgrammeProjection | DocumentAction] = [programme, *actions]` перед прежним loop | Объекты, их порядок, все predicates и reason mapping/deduplication буквально сохранены. Оба union members предоставляют читаемый attribute. | Устранён ошибочно выведенный common `Base`; не ослабляет типы и не меняет reason semantics. |

Затронутый postimage: [route:363](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-mypy-repair1/files/backend/app/api/routes_admissions_actions.py:363), [reason loop:781](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-mypy-repair1/files/backend/app/api/routes_admissions_actions.py:781). Нативные типы: [preparation_graph.py:219](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/preparation_graph.py:219).

По полному byte-inverse все остальные route bytes сохранены: собственность, UUID replay, dirty-session checks, CAS/rollback, source/access authorization, UTC canonical headers, Today/export/history/metadata, безопасные ошибки и DTO. Тестовые assertions, конфигурация и другие paths не входят в этот delta.

## Сохранённая диагностика и formatting

В raw staticAPI2 predecessor: Ruff/format exit0, mypy exit1; **ровно два** error — optional `latest_revision` в строке 414 и common `Base.unresolved_reasons` в строке 780. Отдельные annotation-unchecked notes не скрыты. Source-before/source-after maps byte equal. Это старый диагностический результат, не PASS нового postimage.

Format1 содержит captured installed-native Ruff import-sort/format exit0 и логи `All checks passed!` / `1 file left unchanged`. Его `format-input` и final `files` byte equal друг другу и предложенному `31c445…`; **дополнительных formatting изменений нет**. Reviewer только прочитал и сверил сохранённые bytes/metadata, не повторял tools.

Parent сообщает, что route уже применён после write-ahead amendment и staticAPI3 прошёл Ruff/format/mypy406. Этот новый gate не выводится из predecessor и не исполнялся reviewer. Full/focused проверки этим отчётом не заявляются.

## Диспозиция

В конечном трёххунковом source delta конкретного блокера не найдено. Форматированный postimage идентичен проверенному. Источник подходит для root-owned последующих native gates; их результат должен сохраняться отдельно. Это не новый design freeze и не возобновление остановленных provider/model/quota/security/live/expert/heldout/controller работ.
