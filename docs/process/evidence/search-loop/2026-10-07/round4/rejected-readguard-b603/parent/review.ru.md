# Родительский разбор READ-кандидата

Pinned b603fe6a/c09219f0 отклонён до переноса исходников: независимые реальные SQLite controls показали стирание durable count60 и 61-й get; реальный verification caller при занятой БД теряет typed stop и выходит с OperationalError. ZeroIO и ранее сохранённые факты подтверждены; durable unknown под удерживаемой блокировкой не подтверждён.

Обычный Worker не запускает повторно тот же Job/attempt в штатном claim пути; stale takeover проверен свежим fence. Искусственная mixed-mode гонка не доказывает штатную достижимость. Это не основание заявлять универсальную сохранность счётчика. Единственный присваиватель settings_snapshot в app — runner; whole-JSON замена до locked save и autoflush требуют проверки. Current canary не создаёт Job и не годится для guard-on production evidence.

B готовит отдельную v2 с сериализацией замены JSON и typed busy propagation. A receipt/raw/report frozen; файлы SQLite runtime/DB/WAL/SHM не архивировать. Production PG, source-toggle intent, 120s и durable queries остаются открытыми.
