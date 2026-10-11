# Независимый static review mobile-layout

**Условно принять отдельный пакет для применения root после source freeze. Статическая причина F-PREP-MOBILE устранена в предложении; native UI acceptance остаётся PENDING.** Подтверждённого blocker в этих трёх изменённых путях не найдено. Область предлагаемой проверки: **320px и 390px, стандартный размер шрифта**. `<320px`, text zoom и физический notch не приняты и не проверены.

Reviewer не автор mobile/frontend/E2E пакета; он автор backend foundation. Проверка выполнена только чтением сохранённых файлов и вычислением SHA/размеров/сравнением байтов. Source, proposals, Git, тесты, браузер, API, сеть и провайдеры не изменялись/не запускались. Единственная запись — этот внешний отчёт. Сообщённый root backend run не является результатом этого review и не переносится на frontend bytes.

## Проверенные pins и сохранность

Пакет: `exam-preparation-2026-10-11/proposals/mobile-layout`.

- `READY.json`: `23d9f35a8fcb59eff0b23fc2a9c538dd7a6b80e7ef1c16a6715e7ca11ddfda6c`.
- `MANIFEST.json`: `779e67e6c0795a4f12faba1bd69f4337aeaf487f08ec5013dfdda70de5336eb8`; **11/11** размеров и SHA совпадают.
- `mobile-layout.patch`: `ece267daca36e3240e286a7bc6d6d1c4536190704cc58be32917a457feb79711`; независимо построенный diff original→files совпадает **byte-exact**, ровно три пути.

| Путь | Текущий source / original preimage | Предложенный SHA256 |
| --- | --- | --- |
| `frontend/src/App.tsx` | `5ae85ec856ec796ec5a7c63ce50f74c0ce4ebba45d16d87c1f88fe97d6167541` | `5cd7408024f9732cfd661a78e3a8f2f45c01267117a6d50dee9b24a1f9328e26` |
| `frontend/src/styles/unimatch.css` | `73a37964ea1e186f89e05682f58b8157267cedf4119fc4828980a5f9c257a035` | `a33a9a3dd125b907c84d8e0c9b3c5f986ce5d7b56b8e3a0be1d19b300a819c04` |
| `frontend/e2e/preparation.spec.ts` | `b3e092f8409bca0da2b731642e82886c91dcc497ac51233494a79233f2bf2e09` | `0db6249c15197fe2156cd9f9bda70d10602d942f9b4c25f9cf42f8bf25b0da14` |

Три текущих preimage и шесть style/helper/config dependency pins из `SOURCE_INPUTS.json` совпали с owned source при чтении. Root-authored original E2E и `ROOT-preparation.spec.ts` также совпали. Ни один Git head reviewer не проверял.

Весь original E2E prefix **5 311 байт**, включая все **три** исходных test bodies, сохранён без единого изменения. Новая версия имеет **пять** test declarations: только два appended controls, без skip/fixme, API mock, изменения прежних assertions или deadline. Это static count, **NOT_RUN**.

## Layout и доступность по коду

`files/frontend/src/App.tsx:95–102,299–314` сохраняет шесть маршрутов и их handlers/active state, добавляет компактные видимые Home / Find / Plan / Prepare / Docs / People. Полные accessible names задаёт `aria-label`; desktop label остаётся прежним. Focus/ownership/case/lesson/UUID код не затронут.

`files/frontend/src/styles/unimatch.css:390–408` меняет пять колонок на **шесть** `minmax(44px,1fr)` и одну объявленную строку `max(44px,3.25rem)`. При стандартном 16px root и нулевых safe insets арифметика даёт 52px строку, 65.8px бар, 48.67px ширину каждой цели при 320px и 60.33px при 390px. Это расчёт CSS, не измерение браузера. Compact text имеет 12px, nowrap и отдельный полного имени label; новый native control должен подтвердить отсутствие clipping.

Одна переменная `--mobile-nav-height` теперь задаёт fixed sidebar height, `.main` bottom reserve и `html` scroll padding; reserve добавляет 0.75rem. Global `box-sizing:border-box` и порядок stylesheet imports проверены. Safe-area-bottom входит и в высоту, и в нижний padding; left/right insets независимы. `.screen .btn` получает min-height44px; прежние motion/focus/reduced-motion декларации вне этих hunks сохранены.

**Граница поддержки:** README описывает 320/390 arithmetic, но его фразу «one row ... at max900px» нельзя читать как гарантию любой меньшей ширины. Шесть 44px minimum columns плюс padding/gaps при стандартных параметрах требуют примерно 292px; ниже неизбежен overflow. Root согласовал итоговую квалификацию **>=320px / default font**, `<320px` и zoom вне acceptance. Ненулевые hardware safe insets этим packet не эмулируются.

## Предложенные native проверки

- `preparation.spec.ts:88–150`: реальные DOM rectangles, computed columns/rows/padding/reserve; шесть полных accessible names и компактных labels; width/height>=44px, font>=12px, labels в своих кнопках, без переноса/clipping. 390px и 320px, JSON attachment, viewport restoration. Default `expect.poll` не ослабляет deadlines.
- `:152–195`: реальный original IELTS lesson GET, три настоящих выбора, enabled Submit/Restart, настоящий scroll и poll по геометрии/centre hit-test **последнего Restart**. Затем Restart должен быть целиком выше fixed bar с8px clearance, height>=44px и в viewport; Submit имеет bounding-box и проверку **нижней границы**. JSON и screenshot сохраняются. Нового POST/attempt этот control не делает; retained три tests продолжают проверять реальный submit/replay/score separation/reload/export.

**Не завышать результат:** отдельный 390/320 control не проверяет Submit top>=0, centre hit-test или measured height44px; retained practice test реально кликает Submit в штатном mobile project. Поэтому новая геометрия доказывает только заявленные Restart reachability и Submit bottom clearance, если пройдёт. Физический notch, 200% text zoom, все другие экраны и клавиатурное перекрытие не покрыты этими двумя controls.

## Что остаётся до acceptance

Root применяет только три exact paths после завершения freeze и повторного preimage check. Нужны свежие native frontend type/lint/unit/build и demo/auth Playwright receipts на applied bytes, включая оба новых mobile controls. До этих результатов **mobile acceptance PENDING**, не PASS. Backend receipt переносится только по отдельной проверке неизменности его consumed source; этот review не делает такой перенос и не утверждает deployment/full product/search quality.

Этот отчёт закрывает только **статическую** часть ранее найденного F-PREP-MOBILE в оговорённых пределах. Исходный `frontend-contract-review.md` и его более ранний verdict сохранены.
