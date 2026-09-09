# T37 A1 — Review (on frozen candidate 2e8e6f9f784d03960562ca25e9b6b6c85d05eca2)

## Reviewer (agent_6426b7eb-e8ea-40cb-b586-297541ef637f) — VERDICT: PASS

(Security review опционален по master-карточке T37; dispatcher ruling: не проводится — data не переносится между run'ами, удаления скоупированы PK, security-поверхность минимальна; reviewer независимо подтвердил.)

ACCEPTANCE_MAP: все пункты подтверждены (RED «Groningen 40→58», 14/20 удвоений; post-fix 0 doubled; user_* оба уровня; T32 gates 47 passed; TestRetry green; 5 assertion-групп). Честное отклонение assertion-5 (guard, не RED — корпус без funding-конфликтов) задокументировано, ослаблений нет.

GATE_CHANGE_RULING (is not None): корректен — 5 call sites: 3×None без изменений; funding :813 единственное поведение (пустой список честно заменяет — заморожено, unknown→zero смягчён UnresolvedQuestion runner.py:802-811 при ошибке адаптера); :1072 no-op за _replace_evidence. Ни один вызов не рассчитывает на старый skip.

Качество: synchronize_session=False уместен (новые ClaimRow добавляются ПОСЛЕ deletes — autoflush-safe; прецедент _replace_evidence); SUPERSEDED-паритет; ConflictRow без status по модели; скоуп PK — кросс-рановое удаление невозможно; константа 14 членов по префиксу (scholarship_administrator — SourceSpecificity, не попадает), re-open правило в комментарии.

COVERAGE_RESIDUAL_RULING: ПРИЕМЛЕМО как residual — все НОВЫЕ строки выполняются (1117-1134); 84% — модульное число подмножества тестов, не гейт; непроверенный эффект — конфликт-delete (корпус не эмитит) — механизм идентичен по форме покрытому, follow-up обязателен.

Nonblocking followups: (1) контрактная сессия — посеять funding ConflictRow перед re-entry (пиннинг delete + :1136); (2) владельцу — чистка существующих прод-дублей; (3) нит — .value-стиль в in_(); (4) интегратор — full-suite cov 92 + frontend.
