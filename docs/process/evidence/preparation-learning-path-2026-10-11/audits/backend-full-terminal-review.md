# Learning path — terminal full backend review

**Вердикт: QUALIFIED_LOCAL_ENGINEERING_ACCEPT.** Root full native backend gate закрыт PASS в обеих фазах. Это saved-only review actual receipts, JUnit IDs, coverage/source/helper/guard/probe hashes. Reviewer ничего не исполнял и не менял source/Git/helper/receipts. Сохранённый ранний [SQLite PG_PENDING review](backend-sqlite-terminal-review.md) остаётся историей; заключение ниже относится к terminal full result.

## Фактические результаты

| Native phase | Unique cases | F / E / skip | Warnings | Coverage JSON | Pytest summary |
|---|---:|---:|---:|---:|---:|
| SQLite default | **4 883** | **0 / 0 / 0** | **42** | **95.54828352679674%** (15 475 / 16 196) | **560.89 s** |
| Private Unix PostgreSQL default | **4 883** | **0 / 0 / 0** | **42** | **95.54210916275623%** (15 474 / 16 196) | **580.24 s** |

Обе pytest exit0; outer command wall time564.861/584.145s. Unique ID sets совпали точно: **4 773 accepted predecessor +54 domain +56 API** без удаления/rename старых IDs. API56 — 28 сценариев×SQLite/PG fixtures; обе default phases сохраняют эти явные engine fixtures. Это 9 766 successful executions двух фаз, а не 9 766 различных логических scenarios. Predecessor — terminal deadline `20261011T145907489813Z`, отдельно сверенный для каждой фазы.

Actual argv в обеих фазах использует full `tests`, `--cov=app --cov-fail-under=92`; module filters/deselect/новые skips отсутствуют. [Точные IDs и pins](backend-full-terminal-review-pins.json).

## Source/область acceptance

- Full root `result.json` PASS содержит обе phase receipts, которые byte-semantic совпадают с отдельными terminal result.json. Conditional fallback `postgres_if_not_started:NOT_RUN` не является фактическим статусом: настоящий PostgreSQL phase присутствует и PASS.
- Все четыре source-before/after maps равны, **604 captured paths**; каждый из **566 expected** pin совпал. Approved expected delta от563 — ровно6 путей (routes/schema/type и три new learning-pack content/domain/API-test files). Captured и expected counts различаются по намеренно более широкому capture scope.
- Проверены **25 evidence hashes каждой фазы** и **19 current helper pins**, расхождений нет. Семь core launcher/guard/mock/probe файлов byte-equal accepted predecessor; inherited helper manifests сохранены как история, actual helper/SOURCE_BINDING pins authoritative.
- Все21 recorded native migration version files и Alembic config/env hashes неизменны от accepted deadline predecessor. Новая learning-pack миграция не добавлялась; recorded predecessor head `a9e5c14d2021` сохраняется в той же цепочке. Сохранены и PASS13 migration-named native controls каждой фазы. Это source-bound сохранность цепочки, без нового production DB/remote migration claim.
- Root сообщил clean source commit `4151afb5` с fixture-alias-only коррекцией после packet15+display delta. Reviewer не исполнял Git; заключение связано с exact604 consumed hashes, а не неподтверждённой полнотой commit metadata.

## Isolation/cleanup

В каждой фазе **13 guard receipts**, outside_attempts=[] и startup failures=[]; app_preimported=false, IPv6 trait restored=true. Main driver guard установлен; stdlib child guards работают без требования импортировать optional psycopg. **903 SQLite-phase /904 PG-phase private endpoint checks**, все host paths внутри соответствующего owned runtime.

OS parent и actual Bash/Python-I descendant IPv4/IPv6 bind/connect/sendto negative probes PASS; private Unix PG SELECT1 positive probe PASS. Network SBPL допускает Unix socket только внутри directory-boundary prefix owned runtime. Guards/mock policies byte-equal predecessor; floor не ослаблен для новой feature.

В обоих terminal receipts active_cluster_markers=[], shutdown_confirmed=true, runtime_removed=true и source_unchanged=true. Reviewer проверил сохранённые cleanup/hash receipts, новых live process/port probes не выполнял. Shared root gate/serialization semantics прежнего launcher сохранены; provider/live research calls этим gate не разрешались.

## Что закрыто новой native проверкой

- Legacy catalogue/item/version/serialization и literal v1 digest, opt-in9 lessons/30 original added items и exact-version dispatch; initial keys/explanations privacy.
- Closed short variants и bounded case/whitespace/one-period normalization, raw accepted text/array order и private feedback snapshot; malformed/incomplete/unknown answer422 без записи/keys.
- Owned/foreign-case404, accepted row/progress/export; same client UUID sequential identical replay, changed raw payload409 сохраняет original receipt. Expired term разрешает owned accepted replay/review/history, отказывает unseen lesson/new submit402.
- Exact immutable owned review и unavailable historical lesson:null без current-version substitution. Practice не меняет Academics/profile/quota/research/calendar. Actual HTTP profile DELETE проверяет cascade при SQLite FKoff.

## Обязательные квалификации

Этот acceptance ограничен local engineering backend. Native Demo/Auth UI/table/second-session/visual receipts отдельны и ещё не включены сюда. Sequential replay — не concurrent HTTP race proof. Account-deletion browser flow не добавлялся; profile DELETE proof не переименован в него. Teacher/learner outcomes, calibrated difficulty, readiness, full IELTS/SAT course и official-score growth не доказаны. Deployment/production data/migration не проверялись. Исторические fixed native offline contracts не являются текущим search-quality scoring; GLOBAL_PROVIDER_STOP / UNSCORED остаётся закрытым.

Reviewer автор backend proposal; отдельный frozen code/content review выполнен независимым агентом. Primary runtime receipts принадлежат root и не наследуются из author isolated54/collection56 evidence. Полные raw closed receipts сохраняются; first author/static/native failures не переписывались.
