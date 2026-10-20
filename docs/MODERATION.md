*Draft, not reviewed by the owner.* This runbook describes what the code does today and proposes how a person
works the report queue. It is not legal text, and the community rules' wording and the appeal path are not decided
here (see the end of this page).

# Moderation runbook

The community module (feed, replies, private messages, profiles) has two safety tools. **Blocking** is the
member's own decision and works at once, in both directions, without waiting for anybody
(`backend/tests/test_social_moderation.py`, the blocking tests). **Reporting** is a request to a person: it puts the
content in a queue that a moderator works from. This page is about that queue. The member-facing summary is the
"Community guidelines (draft)" panel and the "What you write in the community" paragraph on the legal screen
(`frontend/src/screens/LegalScreen.tsx`).

## 1. What the report queue is

- **Filing a report.** A signed-in person reports a post, a reply, a private message or a profile with
  `POST /api/social/reports`: a reason from a closed list (`harassment`, `personal_information`, `impersonation`,
  `spam`, `misleading_advice`, `other`; `ReportReason` in `backend/app/domain/enums.py`) and an optional note of
  at most 500 characters. A reason outside the list is refused (422), and the same person cannot report the same
  thing twice (409) (`test_a_reason_the_product_does_not_define_is_refused`,
  `test_the_same_person_cannot_report_the_same_thing_twice`). A private message can be reported only by one of
  the two people in the conversation (`file_report` in `backend/app/api/routes_social.py`).
- **What a report keeps.** The reporter, the type and id of the content, whose content it was, the reason, the
  note, and an **excerpt of up to 600 characters copied when the report is filed** (`ContentReport` in
  `backend/app/models/social.py`). The report survives the content being deleted, by its author or by a
  moderator, so the queue can still be reviewed (`test_a_report_survives_the_thing_it_was_about`).
- **The queue.** `GET /api/social/moderation/reports?status=open|actioned|dismissed`, oldest first, paged. The
  screen is `ModerationScreen` (`frontend/src/screens/ModerationScreen.tsx`), with one tab per status, the
  excerpt, the reporter's note, a note box and two buttons, **Remove** and **Dismiss**.

## 2. Who may read it

Only the accounts the deployment names in `UNIMATCH_MODERATOR_EMAILS`, a comma-separated list of account e-mails
(`moderator_emails` in `backend/app/config.py`; `require_moderator` in `routes_social.py`). Anyone else gets 403
from the queue routes, and the screen explains that instead of showing a blank page
(`test_only_a_named_moderator_can_read_the_queue`).

This is deliberately **not** a workspace role. An organisation's owner administers their own workspace, and the
community spans every workspace, so no workspace role (owners included) can read or act on the queue. The
deployment operator decides who moderates by editing the setting. With the setting empty (the default), nobody
can work the queue, and a deployment that turns the community on should name at least one moderator first.

**Reaching the screen.** Open `#/moderation` in the app. The sidebar entry is shown only to a principal whose
role is `moderator` (`frontend/src/App.tsx`), and no account has that role today: workspace roles are `owner`.
So a named moderator reaches the queue by its address, not from the sidebar.

## 3. What a moderator does with a report

Work the **Open** tab from the top (oldest first). For each report:

1. **Read** the excerpt, the reason and the reporter's note. The excerpt is what the content said when it was
   reported; the content itself may already be gone.
2. **Decide** one of the two actions the product has
   (`POST /api/social/moderation/reports/{id}` with `action` and `note`; `ResolveIn` in
   `backend/app/schemas/social.py`):
   - **Remove**: the reported content is deleted and the report becomes `actioned`
     (`test_removing_content_deletes_it_and_closes_the_report`). For a post, reply or message, that one item is
     deleted. For a **profile**, the profile, the person's posts and replies, and their picture are deleted; the
     account and its applicant research stay (`_remove_subject` in `routes_social.py`; the same operation as the
     person leaving the community). Content its author already deleted still closes the report as `actioned`.
   - **Dismiss**: nothing is deleted, the content stays, and the report becomes `dismissed`
     (`test_a_dismissed_report_is_closed_and_the_content_stays`).
3. **Record the reason** in the note box before pressing the button (up to 500 characters). The note is stored
   with the decision and shown in the closed tabs. Write what rule the content broke, or why it did not.

A report is decided once: resolving it again is refused with 409 (`test_resolving_twice_is_refused`).

**What the product does not offer a moderator.** There is no "hide" (removal is deletion), no edit of someone
else's content, no suspension or ban, and no moderator-side block. Blocking is a member's own tool. Several
reports about the same content are separate rows; each one is resolved on its own.

## 4. Target times (proposed, not a product promise)

- **First look at any open report within one working day.**
- **A report on a private message, or with the reason `harassment` or `personal_information`: within the same
  working day.**

The product sends **no alert** when a report arrives and does no automated filtering, so these times hold only if
a moderator opens the queue on a schedule. The legal screen tells members exactly that, and points them to
blocking for anything that has to stop at once. These targets are not shown to members anywhere in the product.

## 5. What is logged, and what the reported person is told

- **Logged**: the report row itself. On a decision it records the status (`actioned` or `dismissed`), the
  moderator's account e-mail (`resolved_by`), the time (`resolved_at`) and the note (`resolution_note`); the
  excerpt and the content's id stay on the row after a removal (`test_a_removal_leaves_a_record_behind`). The
  closed tabs of the queue are where this record is read. A moderation decision writes no separate entry in the
  workspace audit log.
- **The reporter** sees no outcome in the product: nothing reports a decision back to them.
- **The reported person** is not told by the product either. There is no notification channel: removed content
  simply disappears (a removed post answers 404), and a removed profile disappears from the community while the
  account stays. If a moderator wants the person to know, that is a message outside the product, and whether to
  send one is the owner's decision (section 7).

## 6. How a person leaves

- **Leaving the community** (`DELETE /api/social/me`) deletes the person's profile, posts, replies and picture
  and keeps their account and research. Their private conversations stay, because the other person's copy is
  theirs too (`test_leaving_removes_the_profile_the_posts_and_the_replies`, `test_the_account_survives_leaving`,
  `test_leaving_does_not_delete_the_other_persons_copy`, `test_leaving_the_community_takes_the_picture`).
- **Closing the account** (`POST /api/auth/me/delete`, confirmed by password) is the stronger act and erases
  the person's social footprint with it (`test_deleting_an_account_erases_its_social_footprint`). Reports the
  person filed are tied to their account (`reporter_id` is `ON DELETE CASCADE` in `ContentReport`); reports
  *about* their content keep their excerpt, because the content's id and author are not foreign keys.

## 7. What is not decided here

These belong to the owner and are left open on purpose:

- **The rules' wording.** The "Community guidelines (draft)" panel on the legal screen is the only text members
  see. This runbook does not add rules to it.
- **The appeal path.** There is none in the product. A removal cannot be undone, and nothing tells the author
  that a decision was made or how to contest it.
- **Whether the reported person (or the reporter) is told**, by whom and in what words.
- **Who the moderators are**, beyond the mechanism (`UNIMATCH_MODERATOR_EMAILS`), and whether the targets in
  section 4 are adopted.
