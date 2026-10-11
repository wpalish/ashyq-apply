# Preparation evidence/details/mobile — independent static review

**2026-10-11 · QUALIFIED STATIC ACCEPT · runtime acceptance PENDING.**

Конкретного блокера в четырёх предложенных путях не найдено. Разрешение на применение остаётся у root. Автор и reviewer не запускали этот пакет, приложение, API, браузер, тесты или провайдеры. Reviewer ранее авторствовал backend foundation, но не этот frontend-пакет; это независимая проверка UI-изменений, а не слепая приёмка всей системы.

## Точная привязка

Пакет: [preparation-ui-details](../proposals/preparation-ui-details/README.md). Root сообщил freeze `731e241c`; Git здесь не проверялся. Независимо сверены SHA256/размеры всех **13/13** записей MANIFEST, четыре текущих preimage, четыре proposed файла, четыре dependency pin, три observation pin и весь unified diff. При финальной проверке preimage текущего owned source совпадали. Diff, повторно собранный в заявленном порядке, побайтно совпадает с patch.

| Артефакт | SHA256 |
| --- | --- |
| READY.json | `ae1c5462715db5b52c7b8c14e13c7e28337cd6058e0aa7f79709ddc8455447db` |
| MANIFEST.json | `0407bcaab17b99396ba80c8a807508d53046bb718144d7322f67778037737001` |
| preparation-ui-details.patch | `b57c91c80ef97645ccba71bcee4112f480104e060e4b9d30fc2b3b0e7d343509` |

| Repo path | Preimage SHA256 | Proposed SHA256 |
| --- | --- | --- |
| frontend/src/screens/PreparationScreen.tsx | `0a63e84ab9ce69af742c25f9e33f909af510218d3cfe32420c99a154e5b5c451` | `bed6bd70d11c203bfdb7ca68b13b4a3859009298dab185936a3a5d96b04ef4bb` |
| frontend/src/styles/unimatch.css | `a33a9a3dd125b907c84d8e0c9b3c5f986ce5d7b56b8e3a0be1d19b300a819c04` | `8977b036f008c4f8c69a659648c6248f377873798b81c9dd0b1fb3f30441f85a` |
| frontend/src/screens/PreparationScreen.test.tsx | `f5033339a95493e3337cccf278171c4049f7446c961328539be723d99705bdf1` | `74b0794cb51948890e993f295e8c4cb26e67af52e8da41de2724b0c42fd5e502` |
| frontend/e2e/preparation.spec.ts | `0db6249c15197fe2156cd9f9bda70d10602d942f9b4c25f9cf42f8bf25b0da14` | `35fcc0c7812eb3688832158998103310232803e30ec91a36426e7c525adf0851` |

## Что сохраняется

- `PreparationScreen.tsx:160,203–220`: нативный закрытый `details` сохраняет полные original quotation, claim status, source URL/href, recorded scope, programme/intake и дату чтения. Published/entered values, published scope, requirement/policy/evidence statuses и предупреждение об отсутствии доказавшего источника остаются сразу видимыми. `N` считает записи claims плюс непарные ссылки, не независимые сайты или подтверждённые требования. Disclosure сам не подтверждает применимость источника.
- `PreparationScreen.tsx:303–310`: изменены классы fieldset/label; исходные radio name/value/checked/onChange и disabled/frozen семантика сохранены. Код владения profile/case/intent, поздних ответов, same-value selection, immutable UUID/retry, submit и official-score separation не изменён. Новых API, writes, entitlement/quota или catalogue правил нет.
- `unimatch.css:314–336`: правила ограничены preparation screen, разрешают перенос полного текста URL/кнопок/chips и снимают intrinsic flex minimum. Нет глобального clipping/скрытия overflow/удаления фактов. Choice имеет min-height44px, native radio, checked/focus styles; новых анимаций нет. Существующие reduced-motion/nav/safe-area правила не меняются.
- Binding неправильно назначенных claims — отдельная backend-ошибка. UI хранит полученные записи целиком. Отдельный [evidence-binding review](evidence-binding-review.md) проверяет её узкое исправление; disclosure не заменяет эту интеграцию.

## Сохранение и смысл контролей

Независимая проверка diff обнаружила в component tests только вставку: **18 старых →19 деклараций**, без удаления/замены исходных строк. Новый контроль проверяет default closed, quote в DOM/скрытую видимость, native open/close, сохранённый scope, точные hrefs и видимое предупреждение. Все прежние same-selection/ownership/retry assertions сохранены.

Native файл сохраняет целый **13 218-byte prefix**, SHA `0db6249c15197fe2156cd9f9bda70d10602d942f9b4c25f9cf42f8bf25b0da14`: **5 прежних →6 деклараций**. Новый `preparation.spec.ts:198–266` проверяет реальное stored evidence normal open/close, точные catalogue URL text/href из API, `window.innerWidth==requested`, отсутствие горизонтального document overflow и границы ссылок при **320/390**. Для каждого из трёх starters проверяет centre hit-test, обычный click, успешный настоящий lesson GET/heading и высоту choices≥44px. Viewport восстанавливается в `finally`. Нового POST нет, поэтому сохранены исходные attempt/progress-count предусловия.

Нет force-click, нового mock, skip, ослабления timeout/assertions или изменения старого viewport. Первоначальный normal mobile Start Reading сценарий при412px сохраняется побайтно. Новые width/hit-test проверки дополняют этот путь.

## Приёмка ещё не завершена

Сохранённый второй Demo run `20261011T131348Z-demo` действительно завершился с ошибкой обычного mobile click. Trace подтверждает configured412×839 и последующие822×1674 snapshots; точный overflowing node не доказан. Данный CSS — проверяемый ремонт этого класса проблемы, **не доказанный runtime результат**. Исходная ошибка и её receipts остаются.

Root должен применить только совпадающие preimage либо выполнить узкий semantic merge при drift; затем свежие consumed frontend static/unit/build, завершённые native Demo/Auth и обе обязательные полные backend SQLite/owned Unix PostgreSQL фазы после backend binding change. Expected counts не являются PASS. Этот review закрывает только статическую часть: физический notch, <320px, text zoom, полный accessibility audit, полные курсы, официальный score, deployment и live search quality здесь не подтверждены.
