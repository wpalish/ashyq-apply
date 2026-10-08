# Повторное чтение после параллельных правок

Исходные REPORT.md, findings.json и source-pins.json сохранены. Финальная проверка обнаружила изменение пяти файлов; отрицательный результат сохранён, поэтому здесь нет утверждения о неизменном frozen source. Правки сделал не этот reviewer.

- FLOW-01 частично закрыт: Home теперь отправляет needsAttention/empty completed research в Progress (HomeScreen.tsx:10,22). Find/Shortlist по-прежнему не читает run (ShortlistScreen.tsx:42,96), Sources не учитывает run.errors/unknowns (SourcesScreen.tsx:14,142). При пустых per-result unresolved строка «Nothing outstanding» остаётся; именно эту часть следует проверить до запуска.
- FLOW-02 исходное approved→maybe исправлено: ShortlistScreen.tsx:462 передаёт approved для approved и показывает title «Remove from your plan». Теперь действие снимает решение через существующий toggle; это явный выбор removal semantics. Runtime проверки не выполнены.
- FLOW-03 исходный переход после отказа исправлен: store.tsx:707 возвращает boolean, ApprovedScreen.tsx:71 вызывает onCollect только при true. Подсказка Documents в ResultDetail.tsx:355 всё ещё требует approve, хотя Plan принимает approved+maybe; прямого Open plan внутри деталей пока нет.

Новые SHA — source-pins-reread.json. Это узкое read-only повторное чтение параллельной реализации, не тестирование и не приёмка запуска. Primary/Git/API/network/provider/model действий — 0.
