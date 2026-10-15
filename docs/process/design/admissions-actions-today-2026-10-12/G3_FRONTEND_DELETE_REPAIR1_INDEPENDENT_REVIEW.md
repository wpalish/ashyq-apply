# G3: независимая проверка ремонта удаления анкеты

**SOURCE_ONLY / finite F1 qualified / NOT_APPLIED_BY_REVIEWER / NOT_IMPORTED / NOT_RUN.** Конкретного блокирующего дефекта в двухфайловом ремонте не обнаружено. Это проверка исходников, а не подтверждение выполнения тестов, очистки реального браузера или готовности всего G3.

## Проверенный неизменный пакет

[DELETE repair1 SEAL](proposals/g3-frontend-delete-repair1/SEAL.json) SHA256 `2c7d73199aa4a691257d5d9a7af59797949e3f5de57f443b49db4c3a2e9e43bb`: все **12/12** членов совпали по SHA256 и размеру. Полностью прочитаны оба postimage, оба diff, manifest, README и относящиеся к ремонту полномочия. Preimage обоих файлов точно совпал с первоначальным foundation-пакетом `e48a39997f0295d91710525fa3d4a0c873cf00e1397433ffc23b2b52de4c7b01`.

| Файл | Preimage SHA256 | Postimage SHA256 |
|---|---|---|
| `admissionsActionsRecovery.ts` | `b95410e93644b93506e2891565b80ebf341ebb78d3c65cf18022f7c85a2e4f6c` | `e6ef9c02b45006c23d4a9cc8046c231455f362f159dfebe11b29e668cb55c86f` |
| `admissionsActionsRecovery.test.ts` | `fa441aaa3b641bb413e10662a84ea98cb59c3a434d7924832148cb4f7e84b6ef` | `d32d94425a55d374c065a574b72b8427b6acc2ac411f2127b3ad16c12f457c83` |

Полномочия ограничены отдельной защитой удаления и дополнительными тестами в этих двух файлах. Source, wire, Store, auth, G2 и прочие функции здесь не изменяются.

## Проверка поведения

1. **Поздний успешный DELETE A при открытой B.** Нативный [Store: switchCase](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx:364) меняет epoch/operation generation. [deleteEverything](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx:890) сохраняет A, ожидает DELETE, повторно проверяет владельца, очищает захваченную A и только затем проверяет obsolete generation на строке 904. Возможность переключения реальна; прежний обычный `active(binding)` был слишком строг именно для этого подтверждённого удаления.
2. **Отдельная, ограниченная полномочием удаления защита.** [deletionIdentityFailure](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-delete-repair1/postimages/frontend/src/lib/admissionsActionsRecovery.ts:473) проверяет текущий scope и независимый нативный `currentApplicantOwner()`, точную захваченную family/profile/generation. Текущая B/новый epoch допускаются только здесь. [deletionFenceFailure](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-delete-repair1/postimages/frontend/src/lib/admissionsActionsRecovery.ts:484) проверяет владельца по обе стороны чтений, прежний generation и точные fence/tombstone bytes. Чужая, повреждённая или заменённая authority не принимается и не перезаписывается.
3. **Точное семейство и изменённые данные.** Сканирование и чтения ограничивают кандидатов точным captured family, существующими лимитами и проверками own header/shape. [Удаление кандидатов](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-delete-repair1/postimages/frontend/src/lib/admissionsActionsRecovery.ts:593) сравнивает текущие bytes с захваченными перед удалением, повторно проверяет authority и проверяет отсутствие удалённого ключа. Изменённая запись, смена владельца/generation или сбой хранилища дают `residual_unknown`; новая запись не считается успешно очищенной.
4. **Tombstone и сохранение повреждённых остатков.** При собственной валидной authority успешный native DELETE позволяет поставить отдельный tombstone даже при недопустимом payload/index, сохранив эти bytes и вернув `residual_unknown`. Имеющийся foreign/malformed tombstone блокирует действие. Поздний alive initializer не отменяет отдельный tombstone. Ответ `tombstoned: false` после сбоя проверки не утверждает, что частично записанного маркера нет.
5. **Обычные защиты сохранены.** Байтовое сравнение подтвердило: helper строки **1–471** и весь suffix от `G3LegacyBrowserCandidateV1` неизменны. Read/journal/retry/command ACK продолжают требовать текущую собственную анкету и epoch; raw legacy marks не изменяются. Это не послабление обычной гидратации или отправки.

Нативный `currentApplicantOwner()` проверяет согласованность local/session owner и отклоняет signed-out/transition/stale tab; его исходник прочитан. Пины native seams: `store.tsx` SHA256 `81afb3fbe97ccd015d9755bfd1fe4079e57eae8bfd2a48363c308545842f272a`; `applicantStorage.ts` SHA256 `0a3230d223e5dbfc1ead6dbece478ce54c9ec6bc557493115716e5709818fd0e`.

## Тестовые контролы и граница результата

Удаление только добавленного блока postimage строк **228–343** восстанавливает **все оригинальные bytes** тестового файла. Старые assertions, helpers, значения и контролы не ослаблены.

Новые контролы содержательны: authenticated A→B с точной сохранностью B/legacy/unrelated bytes и прежним отказом обычных stale-A операций; wrong-case ACK; независимая смена владельца; пять повреждений fence/tombstone authority; четыре повреждения payload/index; смена владельца при scan и marker write; смена generation во время чтения entry; interleaved replacement intent. Итого **15 дополнительных случаев по чтению исходников**; это не pytest/Vitest collection и не PASS. Старые late initializer/late write/storage refusal контролы сохранены.

Вызов helper требует уже полученного успешного matching native DELETE и повторной проверки владельца. Переданный profile string и локальный marker сами по себе не доказывают серверный ACK. Подключение к actual Store и его интеграционный тест остаются следующим UI шагом; здесь они не выполнены.

LocalStorage не является транзакционным: `completed_best_effort` означает отсутствие наблюдавшихся остатков в финальных проверках, а не гарантированное атомарное удаление между вкладками. Пересчёт entry digest в синхронном DELETE отсутствует сознательно: authority здесь — успешное собственное native удаление и точные captured family/header/generation/bytes, не браузерная подпись доказательства удаления.

**Не закрыто этим ремонтом:** отдельные foundation F2/F3/F4 (ACK replay bytes, strict string literals, receipt association), actual UI hook, source-bound lint/type/tests/native gates и явная UX-политика retention при 64 UUID entries. Автоматический discard не добавлен. Оригинальные seals и источник приложения не изменялись; AST, imports, formatter, runtime, браузер, сеть, Git и HANDOFF не использовались.
