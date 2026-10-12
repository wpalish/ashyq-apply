# G2: terminal clock после native term SELECT

**SEALED_SOURCE_PROPOSAL / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Root отдельно разрешил только два application paths. Existing immutable persistence/test/frontend packets и seals не меняются. App, tests, migration, helpers, Git и network здесь не запускались.

## Два разрешённых пути

- [routes_shared_route.py](files/backend/app/api/routes_shared_route.py), preimage `f6dc485b26b9af6d04ba6e4a83d1da28ff1146b47ac3cab51c16d825d7bfb3d5`.
- [test_shared_route_api.py](files/backend/tests/test_shared_route_api.py), preimage `13e04e275e8b3ffd263f513f7e382a53bd736eec4fc687ab8c5f179c209b3636`.

Оба полных исходника сохранены в `originals/`; exact diff — [DELTA.patch](DELTA.patch). При metadata проверке root preimages совпадали с сохранёнными bytes. Root сообщил `92199be5`; Git независимо не читался. [SOURCE_ONLY_CHECKS.json](SOURCE_ONLY_CHECKS.json) фиксирует AST и SHA, [SEAL.json](SEAL.json) — конечный owned manifest.

## Минимальное исправление

Private `_require_preparation` возвращает уже вычисленный native `PreparationAccess` вместо `None`. Непосредственно после final native Subscription SELECT новая команда получает **fresh UTC `accepted_at`**. Сначала проверяется local day preview; затем те же observed `starts_at`/`ends_at` (`starts<=accepted_at<ends`) без второго SQL или повторного allocation. `development_only` сохраняет действующее native development поведение; missing term bounds для обычного доступа отказываются. Same error code/messages 402/409. DTO, source/ref/legacy bindings, owner, canonical UUID replay и export остаются прежними; replay расположен до этого gate.

## Два meaningful controls — ещё NOT_RUN

Новая parametrized function проверяет `local_midnight` и `term_expiry` в том же approved migrated synthetic lab. Clock seam меняется в `after_cursor_execute` после **реального второго Subscription SELECT** команды. First SELECT — пересчитанный preview, второй — final native term gate. Preparation helper, access DTO, models, source loaders и commit не mock/substitute. Нет sleep или внешних запросов.

Expected: midnight → 409 `shared_route_preview_stale`; expired observed interval → 402 `preparation_subscription_required`; ровно два Subscription SELECT (без дополнительного terminal query/loop), no DML, полный synthetic DB snapshot неизменен. Старый midnight test меняет только observation iterator с 2 на 3 timestamps для нового final observation. Остальные старые class/function AST в тесте byte-source семантически не меняются; metadata показывает ровно один изменённый старый test node и один новый parametrized node.

Root может сначала применить только тестовую часть к original API для настоящего pre-repair failure, сохранить first-failure receipt, затем применить API и повторить source-bound gates. Эта бумага не утверждает, что reproducer действительно падал или repair проходил: tests/imports здесь отсутствовали. Full stage/native/public-product acceptance требует root actual receipts.

Дополнительные retirement tests, schema/model/routes wiring, migration и frontend в этот пакет не входят. Независимый source review сохранён отдельно в `../G2_APPLIED_BACKEND_COHERENCE_REVIEW.md`; его замечания не расширяют разрешённый delta.
