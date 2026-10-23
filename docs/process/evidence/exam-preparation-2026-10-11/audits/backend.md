# Backend: подготовка к экзаменам — исходная архитектура и границы

Проверен обычный исходный код `integration-2026-10-11/source` без запуска API, провайдеров или оценивания. Parent сообщил исходный commit `1d5a622d`, затем только документальный `11091904`; Git этим review не выполнялся. Закрытые search-пилоты, labels и heldout не читались. Это аудит backend и основание внешнего предложения, не подтверждение запуска курсов.

## Что уже есть

| Область | Фактический путь | Значение для подготовки |
| --- | --- | --- |
| Результаты ученика | `backend/app/schemas/profile.py:94` | SAT total/Math/R&W; IELTS overall и четыре компонента с типом/датой/статусом; другие языковые тесты как свободная запись. |
| Требования | `backend/app/schemas/result.py:47` | RequirementCheck сохраняет published/applicant values, status, explanation, claim_ids и published_scope. |
| Доказательства | `backend/app/schemas/claim.py:24` и `domain/claim_scope.py:91` | URL, цитата, дата, статус, специфичность, записанная область действия. Claim scope=None не равен всеобщему применению. |
| Проверка разрыва | `backend/app/domain/eligibility.py:485` | IELTS overall и компоненты проверяются отдельно; waiver остаётся вопросом для подтверждения. |
| Владение | `backend/app/api/tenancy.py:12` | Case принадлежит организации текущего principal; чужой UUID возвращает 404. |
| Сохранение/экспорт/удаление | `backend/app/models/applicant.py:24`, `api/routes_profile.py:266` | JSON профиля, ORM cascade research, собственные экспортируемые записи. Для StudyAttempt нужен такой же ORM cascade, включая SQLite с FK off. |
| Подписка и оплата | `backend/app/models/subscription.py:39`, `payments/subscriptions.py:56` | Сегодня подписка покупает квоту research-case. `current_subscription` исключает exhausted; это не подходящий checker срока обучения. |
| Практика | API/router/model отсутствуют в исходной версии | Research progress — этапы поиска; document checklist — подача документов, не учебный курс. |

## Конкретные ограничения текущей модели

1. **Overall не заменяет компоненты.** IELTS writing=6.0 при достаточном overall не закрывает writing minimum. Reading starter не исправляет Writing/Speaking/Listening и не доказывает принятие Academic/Online/UKVI/retake.
2. **Альтернативы не моделируются явной OR-группой.** В существующем `_english_checks` TOEFL рассматривается только при отсутствующем IELTS overall. Подготовка должна сохранять эти проверки как снимок и показывать неопределённость выбора альтернативы, а не брать максимум всех порогов.
3. **Waiver — условие, не готовое освобождение.** Наличие публикации не доказывает, что школа/категория конкретного ученика ей соответствует.
4. **Optional, blind и funding различаются.** Native SAT NOT_APPLICABLE включает optional и blind; новый planner не должен переводить blind в optional. Scholarship может требовать SAT при test-optional admission.
5. **Scope и freshness обязательны.** `claim_ids` часто содержат URL. Одного VERIFIED_CURRENT или строки «IELTS 6.5» недостаточно для программы/2027 intake. Старое либо противоречивое доказательство не становится новой целью.
6. **Новые издания нельзя незаметно вложить в старые поля.** Исходный TOEFL DTO поддерживает legacy 0–120/0–30, не новый отчёт 2026. HSK level/edition, отдельный HSKK и CSCA subjects пока не first-class profile fields. Официальные замечания доступны в [official-exams.md](official-exams.md); текущий аудит не меняет эти шкалы.
7. **Case payment запускает research.** `payments/service.py::_grant_and_schedule` выдаёт case access и ставит research job. Его повторное использование для обучения расходовало бы другую квоту и запускало поиск.

## Минимальное решение

Отдельный read-only term access: ACTIVE или EXHAUSTED, starts_at ≤ now < ends_at, независимо от case_quota. Pending/cancelled/expired/незаданный срок не дают доступ; payments-disabled — явно development_only. CASE_FULL продолжает отдельно защищать исследовательские доказательства.

Публичный versioned catalogue → оригинальный короткий lesson → полный выбор известных answer IDs → детерминированная проверка → StudyAttempt собственного case. Client UUID и canonical payload дают одинаковый receipt при retry и 409 при конфликте. Нет draft-server promise, essays/audio/AI, новых платежей/задач, официальной шкалы или вероятности поступления.

Planner только проецирует сохранённые RequirementCheck+ClaimOut, проверяя ID/URL, записанный scope, stale/conflict и актуальность снимка профиля. Не fetch/reassess; неизвестное остаётся unknown. Уроки связываются лишь с реализованными навыками. История и экспорт остаются данными ученика после окончания срока.

Внешнее предложение находится в `../proposals/backend/`; root отдельно проверяет/применяет его. Три starter lesson не означают полный IELTS/SAT или Chinese course. Для коммерческого запуска ещё нужны отдельные решения о содержании курсов, entitlement/pricing для новых покупателей, лицензиях и новых score DTO.
