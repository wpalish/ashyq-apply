# T18 / A2 — ashyq-qa VERIFY_CANDIDATE output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE (A2 final)
- INVOCATION_REF: agent_3892a96c-fee4-4d4c-8432-65cb6de2c1f2 (real runtime agentId)
- STATUS: **VERIFIED_FAIL**
- CHECKED_SHA: ea4be635a585f16c0125ad8856b2a33ab400ee7a (ветка ai/c1/t18/verify; цепочка подтверждена)

## ПРИЧИНА FAIL
Полный suite: **1149 passed, 1 FAILED** (exit 1), coverage 92.91% ≥ 92. Отказ: tests/test_adapters.py::TestAdaptersAgainstTheCorpus::test_an_unreachable_programme_is_reported_not_skipped — `assert result.errors` → `[]`. Candidate убрал adapter-level prose-error (fetch-failure теперь только в PageOutcome), сломав контракт `AdapterResult.errors`, на который ассертит shared-тест ВНЕ allowed_paths T18 (не мог быть правлен developer). Тест не менялся (git log пуст). Детерминированный, воспроизведён дважды.

## GATES
a) target 187 passed exit 0; b) mypy 154 файлов 0; c) ruff 0/0; d) full suite 1149/1 FAILED exit 1, cov 92.91%; e) alembic+seed_demo exit 0 — Groningen #1 (0.7947), UBC OUT_OF_BUDGET подтверждены sqlite-запросом.

## ADVERSARIAL (27/27, PROBE_EXIT=0)
Precision: scholarship $500 не tuition; IELTS без числа — нет claim; USD/EUR goldens без изменений. unknown≠zero: no-pattern-match с причиной, 0 claims. PageOutcome: все 5 категорий на фикстурах. Regex-дельта OLD vs NEW — только заданные добавления; edge «in 2026 KZT» — pre-existing shape, claim не создаётся. Fencing: diff runner.py grep fenc/lease/_save → 0 строк. Canary parser — только unit-образно (live не запускался).

## SCOPE
diff 1e9f841..HEAD: ровно 6 production файлов + test_live_extraction.py + 8 фикстур qa_t18; models/migrations/schemas/domain отсутствуют — всё в allowed_paths. diff 9d328c4..HEAD: test_live_extraction.py 1 insertion. diff 18c4a901..9d328c4: только production, ноль тестовых правок — QA-тела не ослаблены.

## BLOCKERS / РЕШЕНИЕ ДИСПЕТЧЕРА
Вариант (ii) принят: developer A3 возвращает dual-write (prose errors + PageOutcome) в web_requirements.py/web_costs.py → новый candidate → повторная VERIFY с полным suite. Амендмент shared-теста не требуется.

## UNTESTED_RISKS
canary live не запускался (PILOT-ONLY); browser-tier/E2E вне прогона; funding-stage без PageOutcome (disclosed deviation).

## ЛОГИ
/tmp/qa_t18_verify_gate_{a,b,c1,c2,d,e}.log, /tmp/qa_t18_verify_fail1.log, /tmp/qa_t18_probe_result.log
