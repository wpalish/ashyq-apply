# T04 / A1 — ashyq-planner output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-planner
- INVOCATION_REF: agent_9a4c22d6-be95-45b5-9460-b4019184b6be (real runtime agentId)
- STATUS: PLANNED
- BASELINE_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (подтверждён по ref-файлам worktree c1-t04-qa)
- FINDING_IDS: F01 (F02/F03/F04 — T05–T07)

## ROOT_CAUSE
- costs.py:25-76 total_cost(): реконструированная сумма известных категорий неотличима от published полного COA; нет состояния complete/partial, нет перечня отсутствующих категорий.
- costs.py:106-268 compute_funding_gap(): трактует частичную сумму как полный annual cost (строки 114, 215); неполный набор категорий не входит в условия отказа; category_mismatch только для FULL_RIDE_CONFIRMED (201); residual_positive=0 не добавляет warning (241-245) → computable=True, gap=0, warnings=[] для tuition-only+award.
- schemas/result.py:133-137: отсутствие ключа в items семантически не используется; FundingGap (141-155) без basis/missing.
- Смежный усилитель вне write-scope: runner.py:561-582 передаёт частичную сумму в classify() (residual → T05-T07).
- Потребители: scoring.py:126-170, ranking_v2.py:442-453,533, routes_results.py:71-96, tabular.py:111-118, entitlements.py:91, seed_demo.py:78-84, FundingScreen/ShortlistScreen/ApprovedScreen.

## CONTRACT (кратко; полный в отчёте)
- FundingGap аддитивно: cost_basis: Literal["published_total","itemised_complete","itemised_partial"] | None = None; missing_categories: list[CostCategory] = [].
- basis=partial → computable всегда False, gap=None, gap_low/high=None, total_cost = known subtotal (lower bound), reason/warnings называют missing.
- known zero = ключ в items с Money(0) — валиден; отсутствие ключа = missing.
- Обязательные категории = существующий CORE_COST_CATEGORIES (tuition, mandatory_fees, housing, meals); опциональные расширения не делают partial. Published total авторитетнее реконструкции.
- computable-гейт потребители демотируют partial в unknown affordability (ranking None, API sort после computable, export "not computable").
- Схема БД не меняется (payload JSON); legacy dict валидируется с дефолтами; после model_dump поля обязательны → types.ts FundingGap дополняется обязательными полями.
- Сигнатуры total_cost/compute_funding_gap не меняются (runner.py:561,750 не трогаются — лок T10).
- Rollback-окно: extra="forbid" (result.py:29) — payload новой версии не читается старой.

## ACCEPTANCE (кратко)
1. F01-сценарий: computable=False, gap=None, basis=itemised_partial, missing ⊇ {housing,meals,mandatory_fees}, subtotal=10000, warnings непусты.
2. Known zero ≠ missing: все 4 core с meals=0 → complete; без ключа meals → partial, missing=["meals"].
3. Published total → published_total, прежние правила (UBC OUT_OF_BUDGET путь).
4. Legacy round-trip + test_frontend_contract зелёный + seed_demo порядок.
5. Обновление 3 существующих тестов test_costs.py на полный basis (перенос fixture, assertions сохранены).
6. test_pipeline.py:178-182, test_api.py:876-880 — без правок.

## WRITE_SCOPE
- backend/app/domain/costs.py (ядро), backend/app/schemas/result.py (2 поля), backend/app/schemas/money.py (зарезервирован, правок не ожидается), frontend/src/types.ts (FundingGap), frontend/src/components/ResultDetail.tsx (partial-отображение), backend/tests/test_costs.py, backend/tests/test_funding_classification.py (ожидается без изменений).
- financial_policy.py НЕ существует на baseline — не создаётся (non-goal).

## RESERVATIONS / DEPENDENCIES / RISKS
- Локи: financial-contract, costs, shared-types. Пересечений записи с T09/T10 нет. Риск: T09 владеет frontend-e2e — e2e-ассерты tuition-only программ могут изменить вывод после демотации; проверить до merge.
- РЕШЕНИЕ ДИСПЕТЧЕРА (координатор, 2026-09-07): (1) набор обязательных категорий = дефолт CORE_COST_CATEGORIES из кода — УТВЕРЖДЁН; (2) share/classify residual (runner.py:579 → funding.py:207-225 может сказать «covers ~100%» от частичного subtotal) — ПРИНЯТ КАК RESIDUAL, устраняется в T05–T07 (обе получают cost_basis из контракта); зафиксировано в ledger, не молчаливое допущение.
- T05/T06/T07 строятся на этом контракте (аддитивность обязательна).

## NON-GOALS
F02/F03/F04; валюты/конвертация; extraction/адаптеры; новая архитектура; математика ranking; редизайн экранов beyond ResultDetail; e2e.
