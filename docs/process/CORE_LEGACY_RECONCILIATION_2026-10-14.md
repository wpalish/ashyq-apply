# Unimatch — следующий этап: сверка и ограниченный increment B

14 октября 2026. Проверенный baseline: `42f4d814fcda0c8cd5636319915e4d9770b1860e`, ветка `task/admissions-actions-today`; origin совпадает, дерево чистое, Draft PR88 открыт, base `task/shared-preparation-route`. Единственная migration head `a0d94e902027`. Common runner lock свободен, активных native runners нет. Основной инженер работает один.

1177 файлов из внешнего read-only аудита побайтово совпадают с нынешним source. Это проверка привязки аудита, не семантическое чтение 418141 строк. Сохранённые 5840 тестов каждой БД, 857 frontend и восемь native stories принимаются как прежние source-bound результаты; новых прогонов пока нет. HANDOFF checker прочитал `nobody.` как имя holder и выдал ложное предупреждение возраста; чистое дерево, выпущенный baton и завершённые процессы проверены отдельно.

## Reuse/change/missing

| Контур | Существует и используется | Требуется изменить / отсутствует |
|---|---|---|
| Анкета | Store normalized save/newer typing, case identity, API/SQL payload | N01/N02 async input fences; N09 atomic server profile revision |
| Найденные программы | Early programme observations, existing job lease/cancel fence | Свежая search quality не измерена; таймер300 против DoD120 не принят |
| Требования | Detached read mapper, input provenance, official quotes/unknown | N05 mutation response читает исторический DTO |
| Документы | G3 IDs/bindings/CAS/receipts/history/export/delete, PersonalDocumentsPanel | Переиспользовать, продолжить targeted history/source review |
| Заявки | ApplicationsPanel/manualV2/selected programme targetV1/declaration/correction | Selected scholarship UI с явным result+award, без выбора по имени |
| Today/recovery | Server projection/exact IDs/generations/64 ACK cleanup | Переиспользовать, проверить residual correction/conflict UX |
| Результаты | ProgramResultRow + Store decisions/notes/refresh/rerank | N03/N04/N07 единая согласованность всех writers и сохранение drafts |
| Даты/export | LocalDate formatter, sourceDatePosition, owner/delete fences | N06 legacy deadlines/calendar; N08 handled export errors |
| Выпуск | Draft88/stacked chain и local receipts | Live/heldout/operator/release/backup/ingress/published smoke не приняты |

## Findings на нынешних bytes

| ID | Приоритет | Контур / точный source | Статус до исправления |
|---|---|---|---|
| N01 | P1 | ProfileScreen.applyConversion/readTranscript/applySuggestion | Source-confirmed; native reproduction NOT_RUN |
| N02 | P2 | Store validation debounce | Source-confirmed; native reproduction NOT_RUN |
| N03 | P2 | Store.decide/saveNotes | Audit source matches current; native reproduction NOT_RUN |
| N04 | P1 | routes_results.set_decision/set_notes | Source-confirmed RMW without CAS; DB race NOT_RUN |
| N05 | P2 | routes_results mutation responses vs result_read | Source-confirmed; frozen clock NOT_RUN |
| N06 | P2 | routes_results.deadlines → export/calendar.upcoming | Source-confirmed UTC day; timezone native NOT_RUN |
| N07 | P2 | Store.saveNotes → ShortlistScreen unconditional close | Audit source matches current; failure native NOT_RUN |
| N08 | P2 | ExportScreen.showProfile/downloadProfile | Audit source matches current; failure native NOT_RUN |
| N09 | P1 | routes_profile.update_profile whole payload | Source-confirmed missing precondition; DB race NOT_RUN |

## Increment B: N01/N02

Reuse `currentAdmissionsCase()` synchronous identity and existing `setProfileDraft`, normalized save and accepted baseline. Add a read-only synchronous current draft getter and private semantic draft generation; every draft writer uses the same setter. Validation captures exact serialized input, draft generation, request serial and case/owner identity; obsolete success and failure are ignored. Visible report is bound to that accepted input. Conversion/transcript/method lookup use current owner/case/generation, request serial and original GPA (method list: scale) fingerprint; suggestions require explicit user choice and current binding. No remount-only/AbortController-only protection. Case changes clear local suggestions/busy/error state; no server schema or payload change.

Exact code/test allowlist is sealed in external `increment-b/GRANT.json` with preimages. Two old test fixtures gain real required read getters; original assertions remain unchanged. New deferred controls cover A→B/A→B→A, two previews in reverse order, changed GPA, old error after new success, transcript suggestions from old case/input, stale method list and validation. Run meaningful OFF reproduction before source apply, retain all first failures; then new ON controls/full frontend gates with common freeze lock and exact source maps. Backend bytes remain unchanged, so current 645-file full proof may be carried only after exact map comparison.

## State ownership and follow-up

ApplicantProfileRow: identity profile ID, principal org owner, whole JSON payload + scalar name, no revision yet; creation/update API writers, runner consumes accepted profile, own API/export/cascade readers. N09 must specify additive atomic revision and creation/unknown ACK compatibility before changing it.

ProgramResultRow: identity result ID within run, owner via run/profile/org, scalar user fields + JSON, no row revision yet. User notes/decision, runner upsert, refresh/rerank are distinct writers; compile complete writer/lock/CAS matrix before N04. Readers include GET/read projection, summary/export and G3 target selector. Do not invent a row strategy from one endpoint.

G3: native current record revision + immutable events/receipts, exact UUID/body/CAS and owner references, one existing persistence model. Store is a UI projection/draft/recovery host, never a second document DB. Requirement read projection does not rewrite original assessment. Personal history/export/delete retained independently of subscription evidence access.

Stages C–G remain pending, full every-line audit remains incomplete. All STOPs stay binding. Closed search collection stays UNSCORED; heldout150 untouched. No models/providers/live benchmark, production/secrets/payments/hosted settings/main merge/deploy. Ordinary owner-authorized core fixes continue; fresh live and release need their own applicable authorization.
