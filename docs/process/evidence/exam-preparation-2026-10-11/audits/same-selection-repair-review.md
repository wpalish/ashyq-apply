# Independent static review: same selected programme

**Verdict: ACCEPT_NARROW_REPAIR_PENDING_FRESH_GATES.** Это review двух exact applied files; runtime/UI acceptance пока **PENDING**. Автор review не менял source, Git, native tests, приложение, провайдеры или runtime и не запускал тесты. Live gate logs не использованы как terminal proof.

## Фактическая причина и границы

Первый native Demo `20261011T130607Z-demo` завершился exit1:79 PASS,2 FAIL,1 прежний intentional skip и8 serial NOT_RUN; JUnit total90/errors0. Desktop/mobile новый Goals test не находил IELTS writing. Сохранённый desktop context показывает «Loading stored exam evidence…» после повторного выбора default programme; сохранённый trace содержит preparation plan GET200 с подходящими profile/result и IELTS checks. Это не доказательство API outage или foreign-case exposure: одинаковый display name/число runs в roster сами по себе не устанавливают такую связь.

В исходном `PreparationScreen.tsx:177` onChange безусловно очищал plan и включал planLoading, даже при том же selected value. Действующие dependencies эффекта `:111–121` оставались прежними, поэтому resolved plan исчезал без нового запроса. Native spec явно делает selectOption уже выбранного value.

## Exact production delta

`PreparationScreen.tsx:177–181` теперь получает `nextResultId` и возвращается до любой мутации, если он равен `currentResultId`. Для настоящего нового выбора сохранён прежний набор state mutations; эффект, request ownership/active checks, stale-response suppression, response profile/result matching, case key/epoch и lesson/UUID guards не менялись. Текущий in-flight запрос продолжает работать; loaded/error state сохраняется при выборе того же value. Для повторения после ошибки остаётся отдельный existing **Retry exam evidence**.

Исходный component целиком совпадает с immutable frontend proposal, кроме этого одного hunk. App, API, backend, entitlement, practice content, mobile layout и native assertion/deadline changes не входят в repair.

| Путь | Before SHA256 | Applied SHA256 |
| --- | --- | --- |
| `frontend/src/screens/PreparationScreen.tsx` | `f833211fa7caeff3564844ae8f08b78eef8770b56319c8feb8269e01d46ee71c` | `0a63e84ab9ce69af742c25f9e33f909af510218d3cfe32420c99a154e5b5c451` |
| `frontend/src/screens/PreparationScreen.test.tsx` | `bb8769fc3adaa7c7749e5520c593817248e15ddbc3037dc030f1d2ccf1f4c16e` | `f5033339a95493e3337cccf278171c4049f7446c961328539be723d99705bdf1` |

Оба before/after hashes совпали с root `SAME_SELECTION_REPAIR_BEFORE/AFTER.json` и независимо прочитанными immutable/current files.

## Controls и сохранность native acceptance

- Новый resolved control (`PreparationScreen.test.tsx:40–51`) загружает check, посылает change с уже выбранным value, затем требует сохранённый check, отсутствие Loading и ровно один plan API call. Он непосредственно покрывает обнаруженный lost-ready-state defect.
- Новый in-flight control (`:53–66`) выбирает тот же value до разрешения deferred response и требует последующий check, отсутствие Loading и один call. Это meaningful positive guard сохранности pending request; не утверждается, что он обязательно падал на исходной версии.
- Все исходные16 test bodies/setup/teardown/assertions сохранены **byte-exact**: после удаления только27 добавленных строк новый test file равен исходному.
- Полный native `frontend/e2e/preparation.spec.ts` совпадает **byte-exact** с sealed mobile proposal: SHA`0db6249c15197fe2156cd9f9bda70d10602d942f9b4c25f9cf42f8bf25b0da14`. Значит сохранены все три original scenario bodies и два mobile controls; selectors, assertions, waits, timeout, serial mode и API usage не ослаблены.

## Что требуется дальше

Свежие frontend type/lint/unit/build и завершённые native Demo/Auth на applied hashes. Previous465-unit PASS относится к исходному source и не переносится как fresh receipt на repair. Сохраняется исходный failed run. Восстановленный native сценарий должен доказать фактические evidence→lesson→submit→reload/progress/export и заявленную mobile geometry; до результатов этого review **не** утверждает их PASS, полноту курса, efficacy, официальные scores, production/search acceptance или integration в иной active primary.
