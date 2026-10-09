# Finite security UI report — template

**Status: NOT RUN / WAITING_ROOT_READY.** Это шаблон. Все observations, screenshots, AX, geometry и browser outcomes ниже ещё отсутствуют. UI не начинать до root actual full13 closure, exact source/delta/launcher peer binding, `ROOT_CONFIRMED_SOURCE_BOUND_UI_GO` и actual preview READY. Разрешённый объём — reversible local synthetic tests; новая человеческая авторизация не требуется.

## Привязка исполненного сценария

Заполнять только по фактическим сохранённым receipts, без подстановки старого authfalse preview:

| Поле | Фактическое значение сейчас |
|---|---|
| Applied head прочитан | `a0fc4a7b38162a7af7d438b8b148c49592e0563c` |
| Applied19 receipt SHA | `8ace9a3e51ffdaa8eaaa7068fc98c0df38ef7f6a289156ba584597fb16b6d380` |
| Actual tested full head / branch | NOT BOUND |
| Actual original full summary path/SHA, 13 step results | NOT BOUND |
| Initial source-manifest path/SHA + declared-map identity | NOT BOUND |
| Actual declared E2E PNG delta path/SHA / before-after qualification | NOT BOUND |
| Same19 + four config inputs before/after preview | NOT RUN |
| C final verifier plan | ready `06cfb7721d817770ea4abb2ef374963a5734545a7d8614363465e3dc23ccdfd8`; helper `4de011c7529cf4382901054ddea55d6998dafaa0f9601c10157dac8162879932`; static-only |
| Independent verifier review | B READY `6bd0e381c0e5d14cb516a9e76a91745a4034f6e6127ac51a7b4dbe16c71a5dfc`; receipt `77411ae8fd6b2a5bab4288b112d51862f9fa660b9f85dc51e0a3ed310de862d0`; QUALIFIED_ACCEPT static, no execution/GO |
| Separate final root launcher static binding | Launcher `4d2b0ea8e6494e73d677932d1a8e8038a49ac98a28751c1e30159bcdb1e3dff0`; B READY `0ff986846afdcdee491af52a74075f61c3f9169d271242e4afe5169ef4ac476b`, receipt `8f06ec69782f0f9a3debd7a9af1871b1534f36e905e00794e8b8e4a011805a83`; QUALIFIED_STATIC_ACCEPT/NOT_RUN. Actual runtime binding remains NOT BOUND; prior b78d rejection preserved as history |
| Root bound GO receipt/message | NOT RECEIVED |
| Actual fresh preview root / SQLite / nonce / local URLs | NOT RECEIVED |
| Actual auth=true / development / demo=true / provider+decision=none / noWorker settings receipt | NOT RECEIVED |
| Actual ready health + signed-out auth-enabled receipt | NOT RECEIVED |
| Owned process groups / shared lifetime lock receipt | NOT RECEIVED |
| Retained STOP before/after | Expected unchanged `65b5ff0e…`; execution postcheck NOT RUN |
| Owned browser task session / tab IDs / viewport | NOT CREATED |
| Browser closure/reset + root cleanup/errors/free-ports receipt | NOT RUN |

InitialSHA — identity до full checks. Финальный physical whole tree не объявлять равным initialSHA: separately bound generated PNG deltas и unlisted runtime/cache outputs имеют другой scope. Source pins этого шаблона — readiness read до full closure, не будущий browser source binding.

## Фактическая finite matrix

Для каждой строки сохранить: actual native action/time, screenshot path+SHA, AX path+SHA, geometry path+SHA, actual viewport, shared binding receipt SHA и result/reason. Geometry включает viewport, body/document widths и horizontal overflow; длинная вертикальная страница требует обычного scroll. Expected criterion ниже не является observed outcome.

| № | Planned capture / expected criterion | Actual observation | Result |
|---|---|---|---|
| 01 | Public legal desktop1440×900: draft notice, workspace/data scope, operator and consent gaps доступны signed-out без принятия terms | Нет screenshot/AX/action | NOT RUN |
| 02 | Public legal phone390×844: те же notice/gaps доступны через scroll; body/document geometry сохранена | Нет screenshot/AX/geometry | NOT RUN |
| 03 | Synthetic owner A saved case, **no run**: Export native route, Show my stored data, свой field marker и `runs:[]`; нет shortlist export обещания до research | Нет account/case/export observation | NOT RUN |
| 04 | Phone: только disposable saved A case; control disabled до exact DELETE, native acknowledged delete, конечный UI и native reload case list | Нет delete/confirmation/reload evidence | NOT RUN |
| AX/action-only prerequisite | Новый **unsaved local A case**: A draft field marker, no Save, bounded debounce, native same-owner reload сохраняет draft/restored notice | Не выполнялось; отдельный screenshot сверх семи не требуется | NOT RUN |
| 05 | Tab2: native sign-out A/register B, settled profile **до ввода B marker** не содержит old A draft/restored notice. Screenshot; потом Save B case no-run | Нет B auth/reset/field observation | NOT RUN |
| 06 | Cooperative tab1 после owner event **до reload**: private A tree заменён; visible B owner/workspace, нет A draft/restored-A notice | Нет settled cross-tab observation | NOT RUN |
| 07 | Phone: B saved case после reload; новый local B unsaved marker, no Save, debounce + same-owner reload сохраняет B draft без A marker | Нет B persistence/phone evidence | NOT RUN |

Dictionary берётся из exact final C plan `test-data.json`: `.invalid` fresh nonce owners A/B, owned workspaces, pinned bundled synthetic profile, field markers A saved/A draft/B saved/B draft. Не придумывать editable profile-name input и не устанавливать данные через JS/storage/cookies/API/SQL. Saved profiles autosave: draft prerequisite делается в **новом unsaved case**. A saved case удалён в04, поэтому его отсутствие у B не является независимой tenancy proof; cross-owner sentinel — local A draft.

Capture limits: ровно семь planned screenshots + обязательные AX/action-only checks; никакого research/collect/retry, account-wide delete, password reset/mail, payment, social/messages, transcript upload, provider/model/university activity, external links, production или terms acceptance. Download остаётся optional NOT RUN, если documented CUA save/download mechanism не доступен. Не заменять failed criterion соседним flow. Не выполнять дополнительные tests/full для этого walkthrough.

## Readiness до browser исполнения

Прочитанные current docs/source pins находятся в `source-pins.json`. Это saved-source inspection, не runtime result:

- `operator-facts.json` сохраняет `UNCONFIRMED_NOT_FOR_FINAL_PUBLICATION`. Legal identity, contacts, actual DB/replica/backup/log countries, processors, lawful-basis review, minors/representative protocol, consent runtime evidence и incident readiness — null/unresolved. Region `ams` не устанавливает страны данных.
- LegalScreen явно показывает workspace sharing, отличия case/account/community controls, operator/location/recipient/retention gaps и отсутствие принятой notice-version/representative receipt. Public draft accessibility сама по себе не означает согласие или legal publication readiness.
- README/CONSENT_SPEC/DATA_RETENTION говорят о separate consent server contract и data-class lifecycle. Case cascade/UI delete не закрывает jobs/audit/payment/recipient/backup copies. Исторический restore drill и source claims не заменяют actual current deployment evidence.
- RELEASE_READINESS пока содержит **до-apply baseline8010806f / NOT READY** и instruction заполнить final source/gates/peer receipts. После full root может закрыть именно выбранные локальные code-control rows по фактическим тестам/peer/UI; остальные operator/consent/retention/production rows продолжают unresolved. Шаблон не редактирует эти документы.
- SECURITY.md признаёт, что rejected query/URL errors могут сохранять rejected values. C diagnostic-redaction packet — separate DESIGN_ONLY, не применённый privacy fix. Atomic reset и Nginx route-header tasks также не покрываются этими семью captures.

## Exact product-close fields для root

Заполнить отдельно, используя явные PASS/FAIL/NOT RUN и конкретный scope:

1. **Selected local engineering controls:** exact app/test19 and docs10 bindings, author/independent source peer receipts, meaningful native OFF/ON evidence, actual core/full summary/logs. Full result заполнять по original actual receipts; не из commentary/ожидания.
2. **Finite UI behavior:** выполненное число из7, actual outcomes по каждому критерию и AX-only prerequisite, source/runtime binding, missing/failed actions. Static helper/launcher review не является browser PASS.
3. **Lifecycle:** shared lock held, actual own fresh DB/no seed/noWorker/provider-none/auth flags, owned browser closure/reset, every owned group cleanup attempt/error, free5173/8099, source19/config/STOP postchecks. Чистый UI не закрывает неуспешный cleanup.
4. **Legal/operator state:** документы остаются draft/unconfirmed; identity/contact/storage/processors/minors/consent/retention/incident fields подтверждаются отдельно. Не переименовывать общий статус в compliant/production-ready из-за local gates.
5. **Open next work:** rejected PII diagnostics, atomic reset, version-bound Nginx/header verification, operator/consent/rights/retention и deployment evidence. Design-only не считать delivered implementation.
6. **Evidence archive scope:** only source-bound manifests/logs/synthetic screenshots/AX/geometry/actions. Без DB/private runtime/dependencies/browser profile/cookies/tokens/password or credential request bodies; untouched original full logs preserved separately.

## Формулировка итогового вывода после исполнения

`На exact source <HEAD>/<source19 SHA> и fresh synthetic local auth preview <receipt SHA> выполнены <N>/7 captures: <PASS/FAIL/NOT RUN>. Наблюдались <specific UI outcomes>; <missing/failures> остались. Native same-owner reload и cooperative tab A→B показывают только зафиксированное видимое поведение. Full/gates <actual receipts> и lifecycle cleanup <actual status> приведены отдельно. Документы остаются draft; operator/consent/minors/retention/production gaps не закрыты. Это не full privacy/security certification, wiping proof, competitor benchmark или гарантия отсутствия всех races.`

До actual READY все поля этого шаблона остаются NOT RUN/NOT BOUND.
