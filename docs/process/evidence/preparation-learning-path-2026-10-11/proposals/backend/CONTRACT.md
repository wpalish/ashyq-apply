# Original learning pack — backend contract

2026-10-11. Proposed additive contract; not yet applied or a native gate receipt.

`PACK_VERSION = learning-pack-2026-10-11-v1`; unchanged `STARTER_VERSION = starter-2026-10-11-v1`.

## Requests

- `GET /api/preparation/catalogue?catalogue_version=learning-pack-2026-10-11-v1`: opt-in catalogue. Omit the parameter for the exact legacy catalogue; explicit starter version also selects legacy. Unknown catalogue version:422.
- `GET /api/profiles/{profile_id}/preparation/lessons/{lesson_id}?version={summary.version}`: exact lesson/version pair required. Old three use starter version; six new use pack version. Ownership404 and current learning-term402 preserved.
- `POST /api/profiles/{profile_id}/preparation/attempts`: unchanged outer keys `{attempt_id:UUID,lesson_id,version,answers}`. All questions exactly once. Each answer is **either** legacy `{question_id,choice_id}` **or** short `{question_id,text}`; extra fields/mixed format/wrong question/version/choice fail422 without keys. Text length1..100. New UUID creates one submitted receipt; identical case-scoped UUID/payload replay returns that receipt, including after expiry; changed payload409. Old request digest remains exact. Retry uses the same immutable UUID and payload.
- `GET /api/profiles/{profile_id}/preparation/progress?catalogue_version=learning-pack-2026-10-11-v1&limit=20`: same raw aggregate counters and owned history; opt-in adds `catalogue_version` and `completed_lessons:[{lesson_id,version}]`. `completed_lesson_ids` contains known exact-version submitted lessons in this catalogue, not mastered skills. Default retains old top-level keys and starter completions; history can include submitted short-format records. History is readable after term expiry.
- No calendar, official Academics, quota, research, checkout, migration, new diagnostic or baseline writes.
- `GET /api/profiles/{profile_id}/preparation/attempts/{attempt_uuid}/review`: owned stored client UUID receipt404 if absent/foreign, no active-term requirement. Returns `{attempt: stored receipt union, lesson: version-exact public lesson union|null, notice:string}`. It never regrades or resolves another version; unknown/retired lesson pair returns `lesson:null` and an explicit unavailable-version notice while preserving the stored receipt. No read-side practice/quota/calendar writes.

## Public DTOs

Opt-in catalogue has the legacy keys `{version,tracks,lessons,exams,notice}`. Its `version` is the pack catalogue version, not the version for every lesson. Each lesson summary is `{id,track_id,title,question_count,version}`. Track `lesson_ids` are ordered:

- IELTS Reading: `ielts-reading-1`, `ielts-reading-headings-1`, `ielts-reading-completion-1`, `ielts-reading-features-1`.
- SAT Math: `sat-math-1`, `sat-quadratic-structure-1`, `sat-data-interpretation-1`.
- SAT Reading & Writing: `sat-rw-1`, `sat-grammar-transitions-1`.

Lesson top-level fields remain `{id,track_id,title,version,introduction,questions,unofficial:true}`. `introduction` includes full original teaching/examples/passages/instructions from the reviewed student material, with no private keys. The lesson question union is:

- Choice: unchanged `{id,prompt,choices:[{id,text}]}`.
- Short: `{id,prompt,answer_format:'short_answer',max_words:2}`. A number is allowed by the lesson's instruction.

Only the IELTS completion lesson has short questions. The original starter item IDs, choices, prompts, grading, feedback and version are unchanged.

## Receipt/history DTOs

Outer receipt remains `{id,attempt_id,profile_id,lesson_id,version,answers,correct,total,feedback,created_at}`. Choice answers and feedback remain exact. Short feedback is `{question_id,selected_text,accepted_answers:string[],correct,explanation}`. Private accepted forms and explanations appear only in accepted attempt receipts/history/export, never initial lessons/catalogue or validation errors. History is the stored feedback snapshot, not reconstructed from whichever content version is current.

New pack receipts preserve the first submitted answer-array order and raw short text, including outer/internal whitespace, case and final full stop; whitespace-only text fails422. Grading normalization does not rewrite stored answers or selected_text. Order-independent UUID replay returns that first stored receipt. Legacy starter receipts retain their original canonical question order and exact choice representation.

Short grading normalizes letter case, surrounding/repeated whitespace and **one** optional final full stop. Preserve interior punctuation, word order and singular/plural. Require complete equality to an item's closed variant list plus maximum two whitespace-delimited words/numbers. Accepted forms: `dividers`; `36`; `condition sheet`/`sheet`; `briefing session`/`briefing`/`session`; `download code`/`code`. No fuzzy, substring or external grader.

Raw `correct/total` is formative practice; repeating known questions is review, not unseen diagnosis, official IELTS/SAT score, mastery, readiness or requirement attainment. No automatic calendar completion.

## Integration scope

Preserve default old catalogue bytes/old payload digests and old tests. Add schema types, a separate immutable pack module, compatibility dispatch in routes, and new native controls only. `catalogue.py` and existing tests remain byte-identical. Keys/teacher sections in the external drafts are authoring inputs, not public delivery assets. All new content remains modest original practice with qualified pedagogy/learner validation pending.
