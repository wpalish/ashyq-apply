Aalto: DEV source-funnel, только сохранённые bytes

Aalto дал 0 programme URLs и 0 predictions при завершённом Job, а не при остановке общего 60/6/120 бюджета. Это не доказывает отсутствие подходящей программы или требований. Подтверждены отдельные CLASSIFIER и EXTRACTOR барьеры; воспроизведение не доказывает прирост core coverage или корректность для 2027/28.

До анализа проверены `COMPLETED_JOB_CAPTURE` в receipt и source head `7c74a12d71bd00228014c11d194928d223e110be`, full snapshot tree `19f349a0a242478e13f95e1905e8f41662a769b579833b004cafb03b73825c9a`. Терминальные пять файлов скопированы, затем скопированы 43 official public cache meta/body пары с оригинальными URL, final URL, fetched_at и SHA. 14 использованных source файлов совпали с frozen snapshot и были скопированы отдельно. Native replay импортирует исходные модули; Fetcher не создаётся: его контракт заменён локальным RetainedOnly, который вызывает исключение при любом URL без сохранённого body. Classifier не подменялся. Сети, provider/model, labels и scoring: 0.

Терминальный Aalto: 56 Fetcher.get attempts, 6 search attempts, 58 HTTP requests по метру harness, 110157 ms; stop_reason/provider_failure/run_error отсутствуют. Native guard OFF и genuine Job succeeded. Бюджет оставил 4 чтения и примерно 8.8 секунд до source deadline119000; это не обещание, что новые страницы успели бы открыться. Позже общий original10 collection остановлен родителем после Exa refusal на KAIST и объявлен GLOBAL_PROVIDER_STOP_UNSCORED. Aalto остаётся завершённым case; коллекция не получает score.

| Funnel | Наблюдение |
| --- | --- |
| Sitemaps | root index +11 child документов, 55000 locations; native seen55000, kept184 |
| Unique | отдельного native unique counter нет; log+meta дают 46 exact requested URLs:43 успешных и3 robots.10 повторных успешных get attempts |
| Initial programme queue | ranked40; фактически проверены первые8, ни одного подтверждения |
| Walker | 2 каталога,17 чтений,185 scored candidates,0 подтверждений. Native replay совпал с live get22–38 и всеми185 candidates |
| Walker trace | raw хранит первые200 outcomes; replay на тех же bytes дал305. Нельзя считать raw200 полным журналом |
| Search | 6 queries, failed0; entrypoint1read +identity recovery8read, confirmed0. Полный vendor result/rank population неизвестен |
| Readers | requirements1, costs1, funding7 =9последних attempts. Claims0 на входе persistence; подтверждённой SLOT потери нет |

Calls по стадиям: robots+sitemaps13, initial confirmation8, walker17, search entrypoint1, search recovery8, requirements1, cost1, funding7 =56. Три failures — только robots на official `/en/node/1008496`, `/en/node/835691`, `/en/node/30591`; body для них отсутствует, award eligibility/availability неизвестны. Browser/PDF/model meters0.

Причины programme-funnel

1. JS / NOT_DISCOVERED, с ограничением вывода. `/en/study-options` — сохранённый HTTP shell: в main0 anchors и пустой `#aalto-studies-search` внутри Vue component. Whole-document177 anchors дают navigation; walker берёт CS department, Bachelor admissions hubs и departments, затем повторяет те же leads на Courses catalogue. Browser был OFF. Это подтверждает отсутствие programme list в конкретном HTTP body, но не отсутствие списка после JS и не факт, что renderer нашёл бы CS Bachelor. Share URL содержит masters query, но final_url без query; нельзя выдавать share URL за actual redirect или applied filter.
2. OTHER_PAGE / subject/level gates. Первые8 sitemap programme-shaped URLs — WiT/WOOD/people и Swedish magister continuation. Native classifier отвергает их; сохранять такие URL как CS Bachelor было бы неверно. Search читает два Bachelor Science and Technology curriculum pages, research publication, CS minor, department, summer-employment page, curriculum index и Study computer science. Последняя прямо предлагает master's degree или отдельные Lifewide courses. Два curriculum pages классифицированы как Bachelor `Aalto Bachelor's Programme in Science and Technology`, но own identity не содержит requested Computer Science. Автоматическая alias/major эквивалентность не доказана. 2026–2028 curriculum также говорит under construction; curriculum range не превращён в admissions2027/28.
3. BUDGET в локальных stage caps, а не terminal60/120 stop. Sitemap reader достигает MAX_SITEMAP_DOCUMENTS12: из12child sitemaps прочитаны11, один не прочитан. 55000 не является MAX_SITEMAP_URLS (он200000). Initial confirmation и search recovery имеют отдельные8-read caps; walker20lead topN +subject rules и2catalog roots. Нет bytes непрочитанных страниц, чтобы доказать потерю нужного programme.10 repeated get attempts расходуют outer page allowance, но этот case всё равно завершился.

Первый конкретный CLASSIFIER барьер downstream

`/en/admission-services` сохранён с same-site final_url `/en/admissions`. Own title `Admission Services | Aalto University` и mainH1 `Admission Services` не off-topic. Main содержит `How to apply to Aalto`, application periods for studies starting in2027 и Bachelor admissions routes. Единственное совпадение `_IRRELEVANT` по headings — secondary `Contact us`. `classify_page` строит title+ВСЕ headings и возвращает IRRELEVANT на строке427 с misleading signal `title is off-topic`. Actual WebRequirementsAdapter fallback programme (url=None) делает1read и возвращает classifier-rejected/0claims точно как live.

Это доказанный page-purpose trigger loss, но не готовый programme/requirements fix. На той же hub есть subsidiary funding headings; изменение только Contact us может открыть следующую ветку funding. Нельзя широко разрешить UNKNOWN/IRRELEVANT для всех extractors, объявить даты hub programme-specific или считать extracted2027 корректными без отдельного scope proof. Ни classifier override, ни диагностический forced-admission replay здесь не использовались.

Первый конкретный EXTRACTOR барьер

`/en/admission-services/scholarships-and-tuition-fees` принят COSTS и читается29568chars. Реальный WebCostAdapter возвращает0claims/no-pattern-match. DocumentIR имеет18 table cells: Bachelor table с Field Business, Art/Architecture, Technology annual tariffs; Master table отдельно. Таблицы имеют own applicability `rights to study beginning on or after1August2025`. Monetary atoms `€12 000` корректно парсятся как12000EUR: проблема не в пробелах или currency atom.

`extract_structured_costs` принимает tuition rows только под полным heading `Annual tuition fees for <population> <year>/<year> academic year`; существующие `Tuition fees` / `How much is the tuition fee?` +cohort table headers не подходят, handled_types остаётся пустым. Legacy `extract_costs` берёт только первое tuition prose окно из introductory paragraph, где нет money. Population fallback требует минимум2populations с money; эта tariff table разделяет degree/field, поэтому не применяется. Native saved-byte caller подтверждает0costclaims при наличии квалифицированных source rows.

Это потеря опубликованных source facts. Для конкретного CS programme field/fee status, exact academic year2027/28 и totalcost остаются неизвестными; университет прямо reserves right to change fees. Нельзя подставить technology tariff как решённый applicant cost или принять effective-from2025 за guaranteed2027 price.

Минимальный следующий кандидат на отдельную проверку

Приоритет — bounded structured fee-row retention, без выбора applicant tariff: распознавать annual-money row под tuition section с own degree table header и field row header; retain наблюдаемый effective-from cohort, degree, field и period как источник. Не назначать requested academic_year, exact programme, country/residence exemption или total. Брать только whole currency atom и contiguous original quote, который содержит локальные qualifiers; если общий qualifier не помещается/не принадлежит row, не синтезировать quote и оставить unknown. Новый rule должен быть defaultFalse; это предложение, patch не создавался и никакие defaults не менялись.

Нужные локальные controls до любого применения: оригинальные обе таблицы отдельно; Bachelor/Master граница; field rows; неполный/двусмысленный header; persemester/permonth/oneoff fees; стипендия/waiver/процент; residence exemption; устаревший/unknown cohort; out-of-table navigation money; signed/decimal/grouped full numeric atoms; claim scope и flat context различие; exact OFF whole-output equality. Отдельный classifier experiment может ограничить irrelevant vocabulary own identity/title, сохранив genuine Contact us/job/research страницы и sibling funding guards; он не входит в fee-reader change и не имеет доказанного end-to-end gain.

Неустановленное

Нет тела непрочитанного sitemap, rendered catalogue payload, полного vendor rank и robots-blocked awards. Нет gold сравнения, score, quality denominator или доказательства CS Bachelor2027/28. PDF отсутствовал, source hierarchy/SLOT loss не подтверждены. ACCESS относится к трём awards; она не объясняет ноль programme confirmations. Актуальность и применимость сохранённых source facts не подменяются query context.

Повторяемые native checks: `replay_page_purpose.py`, `replay_native_saved_bytes.py`, `verify_funnel_counters.py`, normal PYTHONPATH frozen snapshot/backend и backend/.venv/bin/python. `funnel-counters-and-controls.json`:5 PASS assertions; walker17read/0confirmed, requirements1/0, costs1/0. Это DEV diagnosis, не новая слепая экспертная оценка и не 40/62 acceptance.
