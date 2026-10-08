# Primary-purpose ablation: диагностический результат, правило не готово

На 30 сохранённых HTML-страницах первоначальный native classifier точно воспроизвёл исходный отчёт B. Внешняя копия меняла только область проверки off-topic vocabulary: title и own identity вместо всех h1/h2. Исходный app source, STOP, Fetcher, провайдер и классы разрешённых читателей не менялись.

Изменились две страницы: Admission Services — IRRELEVANT → SCHOLARSHIP_INDEX; SGT People — IRRELEVANT → UNKNOWN. На странице приёмной комиссии после удаления Contact us барьер остаётся: subsidiary funding branch выигрывает приоритет. Requirements по-прежнему запрещены, и прирост core полноты не доказан. Один Contact us fix недостаточен.

Два synthetic recruitment counterexamples, чья own identity похожа на BSc Computer Science, после этой релаксации стали PROGRAM_DETAIL. Настоящий первичный Contact us остался IRRELEVANT. Поэтому broad primary-only irrelevant guard нельзя применять как безопасное правило. Это конкретные новые ложные разрешения в diagnostic ablation, а не ошибки исправленного production source.

Следующий classifier seam потребовал бы отдельного доказательства own academic/admissions purpose, subsidiary funding/contact boundaries и реальных downstream scope controls. Не включать ablation в приложение, CLI, живой прогон или default. Сейчас основная подготовка — сохранение строго подтверждённого provisional routing при native typed read_cap; async-cancelled Groningen и долговечное SQL сохранение остаются отдельными границами.

Повторение только локально: PYTHONDONTWRITEBYTECODE=1 /Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python /Users/wpalish/Documents/Codex/2026-10-07/x20/work/local-round11/root-primary-purpose-diagnostic/replay.py

Scoring, semantic labels, network/provider/model calls, app source changes: 0. Exa STOP сохранён; stopped cohort не оценивается.
