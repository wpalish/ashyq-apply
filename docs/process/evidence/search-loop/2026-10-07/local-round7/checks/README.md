# Локальные проверки зафиксированной версии

Doctor 5/5, core 8/8, full 13/13 PASS. Core и full проверяли HEAD
2a11d5b4089213d4c0c5b76ad5535a28ad00516e и одинаковый snapshot SHA-256
ccfe1bb12ef25b4067d6e1657c630df69014dcffcf98af7b151325ca9ec02388.

Команды из prepared local-runner:
`./local.sh --repo /Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply doctor`
`./local.sh --repo /Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply check --suite core`
`./local.sh --repo /Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply check --suite full`

Full: 4077 backend tests на каждой из двух БД, 95.07% SQLite coverage,
232 frontend tests, 79 demo E2E passed / 1 skipped, 6 auth E2E passed.
Pip/npm audit: известных уязвимостей 0. Docker/container gates не выполнялись.
Это локальные проверки кода и demo/auth, не качество живого поиска,
публикация или hosted required status. Старый мобильный timeout сохранён;
успешный новый прогон не устанавливает его первопричину.

Сохранены только summary/manifests, полные этапные logs и JUnit. Private Git,
Node dependencies, PostgreSQL/SQLite runtime, WAL/socket и browser runtime не
публикуются. Полные browser artifacts остаются в исходной local-runner папке.
Fixture-contract review воспроизводит старую ошибку `_Result.is_pdf` и
исправление через реальный FetchResult; исправление пока не применено.
