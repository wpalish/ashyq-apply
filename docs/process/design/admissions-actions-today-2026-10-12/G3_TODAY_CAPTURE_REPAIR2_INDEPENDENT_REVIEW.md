# G3 Today capture repair 2 — независимый finite review

**SOURCE_ONLY / NOT_IMPORTED / NOT_RUN.** Блокирующих дефектов в двух заявленных заменах не обнаружено. Это проверка внешнего test-only пакета, не новый результат выполнения и не qualification приложения.

## Что проверено

- [Пакет](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-today-capture-repair2/SEAL.json): SHA-256 `7094ec37d187c26b7f1440dcafc5d7a1a08c6dd4843df2776c47bfa14c72cabd`; все четыре member SHA/size совпадают.
- Today preimage `2505c188aeb0d37eea2cdd4762a57279500e9e98d979cebad1175abaf958693b` → postimage `90524775eeb24774fa55fde0a10b3a3bd499bd9cc5665d2a6cb6718f866b93bc`.
- Полный unified diff совпадает с файлами. Forward application и literal inverse ровно двух замен восстановили точные postimage/preimage. Других изменений/ослабленных assertions нет.

## Причина фактического отказа

[Сохранённый focused3 log](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g3-execution/evidence/backend-focused-api3/20261013T062658735530Z/sqlite/pytest.log) и JUnit содержат 192 cases: 190 PASS, 2 FAIL, 0 errors/skips. Оба отказа — `test_one_real_metadata_recheck_withholds_mixed_joins_and_clears_newly_locked_proof[sqlite-decision]` и `[postgres-decision]`, точный read-count `3 == 2` на строке571. В обоих traces виден дополнительный SELECT full ProgramResultRow по первичному ключу. Это параметризованные SQLite/PG controls внутри сохранённой outer diagnostic phase; отдельный outer full PostgreSQL gate из этого не следует.

[Native _capture:84](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph_api.py:84) ставит engine-wide before_cursor_execute listener и сохраняет SQL всех соединений engine. [interleave_once:251](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_admissions_actions_api.py:251) после выбранного реального чтения запускает callback во второй factory Session, предварительно ставя fired=True. Исходный callback `session.get(ProgramResultRow, result_id)` читает всю native строку, включая checklist; этот тестовый SELECT попадает в неизменённый engine-wide premium_queries filter. Сохранённые traces и исходный код подтверждают эту причину; счётчик нельзя автоматически считать третьим premium чтением приложения.

## Почему узкая замена сохраняет контроль

1. Импортируется native sqlalchemy.update; единственный decision callback вместо загрузки ORM-строки делает реальный targeted UPDATE по тому же result_id с тем же user_decision="rejected". ProgramResultRow native mapping имеет checklist JSON и user_decision String; payload/checklist новый UPDATE не читает и не подменяет.
2. Вторая независимая Session, session.commit(), точка interleave после настоящего premium SELECT, пять параметров гонки и fired/callback_result assertions неизменны. Callback продолжает физически менять сохранённый decision до terminal recheck.
3. Не меняются mixed_revision/needs_refresh/notices, cards=[], application summary, unknown workload/null minutes, research-lock redaction, g3 native snapshot checks, refreshed component_reads и неизменность после чтения.
4. Exact premium read-count **==2** остаётся исходным. Не добавлены фильтрация тестового SELECT, mock ответа, skip/xfail, retry, ослабление результата или production-code изменение.

**Disposition:** source-only finite repair принимается к root application и штатному повторному gate. Постimage ещё не выполнялся этим reviewer; PASS исправленного теста, полнота regression, FE/native readiness здесь не заявлены. Только новые report/seal записаны; первоначальный пакет, приложение, lab, runtime, helpers, Git/HANDOFF и STOP границы сохранены.
