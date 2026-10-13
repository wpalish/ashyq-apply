# G3 API native import repair1 — независимое чтение

Статус: **SOURCE_ONLY_QUALIFIED_FINITE_TEST_IMPORT — NO_CONCRETE_BLOCKER — NOT_RUN_BY_REVIEWER**.

Проверен неизменный [пакет](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-native-import-repair1/SEAL.json), SHA-256 `4dd6a2a4d29146ddbcc7990044917b1ec387b91f39a0924cf466562b31f95728`: все 8 членов по SHA/size. Разрешён только `backend/tests/test_admissions_actions_api.py`.

Прочитаны весь двуххунковый diff, manifest, README, сохранённая focusedAPI1 диагностика и текущие native imports `main`, `db`, `security`, `conftest`; определение существующего cached `app.config.get_settings` находится в `config.py:387–391`.

## Причина и точное исправление

[Исходная диагностика](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g3-execution/evidence/backend-focused-api1/20261013T051922200074Z/sqlite/pytest.log) подтверждает `ModuleNotFoundError: app.settings` в API test строке 36; Today test получает тот же отказ через импорт API helper. Прогон остановился **при collection**, до исполнения тестовых тел. Две JUnit error entries — ошибки сбора модулей, не два выполненных теста. Сохранены cleanup logging `I/O operation on closed file` сообщения; они не выданы за исправленные этим импортом. Result сообщает source unchanged, shutdown confirmed/runtime removed; PostgreSQL phase не запускалась.

Diff только переносит один исправленный import:

- прежний `from app.settings import get_settings` удалён;
- `from app.config import get_settings` добавлен в native import group.

Это тот же существующий native cached settings callable, который используют `main.py:36`, `db.py:23`, `security.py:16`, `conftest.py:244/266`; нового settings/cache/config wrapper не вводится. Все обращения, fixture bodies, assertions, callbacks, skips, guards и конфигурация сохраняются.

## Полные byte pins

| Состояние файла | SHA-256 |
|---|---|
| Оригинал | `ecd23075788374447c2c96470dcd36b576dd207b18c4af1815ebf36392b6479c` |
| Exact-one исправление до root Ruff import sort | `695da565a357880843f28f972b43c07f6027b624ac31a877660db4c53273234d` |
| Конечный postimage | `af984816e28aa0af12f69c49eba8dff5d555c5804a4cbd7d887f5106440eea6a` |

Whole-file сравнение после удаления **ровно одной** затронутой import строки с каждой стороны даёт byte equality; точная одиночная substitution возвращает сохранённый format-input. Поэтому двуххунковое изменение не скрывает правок test bodies. Captured root formatter metadata сообщает import/format exit0; reviewer эти инструменты не запускал.

Конкретного source blocker в этом конечном исправлении не найдено. Нужен новый root-owned прогон collection/focus; старый collection failure не превращается в PASS. Приложение, AST, formatter, DB, тесты, Git, HANDOFF, source/lab/helper и остановленные provider/runtime работы этим review не запускались и не менялись.
