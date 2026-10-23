# Предлагаемая правка identity/programme query ledger

**Готовое внешнее предложение; в репозиторий не применено.** Frozen bytes совпадают с версией `d669fd2`, которую назвал владелец; последующий `9330929` менял только документацию. Git-команды экспертом не выполнялись.

[Implementation diff](identity-query-ledger.patch): SHA-256 `d36a6cd4a815c997d07883edad252913a855dc19851af41ea44d7e53b7516245`. [Standalone tests](test_identity_query_ledger.py): SHA-256 `8ff8b386f62ef51788d4e06b97656e67445014602499bdee7d3b434dacd95d6b`. [Test-addition diff](identity-query-ledger-tests.patch): SHA-256 `282dcd56a9dcc2aa3c029fcd9ae3673191f9cf0dd9b47b56f7ec97dc896f55bc`. Полные proposed module copies находятся в `source/backend/...`; [source-manifest.json](source-manifest.json) и [function-hashes.json](function-hashes.json) фиксируют файлы и функции.

## Интерфейсы и учёт

Identity search списывает одну попытку после успешного получения provider и до вызова seam. Factory error до вызова не списывается. Seed/registry page probe query не расходует. При израсходованном shared budget identity не вызывает даже factory. `_enrich` берёт больший из известных trace/candidate counts, переносит его до планирования и сохраняет при unknown/error identity.

`_discover_one(entry, profile, *, search_queries_used: int = 0)` получает новый необязательный keyword с default=0. Старые callers с двумя positional arguments совместимы. Single и multi programme planners при shared=True расходуют только `max(0, 6-count)`. При нуле retrieval пропускается; `queries_for(0)` не вызывается.

`discover_candidates(..., on_query_attempt: Callable[[], None] | None = None)` получает необязательный callback. Callers без аргумента сохраняют прежнее поведение. Programme adapters передают `trace.charge_search_query_attempt`, вызываемый непосредственно перед каждой seam-попыткой. Escaping обычный `SearchError`/`SearchProviderNotConfigured` поэтому не теряет count до возврата `RetrievalReport`. Post-report increments удалены, двойного списания нет. Catch/retry policy не расширяется: прежнее распространение ошибки и handling caller сохранены.

Legacy внутреннее имя `search_queries_sent` остаётся, но комментарий точно определяет charged seam attempts. `Candidate.search_queries_used` — такой же ledger. `DiscoveryTrace.as_dict` добавляет `search_queries_attempted`. `RetrievalReport.queries_run` также означает attempted families. Local wrapper rejection может расходовать консервативный budget без vendor вызова; эти поля не доказывают HTTP dispatch или paid spend. Vendor HTTP counter не создаётся.

Source default `SHARED_QUERY_BUDGET=True` сохранён. При explicit=False programme planners оставляют исторические шесть новых programme attempts независимо от identity search, но полный расход становится видимым. Count=0 даёт total=7, count=6 — ledger=13 при семи новых попытках. Это явно протестированная legacy-ветка, а не обещание cap=6 при выключенном BL-1. Caps 6/60/120 не повышены; SI-1 proofs/guard не меняются.

## Проверки

Финальные **50 сценариев** покрывают реальный `_enrich`→single/multi planner при count=0/1/6; seed/registry без charge; unknown/error identity; factory error; direct exhausted planner; перенос candidate count в свежий trace; реальный strict wrapper и429 latch; local-refusal telemetry; shared=False; ordinary SearchError/SearchProviderNotConfigured и in-memory cancellation count.

- Frozen source: **42 failed, 8 passed, 0.60s**, ожидаемый exit=1; [red-final.log](red-final.log).
- External callback proposal: **50 passed, 0.13s**, exit=0; [proposed-green-final.log](proposed-green-final.log).
- Ruff check: **All checks passed** для четырёх внешних source, теста и loader. Ruff format применялся только к внешним файлам.

Ранние результаты до callback (45 сценариев, 37fail/8pass →45pass) сохранены отдельно как история и не подтверждают финальную редакцию.

Воспроизведение из существующего `backend` окружения:

```sh
EXPERT_B_PROPOSED_SOURCE=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -o addopts='' -q -p no:cacheprovider --tb=short --basetemp /Users/wpalish/Documents/Codex/2026-10-07/x20/work/search-loop-round3/reviews/expert_b/proposed/pytest-red-review /Users/wpalish/Documents/Codex/2026-10-07/x20/work/search-loop-round3/reviews/expert_b/proposed/test_identity_query_ledger.py
EXPERT_B_PROPOSED_SOURCE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -o addopts='' -q -p no:cacheprovider --tb=short --basetemp /Users/wpalish/Documents/Codex/2026-10-07/x20/work/search-loop-round3/reviews/expert_b/proposed/pytest-green-review /Users/wpalish/Documents/Codex/2026-10-07/x20/work/search-loop-round3/reviews/expert_b/proposed/test_identity_query_ledger.py
```

External [conftest.py](conftest.py) при flag=1 загружает ровно четыре proposed modules под обычными package names; остальные зависимости берутся из frozen checkout. При flag=0 override отсутствует. Fake vendor/memory session, mocked probes и unrelated page stages изолируют I/O; socket guard запрещает real network. Test-addition diff не добавляет loader в repo: regression file использует обычные backend imports.

## Границы

Callback сохраняет in-memory attempt при cancellation до report, но candidate/trace могут ещё не вернуться и не сохраниться. Crash/cancellation, replay/resume и конкуренция не получают durable guarantee. Внутренний trace нового `_discover_one` после отмены может остаться недоступным `_enrich`. Полный persistent guard — последующая работа владельца; этот пакет не заявляет её завершения.

Existing Capture.config не сохраняет effective SHARED_QUERY_BUDGET в normal/pre-start STOP envelopes. Это отдельный provenance пробел, сообщённый владельцу; bounded diff не меняет live.py или frozen captures. В дальнейшем нужно записать runtime flag: source default=True отличается от CLI default=False.

Все четыре source SHA совпали до/после. Network/provider/CI requests и Git-команды эксперта — **0**; gold/heldout не читались и не менялись. Sticky общий STOP после сообщения владельца об отказе GitHub Actions сохранён. Полные local gates и применение diff выполняет владелец; 50 proposal tests не заменяют release gate.

| Файл | Frozen SHA-256 | Proposed SHA-256 |
| --- | --- | --- |
| `backend/app/catalogue/discovery.py` | `b2f057bc90831ea465c35561e710ad4cded038e88c45a629f34c2bccf226daab` | `717ea35eaddadc5b3db7a10c3b92280e6beb137f46b3bbffeadec46c08572b02` |
| `backend/app/adapters/discovery/live_discovery.py` | `b1d7e8f34a3cb59a3a93a1606aee191256e32f5d08e4ba71bc08d75a03521c4f` | `4c53f906dbe09471138a34aa752ad64fc62acc44043f50e9d8ccfb99d6650068` |
| `backend/app/adapters/base.py` | `5b7a509c97e01d3e5b539ea0b2ebc15aeaae743a36ac1cf3ff803a198e1631f7` | `68355f99ee62ea2eefac63a7b991b057b16c374a26a9b1b210a0a07cad1e9637` |
| `backend/app/adapters/search/retrieval.py` | `ccbe3611602762f8f9ff3729bc75e76bbce7b9a04388e74ae561e996a46e1d7b` | `5a909e274fb4861b60209409b08fd51ef8febacc0d6021a38326335740512034` |
