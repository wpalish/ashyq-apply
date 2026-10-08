# Независимая проверка corrected full: ACCEPT с ограниченной областью

Проверены сохранённые originals единственного завершённого local full `20261008T085213Z-check-97246db0`. Все 13 шагов имеют фактический exit 0; terminal summary `passed`, 923.97619 s. 17 оригинальных файлов (5 697 217 bytes) совпадают с копиями root по SHA-256/размеру до и после проверки.

Оба JUnit содержат одинаковые 4369 уникальных identities, без failure/error/skip. Все прежние 4349 identities сохранены, добавлены ровно те же 20 `tests.test_local_pilot`; прежний неизменённый schema-equality node теперь PASS. SQLite: 4369 PASS, 459.67 s, app coverage 95.27%; PostgreSQL: 4369 PASS, 330.45 s, отдельной coverage строки нет. В каждом DB сохранены 32 warnings: 1 Starlette, 16 Markup, 15 XML parser; 30 parser warnings принадлежат новым synthetic live_discovery случаям.

Frontend unit 232 PASS; demo E2E 79 PASS + 1 viewport-specific desktop skip для phone-reachability test (тот же test в mobile PASS); auth 6 PASS. Ruff/checkformat/mypy охватывают app/tests/evaluation; format и mypy указывают 386 файлов. Audits exit 0 с отсутствием известных vulnerabilities. Mypy unchecked-body notes не удалены.

Все 1002 выбранных code/test/source paths физически совпадают между текущим repo, frozen snapshot и root map; source HEAD `eb81c127c8a2a5154dd0d6f7ac115d8dc4464288`, frozen tree `3da2152c711107623edd78f1e9f2cf41c36a58415df1bdc90494d63a0fc2ef84`, snapshot status clean. От первого FAILED full отличаются ровно models.py и test_local_pilot.py; остальные 1000 равны. Все шесть accepted source/test pins совпадают. Сохранённый trace.schema.json и старый test_expert_catalogue_trace.py не изменены.

Сохранённый corrected seed (28 selected originals) проверен без повторного исполнения: все 265 app/migration/script pins равны current/frozen/candidate; четыре сохранённых команды exit 0, единственная head/revision d8e412c6a901, 20 undecided rows, Groningen первый. UBC portfolio.bucket OUT_OF_BUDGET и funding FULL_TUITION — отдельные поля. Это synthetic compatibility, не подтверждение live quality.

Старый FAILED B-пакет и его 17 full originals неизменны: в каждом DB остаётся первоначальный 4368 PASS/1 schema failure. Предыдущие seed30 originals также неизменны. STOP `65b5ff0e…`/142 bytes проверен до и после.

Первый собственный stdlib verifier завершил все assertions, затем serialization receipt упал из-за отсутствия datetime.UTC в системном Python. Скрипт и ошибка сохранены. Отдельный compatibility script меняет только UTC на timezone.utc и завершился exit 0. Это ошибка собственного checker, не app failure. Ни app imports, ни tests/full/seed/SQL/CLI/network не выполнялись.

ACCEPT относится к exact corrected local source/full/seed binding. Hosted/container/production, live provider/model runtime, реальная OS isolation admission, owner fresh-cycle grant и качество поиска здесь не проверялись. Scoring/labels не открывались. Первоначальный full остаётся FAILED в истории.
