# T33 A1 — Reviews (both on frozen candidate 540e3567f78e0bbe4be1da3cd3319ae086e3ca8c)

## Reviewer (agent_89d41721-89ab-43a1-9f0d-856101b9bb37) — VERDICT: PASS

SHA pinned via ref + reflog. ACCEPTANCE_MAP: все пункты покрыты (RED на baseline 3+1 scan-params; projection byte-identity routes_results.py:303,347; export free-ветка routes_profile.py:313-375 + counts живые запросы; 17-route scan green; GREEN-guard purchase). PD-1/2/3/4 реализованы как решено. Diff реконструирован независимо: tenancy сохранена (access_for_run → owned_run), persist-before-project (row.payload ПОЛНЫЙ до проекции), aliasing отсутствует (model_copy(deep=True)), allowed-ветка export байт-идентична baseline.

FREE_VIEW_HARDENING_RULING: costs.source_urls=[] корректен (CostBreakdown единственный обязательный, default_factory для legacy); остаток Money.source_url (money.py:28; web_costs.py:105-110) и RankingEntry.url (result.py:43) — вне замороженного словаря, PRE-EXISTING → ПРИЕМЛЕМО как residual; расширение обрезки — новое контрактовое решение (внести в реестр диспетчера, не молча).

Nonblocking: docstring free_view шире факта (entitlements.py:80-82); developer.md numstat занижен (реально 64/27, 11/4, 4/1). Untested → интегратору: full --cov sweep, frontend gates, pg-suites.

## Security (agent_be7d52d2-401b-4790-89de-3088a6907595) — VERDICT: PASS

SURFACE_EXHAUSTIVENESS: все 13 модулей маршрутов + 18 payload-разыменований перечислены; таблица всех материальных маршрутов OK; вне двух префиксов материальных маршрутов НЕТ. Скан-пробелы (RunView-маршруты /recheck /retry /get_run — только метаданные/retry_urls, без материала) — LOW residual, тикет #2.

BYPASS: 10 сценариев — все закрыты/невозможны (fix verified at routes_results.py:303/:347; no aliasing; cross-tenant 404; PD-4 без cross-profile эскалации; payments_enabled=False регрессии нет; webhook-грант не тронут).

RESIDUAL_LEAKAGE: item-level URL-поля (Money.source_url/RankingEntry.url/program_url) — low-moderate, вне словаря, тикет #3; counts (PD-2) — принято (соответствует открытому /summary); RunView/audit-детали — метаданные.

NEW_FINDINGS tickets: T33-F1 MEDIUM (контрактный): free-экспорт обходит free_shortlist_rows=5 — free-орг видит ВСЕ строки (имена/стоимости/рейтинги) — решение владельца: триммить или принять; T33-F2 LOW: scan пропускает RunView-маршруты (202-с-телом; обоснование "202 без материала" неточно); T33-F3 LOW: словарная поправка (Money.source_url и др.); T33-F4 LOW (pre-existing, ops): /recheck /retry не гейтятся и не лимитятся (middleware покрывает только POST /api/runs) — compute-abuse вектор.

Required extra tests (QA, non-blocking): cross-tenant decision/notes → 404 явный; mixed-профили на write-маршрутах; scan-расширение на RunView; trim-решение по T33-F1 если принято.
