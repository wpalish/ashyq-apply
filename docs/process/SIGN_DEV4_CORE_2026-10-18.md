# Подпись dev4 — шесть основных вопросов — 2026-10-18

Черновик, ничего не подписано: `backend/evaluation/research/data/dev4.draft2.json` (строки программ из
dev4.draft1 не тронуты, добавлены метки шести вопросов) и `identity_bindings.dev4-draft2.json` (4 привязки
стипендий). Ответы эксперта: `backend/evaluation/research/expert/data/core_drafts_dev4.2026-10-18/`.
Запрос в каждом случае: бакалавриат, computer science (или ближайший аналог из dev4.draft1), набор осень 2027.
Только официальные сайты, robots.txt соблюдается, без обхода.

## Проверка цитат — пока не пройдена

`scripts/verify_evidence.py` запущен здесь на все 25 предложенных цитат: **0 из 25 проверено**, у всех
`robots_disallowed` — из контейнера агента Fetcher не может открыть robots.txt (ConnectError), сайт тогда
считается закрытым. Это ограничение контейнера, не сайтов. Поэтому **в dev4.draft2.json все 51 метка шести
вопросов записаны `unknown`**; предложенное значение и причина лежат в `notes` каждой метки.

Что сделать: после push запустить `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/core_drafts_dev4.2026-10-18`, скачать `report.json` и выполнить
`python -m evaluation.research.expert.core_drafts_dev4 evaluation/research/expert/data/core_drafts_dev4.2026-10-18 --evidence report.json`.
Прошедшие цитаты станут `known` / `not_applicable`, не прошедшие останутся `unknown`.

Даже после проверки часть предложений останется `unknown` по правилам конвертера: срок или плата только за
цикл 2026/27, плата за семестр (решение тикета 02 Q4 ещё не принято), число не в цитате.

## Таблица

Колонка «итог после проверки» — что конвертер запишет, если цитата пройдёт. Решение владельца:
принять / исправить / unknown.

| университет | вопрос | предложение эксперта | итог после проверки | цитата | источник | язык страницы | решение |
|---|---|---|---|---|---|---|---|
| ČVUT (ctu) | английский | IELTS 5.5, TOEFL iBT 65 (англоязычная версия) | IELTS 5.5; TOEFL 65 | «IELTS score 5.5 and above, or … TOEFL iBT score 65 and above» | [FIT EN admissions](https://fit.cvut.cz/en/applicants/admissions-procedure/bachelor-study-program) | англ. | |
| ČVUT | GPA | порога нет, вступительный тест по математике FIT или SCIO | н/п | «Pass the Mathematics test organized at FIT CTU» | то же | англ. | |
| ČVUT | срок | 31.03.2026 | unknown (только цикл 2026) | «from 1 January to 31 March 2026» | то же | англ. | |
| ČVUT | плата | 64 000 CZK за семестр, 2026/27 | unknown (2026/27, семестр) | «…tuition fee, CZK 64,000 (approx. EUR 2,627 / USD 2,867), for the first semester…» | то же | англ. | |
| ČVUT | стипендия | не найдена для бакалавров FIT | unknown | — | — | — | |
| VUT (vut) | английский | обучение на чешском | н/п: язык чешский | «Language of instruction: Czech» | [программа 10326 EN](https://www.vut.cz/en/students/programmes/programme/10326) | англ. | |
| VUT | GPA | ранжирование по NSZ (найдено поиском, не процитировано) | unknown | — | — | — | |
| VUT | срок | только цикл 2026/27 | unknown | — | — | — | |
| VUT | плата | обучение на чешском бесплатно (не процитировано) | unknown | — | — | — | |
| VUT | стипендия | Accommodation scholarship; доступ иностранцам не указан | есть; иностранцам unknown | «Apply for a scholarship to cover part of your expenses for accommodation.» | [scholarships](https://www.vut.cz/en/students/scholarships) | англ. | |
| RWTH (rwth) | английский | английский B2 (CEFR), цифры IELTS нет; ещё нужен немецкий | IELTS unknown | «students must prove that they have English language skills at level B2» | [Informatik B.Sc. EN](https://www.rwth-aachen.de/cms/root/studium/vor-dem-studium/studiengaenge/liste-aktuelle-studiengaenge/studiengangbeschreibung/~bnzs/informatik-b-sc-/?lidx=1) | англ. | |
| RWTH | GPA | приём без ограничений (без NC) | н/п | «Open (No NC)» | то же | англ. | |
| RWTH | срок | «May 1 until October 20» без года и неясно для не-ЕС | unknown | — | — | — | |
| RWTH | плата | суммы нет на странице расходов | unknown | — | — | — | |
| RWTH | стипендия | Deutschlandstipendium (Education Fund); иностранцам не процитировано | есть; иностранцам unknown | «At RWTH, the Education Fund is the most important scholarship program, particularly the Germany Scholarship.» | [Kosten und Finanzierung EN](https://www.rwth-aachen.de/cms/root/studium/Vor-dem-Studium/~cgfzv/Kosten-und-Finanzierung/lidx/1/) | англ. | |
| KIT (kit) | английский | обучение на немецком, C1 (DSH-2 / TestDaF 4) | н/п: язык немецкий | «Your German language skills must correspond to at least level C1» | [Informatics B.Sc. EN](https://www.sle.kit.edu/english/vorstudium/bachelor-informatics.php) | англ. | |
| KIT | GPA | отбор по аттестату, минимума нет | unknown | — | — | — | |
| KIT | срок | 15 июля без года | unknown | — | — | — | |
| KIT | плата | не процитирована | unknown | — | — | — | |
| KIT | стипендия | не исследовано (время) | unknown | — | — | — | |
| Bologna (unibo) | английский | обучение на итальянском | н/п: язык итальянский | «Language Italian» | [ComputerScience](https://corsi.unibo.it/1cycle/ComputerScience) | англ. | |
| Bologna | GPA | ограниченный приём по тесту TOLC-I | н/п (порог — тест) | «Restricted access - TOLC-I» | то же | англ. | |
| Bologna | срок | нет на странице | unknown | — | — | — | |
| Bologna | плата | не собрана (по ISEE) | unknown | — | — | — | |
| Bologna | стипендия | Unibo Action 1&2 только 2021–2023 | unknown | — | — | — | |
| TalTech (taltech) | английский | обучение на эстонском, вступительный тест по эстонскому | н/п: язык эстонский | «Matemaatika ja eesti keele sisseastumiskatsed; erialade sisseastumiskatsed» | [informaatika](https://taltech.ee/informaatika) | эст. | |
| TalTech | GPA | приём по вступительным тестам | н/п | та же цитата | то же | эст. | |
| TalTech | срок | нет на странице | unknown | — | — | — | |
| TalTech | плата | нет на странице | unknown | — | — | — | |
| TalTech | стипендия | стипендии IT-факультета (dean's list), для обучающихся | есть; иностранцам unknown | «TalTechi IT-teaduskonnas on ülikooli lõikes kõige rohkem stipendiumivõimalusi ja suurim stipendiumite kogumaht.» | то же | эст. | |
| KTU (ktu) | английский | IELTS 5.5, TOEFL 75 | IELTS 5.5; TOEFL 75 | «IELTS ≥ 5.5, TOEFL ≥ 75, CEFR ≥ B2, or equivalent.» | [b-informatics](https://admissions.ktu.edu/programme/b-informatics/) | англ. | |
| KTU | GPA | средний балл > 60 % по каждому вступительному предмету | «60% minimum average grade (CGPA) in each entry subject» | «Minimum average grade (CGPA) >60% in each entry subject.» | то же | англ. | |
| KTU | срок | 01.06.2026 | unknown (только цикл 2026) | «1 June 2026» | [bachelor](https://admissions.ktu.edu/bachelor/) | англ. | |
| KTU | плата | 4201 EUR в год, 2026/27 | unknown (только 2026/27) | «full-time studies – 4201 €, price per credit – 70,02 €» | [b-informatics](https://admissions.ktu.edu/programme/b-informatics/) | англ. | |
| KTU | стипендия | частичное освобождение от платы для сильных кандидатов; конкурс | есть; иностранцам да | «offers partial tuition fee waiver for candidates with outstanding results» / «These scholarships are open to all international applicants.» | [bachelor](https://admissions.ktu.edu/bachelor/) | англ. | |
| Boğaziçi (boun) | английский | IELTS 6.5, writing 6.5 (TOEFL 79 там же) | IELTS 6.5; writing 6.5 | «Overall Score: 6.5 Writing: 6.5» | [documents](https://intl.bogazici.edu.tr/required-documents-undergraduate-application) | англ. | |
| Boğaziçi | GPA | порога по оценкам нет; SAT 1350 (Math 700) / TR-YÖS 450 / A Levels | н/п (порог — тест) | «a combined score of at least 1350 out of 1600» | то же | англ. | |
| Boğaziçi | срок | нет на странице | unknown | — | — | — | |
| Boğaziçi | плата | «5.000 USD» без периода и года; другая страница — 10 000 USD/год | unknown | — | — | — | |
| Boğaziçi | стипендия | стипендий иностранцам нет | н/п (ключи стипендии не пишутся) | «Bogazici University does not offer scholarships or financial aid to international students.» | [tuition](https://intl.bogazici.edu.tr/tuition-undergraduate-and-graduate-degree-programs) | англ. | |
| İTÜ (itu) | английский | таблица распределения по курсам (TOEFL 72–90), не минимум приёма | unknown | — | — | — | |
| İTÜ | GPA | страница условий 2026-27 — 404 | unknown | — | — | — | |
| İTÜ | срок | только цикл 2026-27 | unknown | — | — | — | |
| İTÜ | плата | таблица 2026-27, валюта не подтверждена | unknown | — | — | — | |
| İTÜ | стипендия | не установлено | unknown | — | — | — | |

## Языки страниц-доказательств (для тикета 07)

Из 25 предложенных цитат 23 — на английских страницах университетов (англоязычные версии сайтов), 2 — на
эстонской (TalTech). Ни одной чешской, немецкой, итальянской, литовской или турецкой страницы среди
доказательств нет: где был официальный английский двойник, эксперт брал его.

## Вопросы владельцу

1. ČVUT: метки взяты с англоязычной версии программы (платной), а не чешской (бесплатной, нужен чешский B2).
   Рекомендация: да — иностранному абитуриенту доступна именно она; чешская остаётся двойником в programme_urls.
2. RWTH: английский B2 без цифры IELTS и немецкий для немецкой части. Рекомендация: IELTS — unknown, как сейчас.
3. Плата за семестр (ČVUT) ждёт решения тикета 02 Q4. Рекомендация: как в 02 Q4 — сумма как опубликована,
   `period: semester`, когда опубликован 2027/28.

Подписываю dev4.draft2 (9 случаев): ______
