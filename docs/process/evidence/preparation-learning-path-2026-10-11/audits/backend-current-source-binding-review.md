# Current-source reuse binding — backend gate

**Вердикт: VALID_BACKEND_SOURCE_REUSE_BOUND_BY_HASH.** Сохранённый [full backend acceptance](backend-full-terminal-review.md) применим к текущим consumed backend bytes после узкой UI правки. Это separate saved/source-hash review, без новых app/test/Git/runtime/network/provider действий. Предыдущий full review/seal не изменены.

## Независимая проверка

- Root binder: `backend-current-source-binder.json`, reported source `36084fa52ae036eb94644298f2e3f7ad75b8ffaf`. Reviewer не запрашивал Git; conclusion связан с current filesystem hashes и saved maps, а commit metadata явно root-reported.
- **Все604** closed backend consumed paths заново совпали по SHA256 с current source; закрытые SQLite/PG maps равны. **Все566 expected pins** совпали; missing/drift=[]; current helper19 pins тоже совпали. Existing full result остаётся 4 883 unique0FES в каждой фазе, без повторного backend исполнения.
- Pre/post whole-source maps обе641 paths. Delta ровно **2 paths**: `frontend/src/styles/unimatch.css`, `frontend/e2e/learning-path.spec.ts`. Все current641 postmap hashes совпали. Оба changed paths отсутствуют в backend consumed map; API/content/calendar/types/backend guards не изменены.
- Root-owned correction before/after snapshots, receipt и patches сверены с current bytes. CSS добавляет ровно `min-inline-size:30rem` к semantic teaching table внутри существующего overflow-x:auto region. Native spec добавляет ровно четыре keyboard lines после existing focus assertion: ArrowRight/scrollLeft>0, ArrowLeft/scrollLeft0. Earlier API/history/calendar/Academics/320-overflow native controls остаются в исходном теле.

## Binding и пределы

Backend reuse не переносит первое UI native PASS на новые CSS/spec bytes. Root описал исходный screenshot320 с трёхстрочным переносом SAT formulas; correction направлена на внутренний table scroll и не является доказательством readability до свежего native/visual review. Новый control реально должен проверить keyboard scrolling, а global overflow assertion остаётся. Это page/default-font320 scope, не physical notch/zoom или viewport<320 acceptance.

Fresh static/frontend gates root сообщает PASS; новая native Demo/Auth/visual acceptance остаётся отдельной до terminal receipt. Этот artifact не делает нового UI PASS, production/deployment, учительского/ученического результата, official-score или search-quality claim. STOP/UNSCORED не изменялся. Для backend нет конкретной причины повторять неизменённый18-minute gate: source, tests, helper/guards и exact required pins сохранены; acceptance ограничен прежним frozen local engineering scope.

[Exact reuse pins](backend-current-source-binding-review-pins.json) сохраняют обе старые full review hashes, binder/input/source/correction pins и пустой final_recheck_issues.
