# Внешний READ guard v2: готов к независимой проверке, не применён

Версия v2 закрывает два воспроизведённых блокера кандидата b603: уничтожение первого durable namespace холодным OFF checkpoint и необработанный SQLite busy в реальном verification caller. Это ограниченный прототип для фактического пути `ResearchRunner → adapter → Fetcher.get`, а не доказательство всех production гарантий. Репозиторий, Git, STOP и сеть не изменялись. Флаг `UNIVERSITY_READ_BUDGET = False`; включение по умолчанию не предлагается.

Полный patch SHA-256: `344c8200fce357ca4bc17cc3510031202390d10637780fb9f095b0d9d9759e38`. Предложенный `runner.py`: `a91a4f5259de94ba346190c30ec24fe845907b1a1053919b6830de6d27fc20c8`. Все семь модулей и пять исходных production модулей закреплены в `ready-source-manifest.json`; `ready-manifest.json` дополнительно закрепляет тесты, отчёт и raw logs. Старый b603/c092 snapshot сохранён: все 21 ранее закреплённые artifact/source hashes совпали. Неудачные промежуточные запуски не заменены зелёными файлами.

## Что считалось и когда

Один episode — `decision:<реальный research Job.id>`. Один university key — импортированный стабильный catalogue id либо точная нормализованная пара name/country для curated кандидата. Программы, discovery, requirements, costs, government и scholarships этого университета используют общий counter 60. Catalogue id проходит через необязательное внутреннее поле `Candidate.catalogue_id`; programme URL, текущий домен и город не образуют новый бюджет. Отдельные catalogue ids и разные curated aliases автоматически не объединяются.

Синхронная reservation делает whole-JSON replacement и существующий attempt-token heartbeat fence, затем commit **до** вызова исходного `Fetcher.get`. Cache hit, отказ Fetcher policy, ошибка и cancellation после reservation не возвращают единицу. Это число committed admissions/invocations, а не число vendor HTTP запросов; crash между commit и get может консервативно потратить единицу без I/O. Сам Fetcher, robots, SSRF, cache и security safeguards не изменены.

Ledger валидирует schema, episode shape, exact integer counters 0…60; bool, отрицательные/non-integer значения и неизвестная форма не превращаются в ноль. Ledger не является защищённым журналом: удалённый корректный university key невозможно отличить от ещё не встреченного без отдельного immutable log.

## Исправление namespace erasure

`run_to_decision` хранит новый settings snapshot в `_pending_settings_snapshot`, не присваивая его заранее ORM JSON. Поэтому промежуточный обычный query не может autoflush холодную замену поверх одновременно созданного ledger. Все live cancellation reads теперь используют `no_autoflush`, включая OFF runner, ещё не знающий о namespace.

`_save` сериализует свежий read/merge только когда guard включён, есть pending replacement либо SQLAlchemy JSON history содержит изменение. Он сначала получает настоящий Job fence/lock, затем Run lock, читает свежий durable snapshot и переносит его namespace в whole replacement. У чистого загруженного OFF JSON нет присваивания: обычный ORM UPDATE не переписывает это поле. Чистые docs/recheck checkpoints также не добавляют этот lock path. Dirty docs/recheck replacements сохраняют ledger через тот же merge.

Порядок новых lock requests — Job → Run, оба NOWAIT. На SQLite `FOR UPDATE` игнорируется: условный no-op UPDATE настоящего owned Job начинает write transaction **до** чтения counter. Direct runner без Job при metadata replacement сериализует настоящую Run row и на SQLite получает её write transaction до read. Такой direct checkpoint не выдаётся за fenced budget admission: guard-on reads с `job_id=None` закрываются как `unfenced_episode`.

Точная исходная последовательность независимого A сохранена и воспроизведена на v1: OFF erase после ON count60 позволяет исходный get61. В v2 OFF replacement уже держит write transaction, поэтому конкурентное создание ON namespace получает typed busy; после завершения checkpoint ON допускает ровно 60 get, последующая stale OFF замена сохраняет 60, get61 закрывается. Это новая честная сериализация, а не попытка воспроизвести невозможное interleaving внутри защищённой транзакции.

Default-off не объявляется полностью неизменённым. Dirty/pending live metadata replacements добавляют read/lock/fence round trips и NOWAIT failure behavior. Live cancellation reads больше не autoflush. Demo pending checkpoint проверен отдельно и сохраняет legacy путь без readguard lock. Полный demo artifact comparison для этого внешнего patch не запускался.

## Retry, source toggle и legacy initialization

При reclaim того же настоящего Job с новым attempt token ledger episode сохраняется. Если source default позднее становится False, уже записанный текущий `decision:<Job.id>` всё равно включает cap: durable ON intent не теряется. Malformed сохранённый namespace не игнорируется при False. Предыдущий episode другого Job не доказывает intent или нулевой counter текущего Job.

Новый ON episode разрешён лишь для token1 и durable Run, который ещё не имеет `started_at`; он сохраняется до первой source work. Retry без current episode и включение на уже started legacy Run закрываются как unknown. Новый Job на старом started Run также требует отдельного настоящего initialization protocol и здесь автоматически не получает ноль.

Полного frozen OFF intent при enqueue в этом patch нет. Новый untracked Job при False сохраняет legacy поведение, включая 61 get в контрольном тесте. Одновременно существующий старый OFF runner, начавший работу до первого ON episode, не превращается автоматически в budgeted runner. Исправлено уничтожение ledger и SAME Job ON resume; универсальная граница 60 для любого смешанного OFF/ON source deployment **не заявляется**. Это отдельная production интеграционная граница, если такой rollout требуется владельцу.

## Busy и сохранение фактов

SQLite BUSY/LOCKED (включая extended codes) и PostgreSQL `55P03` из checkpoint reads переводятся в `UniversityReadStopped("checkpoint_busy")` после rollback. Actual discovery, verification и funding callers пробрасывают busy до result/audit persistence. Верхний `run_to_decision` делает rollback и re-raise до generic Run FAILED branch. Cancellation и LeaseLost остаются отдельными control exceptions.

Actual verification/run controls с BEGIN IMMEDIATE и BEGIN EXCLUSIVE подтверждают: ноль get, ранее committed result/ClaimRow сохранены, ошибочный FAILED checkpoint не добавлен. Busy discovery/funding и bootstrap intent read также проверены. Во время удерживаемого DB lock durable `run.unknowns` **не обещается**. Типизированная причина передаётся существующему Worker.fail/backoff; сам Worker не изменён, его durable retry возможен только когда DB разрешает запись. Не заявляется перевод любой OperationalError на любой commit/неизменённом worker SQL path в typed busy.

Обычный read cap даёт honest unknown, не HTTP status и не доказательство отсутствия программы. Для нового result возвращённые completed partial claims сохраняются; для существующего result старые payload/ClaimRows не заменяются пустыми, новые завершённые partial claims закрепляются audit evidence для последующей reconciliation. Adapter locals, которые он не вернул до interruption, не считаются сохранёнными или отображёнными.

## Проверка и оставшиеся границы

Текущий внешний snapshot: **92 passed / 7.69s**, Ruff clean, mypy clean для 7 proposed source files. Тесты исполняют настоящие `ResearchRunner`, `_save`, JobStore fence, ORM и исходный Fetcher с mock I/O; DNS/network/provider factory запрещены. Среди контролей — реальные две SQLite sessions/threads, 80 attempted admissions → 60 get, stale same-worker token, cancellation после admission, cache/error charge, malformed ledger, разные programmes общего university, cold OFF creation, early autoflush, прямой no-job writer и current ON intent при False.

Неизменённый production красный: два actual-path теста получают 61 get, **2 failed / 0.67s**. Сохранённый v1 на новых выбранных controls: **6 failed, 1 passed / 1.93s**; один EXCLUSIVE верхний caller уже останавливался после generic rollback, поэтому не выдаётся за седьмую красную репродукцию. Точные независимые A tests на pinned v1: **1 failed, 1 passed / 0.72s**; busy negative-proof test проходит именно потому, что фиксирует старый OperationalError. Его успех не означает исправление.

На момент pin реальный PostgreSQL contention ещё не исполнен. SQL compilation и injected `55P03` не доказывают PostgreSQL concurrency. Родитель сообщил готовый локальный pgserver; независимая A проверка должна брать только этот immutable manifest. До её успешного выполнения PostgreSQL гарантия остаётся неизвестной. Новые NOWAIT requests не доказывают отсутствие deadlock во всех прежних транзакциях: более ранние ORM flush/другие writers могут иметь собственный порядок locks. SQLite proof нельзя переносить на PostgreSQL.

120s hard wall, renderer/direct rendering, query durability, документы/recheck source reads, crash/resume across processes, все production transaction paths, capture CLI/provenance и owner off/on/on/off acceptance здесь не решены. Синхронный SQL/driver timeout не является hard latency cap. Direct live canary без реального Job fence guard-on не совместим с этим contract. Patch готов для peer/source review и локального PostgreSQL checkpoint; для default promotion и заявления универсального durable production бюджета оснований пока нет.
