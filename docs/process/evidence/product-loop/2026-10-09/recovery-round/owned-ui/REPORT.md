# Recovery UI — пять synthetic captures

**OBSERVED PASS для пяти ограниченных критериев.** Native CUA Chrome проверка выполнена после explicit root go на `http://127.0.0.1:5173/#/shortlist`. Пять JPEG screenshot + AX + DOM geometry, action/reload записи и хэши находятся в этом пакете. Optional zero-results stopped / new-no-run browser — **NOT RUN**, owned seeds для них не было.

## Версия и fixture

Root receipt связывает preview с tested source `c7ece3c0a057a4fe6a8b8b5e43c3b17c8338cbd4`. Все **16 applied source SHA-256** при нашем read совпали; точная связь с source/fixture/processes/delta/targets/cleanup receipts сохранена в [actual-source-binding.json](./actual-source-binding.json).

Initial whole snapshot SHA `7d2aac5dd661b438445f72d1b4dbb4ad50a80ab06f46ce8835b6cc971cc552eb` относится к pre-full manifest. Native E2E затем изменил ровно38 declared PNG outputs; delta связан отдельным hash. Этот UI отчёт **не утверждает**, что нынешнее физическое дерево равно initial whole SHA. Старые PLAN.md/source-pins.json — история подготовки, а не binding выполненного UI этапа.

Root владел fresh isolated `runtime/checks.db`: provider-none, auth-false, demo-true, noWorker, cancelled runs,20 retained results. В checked UI выбран synthetic case `4b7d433f0ab44195b3781049834af00c`, единственный run согласно receipt — `38294441572543e595faa7acd3192ca0`. Run ID напрямую в проверенном UI не отображается: связь основана на pinned owned receipt и видимом selected one-run case; DOM value case после reload совпал. KU Leuven/BSc Informatics — result `2e11209cd78e4f258764663c2fde95f5`, checklist null; Groningen — `2b90714b94454d84b0352e800291682a`, considering/haslist. Все числа и университетские условия в этих экранах — synthetic fixture, не факты реальных университетов.

**Квалификация остановки:** clone меняет stage/cancelled; сохранённый stage_state остаётся completed. Поэтому Progress показывает100%/done рядом с Research cancelled. Проверена synthetic cancellation branch с retained results, навигация и видимость; это не midrun partial-stage или worker cancellation доказательство. DB/fixture не исправлялись.

## Что наблюдалось

| Capture / действие | Итог и наблюдение |
|---|---|
| [01 desktop Find](./captures/01-desktop-find-stopped.jpg) | **PASS:** Research needs attention и View research progress видны; локальный Leuven query, active chip,1of20 и KU card retained. Page client/scroll widths1131/1131. Полная карточка ниже fold — обычный vertical scroll |
| [02 desktop Progress](./captures/02-desktop-progress.jpg) | **PASS:** native View research progress click → `#/progress`, Research cancelled, тот же выбранный synthetic one-run case |
| [03 phone Find](./captures/03-phone-find-stopped.jpg) | **PASS:**390×844, document/body clientWidth=scrollWidth=390. Recovery button rect x33/y690.77/w189.57/h43.20 внутри viewport. Notice и Leuven filter/1of20/KU находятся в одном UI состоянии; filter/card ниже fold, доступны обычной прокруткой. Для этого состояния сохранён один full-page screenshot390×1935 |
| Phone native recovery click | **PASS:** `#/progress`, Research cancelled,390 widths и выбранный case. Отдельные AX/geometry записи без шестого screenshot: `03-phone-progress-action.*` |
| [04 desktop KU Documents](./captures/04-desktop-ku-missing-list.jpg) | **PASS:** точный KU detail, Documents selected; null-list подсказка полностью в viewport, x291.62/y629.48/w755.77/h82.70 |
| Native phone reload | **PASS в checked scope:** same case DOM value,20 result card IDs, KU остаётся Save, Groningen остаётся Saved, attention остаётся. Query пустой после remount/reload — ожидаемый ephemeral state, не потеря backend данных. Запись `reload-state.*` |
| [05 phone KU Documents after reload](./captures/05-phone-ku-missing-list-reload.jpg) | **PASS:** повторно открыт точный KU result/Documents через UI. Hint полностью виден после native scroll: x58.59/y345.62/w272.81/h158.29; document/body390/390; текст не обрезан |
| Optional zero/no-run | **NOT RUN:** нет соответствующей owned seed. Unit coverage root не превращается в browser observation |

Финальный текст подсказки использует **“Chosen by you” / “Considering”**, затем **Plan / “Collect documents”** и явно говорит: “A collected checklist does not mean an application is ready.” Старые ожидаемые Yes/Maybe и Review research в PLAN не являются фактически проверенными labels; observed recovery label — **View research progress**.

В phone screenshot05 видны переносы вкладок и полный текст подсказки. Обе проверенные phone страницы не имеют горизонтального page overflow. Это проверка конкретной ширины390, а не всех устройств, масштабов или accessibility compliance. Full-page03 включает fixed bottom navigation в capture; geometry относится к исходному viewport844, не к высоте composite картинки.

## Evidence и cleanup

- [observations.json](./observations.json): конечные результаты и NOT RUN.
- [screenshot-manifest.json](./screenshot-manifest.json): пять реальных JPEG размеров/байтов/SHA-256; image bytes не редактировались.
- `captures/capture-events.json` и `action-events.json`: порядок действий и файлов.
- Для каждого screenshot есть полный `.ax.txt` и read-only DOM `.geometry.json`.
- [cleanup.json](./cleanup.json): исходный1131×998 viewport восстановлен через reset; единственная own Chrome tab1010110663 закрыта. User/root IAB UniLight не читался и не менялся.
- Root preview cleanup receipt связан в actual-source-binding: root остановил свои процессы; этот агент не запускал и не останавливал порты.

Одна automation попытка использовала desktop Find20 label после переключения viewport; свежий AX показал phone Find. Не было blind retry, app defect или state write. Документированная browser binding была получена перед viewport capability. Screenshot bytes оказались JPEG; final extensions/metadata приведены к JPEG без изменения пикселей.

Не выполнялись start/retry/collect/decision/note/API writes, SQL, test jobs, primary/Git/HANDOFF/STOP edits, accounts/terms, external links или provider/university/AI actions. UI selection synthetic case и поиск Leuven выполнялись только native controls. Этот результат не доказывает production/auth/live поиск, качество университетских фактов, private-product flow, превосходство над конкурентами или полный продукт.
