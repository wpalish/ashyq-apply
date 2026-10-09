# Проверка security/privacy готовности

**DRAFT / NOT READY для публичного запуска.** Срез 9 октября 2026:
`5b48d5e43d0ba7247c850ba4556584ab7415a986`. Применены security boundaries, authorized-case recovery и
acknowledged profile-export view cleanup. Фактический source-bound local full и
finite synthetic UI итог приведён в разделе «Квалифицированная локальная проверка».
Это не подтверждение оператора, versioned consent, production, безопасности всех
пользовательских сценариев или качества университетского исследования.

| Область | Подтверждённое состояние исходников | Оставшаяся проверка / условие запуска |
|---|---|---|
| Глобальные moderator privileges | Применён operator-provisioned `moderator_user_ids`, default empty; авторизация по `Principal.user_id`. Email и workspace-owner роль не дают глобальных прав | Реально идентифицировать и provision нужные account IDs; отдельное deployment подтверждение |
| Private HTTP responses | `/api` и `/api/*` returned responses, включая ранние CSRF/rate отказы, получают `no-store`; static caching не меняется | Source-bound local итог указан отдельно; unhandled exceptions вне completed middleware и публичные proxy/route headers остаются отдельной проверкой. Это не удаление старых копий |
| Browser identity boundary | Применены user/org namespace для drafts/pointers/docsDone, bind до hydration, очистка распознанных applicant keys при owner change/acknowledged logout, invalidation и owner/generation guards | Source-bound local и finite synthetic UI итог указан отдельно. Cooperative controls не заменяют серверные права, не шифруют storage и не отменяют уже отправленные запросы с общей cookie |
| Same-owner case recovery | Pointerless authenticated bootstrap читает authorized `/cases`, затем существующие profile/latest-run readers; explicit new/local/saved intent сохраняется; late responses отбрасываются; `newCase` снимает superseded loading | Квалифицированный local итог указан отдельно; никаких автоматических create/research/retry, tenant-authorization и production границы не расширены |
| Export/delete | Saved case без run доступен; success/reset и очистка открытого profile JSON только после acknowledged DELETE. Direct profile Show/Download защищены case/generation/unmount fence; смена кейса снимает прежний view/Deleted state. Case export не account-wide | Source-bound local/finite UI итог указан отдельно. Shortlist-download route неизменён; отправленные запросы/скачанные копии не отменяются. Inherited API note complete/all и cleanup старых невидимых marks/backups остаются отдельными gaps |
| Public privacy notice | Применён draft LegalScreen: workspace/case/account и query/AI boundaries, operator/minor/retention gaps названы; browser policy paragraph согласуется с принятым кодом | Не публиковать как финальную политику до операторских подтверждений и юридической проверки; версия `2026-10-09.draft1` не является записью согласия |
| Legal operator | `operator-facts.json` остаётся UNCONFIRMED_NOT_FOR_FINAL_PUBLICATION; реквизиты/contact не подтверждены | Полный operator-facts и реально принимающий обращения канал |
| Места хранения и получатели | Source-config app region `ams` не доказывает страну primary DB/copies/logs; actual processors не подтверждены | Конкретные deployment/договоры/локализация и передачи подтверждаются оператором |
| Consent/minors | Нет versioned server receipt/age/authority flow; документ — draft specification | Утверждённые цели/документы и реализованный tested server record; UI checkbox не заменяет запись |
| Retention/deletion | Primary cascade не доказывает очистку jobs/audit/payment/backup/recipient copies; shared workspace сохраняется | Data-class schedule, scope/exception answer, actual cleanup и restore proof; сохранённый audit deletion receipt не гарантируется |
| Logs / reset | Audit errors и console-mail могут содержать персональные данные/ссылки. Reset-request API не возвращает token/link. Read-then-consume reset token требует отдельной concurrent-use проверки | Редакция, ограниченный доступ и сроки журналов; отдельная bounded concurrency regression/atomic fix при подтверждении. Ни repair, ни отсутствие race сейчас не заявляются |
| Nginx headers | Location `add_header` может отменить наследование server headers; изменение конфигурации в этом раунде не применено | Exact deployed version/config и route-header check в отдельной операционной задаче |
| Продакшн | В этом task не проверялся и не менялся | Конкретная deployed version, headers/auth/rights/restore/incident/support и signed-in path |

Исходники: [moderator IDs](../../backend/app/config.py),
[moderator guard](../../backend/app/api/routes_social.py),
[API headers](../../backend/app/main.py),
[browser owner binding](../../frontend/src/lib/applicantStorage.ts),
[auth gate](../../frontend/src/AuthGate.tsx),
[API transition guards](../../frontend/src/api/client.ts),
[case recovery / acknowledged deletion](../../frontend/src/lib/store.tsx),
[authorized case order](../../backend/app/api/routes_cases.py),
[case export/deletion](../../backend/app/api/routes_profile.py),
[reset endpoint](../../backend/app/api/routes_account.py),
[public draft notice](../../frontend/src/screens/LegalScreen.tsx).

## Квалифицированная локальная проверка

Источник `5b48d5e43d0ba7247c850ba4556584ab7415a986`; карта 20 code/test paths `22ca29438dadb49deb393941ed6d67624301418118f0dd501b63949a41a2a1df`; initial declared source map `aa964eb434de85bd890b54b8128b077811de6a71ca7df6b60b12c7bcc4fb5d81`. Метаданные и документы в последующих commit не объявляются тем же физическим деревом.

Один свежий full `20261009T023420Z-check-9769c516`: **13/13 PASS**, SQLite **4 384 уникальных PASS / 32 предупреждения / 95,26% / 486,44 с**, PostgreSQL те же **4 384 ID / 32 предупреждения / 362,95 с** (coverage не измерено), frontend **357 PASS в 34 файлах**, demo **79 PASS + 1 прежний skip**, auth **6 PASS**, pip/npm audit **0 известных уязвимостей**. Core 8/8 и doctor 5/5 сохранены отдельно; повторные suites/БД не складываются. Declared manifest сохранён: отдельно приняты **38** сгенерированных PNG (**18** mobile), остальные **11 449** declared inputs exact.

Новый bounded synthetic browser: ровно **1 desktop capture 1440×900**, немедленное исчезновение открытого JSON/старого marker **после ACK и до навигации/reload** подтверждено AX/DOM/JPEG. Последующий same-owner reload — отдельный **PASS AX-only**, без удалённого кейса. Optional phone **NOT_RUN_NOT_NEEDED**; старый C7 residual/viewport/identity qualifications не переименовываются. Прямые профильные Show/Download ограничены generation/mounted fence; отдельный shortlist export и ранее завершённые downloads не отзываются.

Native peer READY `3de16170e40c311f9eee758c1f40c51780574c156079e67cede574883a848bd0`; browser READY `e3a6cd5c6570366d4ea840fda395e1783ac3e9bf80aefb24f3724ba8ffd35d7d`; independent UI/cleanup peer READY `32c992097ebf3b314606b1a615fee4495a699bf6b03e5f191cb82ba1e0a3c11a`. Root owned preview exit0/cleanup `0dd0025fd45675b7d16b968d9f488f03c22359bcbdd474e11de074a5ef511f6d`: errors[], source/config postcheck и free ports before unlock; своя Chrome вкладка закрыта/reset. Оригиналы и selected safe lifecycle receipts находятся в `docs/process/evidence/product-loop/2026-10-09/security-round/`. DB/API logs/request/session payload не копировались.

Итог: **квалифицированное локальное инженерное принятие этого раунда**. Правовой пакет остаётся DRAFT: operator/страны/retention/minors/согласия не подтверждены, серверная фиксация согласий не реализована. Docker/containers, cloud required checks, production и принятое свежее качество поиска не пройдены этим раундом. Rejected-PII diagnostics, reset atomicity, Nginx headers и inherited endpoint export-note copy остаются отдельными незакрытыми задачами.


## История проверки и незакрытый итог

Pre-security predecessor `c976074b` содержал SECURITY.md; RELEASE_READINESS.md
добавлен в этом раунде. Исходный pre-fix срез `8010806f` сохранён ниже как история,
а не текущий перечень неприменённых исправлений. Первый security full на `a0fc4a7b`
закончился FAILED: unchanged auth E2E не восстановил ранее сохранённый case после
повторного входа. Это не доказательство удаления серверных данных и не green full.
Последующий `c7b41fcf` содержит отдельно reviewed two-file recovery. Его сохранённый
full13 — предыдущий source. C7 finite UI сохранил residual: после acknowledged case
DELETE открытый Stored profile JSON оставался до reload; C7 не доказывает следующий
Export2 source. Последующая локальная квалификация `5b48d5e43d0ba7247c850ba4556584ab7415a986` приведена
отдельно. Focused native39, full и finite UI имеют разные области доказательства;
их нельзя складывать в общий показатель безопасности. Source pins и оригиналы ведутся в [HANDOFF](../process/HANDOFF.md).
Глобальный provider STOP сохранён; эти изменения не возобновляют live research.

Документы: [политика](PRIVACY_POLICY_RU.md), [условия](TERMS_RU.md),
[consent](CONSENT_SPEC_RU.md), [получатели](PROCESSORS_AND_TRANSFERS.md),
[retention/rights](DATA_RETENTION_AND_RIGHTS.md), [инциденты](INCIDENT_RESPONSE.md),
[operator facts](operator-facts.json). Неподтверждённое поле не считается пройденной
проверкой. Обязательные rights не исключаются исходной MIT-лицензией.

Официальные ориентиры остаются прежними: [закон РК](https://old.adilet.zan.kz/rus/docs/Z1300000094),
[OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/).
Применимость к конкретному оператору и deployment подтверждает квалифицированный
специалист. В этой документационной сверке источники закона заново не проверялись.
Security benchmark конкурентов и независимый пентест не выполнены; превосходство
по безопасности не заявляется.

<details>
<summary>Сохранённый первоначальный pre-fix срез — исторический, не текущий статус</summary>

Срез 9 октября 2026; source baseline `8010806f` (исполняемые файлы predecessor c7). **Статус до применения proposed fixes: NOT READY.** Заполнить финальные source/gates/peer receipts после текущего раунда.

| Область | Подтверждённое состояние | Условие закрытия |
|---|---|---|
| Глобальные moderator privileges | Email allowlist + unverified public signup создают условный spoofing путь | Operator-provisioned immutable account IDs; native negative spoof + trusted positive tests |
| Private HTTP responses | Нет явного no-store в обычных и ранних API responses | API no-store + отказ controls, static cache unchanged, опубликованные headers отдельно |
| Browser identity boundary | Unscoped drafts/marks/pointers могут остаться при смене аккаунта | Principal/org namespace, bind before hydration, stale-tab invalidation и meaningful controls |
| Export/delete | Saved profile без run gated; failed DELETE может показать success | Zero-run controls, acknowledged success, safe draft/mark/reset behavior and failure test |
| Public privacy notice | Старые внешние-передачи/полное-удаление/MIT-liability assertions | Truthful source-bound scope, identity/hosting/contact/minor gaps visible; no blanket promises |
| Legal operator | Реквизиты/contact не подтверждены | Полный operator-facts и реально принимающий обращения канал |
| Места хранения | fly.toml region ams; страна primary DB/copies/logs не проверена | Подтверждение локализации/передач у конкретного оператора и договоров |
| Consent/minors | Нет versioned server receipt/age/authority flow | Утверждённый документ и реализованный tested scope; UI checkbox не заменяет server record |
| Retention/deletion | Primary cascade не доказывает очистку jobs/audit/payment/backup | Data-class schedule, scope/exception answer, actual cleanup и restore proof |
| Reset race | Source audit подозрение на read-then-consume reset token; уточняется отдельно | Native concurrent-use regression и atomic fix в следующем bounded task при подтверждении |
| Nginx headers | Location add_header может отменить наследование server security headers | Exact version/config route-header check; исправление отдельно, не production claim |
| Продакшн | В этом task не проверялся и не менялся | Конкретная deployed version, headers/auth/rights/restore/incident/support и signed-in path |

Документы: PRIVACY_POLICY_RU, TERMS_RU, CONSENT_SPEC_RU, PROCESSORS_AND_TRANSFERS,
DATA_RETENTION_AND_RIGHTS, INCIDENT_RESPONSE. Неподтверждённое поле не считается пройденной проверкой. Обязательные rights не исключаются исходной MIT-лицензией.

Официальные ориентиры: [закон РК](https://old.adilet.zan.kz/rus/docs/Z1300000094), [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/). Применимость к данному оператору и deployment должен подтвердить квалифицированный специалист. Security benchmark конкурентов и независимый пентест не выполнены; «в разы безопаснее» не заявляется.

</details>
