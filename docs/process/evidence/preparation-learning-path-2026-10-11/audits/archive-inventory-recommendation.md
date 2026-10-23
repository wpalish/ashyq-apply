# Archive inventory recommendation — no copy performed

Это только конечный allowlist для root; source/Git/runtime/proposals и sealed receipts не менялись. Primary gates ещё pending terminal review. [Exact member inventory](archive-inventory-recommendation.json) задаёт пути/категории и SHA256 для уже закрытых inputs; ongoing evidence перечислена без чтения verdict и без фиксации меняющихся logs.

## Сохранить сейчас при будущей сборке архива

1. **Оба author packets по явным manifest members**: backend40 entries + UI81 entries, их MANIFEST/READY. Все текущие packet/input hashes совпали. Они включают final source/test/patch/contract, original source preimages, первые authoring/type/pytest failures и final selected author receipts. Не копировать `isolated/` и `validation/`.
2. **Девять named authored/provenance inputs из inputs/INDEX.json**, включая IELTS v1/v2 и SAT draft, корректирующий patch и независимые draft reviews. Это оригинальные authored course inputs, не official licensed items или search quality labels.
3. **Пятнадцать текущих named audit/review files**, точно перечисленных в JSON: first native/UI seals, independent30-item ledger/extraction и backend review, display follow-up/review. Сохранить их разные scope и dates; не заменять first receipts окончательными.
4. **Root application + display evidence**: APPLICATION.json, обе FINAL_SOURCE_PINS maps, HELPER_COPY.json и named root apply/static/seed scripts; все восемь display-correction members (before/after production и single-assertion alignment + patches/receipts).
5. **Root gate preparation**: только named backend-full helper manifest members + SOURCE_BINDING.json + predecessor expected map и три e2e helper files. Старый helper manifest/adoption — история; текущие helper/source binding pins отдельны. Inventory отмечает текущие расхождения наследованного manifest, не выдаёт его за current acceptance.

## Добавить лишь после terminal сигнала root

- `evidence/static-frontend-accepted/`: raw commands/results/logs, JUnit, source before/after. Десять observed names уже указаны в JSON; неизвестные будущие файлы добавляются только явно.
- `evidence/backend-full/<run-id>/`: оба SQLite/private-Unix-PG result/JUnit/pytest/coverage JSON; полный root terminal result, before/after source maps, network/optional-driver/mock/OS-probe/helper pins, shared-lock/cleanup receipts. Сохранить первые actual failures, если возникнут. Raw `.coverage` DB не нужен при полном coverage JSON.
- `evidence/e2e/<demo/auth-run-id>/` и wrapper terminal receipt: уникальные JUnit/run counts, сохранённые sanitized console/server logs, source binding, provider-none/outbound floor и owned process/ports cleanup. Сохранить first failure evidence. Отдельно добавить только small synthetic learning-path/review/SAT-table screenshots, которые root просмотрел.
- Root final report/acceptance reviews/commit-source pins — по конкретным именам после создания. **Primary runtime не наследует author selected68/54 receipts.**

## Source и privacy

Архив должен содержать final applied 15 paths из packet + exact display-only production/test delta, а root-authored current `frontend/e2e/learning-path.spec.ts` и `auth-journey.spec.ts` — как отдельные конечные source snapshots/pins. Для auth сохранить original7 prefix hash и current8 controls, не session/auth state. Native helpers/config/source dependency maps позволяют привязать actual E2E без копии всего source/dependency tree.

Исключить dependencies/caches/builds, DB/PG data/socket/runtime directories, `.env`, credentials/cookies/storageState/headers/tokens и browser auth dumps. Большие HTML reports/traces/videos/HAR не нужны в компактном archive; допустимы external location/hash references. Полные raw safe text logs должны остаться; если появляется secret-bearing log, сохранить immutable local original и отдельно sanitized archive copy с явным receipt — не silently redact историю.

Не архивировать закрытые search/evaluation payloads или старые quality captures. Здесь не создаётся новых quality/runtime/course-readiness claims. После закрытия всех gates root формирует новый archive MANIFEST по этому allowlist с exact counts/hashes и проверяет целостность. Никаких copies/archives reviewer не создал.
