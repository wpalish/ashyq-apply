# Frontend learning-path contract

External proposal only; current source remains root-owned. Backend input: CONTRACT.md SHA256 2738502e58ebf483098361f6760cf26b5f56c0961e7aefc6ab139b32bd8ba466; additive owned-review contract 18481d80234b266c88c477d643337f8613ca1f03f6e3501060769d3740a8eafd.

- Screen explicitly opts catalogue/progress into `learning-pack-2026-10-11-v1`. No-argument client methods retain the exact legacy catalogue URL and progress `?limit=20` URL. The new optional query is `catalogue_version`, not a replacement for each lesson's `version`.
- Summary `version` is optional in the common TypeScript catalogue for unchanged legacy responses. The opted-in screen requires each summary version, matching catalogue/progress version and `completed_lessons`. It requests/accepts a lesson only by exact summary ID/version. Old starters keep starter version.
- Choice questions/answers/feedback retain original fields. Short questions `{id,prompt,answer_format:'short_answer',max_words}` use answers `{question_id,text}` and accepted feedback `{question_id,selected_text,accepted_answers,correct,explanation}`. Initial lessons contain no keys; the client does not grade or normalize accepted variants.
- One complete answer payload/UUID is retained through network error, double submission and explicit retry. Fields freeze after first submission failure until retry or explicit new lesson/attempt. A new intent remounts the form. Owner/mount/case and intent fences remain; accepted profile/lesson/version/UUID and ordered answer IDs/values must match (JSON object key order is immaterial) before success or next-lesson feedback.
- Track order comes exclusively from `track.lesson_ids`. Version-qualified saved submission markers use `completed_lessons` or accepted receipts, never raw lesson IDs or correctness as mastery. Next lesson opens only after an accepted receipt; other lessons can be chosen explicitly in the list.
- History review loads `/api/profiles/{profile}/preparation/attempts/{attempt_uuid}/review` after expiry and fences owner/profile/UUID/lesson version/newer selection. It renders the accepted stored feedback with the exact immutable returned lesson; it never reconstructs a changed current lesson. Same pending or resolved selection is a no-op; failed reads allow explicit retry. If original choice text is not stored, show stored question/choice IDs explicitly. Current-session text comes only from the exact matching lesson version. Incorrect feedback appears first, with selected answer, accepted/correct answer and explanation.
- Calendar/StudySchedulePanel/task IDs/manual dates/completion, official scores, baseline, research quotas and subscriptions are not written by practice. Existing calendar starter links enter the ordered unit.

## Stable accessible selectors

Existing mode labels, three native Start labels, radios, `Submit practice`, `Retry same submission`, `Practice feedback`, `practice-result` and `progress-summary` are retained.

New: textboxes `Answer 1`…; `Next lesson: <title>` with `data-testid=next-lesson`, `data-lesson-id`, `data-version`; history buttons `Review saved attempt 1`… with `data-testid=review-attempt`, `data-attempt-id`; `Saved attempt review` section and `saved-attempt-review` result; feedback rows `feedback-item` / `data-correct`, `Your answer:` and `Correct answer:`.

Scope: bounded original practice units; no full-course, official-score, band diagnosis, mastery or admission claim.

TeachingText renders a finite trusted student subset with escaped React text: headings, paragraphs, lists, pipe tables, bold/emphasis/code. No raw HTML, HTML parser, link or URL execution, Markdown dependency or client keys. Exact returned lesson text remains the API authority; unsupported syntax stays literal. Tables have contained keyboard-accessible scrolling.

Final backend authority: CONTRACT.md SHA256 fa13b5868a1af9987ccbf398e51d924508f6a5e6af5989bbacbc685ba16a32df. New pack retains first submitted answer order/raw short text; grading normalization is server-only. Legacy choices retain canonical question order; the UI submits public question order.
