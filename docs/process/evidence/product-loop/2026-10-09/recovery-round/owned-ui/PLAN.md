# Recovery UI: ограниченная acceptance проверка

Статус: **PLAN ONLY; браузерные действия не начаты.** Root baton `aee0bb22` — передан root, не независимо прочитан через Git. Current source reads и SHA-256: [source-pins.json](./source-pins.json). Они показывают исходные empty-Start-research и approve-only Documents формулировки; это не оценка ещё готовящегося B proposal.

До CUA нужен явный localhost go от root с точным URL, approved source snapshot/pins, подтверждением provider-none/auth-false DEMO и принадлежащей root isolated DB. В receipt нужны доступные synthetic case/run/result IDs, их ожидаемое состояние и наличие seed для missing-checklist. Отсутствующая seed — NOT RUN, без SQL или самостоятельного создания кейса.

## Критерии

| Сценарий | Что должно наблюдаться | Что не утверждаем |
|---|---|---|
| Find, partial/stopped, сохранённые результаты | Видимая остановка/неполнота с `Review research`; строки остаются доступны. Выбранный фильтр и matched/total context остаются видимыми; notice не скрывает список | Полнота/точность поиска или сохранение ephemeral filters после remount |
| Review research | Native click ведёт в Progress того же seeded run; видна причина/стадия остановки. Не предлагается незаметно запустить другое исследование | Provider recovery, retry или работа очереди по одной навигации |
| Find, zero-results stopped | Только при отдельной owned seed: объяснена остановка и Review research → Progress; нет подмены пустого остановленного run приглашением начать вместо разбора | Нулевой список не означает отсутствие подходящих программ |
| Find, настоящий new/no-run | Только при отдельной owned seed: Start research доступен; кнопку не нажимаем | Новое исследование не запускается и не проверяется |
| ResultDetail, checklist=null | Для точного seeded result вкладка Documents говорит о выборе **Yes или Maybe**, следующем переходе к **Plan** и сборе списка. Нет утверждения, что отсутствие списка означает «документы не нужны» или готовность к подаче | Сбор документов/подача/owner readiness не выполняются |
| Reload | После native reload тот же seeded run/result/status доступен; не появляется новый run или готовность из отсутствующего списка | Local component filters/expanded tab не обязаны пережить reload; потеря таких состояний не объявляется backend loss |

Если в receipt есть approved/maybe/nochecklist записи, используем их без изменения решения. Выбор/заметки, реальные данные и анкеты не редактируются.

## Не более шести captures

Каждый capture — screenshot + AX + DOM body/control geometry, timestamp и точный URL. Native actions фиксируются отдельно в кратком журнале; каждый click не требует новой картинки.

1. **Desktop Find partial/stopped**: применить один безопасный UI фильтр с хотя бы одной matching строкой; notice, filter context и retained rows в одном состоянии.
2. **Desktop Progress**: native Review research click; подтвердить точный seeded run и stopped stage.
3. **Phone 390 px Find partial/stopped**: после возврата/перезагрузки применить тот же filter scenario; проверить notice, фильтр, retained row и кнопку; click Review research и записать Progress AX/URL/geometry без дополнительного screenshot.
4. **Desktop ResultDetail missing checklist**: открыть точный result и Documents; зафиксировать Yes/Maybe + Plan текст.
5. **Phone 390 px ResultDetail missing checklist**: native reload, снова открыть тот же result/Documents; проверить reflow и читаемость сообщения.
6. **Optional zero-results stopped**: только по explicit owned seed receipt. Одна картинка на 390 px; stopped/new-run различие дополнительно записать AX/geometry на desktop без screenshot. Если root не подготовил оба состояния, записать NOT RUN и не подменять их пустым фильтром.

Desktop размер — точный размер root preview или исходный размер собственной Chrome вкладки, записанный перед проверкой. Phone — ширина390, высота844, если документированный CUA API это поддерживает. Если viewport API недоступен, phone результат NOT RUN; не использовать root IAB как замену.

## Geometry и результат

DOM-only read: viewport width/height, body/document clientWidth/scrollWidth, прямоугольники notice, Review research, active-filter context, первого retained card и missing-list текста. Записать, находятся ли элементы в viewport, перекрыты или обрезаны; длинный список допускает обычную вертикальную прокрутку. Ширина390 не должна создавать горизонтальное переполнение страницы или обрезать recovery кнопку/текст. Screenshot и AX должны соответствовать одному settled состоянию.

Отчёт после go: OBSERVED PASS / OBSERVED FAIL / NOT RUN для каждого критерия, конкретный native action, точный result/run, полученные файлы и SHA-256. Синтетический localhost flow не считается production/auth/live/provider/search-quality/full-product доказательством. Одна кнопка или screenshot не доказывает persistence; только повторное UI чтение после reload подтверждает проверенные поля.

## Границы исполнения

Только собственная новая Chrome task session/tab, документированные CUA APIs и явная UI навигация. Root/user IAB UniLight не читается и не меняется. Не выполняются accounts/terms/AI/сообщения/university/provider/Git/primary edits/ports/SQL/test jobs. После finite captures восстановить исходный viewport собственной вкладки и закрыть только собственные tabs; сохранить подтверждение cleanup. Если root остановит preview или source pin изменится, остановить UI этап и записать достигнутое состояние.
