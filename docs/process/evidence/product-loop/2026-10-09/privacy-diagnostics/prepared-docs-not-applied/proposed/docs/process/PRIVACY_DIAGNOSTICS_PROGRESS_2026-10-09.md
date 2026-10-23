# Персональные данные: диагностика отклонённых значений — 9 октября 2026

**TEMPLATE / SOURCE APPLIED / FULL PENDING. Не итог локального принятия.**
Этот отдельный отчёт относится к source `08450f71e6bbeadd9a2212fbd6c9f96f5c428755`.
Root применил 14 code/test paths из принятых внешних пакетов; прежние 20 security
paths неизменны. Общая карта **34 уникальных paths** имеет SHA-256
`bc960dfdf50a140698ff399c7929cc503f6fee24ef5f050c34d3ef9f72a71dd6`.
Число paths не означает число дефектов, сценариев или пользователей.

Юридический пакет остаётся **DRAFT / NOT READY**, версия `2026-10-09.draft1`.
Оператор, действующий контакт, страны БД/копий/журналов, получатели, retention,
minors/представитель и серверная фиксация согласий не подтверждаются этим кодом.
Цели обработки и правовые факты политики в этом раунде не переписываются.
[Предыдущий security progress](SECURITY_PRIVACY_PROGRESS_2026-10-09.md) на source
`5b48d5e43d0ba7247c850ba4556584ab7415a986` остаётся историей с собственными full/UI
receipts. Его метрики нельзя перенести на текущий source.

## Что изменилось для пользователя

Если существующая защита отклонила URL или discovery field как содержащий
персональные данные, диагностический путь больше не должен повторять само
отклонённое значение в проверенных warning/result/hop, adapter errors/outcomes,
Run/Job/Audit и Research API/log границах. Он оставляет безопасную идентичность
и типизированную причину, чтобы было понятно, почему чтение не состоялось.
Это не новая проверка официальности: безопасный origin/placeholder не доказывает
DNS-проверку или успешное чтение и не превращается в адрес автоматического retry.

Отказ сохраняется как refusal/partial/unknown, без выдуманного отсутствия
программы, готовности к поступлению или новых подтверждённых Claims. Сохраняются
обычные URL, числовые CMS paths, HTTP status/reason, обычные retry, бюджетные
ограничения и generic traceback; LeaseLost/RunCancelled не подменяются privacy
ошибкой. Действующая `find_pii` / `assert_no_pii` политика, TypeSafe thresholds,
robots/egress/caps/defaults, Candidate/Claim schemas и gold не менялись.
Прямое discovery, уже подавляющее небезопасный query, не объявляется доказанной
утечкой. Нет обещания обнаружить все виды персональных данных или очистить
исторические raw, cache, export, backup и внешние копии.

## Узкое сохранённое native доказательство

Это pre-integration source-bound проверка точных принятых байтов, а не новый
full на `08450f71`. Независимый peer: **ON13 PASS / 0 FAIL; OFF3 PASS / 10 semantic
FAIL**, 3 предупреждения. Набор: 6 авторских групп, 1 существующий poisoned-hop
case, 4 независимых subcases и 2 portable повторения. Повторы не складываются
в 13 уникальных findings или 4 разных persistence границы.

| Граница | Что реально исполнено в отдельном синтетическом окружении | Предел доказательства |
|---|---|---|
| P4 | Native Fetcher privacy refusal → cost adapter → Runner recorder → commit → fresh SQL Session → Research API; rejected sentinel отсутствует ON и остаётся OFF | Собственная SQLite. Явно вызванный fixture `_audit` использует native SQL, но не доказывает автоматический audit всех product calls |
| P5 | JobStore enqueue/claim token1 → Worker.execute/_dispatch → Runner failure-save/audit → JobStore.fail → fresh SQL/API/log | Синтетический stage input и собственная session factory; перечисленные sinks нативные. Runfailed/jobqueued/backoff и unknown facts сохранены, Claims0 |
| API tenant boundary | Same-tenant200 / other-tenant404 с explicit synthetic `Principal` | Проверка authorization dependency, не регистрация/login/session-cookie journey. Backoff Job может не входить в RunView; `Job.last_error` проверен отдельно |
| Portable2 | Те же P4/P5 тела перенесены в обычный backend test path, убраны только evidence writer calls | Повторение двух SQLite границ; SQLite остаётся SQLite даже внутри будущего PostgreSQL suite |
| Обычные controls | First/stale successful offsite оба используют current target; 2 offsite + 5 ordinary document failures сохраняют прежний detail; обычные CMS404/status/retry/budgets и generic error controls | Typed synthetic FetchResult на defensive adapter boundary; не успешный настоящий off-site сетевой fetch |

В независимом OFF и ON по четыре owned SQLite connections: две границы и их
portable повторы. DNS/connect/listen/child/forbidden DB counters0. Не проверены
PostgreSQL persistence, concurrent/crash semantics или внешняя сеть. Heartbeat
cancel наблюдался settled после event-loop yield, не как гарантия синхронного
reap. Авторские memory-sink observations не переименованы в SQL-доказательство.
`_recover_search_pages` и `_navigation_fallback` — **SOURCE_ONLY**, native coverage
этих двух live ветвей не заявляется.

## История ошибки и исправления сохранена

Первый C READY `9a2607d2007e4ae89516a629a79b61f2ef295018d10c9a9105e22aa9dfe16846`
отклонён. Peer READY `f71dd805649545b612f97e40c35155106be60f3680c3ff702363f3404dc40c0f`
сохраняет оригинальный 11-case итог: OFF3 PASS/8 FAIL, C9 ON9 PASS/2 FAIL.
В первой успешной offsite ветви возникал UnboundLocalError, после prior404 мог
подставиться URL прежней цели; ordinary document error detail тоже требовал
совместимости. Это реальные authoring regressions, не privacy PASS.

Corrected C READY `2dd776c38d489df632fc84a89e87331943e5af8d1b33ccb48feb43c2a9f4c3f3`
и независимый ACCEPT `60cc8f31dc9038e3a8678028341f97708fea415b96ca026cd444b13252784a30`
относятся к исправленным точным байтам. Portable2 READY
`4730997b9942f573b3c24976f358c014928a566ab1693293de63610fa02ca4b8` — отдельный
один test path; root применил всего 14 paths (11 app + 3 test), не 13+14.
17 из 18 прежних poisoned-hop test function bodies неизменны; изменённый case
сохраняет refusal и проверяет safe identity/отсутствие sentinel. Нормализация
imports отдельно проверена в backend-equivalent Ruff context, без изменения
правил, aliases и nonimport AST. Первые harness/AST/lint ошибки и raw OFF/ON
сохранены; новые наборы 13 и старые 11 не считаются одним сравнением.

## Что заполнить только по реальному terminal и peer

Все null/PENDING ниже — незавершённые поля шаблона, а не 0 или PASS. Root должен
сохранить оригинальные actual logs/summary, full initial manifest и закрытый
execution receipt, затем получить независимую source/delta сверку. Ниже нельзя
вставлять числа предыдущего source или складывать повторные SQLite/PG suites.

```json
{
  "status": "PENDING",
  "source_head": "08450f71e6bbeadd9a2212fbd6c9f96f5c428755",
  "source34_sha256": "bc960dfdf50a140698ff399c7929cc503f6fee24ef5f050c34d3ef9f72a71dd6",
  "doctor": {"status": "PENDING", "passed": null, "total": null, "receipt_sha256": null},
  "core": {"status": "PENDING", "passed": null, "total": null, "receipt_sha256": null},
  "full": {
    "status": "PENDING", "run_id": null, "exit_code": null, "passed": null, "total": null,
    "summary_sha256": null, "execution_sha256": null, "initial_manifest_sha256": null,
    "sqlite": {"passed": null, "warnings": null, "coverage_percent": null, "seconds": null},
    "postgresql": {"passed": null, "warnings": null, "same_test_ids": null, "seconds": null},
    "frontend": {"passed": null, "files": null},
    "demo": {"passed": null, "skip": null},
    "auth": {"passed": null, "failed": null, "not_run": null},
    "static": {"format_exit": null, "lint_exit": null, "mypy_exit": null, "frontend_type_exit": null, "build_exit": null},
    "audit": {"pip_known": null, "npm_known": null}
  },
  "source_closure": {
    "status": "PENDING", "source34_exact": null, "app_config_inputs_exact": null,
    "declared_generated_png_count": null, "declared_delta_receipt_sha256": null,
    "remaining_declared_inputs_exact_count": null, "independent_peer_READY_sha256": null
  },
  "qualified_local_acceptance": null,
  "finalized_utc": null
}
```

Initial declared manifest — входная идентичность full. Если full создаёт
объявленные E2E PNG, их точный delta оформляется отдельно; не утверждать, что
физическое дерево после генерации целиком равно initial SHA. Gates PASS допускают
лишь квалифицированный local инженерный итог данного source. Этот doc proposal
не запускал tests, servers, DB, browser, providers или модели и не изменял primary.

## Что остаётся открытым

Операторский пакет/согласия остаются DRAFT; [release readiness](../legal/RELEASE_READINESS.md)
не является разрешением публичного запуска. [SECURITY](../../SECURITY.md) сохраняет
границы workspace, account/case deletion, shared organization, audit/jobs/payment,
backup/recipient copies и права доступа. Этот fix не очищает прежние данные и
не доказывает account-wide export/erasure или безопасность всех diagnostics.

Отдельный reset native scope safety-stopped: не исполнялся и не возобновляется
этим отчётом; никаких retry/rephrase/substitute. Compose ingress/address-trust
конфликт (public API mapping и forwarded-address trust) остаётся source-confirmed
очередью. Отдельная exact-version Nginx route/header матрица также не исполнена:
нет claim observed header loss, tenant bypass или Fly production fix. Семь
reviewed config/tool inputs совпадают с сохранённым qualified source review;
Docker/containers/production NOT RUN в этой документационной работе.

Provider/university STOP сохранён, research не возобновлён. Fresh research quality,
юридическое соответствие, production, independent pentest и superiority против
конкурентов не подтверждены. Итог этого шаблона пока **SOURCE APPLIED / FULL
PENDING / LEGAL DRAFT**, без вывода о готовности сервиса к публичному использованию.
