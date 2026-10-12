# G2: сохранение черновика и неизвестного результата PUT

**12.10.2026 · SOURCE_ONLY · RUNTIME / NATIVE REPRO NOT_RUN.** Root сообщает замороженный источник `26766a3d`; Git здесь не запрашивался. Проверены фактические исходники и принятый контракт G2. Приложение не импортировалось, tests/runtime/browser не запускались. Исходный `G2_SHARED_ROUTE_REPORT_DRAFT.md` (`e2fee9e8748907c6996824befcbca4b017837098080c025f20ebb26e193d1e1f`) и его pins не изменены. Полный backend gate: SQLite завершён по сообщению root; PostgreSQL ещё RUNNING.

## Реализованная граница

`draft`, `pending`, original write body и UUID существуют только в React state/ref: [SharedRoutePanel.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:252). Первый save создаёт UUID один раз; ошибка сохраняет body; повтор использует тот же `pending.body`: [sendWrite](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:334), [retryOriginal](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:367). Current GET сопоставляет receipt с этой точной in-memory командой: [readCurrent](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:285).

Внутренние вкладки подготовки сохраняют SharedRoutePanel: он скрывается через `hidden`, а не размонтируется: [PreparationScreen.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/PreparationScreen.tsx:326). После принятого save новый mount/reload читает server-backed current/history. Это persistence принятого плана; несохранённый form draft и неразрешённая команда не восстанавливаются.

## Конкретный source scenario

1. Профиль сохранён, profile `dirty == false`. В Shared route ввести личные даты, буферы, общий budget, выполнить preview/save.
2. После network error / 503 виден uncertain; исходные UUID/body остаются в текущем компоненте.
3. Нажать Home, затем вернуть Exam preparation. [App условно рендерит PreparationScreen](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/App.tsx:454); [primary navigation](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/App.tsx:308) не проверяет G2 dirty/pending. Новый mount начинает с `initialDraft`, `pending=null`.
4. Аналогично case A → B → A: [PreparationCase key](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/PreparationScreen.tsx:55), [caseEpoch](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx:363), либо reload.

**Нет предупреждения о потере G2-ввода или original UUID/body.** [App.confirmDiscard](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/App.tsx:116) и [case switch](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/App.tsx:382) используют только [profile dirty](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx:269). SharedRoutePanel не регистрирует unsaved состояние в App/store, не устанавливает beforeunload и не пишет recovery journal. Profile `readDraftEnvelope` хранит другой тип ввода.

Если PUT успел commit, server receipt не потерян: после возвращения current GET может показать его. Если PUT не принят, нет прежнего ввода и команды для точного retry. Если принятый receipt позднее заменён новой revision, current GET не сопоставляет потерянную команду с её историческим UUID. Этот обзор **не утверждает** server data loss, duplicate history или tenant isolation failure. Отсечение late responses при замене кейса работает как изоляция, не как recovery.

## Сверка с принятым G2 и требованием владельца

[Persistence V2](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g2-design/SHARED_ROUTE_PERSISTENCE_SPEC_V2.md:39) и [root integration decisions](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/ROOT_G2_PERSISTENCE_INTEGRATION_DECISIONS.md:12) требуют сохранения draft при отказе и same original UUID/input при uncertain retry. Код выполняет это **внутри одного непрерывного mount**.

Принятые документы не задают durable client journal, межбраузерную синхронизацию unsaved draft или срок его хранения. Поэтому потеря после reload — не закрытая граница UI, а не доказанная поломка серверного replay. Явного согласованного исключения «только in-memory» в этих документах также нет.

Прямое требование владельца [§8](</Users/wpalish/.codex/attachments/f13c163a-be53-4102-b127-d64ce477da34/Вставленный текст.txt:144>): «Отдельно обработай unsaved navigation, case switch и reload». Этот пункт пока не выполнен.

## Граница тестовых доказательств

[Same-UUID/body test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.test.tsx:186) и [GET reconciliation test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.test.tsx:204) не размонтируют компонент. [Case replacement test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.test.tsx:313) доказывает отсечение старого ответа, не предупреждение/восстановление команды. Native additions проверяют reload/clean browser после успешного ACK — другой сценарий.

До заявления о полном journey нужно явно закрыть или принять эту границу: отменяемый уход при unsaved/uncertain состоянии; case switch с понятным предупреждением и owner/case изоляцией; reload с предупреждением либо контролируемым recovery original UUID/body; после recovery только точный replay/reconciliation, без автоматического нового save. Это acceptance gap; нового source/test/runtime proposal здесь нет. Late A→B→A fences и запрет foreign draft ослаблять нельзя.

## Source pins

Пины обычных прочитанных файлов добавлены ниже stdlib-only SHA-256 проверкой; это не импорт приложения.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx`: `a5057f0c6307a863a4b6c7054144682217142400fd4a40a6c8422eaefa9ccd5e`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.test.tsx`: `94c1f5186d95baa392a9a3709f6b85290f748644069672baa002d1c3a8af3f54`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/PreparationScreen.tsx`: `3de3a2a2ed36dc7e2cc840e947b2c4c91a21c5729af468ed8c40611bb85c41fb`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/App.tsx`: `5cd7408024f9732cfd661a78e3a8f2f45c01267117a6d50dee9b24a1f9328e26`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx`: `5f7d2fd0c93c3125442aaa1f2e271748dc25528f39266603735270ec2b8343a3`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g2-design/SHARED_ROUTE_PERSISTENCE_SPEC_V2.md`: `27bc906301708c604c723e1a1d2fdb6ae79f454750871b4d6f82a98cd4728de3`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g2-design/TYPED_CONTRACT_DESIGN_V2.md`: `3916138d910830dfb0b484f2a562a488889798985f11ac2abdb2ffcd7282f37c`.

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/ROOT_G2_PERSISTENCE_INTEGRATION_DECISIONS.md`: `c664a4c0db76e23b56091cf0cb435b5ed657749eb3f1b31df9526eca668c4465`.

- `/Users/wpalish/.codex/attachments/f13c163a-be53-4102-b127-d64ce477da34/Вставленный текст.txt`: `0ecd9c0677b52ca53b3dea74b3966437dc04e7f1cd7b3e9402229b20daf03bf4`.
