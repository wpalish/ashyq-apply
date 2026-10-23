# Применимость сохранения routing к двум текущим остановкам

Проверены исходные round10 raw/normalised/budget/capture файлы Toronto и Groningen. 6 физических утверждений совпали: у обоих внутренний бюджет выключен; Toronto остановлен RuntimeError после возврата 3 programme URL; Groningen остановлен CancelledError с 0 programme URL. Нативный source SHA в обоих:7c74a12d71bd00228014c11d194928d223e110be.

Toronto:60 Fetcher.get,6 запросов,99115ms, внешний BENCHMARK_PAGE_BUDGET_EXHAUSTED; Job queued; discovery trace уже существует, reader outcomes присутствуют, Claim records0. Предлагаемое сохранение при UniversityReadStopped(read_cap) не устраняет этот точный сбой.

Groningen:32 Fetcher.get,5 запросов,119020ms, source_work_deadline_exhausted и CancelledError; Job running, candidate/trace отсутствуют. Callback в памяти не переживает эту отмену и не является долговечным checkpoint.

Настоящий синтетический Worker/SQLite контроль A при NativeReadBudget=True может доказать будущий контракт cap60, но не рост текущего DEV результата или исправление этих двух сохранённых запусков. Нет ON replay этих кейсов, чтения gold, scoring, сети или изменения source/default. Неполный cohort остаётся UNSCORED.
