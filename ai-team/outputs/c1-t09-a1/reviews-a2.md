# T09 / A2 — reviewer + security outputs (сохранено диспетчером; сокращено без изменения оценки)

## ashyq-reviewer A2 (re-review) — ref по самоотчёту вызова: agent_93a2f1c4 (runtime не экспортировал полный agentId диспетчеру — помечено; независимость обеспечена отдельным вызовом и отдельной верификацией артефактов)
- VERDICT: PASS (только на 7fb0d3270de24f79adfea6a315ee80092a298bc0; правка кода после аннулирует)
- Метод: read-only без Bash; SHA по git-refs/reflog; diff пофайловым сравнением b0caa004↔7fb0d327 и cdb4403↔7fb0d327

### FINDINGS_CLOSURE (прежние findings 1-5)
1. Save-failure coverage — ЗАКРЫТ: drafts.test.tsx:246-309, значимые ассерты (error, dirty=true, envelope жив по content-scan, retry → слот retired).
2. Vacuous 404 — ЗАКРЫТ: drafts.test.tsx:557-570 (sessionStorage null + pointerSurvives false — полный scan), store.test.tsx:81-101 (+ run-указатель). Мок Error→ApiError правомерен (transient по контракту сохраняет указатели — со старым моком тест был невыполним при любой контракту-корректной реализации).
3. Local-case two-reloads — ЗАКРЫТ: фикс store.tsx:232 + deps (235); RED-доказательство в логах cdb4403; GREEN трассировкой + vitest; server-кейсы очищаются по baseline-правилу; retire/discard/deleteEverything/404 не сломаны; для серверных кейсов нового пути «никогда не очищается» нет.
4. Vacuous discard — ЗАКРЫТ: store.test.tsx:288-317 (content-scan до, удаление после, анти-vacuous guard).
5. Envelope depth/size — ПЕРЕНЕСЁН в backlog (решение диспетчера).

### NEW_FINDINGS
Блокирующих нет. 1. [Info, pre-existing с b0caa004] startRun create-ветка не сбрасывает draftRestored — устаревший баннер (косметика, backlog). 2. [Info, evidence-quality] формального green-лога VERIFY A2 в outputs не было на момент ревью (vitest-кэш + typecheck.log) — диспетчеру не интерпретировать final-targeted/final-full.log (это RED-прогоны на cdb4403) как green кандидата.

### CONTRACT_COMPLIANCE A-F: выполнено, без изменений от A1; фикс минимальный в scope; scope creep нет; dev не трогал QA-ассерты (drafts/store.test идентичны qa-a2).
### ACCEPTANCE_COVERAGE: 1✓-10✓; e2e 11-13 NOT_RUN — deferred release gate.
### NEXT: PASS на 7fb0d327; обязателен security на этом SHA до интеграции (выполнено диспетчером); combined gates интегратора; e2e 11-13 отдельный gate; findings 5 + наблюдение 1 → backlog.

## ashyq-security A2 — INVOCATION_REF: agent_c074846b-5c07-45be-9f03-f0064f269138
- VERDICT: PASS (только на 7fb0d327...; ограничение метода: нет Bash — backend/api-not-touched принят по QA-артефакту A1 + прямому чтению)
- 1. parseEnvelope/prototype pollution — БЕЗОПАСНО: все storage-чтения в caseDrafts.ts; пересборка envelope из именованных полей; __proto__ как own-property инертен (JSON.parse не триггерит setter; setIn immutable.ts:29 computed key = DefineOwnProperty; рекурсивных merge нет); битый/невалидный envelope → слот удаляется. Глубина/размер не ограничены — backlog (LOW, same-origin write required).
- 2. Draft→DOM XSS — ЧИСТО: ноль dangerouslySetInnerHTML/innerHTML/eval/new Function/document.write; draft только в React-контролы; href'ы не строятся из draft.
- 3. Изоляция/тенанты/logout: слот по case_key, применяется только при совпадении; local keys = crypto.randomUUID() (непредсказуемы); logout → sessionStorage переживает, но 404 (анти-enum tenancy.py:12-24) само-исцеляется без раскрытия; осиротевшие envelopes невидимы (data-at-rest, не хуже baseline; опциональный wipe при logout — backlog); same-org восстановление unsaved draft коллеги — org trust domain, принято; legacy-миграция при чужом указателе уничтожает (не раскрывает) draft — one-time upgrade окно, LOW.
- 4. Mass assignment — FAIL-CLOSED: ApplicantProfileIn extra="forbid" (profile.py:26-27) → 422; персистенция только model_dump; id/timestamps серверные.
- 5. A2-guard: не создаёт новый класс роста; слоты уходят на save/discard/404/deleteEverything; брошенные local-кейсы без GC — QuotaExceeded глотается (graceful); suggested backlog: prefix-scan GC с eviction по saved_at.
- 6. Guards не тронуты: 401-reload/402-paywall на месте; gen-guards не ослаблены; A2-фикс вне путей генерации.
- FINDINGS: только LOW/backlog (1-5 выше) + INFO e2e NOT_RUN. Ни одного Medium/High/Critical; RCE/SSRF/tenant-bypass не заявлялись и не воспроизводились.
- REQUIRED_EXTRA_TESTS: same-tab user switch (404 → указатель забыт, слот удалён); QuotaExceeded graceful; __proto__ own-property инертность + 422 fail-path; GC-характеризация.
- NEXT: принять 7fb0d327 по security; пп. 1-3 тестов → QA; e2e 11-13 release gate; backlog: depth/size, GC, draftRestored-cosmetic, client.ts:201-222 path-интерполяция id (pre-existing, LOW).
