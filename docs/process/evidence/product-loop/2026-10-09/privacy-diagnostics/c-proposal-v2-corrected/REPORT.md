# Diagnostic privacy proposal — исправленный sibling

Статус: **EXTERNAL_CORRECTED_PROPOSAL_NOT_APPLIED**. Исходный C9 пакет с READY `9a2607d2007e4ae89516a629a79b61f2ef295018d10c9a9105e22aa9dfe16846` сохранён без изменения всех 450 selected records. Его material rejection не отменяется: root и A обнаружили реальную ordinary off-site regression. Новый пакет заменяет предложенные байты для review, не переписывает историю и не применяет primary.

Ошибка возникла из слишком широкого replacement: `failed_url`, определённый только внутри `not res.ok`, был перенесён также в успешный off-site branch. Свежий successful response вызывал `UnboundLocalError`; после предыдущего 404 branch повторно использовал URL того failed target. Дополнительно C9 изменил PageOutcome.detail **всех** document fetch failures; ordinary изменение не было необходимо для privacy boundary.

## Минимальная коррекция

1. В `web_requirements.py` успешный off-site PageOutcome снова использует **current target.url**, как исходный source. Privacy failure branch продолжает использовать safe diagnostic identity; ordinary off-site error/detail/category/counts/retry behavior сохранены.
2. В `web_documents.py` добавленный typed detail остаётся только для `REFUSED_PRIVACY`. Все обычные fetch failures возвращают прежний empty detail; their original errors/retry/counts/PageOutcome fields совпадают с legacy contract.
3. В существующей P4 группе six-body test добавлены семь ordinary native controls: successful off-site первым target и после 404, затем document 404/robots/timeout/blocked/too-large. Cases исполняются до assertions и сохраняют полные observations, даже если свежий off-site branch бросает исключение. Это реальные adapter methods с scripted FetchResult; HTTP statuses тут заданы fixture, сеть не проверяется. Основной P6 отдельно сохраняет реальный MockTransport404 control.

Две semantic source correction paths с before/proposed SHA находятся в `correction-manifest.json`; полный before-primary/proposed manifest и patch — в `proposal-source-manifest.json`/`proposal.diff`. Полный proposed set остаётся **13 paths (11 app + 2 tests)**. Семь paths отличаются от C9: две semantic corrections, три source import-grouping normalization, старый hop-test import grouping и новая P4 body/import grouping. Остальные шесть proposed paths C9 byte-exact.

## Одни и те же шесть bodies в трёх source modes

| Source mode | Полный шестигрупповой результат | Ordinary controls внутри P4 |
|---|---|---|
| Original primary privacy baseline | **5 semantic privacy FAIL / 1 PASS** | Оба off-site cases и все пять document diagnostics совпадают с legacy |
| Bad C9 OFF | **1 semantic ordinary regression FAIL / 5 PASS** | Fresh UnboundLocalError; stale URL=prior404; пять detail mismatch |
| Corrected ON | **6 PASS** | Exact current admissions URL; prior404 retry preserved; полные outputs пяти ordinary failures совпадают с legacy; privacy typed detail retained |

`ordinary-control-receipt.json` выводит результаты из actual P4 raw observations. C9 OFF последовательно вызвал оба requirements branches и все пять documents failures перед assertion: exception первого branch пойман только для сохранения evidence/исполнения остальных controls, затем test FAIL. Это не bypass и не ожидаемая product exception. Исправленный ON не бросает его. Privacy refusal остаётся typed partial, без invented no-program-list/absence. Existing 9 privacy native seams внутри P4 по-прежнему исполняются; новая группа не добавлена.

Final native guards во всех modes: DNS/connect/listen/DB/child_process **0**. Safe initial P2 resolver calls **2**, mocked initial HTTP **1**, poisoned hop calls **0**; final refused page status None. Обычные CMS URL/query/status/reason, query budget6/sharedTrue/reserve1, ordinary traceback/audit/rethrow, lease/cancel semantics P6 сохранены. Current154 app и exact20 baseline source всё ещё unchanged; это verified source-file scope, не whole Git tree/HEAD.

## Backend-equivalent static gates

Root правильно сузил qualification прежнего packet-root Ruff PASS: `config/ruff.toml` + `proposed/backend/app` не давали такое же auto first-party discovery, как actual backend. Этот sibling сохраняет старые tool diagnostics. Backend-equivalent `ruff check` в изолированном **runtime/on/backend**, с exact normal `ruff.toml` в этом backend и actual `app/...`/`tests/...` paths, воспроизвёл **5 I001**. Только import normalization исправила их. Никаких новых known-first-party/rule overrides.

На финальных байтах: **backend Ruff13 PASS, format13 PASS, mypy154 PASS**. `backend-format-equivalence.json` подтверждает для всех 13 файлов одинаковые scoped import symbols/aliases и одинаковый non-import AST до/после normalization; bytes изменились у пяти файлов. Сравнение относится к pre-backend-format corrected source, а не утверждает отсутствие двух semantic corrections относительно C9. Конфиги совпадают с primary. Native three-mode pair повторён после финального grouping; final test SHA в receipt.

## Сохранённая история и пределы

Сначала three-mode native proof прошёл на corrected bytes до backend grouping; raw в `logs/pre-backend-grouping/`. Затем backend-normalized exact pair повторён: всего **6 native executions × 6 groups = 36 group executions, 24 PASS / 12 FAIL / 0 pytest errors**. Это две authoring тройки, не 36 независимых privacy cases. `logs/*-issued.log`, execution JSON, JUnit, P1–P6 observations сохраняют actual argv/output. Старый C9 package со всеми исходными retention/harness/import/expanded-catalogue failures untouched.

Одна новая authoring error сохранена отдельно: host `python3` (3.9) не смог parse product Python3.12 `type PageRecorder = ...` при static AST comparison. Проверка повторена существующим product Python3.12; это grammar/setup failure, не native defect. Earlier package-root static PASS — исторические результаты; final qualification определяется backend-equivalent logs.

Исполнялись обычные imports в трёх owned source-only `.py` snapshots и safe env, memory session/store spies, tmp synthetic cache, MockTransport/scripted results. Никакие .env/private DB/data/dependencies не скопированы; corpus/registry assets не нужны отказным branches и не копировались. SQL/API roundtrip в **этом C пакете NOT RUN**. A отдельно готовит actual SQL/API same-body peer; его proof нельзя автоматически приписывать этому пакету или corrected source без точного rebind. Исправленный existing old hop-test body здесь NOT RUN; A/root проверяют отдельно. Core/full/production/quality/compliance здесь не заявляются.

Reset-token safety-stopped task не читался и не исполнялся. Provider/model/live/university/worker process/ports/CUA/Git/primary writes — NOT RUN/NONE; STOP read-only unchanged. Интеграция исключительно у root после независимого corrected-source review в новом HANDOFF task и требуемых gates.
