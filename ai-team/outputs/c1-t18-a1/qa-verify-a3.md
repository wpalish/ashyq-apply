# T18 / A3 — ashyq-qa VERIFY_CANDIDATE output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE (A3 — repair после A2 VERIFIED_FAIL)
- INVOCATION_REF: agent_179aa937-efab-4363-8da7-17ab2002cff1 (real runtime agentId)
- STATUS: **VERIFIED_PASS**
- CHECKED_SHA: e533d6229d67e04c05c9b1293c66a64d45d817a5 (ветка ai/c1/t18/verify-a3, чисто; цепочка 1e9f841 → 18c4a901 → 9d328c4e → ea4be635 → e533d622 подтверждена merge-base)

## GATES
a) test_adapters + test_live_extraction + test_live_regressions + test_live_discovery → 258 passed, exit 0
b) mypy app tests → 0 (154 файлов)
c) ruff check + format --check → 0
d) **ПОЛНЫЙ suite**: **1150 passed, 0 failed**, coverage **92.92%** ≥ 92 (A2 был 1149/1 FAILED — регрессия устранена)
e) alembic + seed_demo → exit 0; Groningen #1 (0.7947), UBC OUT_OF_BUDGET — sqlite-подтверждение
A2-regression test_an_unreachable_programme_is_reported_not_skipped → PASSED

## ADVERSARIAL (25/25 PASS)
1. Dual-write: HTTP_ERROR 404 → И prose в AdapterResult.errors, И PageOutcome(fetch-failed) — оба адаптера.
2. Все 5 категорий PageOutcome записываются; fetched-ok НЕ добавляет error-prose и даёт claim (tuition 2,500,000 KZT).
3. Precision: scholarship $500 → 0 cost claims; IELTS без числа → 0 claims; positive control IELTS 6.5 overall → 6.5.
4. Runner→canary roundtrip: строки _page_outcome_line матчатся _PAGE_OUTCOME_RE для всех 5 категорий.
5. Наблюдение (не breach): requirements no-pattern-match — только PageOutcome без prose (frozenset _PAGE_PROBLEM_CATEGORIES = fetch-failed/unreadable/classifier-rejected персистятся через run.unknowns); полный suite зелёный.

## SCOPE
diff ea4be63..HEAD: ровно web_costs.py (+7) + web_requirements.py (+8) — только out.errors.append рядом с PageOutcome. diff 1e9f841..HEAD: 15 файлов (6 production + тест + 8 фикстур), models/migrations/schemas/domain отсутствуют. Тесты не ослаблены: diff 18c4a901..HEAD по тестам = 1 insertion (mypy guard).

## BLOCKERS: нет.

## NEXT
e533d622 → reviewer/security на замороженном SHA → integrator. Открытые риски: canary live не запускался (PILOT-ONLY), browser-tier/E2E вне прогона, funding-stage без PageOutcome (disclosed).

## ЛОГИ
/tmp/qa_t18_a3_{targeted2,mypy,ruff1,ruff2,full,seed,adversarial3}.log
