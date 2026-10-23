# Независимый static review evidence-binding

**Условно принять узкое предложение для root RED→GREEN проверки. Подтверждённого blocker в трёх предложенных путях не найдено.** Это статическая проверка, не пройденный API/pytest/PG/full gate. Reviewer не автор repair packet; он автор исходного backend foundation/planner, что исключает blind acceptance исходного дизайна. Source/Git/proposals не изменялись, тесты/серверы/провайдеры не запускались; записан только этот внешний отчёт.

## Pins и сохранность

Пакет `proposals/evidence-binding`: manifest `0c673337c16150a8181c73e6a50bc0d83d3fc0be33c08cf2785aa8c6a70d0cc3`, source-pins `274c9e7dbffcd1b2a82feb9bf92dcc9e90c1b71d7cfd77e4553006229c5ef17d`, unified patch `968640d23e5bda5d6ef4f74f2085f62ca1103c2ea88470d1dc6b57ae77cb565c`.

Независимо совпали **9/9** manifest SHA/размеров, три текущих preimage, три after SHA и восемь context/dependency pins. Все три patches byte-exact совпадают с независимо построенными diffs в объявленном source-pins порядке. Первая попытка сравнения с алфавитным порядком разделов дала false только из-за порядка domain/API tests; объявленный порядок и каждый отдельный patch подтверждены.

| Путь | Before | After |
| --- | --- | --- |
| `backend/app/domain/preparation.py` | `c66f4a31a656f2e664bf90b75e6130085ab31471335103057ca7a610c74cfcc4` | `07cf2c70355847b76affbe72564b80841bad9009af671056e6b38c2d098295b4` |
| `backend/tests/test_preparation_domain.py` | `44a2026015add0eb2d331f12a1ddc905ae186deae33391c478bbf1c71e28a802` | `c2682c6b37be1955cd7453c87b671b69c92b0a238f4b9d5766edd7139240aa5e` |
| `backend/tests/test_preparation_api.py` | `cd8ab75b35869824c998473f085ea64b64ac166e663040a15d463706b35686ff` | `fde8e742aabc908f807937241f7480b9a1260e88faa9465045c874b258e79437` |

Оба исходных test files сохранены **полным byte-exact prefix**, все прежние функции AST-exact. Assertion nodes: domain19→45, API91→111. Новые восемь pure functions дают **21** параметризованный case; две API functions дают четыре semantic cases × неизменный SQLite/PG fixture = **8**. Итого **29 подготовленных новых controls**, не выполненных reviewer. Ранее 30 pure+92 API не изменены; ожидаемые 151 foundation cases — только static arithmetic.

## Проверенные контракты

- `files/backend/app/domain/preparation.py:65–109,235–240`: canonical native non-exam labels исключаются только из preparation projection; native RequirementCheck/result payload не переписывается. Legacy URL binding ограничен таблицей названного exam/type. IELTS dict subscore обязан содержать конкретный band; scalar сохраняет native all-band semantics (`eligibility.py:539–574`).
- `:112–147`: exact-ID выбирает только совместимую exam claim. Парный URL добавляет provenance этой claim, не всех её page neighbours. Legacy URL с нулём либо несколькими совместимыми candidates не выбирает произвольный record. Порядок выбранных claims соответствует исходному source list.
- `:240–278`: unresolved refs остаются unknown; отсутствующий band/неподдерживаемый exam-like legacy label не получает score clearance или starter. Claims с чужим recorded scope, stale/unverified/conflicting состоянием не становятся current. `combine_states`, `_claim_state`, `_policy` независимо **AST-exact**; существующий unresolved conflict block сохранён.
- `:211–224`: SAT total → два starter skills, named Math/R&W aliases → соответствующий starter; IELTS overall → только partial Reading practice, IELTS Reading → Reading. Writing/Listening/Speaking/type/policy не получают чужой starter. Никакого пересчёта официальных баллов или admission decision нет.
- API route не изменён: owned profile, result→run→profile и claim run/result filtering остаются в `routes_preparation.py:210–249`. Shared URL не расширяет доступ к чужому case/run. Новые response controls используют только уже существующий owned synthetic `prep_lab`, без нового auth/subscription/quota обхода.

Pure controls полностью прочитаны (`test_preparation_domain.py:211–380`): shared-page deadline/GPA exclusion, SAT/IELTS family и все четыре IELTS bands, policy/type/TOEFL/entrance labels, ambiguous URL versus ID/ID+URL, wrong known type/band, unresolved reference, scope/stale/unverified/conflicting и resolved/unresolved conflict. API controls (`test_preparation_api.py:683–821`) проверяют реальные HTTP response objects, точные исходные checks/claim IDs/quotes/normalized values/scope, no result/claim rewrite и no extra StudyAttempt/Job. Existing tenant/term/quota controls сохранены, но их PASS здесь не присваивается.

## Наблюдение и ограничения

Сохранённый первый synthetic demo plan действительно прикреплял смешанные IELTS/TOEFL claims к deadline/GPA/type/components. Там **все rows conflicted, policy unknown, lesson_ids=[]**: этот trace не доказывает уже увиденный wrong Reading recommendation. Отдельные conflict-free regressions должны доказать прежний неправильный starter и его repair; авторская оговорка верна.

Поддерживаемая legacy label/type таблица — существующие native labels, не полный будущий exam catalogue. DET/HSK/CSCA и другие будущие label generators требуют отдельного binding contract; metadata Planned не становится готовым курсом либо доказанным требованием. Существующая conservative blocking логика shared-URL conflicts/alternatives/waiver сохранена и не разрешает AND/OR или applicant waiver. Здесь не проверяется HTTP insertion race, полноценный paid production flow или live official-source quality.

## Root acceptance

Сначала root сохраняет actual baseline RED по неизменному app + proposed-tests.patch, затем применяет reviewed source patch и выполняет те же assertions. Нужны fresh native static/full SQLite+owned Unix PG/source-binding receipts на новых bytes, без skip/assertion weakening и без provider calls. Прежний backend full PASS не принимает новую domain implementation автоматически. Browser/runtime ошибки и эта domain binding ошибка — отдельные причины; E2E terminal review остаётся pending до успешных terminal Demo/Auth.
