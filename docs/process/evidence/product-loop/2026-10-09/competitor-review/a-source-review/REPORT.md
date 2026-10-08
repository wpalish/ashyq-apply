# Независимое review frontend next-action patch

**ACCEPT для bounded source patch против 863a9c64. Материальных новых bugs в проверенных ветках не найдено.** Это read-only code review; reviewer не запускал тесты, full, сервер или API. Root сообщил targeted 64 PASS, затем исправил неполный тип нового test fixture; окончательные typecheck/lint/core/full пока не подтверждены этим review.

Проверенные переходы:

- HomeScreen.tsx:10–38: needsAttention проверяется раньше active и наличия чеклистов. Stale running, failed/dead/cancelled и retryable_failed направляют к Progress; законченный пустой поиск также не предлагает немедленно начать заново. Наличие чеклиста означает возможность работать с ним: текст прямо говорит, что это не application-ready. Если один выбранный programme без чеклиста, переход остаётся в Plan.
- DocumentsScreen.tsx:38–41,99–164: stale/stopped подавляет ложный busy; существующие partial checklist и unresolved остаются доступны. Calendar больше не скрыт за условием withChecklists: он открыт, когда current отсутствует, и включает результат с известной датой до сбора документов. Empty CTA отправляет selected→Plan, otherwise→Find. Утверждения о загрузке/отправке заявления не добавлены.
- store.tsx:707–716 → ApprovedScreen.tsx:70–72 → App.tsx:438: false при отсутствии run и отказе API, true только после принятого ответа. Навигация к Documents обусловлена true; ошибка/402 остаётся в прежнем fail/paywall механизме. Уже собранные checklist можно открыть без новой сети; queued/running запрещает повторный запуск.
- ShortlistScreen.tsx:106–117,462: оба сохранённых состояния approved/maybe теперь вызывают своё текущее решение, существующий toggle переводит их в undecided. Title явно описывает Remove from your plan; approved больше не понижается скрыто до maybe. Заметки передаются без изменения.
- SourcesScreen.tsx:13–16,64–71,148–151: run.errors и run.unknowns сохраняются в Research limitations; отсутствующие per-result вопросы не объявляются отсутствием непроверенных требований. Кнопка ведёт к Progress. Старое Nothing outstanding удалено; конкретные неизвестные факты не заменяются догадкой.

Тесты проверяют нужные ветки, а не только наличие компонентов: новая JourneyScreens покрывает stopped/stale precedence, partial disclaimer, один отсутствующий checklist, queued collection, empty/undecided Plan, оба accepted исхода и календарь без checklist. Store tests проверяют реальные boolean результаты API success/failure и no-run; Shortlist tests проверяют вызов undecided с сохранением notes; Sources test сохраняет обе разновидности run diagnostics. Существующие assertion bodies в diff не ослаблены. Новый fixture тип был поправлен root, это не изменение acceptance.

Известные follow-up за пределами минимального patch: Shortlist zero-results по-прежнему не читает run и предлагает Start research; ResultDetail Documents всё ещё говорит approve this row, хотя Plan принимает maybe. Эти исходные ограничения сохранены в a-flow-audit и не являются новыми регрессиями текущего diff. Источник lifecycle теперь достижим через Home/Progress. Review не закрывает их как исправленные и не означает launch readiness.

Точные 7 application + 4 test source pins — source-pins.json. reviewed.diff фиксирует tracked delta; новый JourneyScreens прочитан отдельно и имеет собственный SHA. Primary/Git write/DB/live/provider/model действий — 0.
