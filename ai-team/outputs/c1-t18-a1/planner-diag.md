# T18 / A0-diag — ashyq-planner diagnostics (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-planner
- INVOCATION_REF: agent_c095ad9b-e9ee-4676-b582-99a080082df5 (real runtime agentId)
- STATUS: PLANNED (diagnosis frozen)
- BASELINE_SHA: 1e9f841ba686d27fc28271f9592ad449c0b35004 (подтверждён по ref-файлам)

## CANARY_ROOT_CAUSE (Nazarbayev 35 pages / 0 claims)
Путь реализован: canary_discovery.py:380 → runner.py:287 _stage_verify → web_requirements.py:142 / web_scholarships.py:143 → persist runner.py:504,1033 (все claims вкл. UNVERIFIED; canary считает все ClaimRow 395-405).
- (a) ПОДТВЕРЖДЕНА — узкие regex: _MONEY/_CURRENCY_SYMBOLS (extraction.py:207-247) без KZT/₸ → KZT-страницы не дают money-claims вообще (web_costs.py:88-91 честный error, claim=0); _IELTS_OVERALL (180-184) требует overall/minimum/score of/band МЕЖДУ IELTS и числом («IELTS 6.5 overall» не матчится); _DEADLINE (214-220) требует keyword + прописанный месяц+год в 60 chars; year-gate web_requirements.py:37-55,211-224 требует целевой год в предложении; _claim_program_exists требует program_matches (matching.py:68-107).
- (b) ПОДТВЕРЖДЕНА как механизм — classifier-гейты: UNKNOWN accepted by nothing (page_classifier.py:12-13,90-91), гейт web_requirements.py:114 / web_scholarships.py:133, NAVIGATION при <1500 chars и >75% links (277-281), main_content на JS-shell (222-247). Конкретные исходы nu.edu.kz из отчёта НЕИЗВЕСТНЫ (см. слепоту).
- (c) ОПРОВЕРГНУТА — LLM в backend/app нет вообще; extraction_method всегда html_rule/pdf_rule/fixture («llm_assisted» — мёртвый литерал claim.py:47); тихих skip нет, каждый отказ пишет error.
- (d) ОПРОВЕРГНУТА — conflicts/hierarchy только понижают статус/перекрашивают, всё сохраняется (conflicts.py:47-169; runner.py:476-507).
- (e) ОПРОВЕРГНУТА путь выполняется, НО canary слеп: pages_failed только fetch-уровнево (canary_discovery.py:417-424), adapter-level failures (web_requirements.py:105-109) невидимы; page_types отбрасывается раннером (runner.py:448-452); «35 pages» включает robots/sitemaps (142-156); registrable_domain("nu.edu.kz")="edu.kz" (live_discovery.py:91-150 нет edu.kz в MULTIPART_SUFFIXES) → все *.edu.kz один домен.
ИТОГ: 0 claims = (a)+(b); «0 failed» = только fetch-уровень; для доказательства по странице нужен диагностический прогон с page_types/readable-length.

## CAPABILITY_MAP
- search_web: НЕТ (нет провайдера; BLOCKED до ключа — решение пользователя)
- fetch_document: ЕСТЬ (fetching.py:297+ Fetcher: robots, redirect re-validation, caps, cache, rate limit, PII guard) — живой HTTP работает без ключей
- render_page: ЧАСТИЧНО (browser.py:32 + эскалация fetching.py:449-465, MIN_USEFUL_TEXT=400; playwright+chromium не подтверждены в окружении; без них тихо возвращает исходный результат)
- read_pdf: ЕСТЬ bounded (extraction.py:63-74, 40 стр.)
- discover_official_domain: ЧАСТИЧНО (seed registry + sitemap; entity→domain resolution нет; edu.kz suffix баг)
- extract_structured_claims: ЧАСТИЧНО (детерминированный regex; узкий словарь; LLM-путь объявлен, не реализован — BLOCKED)
- verify_claim: ЧАСТИЧНО (нет независимого verifier-pass; статус по цитате/домену/specificity + conflicts + freshness)
- compare_source_versions: НЕТ (только content-hash TTL; diff/ChangeSet/supersession отсутствуют)
- evaluate_profile: ЕСТЬ (детерминированно: evaluate_program, funding_fit, admissions_fit, scoring, ranking)
- persist_evidence_and_schedule_recheck: ЕСТЬ (ClaimRow/ConflictRow/ProgramResultRow, next_recheck_at, recheck_stale)
- Прочее: WebGovernmentAdapter в live всегда fixture:// (web_government.py:16-18, runner.py:396 без override; corpus_dir=None runner.py:125) → government claims в live невозможны; падения fetch уходят в псевдо-домен government.

## TASK_MAPPING (этапы промпта → карточки)
1 диагностика → T18 (этот анализ + canary-диагностика); 2 vertical slice → T18; 3 news/freshness → НЕ ПОКРЫТО (нет NewsEvent/SourceChange/diff; T13 только TTL) → НОВАЯ КАРТОЧКА T26; 4 financial → T04-T08 (пробел: KZT/exotic currencies на стыке T18/T05); 5 refresh → T10-T13; 6 benchmark → T18 acceptance; 7 UI/release → T14/T19/T20/T22-T24.
НОВЫЕ КАРТОЧКИ (рекомендация): T25 search_web adapter + capability config (locks network-adapters, search-provider; deps T16; конфликт adapters/** с T18 — после T18); T26 News/SourceChange слой (locks runner, migrations, news-corpus; deps T11, T13, T18; allowed: models/**, runner.py, domain/**, migrations, tests/test_news*).

## SLICE_CONTRACT (заморожено)
- Типы не переименовывать: Claim/ClaimStatus/ClaimType/SourceSpecificity/FetchOutcome (claim.py, enums.py:55,90,317), PageType (page_classifier.py:25-39), DiscoveryTrace (live_discovery.py:466-508).
- unknown ≠ zero: отсутствие паттерна/страницы = unresolved/error, никогда «не требуется» (web_requirements.py:235-238, fetching.py:273-275); «0 failed» canary = только fetch-факт.
- Метрики раздельно: search yield / fetch success / extraction yield (runner.py:504-514; completeness знаменатель CORE_QUESTIONS фиксирован, 0/6=0%).
- Concurrency: per-host semaphore 2, delay 1.5s (fetching.py:46,487-490); runner-leases не трогать (T10/T11).
- Privacy: assert_no_pii на каждый request (fetching.py:545-556) — не ослаблять.
- WRITE_SCOPE: backend/app/adapters/**, backend/app/pipeline/runner.py, backend/scripts/canary_discovery.py, backend/tests/test_live*.py, backend/tests/fixtures/**, docs/LIVE*.md, docs/CANARY*.md. Расширения domain/currency.py (KZT) — через координатора (пересечение с T05 locks).
- ACCEPTANCE: (1) canary-прогон выводит page-classification/длину текста/regex-срабатывания по странице — root cause воспроизводим; (2) KZT-фикстура даёт tuition claim; «IELTS 6.5 overall» → 6.5; существующие test_live* зелёные; (3) отчёт разделяет fetch-failed/unreadable/classifier-rejected/no-pattern-match; (4) ни одного claim без original_text_excerpt+source_url (zero false-positive tolerance сохранена, canary_discovery.py:194-300).
- NON-GOALS: LLM/search-провайдер без ключа; browser против robots/CAPTCHA; изменения финансовых контрактов domain/ (T04-T08); News-слой (T26); переименование enum/схем; понижение cov 92.
- BLOCKED до конфигурации (решение пользователя): search API, LLM API, playwright chromium (проверить установку до заявлений).

## RISKS
1. Без canary-диагностики любой «фикс» — стрельба вслепую (acceptance 1 обязателен).
2. Regex-расширение → precision-loss (6+ false positives в audit); каждый паттерн с негативным fixture-тестом (QA RED → developer).
3. edu.kz suffix баг → cross-university контаминация discovery; правка затрагивает существующие тесты.
4. runner.py — serialized lock (T05/T06/T25/T26) — сериализовать координатором.
5. Не заявлять конкретный гейт nu.edu.kz без нового диагностического прогона (нет сохранённого JSON/page_types).
6. Live-верификация вне fixture не «проходит» без search API → отчётность PILOT-ONLY, BLOCKED-пункты отдельно.
