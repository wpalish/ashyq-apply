# G2 native review: дополнение о применении двух исправлений

**APPLIED_BY_ROOT / NOT_RUN_NATIVE.** Проверка только metadata и source bytes, без imports, Git, тестов или runtime.

Исходный [отчёт](G2_NATIVE_CONTROL_SOURCE_REVIEW.md) SHA `6b6b96131741a76b139fd92416bd46a5ae65624972520c592f21fc0d88dd2ffe` сохранён неизменным. Его F1/F2 и diff относятся к **первоначальному audit source**, сохранённому root в [preimage](../G2_NATIVE_EXACT_REFERENCE_PREIMAGE.ts): SHA `cd8335334d4f80b2dbc01f118f39088a9745f6898348887641addf9f5efacdcd`.

Root применил ровно две предложенные корректировки и сообщил commit `26766a3d`: выбор own-review по полному `savedAttemptId`, ожидание endpoint с `/review`. [Текущий source](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/e2e/preparation.spec.ts:617) имеет SHA `c2e386d225e916f4c145da060ee01a43c6adca3b3f3c7aabdb48f18d9853e40e`. Побайтовое применение только этих двух literal substitutions к исходному preimage полностью совпадает с текущим файлом; UUID/receipt/assertions сохранены. Root [metadata](../G2_NATIVE_EXACT_REFERENCE_POSTIMAGES.json) согласуется с обеими SHA.

**Поздние pins в исходном отчёте уже захватили исправленные bytes `c2e386…`.** Их нельзя читать как доказательство, что F1/F2 ещё присутствуют в этом current source. Для исправленного файла эти два source findings закрыты; браузерное подтверждение остаётся pending.

Auth source неизменен: `3ce4835ea7acf0ce36a63a842b23021fcd4b148045a4511c02afe71e3efa69a5`. Git HEAD здесь независимо не проверялся. [Подробная metadata-проверка](G2_NATIVE_CONTROL_SOURCE_REVIEW_ADDENDUM.json) закрепляет chronology и bytes. Старые report/pins/seals и application source этим агентом не переписаны.
