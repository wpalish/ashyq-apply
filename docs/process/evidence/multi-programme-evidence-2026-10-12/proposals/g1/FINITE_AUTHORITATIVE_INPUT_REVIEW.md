# G1 — finite validation авторитетных входов

12.10.2026. Только статическое чтение `final4` source (`04830101` сообщён родителем). Никаких импортов, runtime, БД, тестов или изменения frozen source. Это дополнительная semantic review после квалификации helper binding.

## Вывод

**Raw finite guard сейчас явно покрывает только `StoredPreparationGraphFields`, но не все авторитетные данные, входящие в graph.** В `_claims`, `_conflicts` и column checklist проверка происходит после Pydantic JSON-mode serialization. Это оставляет условный путь потери nonfinite значений до проверки и хеширования.

Статически подтверждены поля и порядок операций. **Конкретное превращение `NaN/±Infinity` в `None` установленной версией serializer здесь не исполнялось и не подтверждалось.** Поэтому это source-level acceptance gap и гипотеза о потере данных, не воспроизведённый runtime bug. Если текущий serializer сохраняет nonfinite float, существующий `json.dumps(..., allow_nan=False)` уже откажет в этой ветке; полагаться на его конкретный JSON-mode output как на raw-input контракт всё равно не нужно.

## 1. Три точных пути

| Вход | Поле и схема | Порядок сейчас | Возможное последствие при sanitization |
|---|---|---|---|
| `ClaimRow.payload` | `Claim.normalized_value: Any`; bounded `confidence` не является этим полем | `ClaimOut.model_validate(merged payload)` → `claim.model_dump(mode="json")` → `_json_snapshot(...)` | `None`/sanitized вложенное значение проходит finite check. Current/status/scope proof может сохраниться без исходного raw value; manifest digest описывает sanitized view. |
| `ConflictRow.payload` | `Conflict.values: list[Any]` | `Conflict.model_validate(merged payload)` → `conflict.model_dump(mode="json")` → `_json_snapshot(...)` | Исходные значения теряются в digest/quoted conflict. Authoritative `unresolved=True` всё равно сохраняется, поэтому этот путь **не делает conflict current**. |
| `ProgramResultRow.checklist` | `DocumentItem.max_file_size_mb: float | None` в любой из 6 DocumentChecklist locations | `DocumentChecklist.model_validate(result.checklist)` → JSON-mode comparison/selection → `checklist.model_dump(mode="json")` → `StoredPreparationGraphFields.before` | Raw nonfinite уже может стать отсутствующим optional constraint и пройти новый guard; семантическая identity/digest получает другое значение. |

Источники:

- [Claim raw/serialized order](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/api/routes_preparation_graph.py:147) и [normalized_value Any](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/schemas/claim.py:26).
- [Conflict raw/serialized order](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/api/routes_preparation_graph.py:180) и [values list[Any]](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/schemas/claim.py:111).
- [Authoritative checklist before raw loader guard](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/api/routes_preparation_graph.py:121) и [Optional float size](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/schemas/result.py:259).
- [Final4 before validator](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/schemas/preparation_graph_loader.py:27).

## 2. Не преувеличивать влияние

`_claim_state` проверяет verification status, freshness, HTTPS, official/source specificity и covers(scope); самостоятельной numeric-finiteness проверки в нём нет. Поэтому точный referenced IELTS claim с хорошим scope может сохранить `current`, если предыдущие serializers пропустили sanitized normalized value. Это не означает, что G1 рассчитывает admission probability или общий score target: identity всё равно unresolved. [Native claim state](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation.py:159), [Exact proof copy](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation_graph.py:142), [Evidence manifest](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation_graph.py:528).

Для checklist G1 сознательно добавляет `unknown` и `document_predicate_not_projected` даже при current exact proofs. Поэтому **не утверждается, что NaN file-size даёт verified документ/готовность**. Риск здесь — sanitized copied constraint и digest/identity вместо raw-input отказа. [Conservative document state](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation_graph.py:405), [Document identity](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation_graph.py:369).

Malformed claim failure уже уводит programme в unavailable/unknown, а malformed conflict failure — unavailable/conflicted. Эти branches следует сохранить. [Per-slice failure handling](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/api/routes_preparation_graph.py:211).

## 3. Минимальный repair после terminal cleanup

1. В `_claims` проверить исходный **JSON `row.payload`** до `ClaimOut.model_validate`. Не проверять через `json.dumps` весь authoritative merged object: `accessed_at` из колонки — настоящий `datetime`, нормальный для этой схемы.
2. В `_conflicts` так же проверить JSON `row.payload` до model validation; затем сохранять authoritative overrides `claim_type` и `unresolved=True`.
3. В `_stored_fields` проверить JSON `result.checklist` до `DocumentChecklist.model_validate`, сохранив identity/disagreement checks и выбор колонки поверх fallback.
4. Если требуется гарантия и для schema coercion из строк (`"NaN"`, `"Infinity"` в optional float), после model validation и **до JSON mode** добавить узкую recursive проверку native float `math.isfinite` над `model_dump(mode="python")`. В рекурсивной проверке проходить dict/list/tuple и игнорировать корректные `datetime/date/Enum` scalar leaves; existing JSON snapshot check по-прежнему отвечает за сериализуемость. То же нужно для StoredPreparationGraphFields после validation, чтобы optional scholarship/document floats не терялись после coercion.
5. Не менять legacy `Claim/Conflict/DocumentChecklist` Base, native handlers, общие serializer defaults или guards ради G1. Изменение должно оставаться в отдельном G1 loader/router с соответствующими new pins и fresh gates.

Пункт 4 — отдельный typed-coercion boundary. Raw `json.dumps(..., allow_nan=False)` отвергает настоящий float nonfinite, но строка `"NaN"` является finite JSON string; последующее преобразование в float должно проверяться отдельно. Это не повод запрещать слово `NaN` в обычной строковой цитате/Any text.

## 4. Минимальные meaningful controls

Прямые tests read helpers на синтетических row-shaped envelopes избегают проблемы, что PostgreSQL JSON column законно не принимает nonfinite raw numbers. Не следует менять DB codec или ослаблять PG fixtures для их сохранения.

- `_claims`: корректный envelope с `normalized_value={"scores": [nonfinite]}` для `NaN/+Inf/-Inf`; результат empty + failed=True. Соседний finite claim читается корректно. Положительные controls: explicit `None` и finite nested numbers остаются допустимы и не превращаются в failure.
- `_conflicts`: полноценный unresolved envelope с `values=[{"score": nonfinite}]`; failed=True, per-slice unavailable/conflicted. Valid conflict с обычными `None/number/string` values сохраняется unresolved; не исчезает из evidence.
- `_stored_fields`: payload checklist отсутствует, authoritative column содержит valid-identity DocumentItem с `max_file_size_mb=nonfinite`; raises parse failure. Повторить хотя бы одну owner projection и scholarship projection. `None`/finite size controls принимаются без потери значения.
- Typed coercion: optional float поле с raw string `"NaN"`/`"Infinity"` отвергается после validation; ordinary quote string/Any value с текстом `"NaN"` не запрещается без причины.
- Existing unavailable-slice controls остаются: никаких document_actions/requirements/оптимистичного empty success у отказавшего slice, другой selected finite slice не загрязняется. [Existing API acceptance](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:393).

Current new tests `test_nonfinite_or_duplicate_stored_field_snapshots_are_rejected_before_hashing` и `test_nested_nonfinite_observation_cannot_be_serialized_into_missing_evidence` охватывают **StoredPreparationGraphFields requirement observations**, не эти три row input seams. [Current finite controls](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:729).

## Статус

Source binding `final4` по-прежнему согласована; semantic finite coverage этих authoritative seams требует решения родителя после завершения активного full runner. Runtime behavior, фиксация repair и последующие gates этим review не утверждаются. Прежние FAIL evidence, sealed receipts и STOPs сохранены.
