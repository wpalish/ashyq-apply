# T18 / A1 — ashyq-developer output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-developer
- INVOCATION_REF: agent_c4976b8f-fa4f-4a1e-852c-587b3cf2ee07 (real runtime agentId)
- STATUS: IMPLEMENTED
- QA_COMMIT_SHA: 18c4a901ad95fa59f9f83e3bbdae0e2d98436fea
- CANDIDATE_COMMIT_SHA: 9d328c4e81e25ed69a44e98e8f68a9f93431a984 (заморожен; не push/amend)

## CHANGED_FILES (diff-tree)
- backend/app/adapters/base.py — новый PageOutcome (url, category, page_type, detail, readable_chars) + AdapterResult.page_outcomes
- backend/app/adapters/extraction.py — KZT/₸ в обе позиции _MONEY + _CURRENCY_SYMBOLS; третья альтернатива _IELTS_OVERALL (band перед keyword, keyword строго сразу после числа); group(3) в extract_requirements
- backend/app/adapters/requirements/web_requirements.py — PageOutcome на каждую страницу: fetch-failed / unreadable / classifier-rejected (+page_type) / no-pattern-match / fetched-ok; counters не тронуты
- backend/app/adapters/cost/web_costs.py — те же исходы; unreadable 200-ответ честно считается pages_failed; classify_page только для записи (extraction не гейтится)
- backend/app/pipeline/runner.py — _record_page_outcomes + _page_outcome_line: parseable-строки «page <category>: <url> (page_type <t>[, N chars]): <detail>»; problems → run.errors, fetched-ok/no-pattern-match → run.unknowns; leases/fencing не тронуты
- backend/scripts/canary_discovery.py — page_outcomes()-парсер, per-institution page_outcomes/page_types/page_diagnostics, totals + печать разделения

## GATES
- ruff format/check → 0; mypy app → 0 (105 файлов); mypy app tests → 6 ошибок, ВСЕ pre-existing в QA-файле test_live_extraction.py:249-254 (session.get → ResearchRun | None, без None-check); подтверждено на чистом QA-коммите через stash → выносится как QA test-contract item
- pytest target → 187 passed (16 QA + 61 + 110); 11 RED→GREEN (TestTheRunExplainsItsPages ×4, TestKztTuitionVocabulary ×5, TestIeltsOverallWordOrder ×2); Guards 5 зелёные; RED на baseline воспроизведён лично (11 failed / 5 passed)
- seed_demo smoke: вывод идентичен baseline; Groningen #1 (0.7947), UBC OUT_OF_BUDGET подтверждены запросом; полный suite не запускался (heavy slot)

## CONTRACT_DEVIATIONS
1. KZT не потребовал domain-правок (domain/currency.py уже содержит KZT: 480.0; schemas/money принимает 3-символьную строку) — всё в adapters
2. fetched-ok записи → run.unknowns; problems → run.errors (существующие JSON-колонки)
3. Адаптеры больше не дублируют prose-строки проблем — PageOutcome единственный источник (рендерит раннер)
4. Acceptance «regex-срабатывания по странице» покрыт readable_chars + причиной адаптера (без отдельного счётчика regex-хитов)
5. Funding-stage страницы не категоризированы в этом slice (только verify-stage)

## MIGRATIONS: нет (существующие JSON-колонки research_runs.errors/unknowns)

## REMAINING_RISKS
- fetched-ok в unknowns увеличит счётчик «facts were not published» в ProgressScreen (frontend вне scope — копирайтинг отдельной карточкой)
- caps problems[:200]/unknowns[:400] — длинный прогон может терять хвост (как baseline-prose)
- canary-парсер привязан к формату строки (_page_outcome_line / _PAGE_OUTCOME_RE живут рядом)

## NEXT
QA verify 9d328c4e в отдельной worktree; QA-циклом починить 6 mypy union-attr в QA-харнессе (это QA-файл); canary-отчётность PILOT-ONLY: live-прогон вне slice не выполнялся.
