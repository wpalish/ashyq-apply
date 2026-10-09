# Проверка security/privacy готовности

**DRAFT / NOT READY для публичного запуска.** Срез исходников 9 октября 2026:
`c7b41fcf42c2fb84e877a8cb8b1349eedb79941f`. Исправления безопасности и
последующее восстановление серверного кейса уже применены. Это статус исходников,
не принятие текущих full/browser проверок и не подтверждение оператора, consent,
production или качества исследования. Root добавляет фактический итог текущей
проверки отдельной записью после её завершения; не заменять pending предполагаемыми
числами.

| Область | Подтверждённое состояние исходников | Оставшаяся проверка / условие запуска |
|---|---|---|
| Глобальные moderator privileges | Применён operator-provisioned `moderator_user_ids`, default empty; авторизация по `Principal.user_id`. Email и workspace-owner роль не дают глобальных прав | Реально идентифицировать и provision нужные account IDs; отдельное deployment подтверждение |
| Private HTTP responses | `/api` и `/api/*` returned responses, включая ранние CSRF/rate отказы, получают `no-store`; static caching не меняется | Текущий full pending; unhandled exceptions вне completed middleware и публичные proxy/route headers отдельно. Это не удаление старых копий |
| Browser identity boundary | Применены user/org namespace для drafts/pointers/docsDone, bind до hydration, очистка распознанных applicant keys при owner change/acknowledged logout, invalidation и owner/generation guards | Текущий browser/full pending. Cooperative controls не заменяют серверные права, не шифруют storage и не отменяют уже отправленные запросы с общей cookie |
| Same-owner case recovery | Pointerless authenticated bootstrap читает authorized `/cases`, затем существующие profile/latest-run readers; explicit new/local/saved intent сохраняется; late responses отбрасываются; `newCase` снимает superseded loading | Текущая recovery full и finite browser проверка pending; никаких автоматических create/research/retry |
| Export/delete | Saved case без run доступен; success/reset только после acknowledged DELETE. Case export — case-scoped record, не account-wide | Проверить текущий full/browser. API inherited note о complete record/all deletion ещё требует отдельной правки; cleanup старых невидимых marks/backups не доказан |
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

## История проверки и незакрытый итог

Pre-security predecessor `c976074b` содержал SECURITY.md; RELEASE_READINESS.md
добавлен в этом раунде. Исходный pre-fix срез `8010806f` сохранён ниже как история,
а не текущий перечень неприменённых исправлений. Первый security full на `a0fc4a7b`
закончился FAILED: unchanged auth E2E не восстановил ранее сохранённый case после
повторного входа. Это не доказательство удаления серверных данных и не green full.
Последующий `c7b41fcf` содержит отдельно reviewed two-file recovery; его full и
finite browser итог пока PENDING. Фокусированные mock/component проверки не
подменяют этот итог. Source pins и оригиналы ведутся в [HANDOFF](../process/HANDOFF.md).
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
