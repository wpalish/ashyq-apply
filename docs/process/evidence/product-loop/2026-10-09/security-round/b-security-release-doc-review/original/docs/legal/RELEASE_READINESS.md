# Проверка security/privacy готовности

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
