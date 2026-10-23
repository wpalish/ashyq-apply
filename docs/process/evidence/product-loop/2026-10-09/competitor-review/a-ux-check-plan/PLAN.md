# План следующей UX-проверки — 4 приоритетных сценария

**Только план; проверки не выполнялись.** Все действия — после terminal full receipt и отдельного разрешения на изолированный synthetic runtime. Никаких повторных native/full тестов, серверов/портов, live research или обращения к реальным данным сейчас.

Сравнить desktop 1440×900 и mobile 390×844, затем reload после завершения hydration/подтверждения API. Для каждого сценария сохранить исходное synthetic состояние, фактический action/route, screenshot до/после reload и console/network errors. Не считать screenshot или mock acknowledgement доказательством backend durability; пометить, чем именно подтверждена persistence. Сетевой слой остаётся только локальным synthetic и не обращается к университетам/провайдерам/модели.

1. **Остановленный/stale run + partial checklist.** Home должен вести в Progress раньше Documents; Documents сохраняет существующие требования/unknowns и показывает stopped status вместо collecting. Reload не теряет состояние. Checklist и отметки не становятся application-ready.
2. **Saved для approved/maybe.** Оба снимаются до undecided, approved не становится maybe. Plan/filter counts и notes соответствуют подтверждённому ответу и reload; действие удаления понятно на touch без hover.
3. **Сбор документов и календарь.** Calendar/known date доступны без checklist. Отказ collection остаётся на Plan с ошибкой/paywall, accepted queued → один переход в Documents и заметный progress без повторного dispatch; reload сохраняет queued.
4. **Sources с пустыми per-result вопросами, но run diagnostics.** Оба errors/unknowns видны, empty wording ограничено returned programmes, Progress доступен; mobile wrap и reload не скрывают ограничения.

Два известных пробела должны иметь собственную отметку, а не ложный PASS:

- **Find/no-results:** ShortlistScreen.tsx:42,96 не учитывает failed/stale run. Direct Find после остановки по-прежнему предлагает Start research. Home recovery улучшен, но это не закрытие данного direct-route сценария.
- **Sources failed+no-errors:** SourcesScreen.tsx:15,64 строит limitation panel только из errors/unknowns. При failed/dead/cancelled без этих сообщений статус не выводится; новый scoped empty text не создаёт diagnostics. Это ограничение покрытия, не доказательство чистого результата.

Точные synthetic шаги/expected/evidence — scenarios.json. Сверка 11 frozen файлов с принятым review и opaque hash неизменного STOP — context.json. Окончательный full/source receipt будет проверен отдельно после получения от root; здесь нет заявления о его PASS.
