# Native learning-path controls — статический review

**Вердикт: QUALIFIED_STATIC_ACCEPT.** Подтверждённого блокера в двух новых сценариях нет. Проверены сохранённые исходники на `task/preparation-learning-path@192d02b8e5ac5519ffdf61e3d0e8a0173375f737` и замороженный backend contract. Тесты, приложение, браузер, сеть и providers reviewer не запускал; это не runtime PASS.

## Точные входы и сохранность старых контролей

- [learning-path.spec.ts](../../integration-2026-10-11/source/frontend/e2e/learning-path.spec.ts): SHA256 `515bb5baa036c20e839bd2e4d7bc98a6139e40fea238a398d5b2afec194b5fd9`.
- [auth-journey.spec.ts](../../integration-2026-10-11/source/frontend/e2e/auth-journey.spec.ts): SHA256 `4591986814ac67f16d2b2c4900db4663164329b1fe4c268602b84fbcc88d97cf`.
- Независимое чтение именованного `c8bd7204:frontend/e2e/auth-journey.spec.ts`: все **8 481 байт / 157 строк / 7 исходных test declarations** совпадают с префиксом текущего файла; добавлен восьмой сценарий. SHA256 исходного префикса `b3daa53010f34fbead33023cfe9bd46c52a4b5e94d45745ad6a6c65d25292cb3`.
- [Backend CONTRACT](../proposals/backend/CONTRACT.md): `fa13b5868a1af9987ccbf398e51d924508f6a5e6af5989bbacbc685ba16a32df`; manifest `ecbd6f5946b64371023d5ab42739d3d8cbe876471f6ed025457f1cc6af772ba1`. Полные dependency pins и повторная проверка HEAD/байтов: [JSON](native-control-static-review-pins.json).

## Что действительно проверяют сценарии

1. **Публичный каталог и приватная работа.** `learning-path.spec.ts:17–42` получает настоящий public opt-in каталог (9 lessons/39 items), отдельно legacy default (3 lessons), затем UI click получает owned lesson с точной версией pack. В начальном JSON не должно быть `accepted_answers` или `correct_choice_id`. Profile ID извлекается из `/api/profiles/{id}/...` корректно. Ответы/receipt не подменяются route mocks.
2. **Короткие ответы и UUID.** `:48–62` вводит пять ответов normal UI, получает настоящий POST receipt 4/5, показывает ошибку `memory stick`, затем посылает тот же HTTP payload и проверяет тот же database row ID. `:70–76` после reload открывает сохранённую работу по **client `attempt_id`**, а не database `id`; selector/response contract согласованы. Backend допускает эти исходные варианты; private feedback появляется после принятого submit.
3. **Последовательность.** `:64–69` проверяет ID следующего IELTS lesson и pack version на кнопке, затем normal click и заголовок. Ordered track соответствует backend contract. Это потребует от интегрированного UI точного query version и response fence; сам сценарий не инспектирует JSON следующего GET.
4. **Свежие signin sessions.** `auth-journey.spec.ts:159–221` использует два новых BrowserContext, normal signin и server-owned profile. Первый отправляет `SHEET.` и получает 5/5; второй после закрытия первого контекста загружает ту же UUID работу и показывает исходный `SHEET.`. Actual opt-in progress содержит version-qualified completion и UUID. `helpers.ts:26–40` не переносит cookies/localStorage между contexts.
5. **Календарь и Academics.** Demo сравнивает значения до/после practice/review; его календарь может быть пустым. Auth сравнивает ранее сохранённый настоящий календарь из неизменённого четвёртого сценария и все `academics` до/после нового submit и второго signin. Оба пути используют actual owned GET; practice totals обозначены «practice only».
6. **Мобильная граница.** Demo измеряет отсутствие document overflow при ширине 390 и 320 и сохраняет review screenshots. Это контроль заданных viewport/default font, без утверждения о физических safe areas, zoom или размерах ниже 320.

## Обязательные квалификации перед приёмкой

- На момент review UI packet не имел READY. Нужны отдельный frozen UI review и actual native gates. DOM contract должен предоставить `Answer 1..5`, `review-attempt` с client UUID, `saved-attempt-review`, `feedback-item`, `next-lesson` с exact ID/version. Ожидание `.first()` ошибочного feedback требует сортировки ошибок первыми в UI; порядок backend feedback менять не требуется.
- Это **последовательный idempotent replay**, без proof concurrent HTTP race, failed-network retry или doubleclick. Runtime replay/feedback response нельзя заменять этим статическим заключением.
- Сценарии не перехватывают JSON owned review endpoint и не проверяют retired-version/null lesson или expiry здесь; эти границы покрываются отдельными backend/API и frontend control proposals, их native results ещё нужны.
- `runDemoResearch` запускает actual synthetic demo research. Provider-none, owned temporary DB, запрет внешней сети, исходники до/после и cleanup доказываются root launcher/receipt, а не этими двумя spec files. Native configs сами по себе этого не доказывают.
- Auth config исполняет Desktop Chromium; Demo config включает Desktop/Mobile. Число будущих PASS не выводилось из конфигурации. Нет claims production/deployment, новой account-deletion HTTP проверки, официальных IELTS/SAT scores, диагностики или учебной эффективности.
- Reviewer автор backend proposal/contract: проверка независима от root E2E автора, но не является слепым независимым acceptance backend реализации. Отдельный backend static review выполнен другим reviewer.

**Исходники не изменены.** HEAD и обе native spec hash повторно совпали в конце чтения. Замороженные источники и runtime gates остаются ответственностью root.
