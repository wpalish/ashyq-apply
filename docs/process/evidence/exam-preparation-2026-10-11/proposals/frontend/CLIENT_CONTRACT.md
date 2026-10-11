# Frontend preparation contract — agreed, proposed only

Backend CONTRACT `starter-2026-10-11-v1`, SHA256 681cca32ae0ed6d96e0e149d379ec3916e65b639f55a29ad51c81bd0ad6c3809 (coordination confirmed with backend author). The exact endpoint/DTO contract is that saved CONTRACT; this frontend uses its catalogue, access, plan, lesson, submit and progress endpoints.

One #/preparation screen: Goals is a stored-evidence snapshot for an owned selected programme, not a new persisted numeric-goal feature; Practice starts one original starter lesson; Progress is server-saved submitted attempts. No unsubmitted-answer server endpoint: current answers remain in the form only until Submit succeeds. No promise of refresh recovery for an unsubmitted form.

All case-scoped calls use encoded profileId through existing owner-checking API client. Missing/unsaved profile and identity unavailable => no preparation calls. Valid ACTIVE/EXHAUSTED started term may grant preparation independent case/quota; explicit development access labelled. Expired access retains own progress read; 402 preparation_subscription_required never becomes the case-unlock checkout. Billing only claims inclusion from optional confirmed preparation_access.allowed.

Submit captures a single immutable {attempt_id, lesson_id, version, answers} before await. A ref excludes duplicate in-flight calls. Retry retains same UUID/payload; restarting or choosing a different lesson is an explicit new intent and receives a new UUID on its next submit. Case/account/lesson intent fences discard late data and feedback. Server response owns correctness and explanations, never official IELTS/SAT scores.

No new dependencies, provider APIs, content copied from official exams, source writes or executed gates. Root alone applies and runs acceptance.


Additive catalogue `exams` metadata is adopted exactly: IELTS Academic/Digital SAT have starter track IDs; TOEFL iBT/DET/HSK-HSKK/CSCA are planned with no local practice. UI shows real lesson selectors first, followed by external-only exam information/edition caveats. Missing ClaimOut.scope remains unknown; recorded scope uses named fields, including unstated qualifications, without upgrading it to coverage. Component thresholds retain their own values and are not collapsed into an overall score.

Local safety: the child is keyed by verified context identity, saved profile ID and caseEpoch; store loading at case-switch entry hides old case contents. Requests use native client owner checks. Both case and practice session capture/check the live owner on success, failure and finalization, including storage changes before a React remount. Programme ID and lesson request intents fence replacement; progress refresh keeps the latest same-case request. A submitted response must match case/lesson/version/UUID. Immutable payload stays frozen after failed submit; explicit restart/new lesson begins a new intent. No cross-account draft or storage namespace is added.

CONTRACT was amended by its author after the initial 57d736f3 snapshot to add export/replay/conservative scope/stale caveats; those do not change these six endpoint DTOs. The final exact read snapshot is also saved here as inputs/backend-CONTRACT.md. Backend gate results are not frontend acceptance.
