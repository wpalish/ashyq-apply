# Объединение исправлений Unimatch — 11 октября 2026

Статус: **локальное объединение выполнено и проверено, готово к ревью**. Отдельная ветка task/product-audit-integration от origin/task/product-privacy-diagnostics@aa02d5fc; проверяемый код d69de643. Исходная рабочая копия другого автора не менялась. Main и сервер не изменены.

## Изменения
47 файлов перенесены только после точного совпадения с базой. Discovery объединён трёхсторонне с актуальными исправлениями безопасной диагностики. Export объединён отдельно: поздние Show/Download не возвращают старые данные после начала переключения или подтверждённого удаления; подтверждение принадлежит текущему делу; сохраняется только собственная квитанция удаления. Добавлены шесть наблюдаемых проверок epoch/ACK. Старые тесты и входной v3-патч сохранены.

## Фактические проверки новой версии
| Проверка | Результат |
|---|---|
| Ruff / format / mypy | PASS; mypy363 файла |
| Frontend typecheck / lint / unit / build | PASS; **433 теста**, 0 отказов/ошибок/пропусков; 2 lint warnings |
| Full backend SQLite | **4523 PASS**, 0 FAIL/ERROR/SKIP; покрытие95.43% |
| Full backend PostgreSQL | **4523 PASS**, 0 FAIL/ERROR/SKIP; покрытие95.42% |
| Native Demo browser | **79 PASS +1 существующий SKIP** |
| Native Auth browser | **6 PASS** |
| Native demo CLI / portfolio | PASS; Groningen первый, UBC OUT_OF_BUDGET |

SQLite/PostgreSQL повторяют один набор идентичных testcase IDs; числа не суммируются. Явные native SQLite/PG fixtures сохранены; PG-фаза меняет default Settings DB, не обещает каждый тест на каждом диалекте. Покрытие92 и assertions не ослаблялись. В обеих backend-фазах outside/startup attempts0, before/after одинаковы, собственные PG runtimes удалены. Native браузер использовал действительный API/worker, отдельные синтетические базы и provider=none; исходники совпали до/после, собственные порты освобождены. Демо использует локальный корпус и не подтверждает качество живого поиска.

## Сохранённые диагностические отказы
Первый импорт helper на Python3.9 остановился до выполнения: datetime.UTC требует существующий Python3.12 runtime. Первичная проверка отклонила sole tracked zero-byte backend/data/.gitkeep; разрешён только этот пустой nonsymlink placeholder, реальные данные/неизвестные файлы по-прежнему запрещены. Первый E2E не стартовал: sandbox разрешал старые порты; заменены только четыре localhost-литерала, native tests не менялись. Первый demo CLI правильно отказал немигрированной новой тестовой БД; новая БД сначала мигрирована. Затем root-inspector неверно искал bucket внутри payload: исправлен на отдельную row.bucket колонку. Все первые результаты остаются отказными, исходники приложения этими исправлениями не менялись. Полные backend gates после изменений внешних browser/seed helpers повторно не запускались, поскольку app/native source bytes не менялись.

## Границы
Это готовность ветки к ревью, не main merge, CI или production acceptance. Предшествующее независимое финальное принятие приватности остаётся PENDING; quota-stopped collector/reset safety stop не возобновлялись и не заменялись. Остановленный provider experiment UNSCORED сохранён; свежая factual quality NOT_MEASURED. Тарифы/SMTP/legal consent/retention и полная production-проверка остаются отдельными задачами. Старый просмотр5219 не заменяет доказательства этой версии.

Все сохранённые журналы, JUnit, source pins, покрытия, отрицательные OS probes, собственная cleanup и helpers: [EVIDENCE_INDEX](evidence/product-integration/2026-10-11/final/EVIDENCE_INDEX.json). GitHub Actions не запускались; checkpoints используют skip-ci, required statuses не подделаны.

Полный git diff --check сообщил whitespace только в четырёх оригинальных raw log путях (SQLAlchemy query trailing space и native blank EOF). Bytes/hash originals сохранены; отдельная проверка authored backend/frontend/HANDOFF/report diff завершилась0. Это не отказ native gates и не исправление исходного журнала.

Draft PR: [#80](https://github.com/wpalish/ashyq-apply/pull/80), dependent base task/product-privacy-diagnostics. Main merge/deployment остаются отдельным этапом.
