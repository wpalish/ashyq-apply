# IELTS ownership v2: внешний default-False кандидат для независимого review

V1 сохранён как **REJECTED** с manifest `c1e494a944287631c0fc31b0147e611d97e9240e03ad9b1bba7cbca09bf178e0`: независимый родительский actual-caller replay подтвердил четыре ошибки. V2 находится в отдельной папке, не применён в repo. Новых HTTP/provider/model/DNS вызовов = 0; source/Git/HANDOFF/STOP/gold/labels не менялись.

В актуальной v2 **68 offline controls green (7.64 s)**. Исправлены четыре точных родительских admitted bodies: IELTS без года не наследует единственный 2027/28 из соседнего TOEFL; writing test within 6 months не становится writing score; named `writing -6.5` не теряет знак; `IELTS Academic is no longer accepted` не выпускает IELTS minimum/accepted-type claims. Полные red и revised outputs сохранены в `root-controls.original.json` / `root-controls.revised.offline.json`, без classifier override.

**Границы production доказательства:** четыре retained Toronto topic-pages по-прежнему UNKNOWN и classifier-rejected, claims=0. Forced diagnostic admission replay двух English pages отдельно получает IELTS 6.5 / 6.0 с qualification/year/intake unknown. Это не production recall gain, не установленное требование 2027/28 и не blind/gold evaluation. Реально admitted retained Delft остаётся положительным контролем: IELTS overall 6.5 сохранён.

## Изменение и provenance

Флаг `IELTS_PROSE_SECTION_OWNERSHIP=False`. Патч затрагивает только три внешних модуля: optional keyword `extract_requirements(..., read_ielts=True)`; вызов helper в прежней разрешённой HTML requirements ветке; новый `ielts_sections.py`. Classifier classes, gate, Claim schema, Fetcher и capture schema не меняются. Original source hashes шести relevant modules совпадают с prepared snapshot HEAD7277 и нынешними parent source bytes (`source-compatibility.receipt.json`).

Paragraph/list statement должен сам назвать IELTS либо иметь собственный semantic heading owner. Equal/higher headings, explicit sibling regions, nav/menu/aside scopes закрывают чужого владельца. ARIA/accordion связи ограничены тем же semantic region/item; нет university/URL hardcode. Decline проверяется до чтения numeric/types в том же owner, включая другой paragraph, но одинаково названный отдельный sibling heading имеет другой DOM owner. Отказ принимать Indicator/Online/One Skill wording не отменяет IELTS Academic minimum на сохранённых страницах.

Named bands требуют непосредственного числа либо явного score/band/minimum role; произвольные слова между Writing и числом не допускаются. Числовой atom включает знак, decimal и проверку продолжения; months/credits/time units не являются band. `60`, `-6.5`, `6.5e1`, `6,500`, `6.5abc`, `6.5.2027` не обрезаются. `6.50` остаётся 6.5; прежний доменный range/half-band verifier сохраняется. IELTS accepted vocabulary остаётся academic/ukvi_academic/general_training.

Цитата — непрерывный срез original readable page text; промежуточные слова не удаляются. Local qualification/year/intake headings включены в этот срез; прежний MAX_EXCERPT_CHARS не увеличен. При недостаточном контексте reader abstains. Для page-title-only scope собственный source title сохраняется в Claim.page_title, numeric excerpt остаётся contiguous body slice: title и body искусственно не склеиваются.

Qualification/year/intake берутся из локального statement/ancestor headings; year/intake могут наследовать только явно прочитанный собственный page title. Global body read_scope fallback исключён, поскольку его год может относиться к TOEFL. При conflicting/неявных локальных словах unknown остаётся None. Requested-year/intake не являются source evidence.

**Опциональная семантика flat metadata:** legacy caller намеренно хранит routing/request context в flat Claim.academic_year/intake, а observed scope отдельно. Только enabled owned IELTS prose в v2 записывает flat year/intake из того же observed evidence, что scope, включая None. Это bounded opt-in semantic difference, не схема migration. Original builder metadata затем полностью восстанавливается; остальные claims не меняются. Table/PDF сохраняют прежнюю flat-field semantics. Owner должен учитывать эту разницу при integration; default остаётся False.

## Положительные, отрицательные и compatibility контроли

- **10/10 frozen==OFF whole outputs**, включая claims, quotes, scope, metadata, errors, page outcomes, counters и fetch-call list; canonical output hashes в `off-equivalence.receipt.json`. **10/10 ON non-IELTS claims и page classes unchanged.**
- Actual admitted CAEL60 red воспроизводит legacy false IELTS6.0; ON abstains. Соседний IB не становится IELTS qualification. Explicit A-level остаётся A-level и противоречит Attestat.
- Unqualified/relative year → scope/flat year None. Local 2024/25 → requested2027/28 NO. Local2027/28 → YES **по единственному requested year dimension**. Unknown → UNKNOWN; полного applicant-scope YES не заявляем. Reversed TOEFL2024→IELTS2027 сохраняет local2027 во всех IELTS year/intake fields.
- Genuine writing/reading score role positives, signed/whole token negatives, nav/menu/aside/section boundaries, explicit exchange filter и contiguous/max-length quote controls — green.
- **Admitted table-only whole output frozen==OFF==ON**, включая legacy accepted-types. Independently found accepted-type loss до seam fix сохранён в `table-only-seam.red-green.offline.json` и historical caller. Если прежний structural reader ответил IELTS, его legacy type route сохраняется; helper читает только unanswered numeric prose. Scope guarantee здесь именно prose, legacy table scope не объявляется исправленным.
- **UNKNOWN language-follow structural-table whole output frozen==OFF==ON** через настоящий существующий caller route. Page class остаётся UNKNOWN; нового permission нет.
- **Actual PDF caller path frozen==OFF==ON** с mocked conversion bytes→text и native country-credential classification. Это preservation test, не доказательство реального PDF converter/renderer.

Ruff check/format, mypy трёх proposed modules, AST parse — green. Fixtures используют одностраничный mocked Fetcher, no following/topic search, query ledger exhausted=6; DNS/process functions запрещены до app imports. Один fixture typo в имени `named_negative` сохранён и исправлен без product guard changes.

## Что не доказано

Никакого общего отсутствия потерь: unlabelled/mixed-exam lists, disjoint named bands, длинные/дублирующие blocks могут привести к conservative missed gains. Recognition decline/score roles ограничена указанными конструкциями, не всеми формулировками английского языка. Global programme/degree/population/nationality/residency scope остаётся legacy; его исправление не заявляется. Table/PDF scope остаётся legacy. WES/ECE, supplementary vs application deadlines, broad admission-purpose override и tuition не bundled. Нет новых гарантий hard120/read60/query/renderer budgets. Нет paired live evidence или owner default promotion.

Reproduce: backend/.venv Python, `PYTHONDONTWRITEBYTECODE=1`, explicit pytest `test_owned_ielts.py -p no:cacheprovider` с внешним basetemp. Exact source/patch/test/evidence fingerprints в final manifest; исходный v1 не перезаписывался. Root integration и независимый review остаются отдельными действиями.
