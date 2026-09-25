# HANDOFF — the baton

One file, always current, committed with the code. The agent who holds the baton keeps it true.
Rules for using it: `AGENTS.md`. Task definitions: `analysis/AI_TASK_BRIEF.md` §6.
Write for a reader who has **zero** chat history — because that is exactly who reads it.

## 1. Baton

Current holder: **claude-opus-5**, 2026-09-20 UTC. Branch: `claude/greeting-16wj2z`, branched from `task/v2-01-research-benchmark@a4cd5b3`; base: `b267b337`. V2-01 is not accepted; see review blockers below.


| | |
|---|---|
| Holder | **claude-opus-5** |
| Since (UTC) | 2026-09-20 |
| Branch | `claude/greeting-16wj2z`, from `task/v2-01-research-benchmark@a4cd5b3` (owner-assigned branch for this session), which came via V2-00 from `main@b267b337` |
| HEAD when written | `a4cd5b3` (gpt-6-astra's draft5 `wip:`, now validated — see §6) |
| Origin main when checked | `b267b337` (fetched 2026-09-20; the branch is 22 commits ahead and 0 behind) |
| Previous holder | gpt-6-astra; cut off by its token limit during the draft5 gate run |
| Sections 3 and 4 below | Historical: they describe the `[0.8]` recovery and are kept as a record, not as current dirty state. Read §2 and §5 for where things actually stand. |

## 2. Current task

**Phase 2 is `ready-for-review (PR #16)`.** PR #15 was merged by the owner on 2026-09-21 at `cba911a`; a merged PR cannot track new work, so everything since is PR #16 from the same branch. **Phase 3 §10 — conditional wording is not a settled requirement (in-progress).** Previously: **Phase 3 §9 — a document that waits for another.** Previously: **Phase 3 §7 — the availability roll-up, and two dead fields.** Previously: **Phase 3 §4 — "test optional" is not "the test is irrelevant".** Previously: **Phase 3 §3 — the English-test waiver.** Previously: **Phase 3 §6 — two scholarship decisions the schema was missing.** Previously: **plan V2-30 — a requirement says who it is for, backend and screen.** Previously: **plan V2-23, the kind the first pass left out.** Previously: **plan V2-20 exit criterion — the evidence answers its own questions.** Previously: **EXTRA-4 — an optional prefilter rejection, off until measured.** Previously: **V2-29 — a degree word in a heading is not a programme.** Previously: **V2-24a — telling a real change from a re-render.** Previously: **V2-28 — a programme title is not a term.** Previously: **V2-27 — the scope rate says why.** Previously: **V2-22b — the registry read as identities.** Previously: **V2-20 — evidence history (done).** V2-20a shipped `SourceSnapshot`; V2-20b closes the claim half. See the numbering note in §5. Previously: **conflict model v2 (plan V2-23).** Previously: **V2-25 — all five claim-producing adapters read scope.** Previously: **V2-24 — a scope refusal is said out loud to the applicant.** Previously: **V2-23 — the assessment refuses a claim whose page is about something else.** Previously: **V2-22 — fill a claim's scope from what its page states.** V2-21/V2-21b gave scope a shape and put it on the claim; this fills it, from the page's own words only. Previously: **V2-21b — carry the scope on a claim.** Phase 1 is complete, measured and wired (PR #15); this starts Phase 2 on the failure Phase 1 never touched. Phase 1 so far is `ready-for-review (PR #15)`, which supersedes draft PR #14. Phase 1 retrieval was measured live: The owner approved the §6 exception and authorised the live probe; the Exa adapter works and the retrieval ceiling moved **1/10 → 9/10**. V2-01 was accepted 2026-09-21 and its record is below.
Owner explicitly prioritizes the new workstream. V2-01 follows this documentation commit in a task branch from this predecessor (explicit branch exception). Goal: measure current research/discovery quality before architecture changes.


**Historical security audit — PR #12 merged; retained below for provenance.**

Unplanned work: the owner asked for a security review of `main` rather than the next brief task. The
queue in §10 is untouched and the C2 items in the previous §2 stand exactly as codex left them; nothing
in this branch changes the pipeline, the ranking, the discovery adapters or a migration.

Nine findings were fixed on `task/security-audit-hardening`, three of them proved with a
proof-of-concept test that fails against `main` and passes here. The most serious is a forgeable payment
webhook: with payments enabled and the shipped default provider (`fake`), the signing secret fell back
to the string `test-secret` written in `app/payments/provider.py`, so any customer could sign a `paid`
event for their own order id and unlock every case for nothing. `validate_runtime` did not stop a
production deployment from being in that state.

Findings deliberately **not** changed are listed in §7, so the next holder does not re-discover them and
assume they were missed.

### Historical C2 publication and outstanding product decisions

**Campaign `c2` publication is complete; remaining items are explicit product blockers.** GLM integrated
T16 (browser/egress hardening), T27 (claim verifier), T28 (source pages), T29 (catalog walker at the
adapter seam) and T32 (freshness/source scanning) onto this branch. Its own ledger and review correctly
state that T29 remained dormant in production; `8d2fa10` closed that seam and the live smoke proved
catalogue traversal plus `SourcePage` recording. The owner explicitly authorized the two bounded T30
batches. They measured programme recall 7/10, category recall 26/30 and zero material false positives.
The registry itself remains at 19 because no 41-entry, human-checked official candidate set was supplied
or canaried; claiming 19→60 would violate T30's own admission rule. T26 is blocked on a contradictory
scope contract: its promised source-to-UI News vertical slice cannot be built through the currently
allowed model/domain/runner-only paths. T31 remains blocked on an owner-selected provider, secrets
outside Git, and the required data-policy acknowledgement. PR #8 merged the verified campaign into
`main@04a3058`; both PR-triggered matrices and the post-merge release-gates are green.

Status vocabulary: `not-started` · `in-progress` · `blocked` · `ready-for-review (PR #)` · `merged`.

## 3. Done in this task (commit hash per item — a claim without a hash is not done)

**Catalogue walker: footer links are not leads (`35bf92a`).** Siblings are grouped by host and parent path,
so a site root is in no list. A link with no programme signal that leaves the catalogue's own host is
recorded as `walker_no_signal` and not read. The T29 contract (a signal-less lead on the catalogue's
own site is read and classified) is kept; its R2 and R8 tests caught my first, broader version and
are unchanged. Warsaw's pre-search reads are on its own host (cookie-statement, research,
governance), so this does not reach them; that needs a contract decision.

**Run 18 (35855377260) named the pages.** **Aalto:** `get #1` is `https://www.aalto.fi/robots.txt` at
t=2 s, then nothing until 90 s. The fetcher waited out a robots.txt Crawl-delay with no cap, which
fits these symptoms. Aalto's actual delay value is not yet confirmed; run 19 logs it. Fixed (`7ee02a7`): a delay over 10 s is refused at once (ROBOTS_DISALLOWED with the delay named), never waited
out and never ignored. **Vienna, Warsaw:** before search, discovery reads a university homepage's
service links (moodle, wiki, blog, webmail, cookie-statement, library, governance). Most are cached
(0.0 s) but each costs a page of budget. That is the next fix: the pre-search walk should not follow
service links. **Delft, UBC:** the page budget ends in the funding walk, after requirements; lower
priority.

**Run 17 (35853021542, head `44823bc`, all five owner decisions): claim_recall moves for the first
time, 0/62 → 2/62.** claim_precision 0/5 → 2/9, verbatim_evidence_rate 0/5 → 2/9, support 2/18,
unsupported 0/2, wrong_scope 2/9, programme_page_recall 5/10. Six of ten cases still hit a budget, and
the next work is the time spent in reads before search (run 18 has per-read logging, `840fdad`).

**Run 16 (35846785728): where the budget goes, first answer.** Search is fast (0.7–0.9 s per call), and
it is not where the time goes. **Aalto:** 2 reads, 0 searches, empty log, 90 s, so something hangs
before discovery searches. **Vienna:** its first search starts at t=73 s, after 95 reads.
**Warsaw:** 46 reads and never searches. **Delft, UBC:** the page budget ends in the funding stage,
after their requirements were read. The time goes into reads **before** search. `840fdad` logs every
read (start, duration, outcome) so run 18 names the pages.

**The owner's five claim_recall decisions, implemented (2026-09-23).** Each commit ran the full gates.
- **4, support direction (`4215efc`):** a quote supports when ours lies inside the reviewer's, or
  theirs lies inside ours and ours is at most 300 characters (`metrics.quote_supports`). All eight
  published baselines replay byte-identically.
- **1, bindings (`fa4503c`):** `identity_bindings.reviewed.json` (draft1 stays frozen). Live capture
  maps with `normalize_subject_claims`. Live ceiling 14 → 28.
- **2, language key (`aeda991`):** Aalto's label renamed to `programme.language` in the certified
  corpus (`2026-09-23.reviewed`; amendment and new canonical digest in ACCEPTANCE.md).
  `program_exists`' stated language maps to it. Ceiling → 31. Top-level reviewed metrics identical.
- **5, date → season (`34acea4`):** a stated September–November programme start is the fall intake, in
  text and in a deadline table's start column. The scorer compares non-programme scope case-blind
  ("Fall 2027" vs "fall 2027" could never match). Golden demo unchanged.
- **3, HKU (`3bd91dd`):** a catalogue or unknown page may confirm existence only, by a full degree title
  the ontology equates with the request at the requested degree. Golden unchanged.
- Not yet mirrored: the oracle's programme-existence probe does not try the listing path (diagnostic
  only).

**Run 15 (35844255604, head `61a778d`): the title-degree fix holds live.** Groningen's non-EU/EEA
deadline row is now out of scope **only on intake** (degree resolved; population matches). With the
owner's date→season decision it would be fully in scope, and then only the support direction (§7 q.5)
stands between it and a first counted claim. 8 of 10 cases hit a budget this run; run 16 is the first
with the per-case budget diagnostic and honest search/browser counters (`f44a601`, `ddbe18c`).

**Run 14 (35839356648) and a title that names its degree (`5f9ba76`).**
- Run 14 is the first live run with per-population deadlines. Groningen yields 4 claims and KAIST
  yields claims for the first time (4). Groningen's deadline now comes as two claims: the
  **non-EU/EEA row matches the label's population**, and the EU/EEA row reports a different population
  (correctly, not the label's row). The non-EU row was still out of scope only on degree and intake,
  both silent. `critical_field_coverage` is 1/210, `wrong_scope` 3/9.
- **Fix:** `read_scope` required a degree word followed by "programme"/"degree"/…, so a title like
  "Computing Science | Bachelor | University of Groningen" never counted, while one body phrase ("a
  master programme") alone could set the degree. A title naming exactly one degree now settles it; a
  title naming two, or none, leaves the body to decide as before.
- **Golden re-captured with proof:** the old code reproduces the previous hash; 179 leaves changed in
  exactly three shapes (120 × claim `scope.degree` None → "bachelor", 59 × `published_scope` gaining
  "degree bachelor"), every one from a page whose title names one bachelor-level degree. No status,
  value, verdict or check outcome moved.
- Intake stays silent on Groningen ("Start course 01 September 2027" vs the label's "fall 2027"):
  turning a date into a season is a conversion, and it is left for the owner.

**V2-34: availability follows the final eligibility verdict (`2bfdbd2`).** The adapter rolled
`available_this_intake` up from its own early reading of eligibility; the runner then settled
`applicant_eligible` from the full checks and never re-rolled availability. So an award this applicant
cannot hold kept saying "unknown" (or "yes"). In the demo, NUS's ASEAN Undergraduate Scholarship and
KU Leuven's Flemish Community Tuition Grant are both closed to a Kazakh citizen, yet both reported
availability "unknown". The runner now re-rolls availability right after the verdict. The adapter's
early roll-up also no longer says "yes" while a faculty or programme restriction is pending (§7:
UNKNOWN is never rounded up). **Golden re-captured with proof:** the old code reproduces the previous
hash exactly, and exactly two leaves changed, both `available_this_intake` "unknown" → "no" on those
two awards. No claim, check, verdict or classification moved. The new adapter test fails on the old
code.

**V2-32: tuition per fee population (`4163cf2`).** `extract_costs` took the first tuition figure, and
European fee pages list the statutory EU/EEA fee beside a far higher non-EU/EEA fee, so an
international applicant could be shown the lower one and a funding gap several times too small. A
tuition table naming at least two populations now yields one claim per row (`subject_key` and scope
population). `web_costs` records tuition as the highest row, with `range_low`/`range_high` holding
the published rows and `is_range` set. `domain/costs` already sums ranges and the funding gap already
reports `gap_low`/`gap_high`, so the range reaches the applicant without new arithmetic. The
population is still never inferred. Two currencies are not ranged (converting to compare is a
judgement the adapter does not make). A single fee, or one row, keeps the old reading. The golden demo
is unchanged.

**Run 13 (35836097167, head `c990519`): the regression is gone, and question 5 has numbers.**
- HKU's false programme claim is gone (0 claims), and wrong_scope is 1/6. Groningen ran out of wall
  clock this time (86 fetches, 0 claims) after yielding 2 claims in run 12: live discovery varies from
  run to run, so one run's per-case zero is not a regression by itself.
- Live claim_recall ceiling printed: 14 of 62, as computed.
- **Support shapes:** 6 predictions carry the certified value (all `programme.exists`). 0 have our
  quote inside the reviewer's (the scorer's rule today), 2 contain the reviewer's words and more (UBC,
  NTU), and 4 quote a different page than the reviewer cited (Delft ×2, Toronto, NTU MCS). So under
  the reverse direction NTU, whose scope already matches by strong alias, is the likely first non-zero
  claim_recall.

**One deadline per fee population (`7c25df2`).** Groningen's certified page is a table: "Type of
student | Deadline | Start course", with a row each for Dutch, EU/EEA and non-EU/EEA students. The
single-match reading quoted the first row as everybody's deadline, which is the wrong date for every
other population wherever the rows differ (EU and non-EU deadlines often do).
- **Extraction:** a deadline table naming at least two populations yields one claim per row
  (`subject_key` and scope population = the row's population). The date comes from the column the
  header calls the deadline, not from position: "Start of studies | Deadline" puts it second. One row,
  or a plain sentence, keeps the old reading.
- **Assessment:** the applicant's population at a university is still never inferred.
  `population_deadlines` returns the rows only when their dates differ. The check shows the earliest
  date and names every row. It is a hard filter only when every row has passed; when only some have,
  it is `NEEDS_OFFICIAL_CLARIFICATION` naming which, so no applicant is eliminated by another
  population's date. The runner's `deadline_passed` follows the same rule.
- Conflicts already group by `subject_key`, so the rows do not conflict with each other. The golden
  demo is unchanged (no demo page has such a table).

**Run 12 (35829646301) and what it changed (`55fc075`; regression fix `1e44137`).**
- **Groningen now yields live claims** (0 → 2) and `critical_field_coverage` moved 0/210 → 1/210: the
  classifier fix `7626ff2` let its programme page through. Its deadline still scores as wrong scope,
  because degree, intake and population are all silent. The value is read from the "Dutch students" row
  of a three-row table (same date in every row), and the page names three populations, so page-level
  scope is silent by design. The fix is one deadline claim per population row; that touches conflicts
  and supersession pairing, so it is planned, not done.
- **A regression I caused, fixed in `1e44137`:** HKU's "Computing and Data Science" school page became
  a *master's* programme of that name, a false `programme.exists`. The context fallback now refuses a
  heading when the body names a full degree title with another subject, and takes its degree from the
  title or path that named it. `_degree_level` now returns the degree named first; before, any "master"
  in the body outranked a "BSc" in the heading.
- **Why a right value never counts (`support_report`, new benchmark step):** supported means our quote
  is contained *in* the reviewer's. Reviewers quote the least that proves a fact ("6.5", "4 May 2026");
  we quote a sentence or a ±150-character window. So a claim can carry the certified value from the
  certified page and still never be supported. The report shows, per right-valued claim, which
  direction holds. The direction is §7 question 5.

**The claim_recall ceiling (`3649853`).** `evaluation/research/expressibility.py`, printed by a new
benchmark step, answers which of the 62 known facts any claim could ever match:
- **Live: 14 of 62.** `live.py` maps with `normalize_claim` alone, and the identity bindings are
  unreviewed drafts, so no award or document fact can score in a live run. This is deliberate
  (HANDOFF V2-01 notes), and I did not change it.
- **Offline, with `identity_bindings.draft1.json`: 28 of 62.**
- The 34 that can never score: 14 have no claim type (programme language under two different label
  keys, `programme.language` and `programme.teaching_language.primary`; German minimums; faculty;
  `country_credential.*` and `english_evidence.*` sub-keys; subjects; admission route; Toronto
  intake), 11 are unbound documents, 7 are bound fields the mapping does not carry (scholarship
  living coverage, duration, bond, offer applicability; transcript completed/not_completed), and 2 are
  unbound HKU awards.

So live claim_recall at 0 is measured against 14 reachable facts, not 62. Extraction and navigation
can move at most those 14 until the owner decides the identity questions in §7.

**Run 11 (35825874826): the page contexts turned into three fixes (`c3ba545`; classifier `7626ff2`).**
- **UBC IELTS.** The live page reads "International English Language Testing System (Academic) 6.5,
  with no part less than 6.0". The spelled-out name now carries the overall band, but only when a
  per-part floor follows, so a bare number after the name stays nothing.
- **A real bug the test exposed:** with no full stop between UBC's IELTS and PTE rows, PTE's "Reading:
  60" was read as IELTS reading **6.0**. A band may no longer run on into another digit, and the IELTS
  sentence now ends where another test's name begins.
- **Mapping.** A single floor is written as the four bands it governs (VERSIONS.md). No published
  metric moves.
- **Groningen (`7626ff2`).** A bare subject heading ("Computing Science") whose title repeats it, with
  a degree word in the title or path, is a programme page, no longer a catalogue by its links.

Still open from the contexts: **Vienna's deadline** is on the page as "Application period 2 March to 4
May 2026". The certified value is null, so the label needs a reviewer before any pattern can score.
**KAIST's** certified programme page is a Korean navigation menu (the context is menu items only);
that page is the owner's open KAIST `program_page` question, not a pattern gap. **HKU's** page is
`unknown` to the classifier although it says "The Bachelor of Engineering in Computer Science covers
…"; that is the next classifier case.

**Run 10 (35822490998, head `2ae0f94`): the oracle's first clean split (`056dd7a`).** 74 certified
facts: recovered 0, classifier_gated 1, value_missing 12, text_missing 0, not_measured 54,
fetch_failed 3 (Toronto 403), timed_out 4 (Aalto, one page). The oracle took 5.5 min, down from a
cancelled 33.

What the 12 value_missing are: **8 are `programme.exists`**. That claim is made by the adapter, not by
the patterns, and the oracle did not run that path, so this was the oracle's own blind spot. It now
mirrors the adapter's check (accepted as a programme page, with a recognised subject). 1 is Groningen
tuition (the cost extractor, still outside the oracle). **3 are real:** UBC IELTS overall and
subscores, and Vienna's deadline. Vienna's is also a labelling question, because the certified value
is null and so can never match; this needs the owner or a reviewer. Groningen's deadline is
classifier_gated: its page is classified `program_catalog`.

text_missing is **0**, so the page content reaches us for every page the oracle could read. The
remaining gap is claim types and scope (54 facts the requirements path cannot express: scholarship
structure, documents, country credentials, programme language), then classification, and only then
patterns. Every value_missing now carries the page text around the reviewer's words, so the next UBC
pattern can be written against what the page actually says instead of a guess.

**Run 9 (35819428739, head `8fcb23e`) and what the oracle could not yet say (`64d55fa`).**
Moved against the certified baseline: programme_page_recall 1/10 → **5/10**, wrong_scope_claim_rate
4/5 → **1/5** (the one left is NTU "Mathematical and Computer Sciences", an equivalence the owner
still holds). claim_recall is still 0/62. Six of ten cases ran out of budget.

The oracle finished its first live pass: 49 value_missing, 1 text_missing, 3 fetch_failed (Toronto
403), 9 timed_out (Aalto, KAIST). **That value_missing count exaggerates the problem:** the oracle ran
only the requirements extractor, and only when the classifier accepted the page for requirements. So
every programme, document, tuition and scholarship fact was counted as a pattern miss, as was every
requirement on a page the classifier refused. It now separates `classifier_gated` (the patterns read
it; the page type refused it) and `not_measured` (no claim type maps to the key) from real
`value_missing`, prints the page type on every line, and waits on a hung URL once rather than once per
fact.

**Funding and government pages now leave a page outcome (`50f9221`).** Only requirements, costs and
discovery used to record them, so a funding stage that read pages and found nothing had nothing to
explain itself with. Scholarship pages now record: fetch-failed, the funding indexes that were read
(with how many award links were followed), award pages (fetched-ok, or no-pattern-match when no
claims came out), and pages that were rejected (not an award, or an index past the index limit). The
government page records fetch-failed / fetched-ok / unreadable, and an empty body no longer produces
an empty post-study-work claim. The runner records both.

**Oracle wall clock (`8f1b146`).** Run 8's oracle step hung for 33 minutes and was cancelled. Each
probe now has a 90 s limit and gets the `timed_out` verdict if it runs over; findings are printed as
they finish; the step has `timeout-minutes: 15`.

**Owner decision 6 of 6: an unchanged statement is refreshed, not superseded (`38104d2`).**
`reextract_page` superseded every live claim on a re-read URL, so a page that merely re-rendered wrote a
whole generation of history repeating what the live rows already said. Change detection (V2-24a) could
already tell a real change from a re-render; it only ever reached a log line.

Now the classification runs **before** anything is written. A statement the page still makes with the
same value keeps its row, its id and its place in history; only `accessed_at` advances, so freshness
still moves. Anything that changed value, appeared or disappeared is superseded and linked exactly as
before — `test_a_forced_page_change_supersedes_old_and_appends_new_in_one_commit`, the T32 contract, is
untouched and still passes because it forces a change. The new test is meaningful in both directions:
before this change it would find two generations; with extraction broken it would find the old row
superseded.

**All six owner decisions are done.** The two §7 items left open are assertions about facts, not design
choices, and stay with the owner: whether "Mathematical and Computer Sciences" is equivalent to
"Computer Science", and which KAIST page belongs in `program_page`.

**Owner decision 5 of 6: the catalogue walker judges subject too (`5d6b75d`).** The divergence was
one argument wide: the walker called `profile_rejects(page, self.degree, [])`, and an empty `fields`
list disables the subject check. Its reasoning was that a catalogue's own list is the university's
statement of what it offers — true, and it says those programmes **exist**, not that each is the one
this applicant asked about. A BSc Mathematics survived for a computer-science applicant.

`test_r5_js_json_payload_yields_programs` — the T29 contract test — was **amended with the decision
rather than worked around**, which is what I refused to do this morning without the owner's word: its
interception contract (payload read, entries fetched, URLs needing no pattern) is unchanged and still
checked, and the Mathematics entry is still fetched and read, then refused **on its subject**. That
distinction is asserted explicitly, because "refused after reading" and "never fetched" are different
behaviours and only one of them honours the contract.

A source-level guard was added: the divergence is one argument wide, and an empty list is an easy thing
to reintroduce without noticing.

**Owner decision 4 of 6: a programme rule stays usable beside a university-wide one (`768e8d7`).**
The one case where this code knowingly disagreed with the phase guide, and the comment in
`conflicts.py` said so. Both claims were stamped `CONFLICTING`, so neither could support an answer.

The code change is one line — `MORE_SPECIFIC_SOURCE` leaves the set that poisons claims — because the
rest was already right: `_first` sorts by source specificity, so "the specific one is preferred for
assessment" is exactly what leaving them live means, and `preferred_claim_id` already named the
programme page. The disagreement is still recorded and still shown; it simply stops silencing both
sides.

**The demo drift is not additive, and was not waved through as if it were.** 20247 leaf values before,
20247 after; **exactly two changed**, both `claims[*].status`, both `CONFLICTING` →
`VERIFIED_CURRENT`. No value, verdict, bucket or check moved.

**And the two are the textbook case.** Delft's programme page publishes IELTS **6.5**; its university
admissions page publishes **6.0**. Both were poisoned — so the product told the applicant *nothing at
all* about Delft's English requirement, for a disagreement the guide says is not one. The 6.5 is now
preferred and usable, the 6.0 kept and shown beside it.

Two tests were rewritten with the decision rather than around it, including
`test_two_official_pages_disagreeing_produce_one_conflict`, which had encoded the opposite deliberately.
A third was added: `_first` must actually return the programme page's value, because "preferred" that
nothing acts on is a label, not a behaviour.

**Owner decision 3 of 6: two qualifications are two scopes, not a clash (`65b494e`).**
`_KIND_BY_DIMENSION` had entries for population, residency, intake, academic year and degree, and none
for `qualification`, so "the Abitur route requires 6.5" beside "the attestat route requires 7.0" fell
through to `TRUE_CONFLICT`. A conflicting claim cannot support an answer, so the applicant was left
with **neither** value — for a disagreement that does not exist.

`ConflictKind.DIFFERENT_QUALIFICATION` is added and the dimension wired. The applicant's question
generates itself from the kind's own name, as the other `DIFFERENT_` kinds already do: "These appear to
be published for different qualifications. Could you confirm which one applies to me?"

**No migration, and I checked rather than assumed:** the kind is carried on the `Conflict` schema, not
stored as a database enum, so adding a value moves no stored contract.

The safety property is unchanged and has its own tests: the same qualification twice still conflicts, a
scope nobody recorded still conflicts, and one side stating a qualification while the other is silent
still conflicts. Unknown is never rounded into "different" — wrongly keeping a conflict costs a
question, wrongly dismissing one costs a decision.

**Owner decision 2 of 6: a per-section English minimum has somewhere to live (`2468f9e`).**
NTU's certified value is a map — `{"overall": 6, "writing": 6, "speaking": 6}` — and the extractor
produced a single floor, so the named sections were dropped. "Writing 6.5, Reading 6.0" is not the
statement "no band below 6", and collapsing them would convert a value silently.

**It needed no new claim type, and no stored contract moved.** `eligibility` has read a per-band map
since it was written (`if isinstance(required, dict)`), and nothing upstream ever produced one — a
consumer waiting years for a producer. So the change is: the extractor builds the map when the page
names its sections, and `_band_check` checks every band in it against the bounds a single value has
always had, rather than stricter ones invented for maps. One bad band condemns the map.

Two things the cases caught:
- **A decimal point is not a full stop.** My sentence anchor was `[^.\n]*`, which stopped at the 7 of
  "overall 7.0" and lost every band stated after it. A period now ends the sentence only when a digit
  does not follow. Same class as the hedging bug in `claim_verifier` — a window is not a sentence.
- **A section word in the next sentence is not a band.** "IELTS overall 6.5. Writing competitions are
  held in June 7" yields the overall band and nothing else; the bands must sit in a sentence that names
  IELTS.

**And my own test was wrong before the code was.** I asserted that `{"writing": 6.0, "speaking": 0.0}`
must fail, but 0.0 is inside the band range a single value has always been allowed — tightening the
bounds for maps alone would have been an invented rule. The test now uses 9.5.

**Owner decision 1 of 6: the scorer compares programme identity, not strings (`d4b12d6`).**
`scope_matches` compared every dimension with `==`, so NTU's "Bachelor of Computing (Hons) in Computer
Science" scored as a wrong-scope claim against a label reading "Computer Science" — the same programme
written two ways. That measured our naming rather than our research, and `programme.exists` is the
single most common key in the certified corpus, 11 facts of 74.

The `programme` dimension now asks `ontology.titles_name_same_programme`, which was built for exactly
this and already returns a three-valued verdict. **Only `YES` counts.** `UNKNOWN` stays a miss —
"Bachelor of Science in Mathematical and Computer Sciences" overlaps with "Computer Science" without
equalling it, and a benchmark that scores "we could not tell" as a hit measures nothing. Every other
dimension still compares literally.

`scope_report` stops saying "reported, not counted": it now states that these count as matches, because
a diagnostic that implies the old answer is worse than none. The test that pinned the old behaviour was
**rewritten with the decision rather than around it** — its name said "reported but not counted", and
that is no longer true.

**The replay guard caught the consequence, which is what it is for.** Eight published metrics files —
every corpus version from draft1 to reviewed — were computed under the old definition, and the replay
test compares scoring the frozen capture against them. Exactly one metric moved, identically in all
eight: **`wrong_scope_claim_rate` 5/5 → 4/5**, the first time that number has ever left 1.0. The files
were regenerated from the same frozen capture and the same datasets, every non-metric field asserted
byte-identical first; the diff is two lines per file. `VERSIONS.md` now carries the reason, and the
replay test's docstring states the discipline: a deliberate change regenerates and records, an
accidental one fails here. A number computed under a changed definition is not comparable to the one it
replaces.

**EXTRA-12: the classifier called the right programme page a catalogue (`96feda6`).** The per-page
diagnostic built this morning named the cause of five of the ten zero-claim cases, and it is none of
the three I had been arguing about. **Groningen's rejected page is the certified corpus' own source
URL** — the pipeline found it, fetched it, and `classify_page` returned `program_catalog`, which
`ACCEPTS["requirements"]` refuses. Delft's and Toronto's programme pages the same; Vienna's admission
procedure page came back `news`; four KAIST admissions pages came back `unknown`.

The cause was one line's ordering: `program_links >= 5` decided **before** the page's own identity was
read, so a page headed "BSc Computing Science" that links to nine sibling programmes — which every real
programme page does — was a catalogue before anyone looked at its heading. Proved both ways on the same
fixture: **before, `program_catalog`, requirements refused; after, `program_detail`, requirements
allowed.**

The fix is not a new idea — it is the rule the **funding branch of the same module already uses**: a
page with links out is an index when it has *"no award identity of its own"*, and one that names its
award is not. A plural or catalogue-shaped heading still settles it first, because that is the page
saying what it is; link counting now only speaks when the page names no programme.

**Also measured, run 35754594232 (`851b8b8`, EXTRA-9):** `toronto` produced **its first claim ever**
(0 → 1) and `ntu` went 12 → **8** — exactly the four phantom "FAQs on scholarships" claims EXTRA-7
removed, confirmed to the unit. The diagnostic now answers for seven cases of ten, against five before.

**A correction I owe the record:** I twice dismissed capability gating as "not the problem", on the
grounds that `no-pattern-match` proved the extractor had run. That reasoning was sound for the pages it
covered and said nothing about the pages the classifier rejected before any extractor saw them — which
turned out to be the larger group.

**EXTRA-11: two extractor gaps found by testing against the certified corpus' own words
(`8532b9f`).** No live run needed: every certified excerpt is text a human confirmed sits on an
official page, so an extractor that cannot read the excerpt cannot read the page.

- **"no `part` less than 6.0"** — UBC's certified wording. `_IELTS_SUB` knew `score|band|component|
  section` and not `part`, so the overall band was kept and the per-section floor **silently dropped**.
  The guide calls that "the single most common error in this work": 7.0 overall with 6.0 writing fails
  a 6.5 per-band rule, and the applicant is told they qualify.
- **"1250 for redesigned SAT"** — NTU's certified wording, read as **nothing**. `_SAT_MIN` required
  "SAT" before the number; `_IELTS_OVERALL` has carried a reversed alternative for years and SAT had
  none.

**My first reversed SAT pattern was too loose and I caught it before shipping.** A bare "number within
30 characters of SAT" read *"Room 1250 is where the SAT is sat"* and *"1250 EUR with their SAT
booking"* as scores. The forward form has always demanded a qualifier; the reverse now demands a
preposition, and four adversarial sentences are pinned as tests.

**What I did not do, because it is a contract gap rather than a pattern gap:** NTU's certified value
for `english_evidence.ielts.minimum` is a **per-section map**, `{"overall": 6, "writing": 6,
"speaking": 6}`, and `ielts_min_subscore` holds a single number. Collapsing three named sections into
one floor would be converting a value silently. §7 has the question.

**A correction to my own earlier framing, from reading all 74 certified excerpts.** I told the owner
the programme-identity decision "concerns one university". That understated it: **`programme.exists` is
11 of the 74 facts, the single most common key in the corpus.** It binds on two today only because
nine cases produce nothing at all; it binds on all eleven the moment extraction works. The corpus is
dominated by identity and document facts, not by numeric thresholds — which also means even perfect
test-score patterns would move `claim_recall` by only a few points.

**EXTRA-10: the oracle — read every certified fact from its own source page (`6bf098c`).**
`evaluation/research/oracle.py` takes the **74 certified labels that carry a source URL and a
human-reviewed excerpt**, fetches those pages **directly with no discovery**, runs the real classifier
and the real extractors, and files one of four verdicts per fact: `recovered`, `value_missing` (the
reviewer's words are in our text and no claim came out — the patterns), `text_missing` (the words never
reached us — representation or dynamic content), `fetch_failed`. Claims are normalised through
`mapping.normalize_claim`, the scorer's own function, so "recovered" means what a benchmark hit means.

**It costs 24 fetches**, because 74 facts sit on 24 distinct pages — against ~600 for a full capture.
Wired into the workflow as its own step, `continue-on-error`, so it can never hide the capture.

Two things found while building it, both worth keeping:
- The corpus itself corroborates the table problem. Groningen's certified deadline excerpt is
  *"non-EU/EEA students 01 May 2027 01 September 2027"* with the reviewer's note **"Table cells joined
  with spaces for review"** — the human had to flatten a table by hand to quote it.
- The excerpt comparison is word-sequence, not substring, for exactly that reason: a reviewer's joining
  whitespace and a page's non-breaking spaces differ character by character while the words do not.
- My first table fixture was accidentally *recoverable* — a two-column table flattens to
  "Overall IELTS (Academic) 6.5", which the existing pattern catches. The test now uses Groningen's real
  six-column shape, where the header is 39 characters from the value and the pattern's 30-character
  window cannot reach. A fixture that passes for the wrong reason proves nothing.

**EXTRA-9: the extractor was handed a page with the requirements deleted from it (`43f7d9a`).**
The first change on this branch aimed at `claim_recall 0/62` itself. An external deep-research review
proposed a hypothesis I had not listed — representation loss before extraction — and it is right.
Verified in code, then demonstrated on a realistically-shaped page:

| fact | where it sat | seen by the extractor, before |
|---|---|---|
| IELTS 6.5 overall | `<form class="application-picker">` | **no** |
| deadline 15 Jan 2027 | `<aside class="key-facts">` | **no** |
| minimum GPA 3.0 | `<div class="requirements-banner">` | **no** |
| "lasts three years" | a plain `<p>` | yes |

`readable_text()` routed through `main_content()`, which deletes `form`, deletes `aside`, and deletes
anything whose class or id matches `nav|menu|…|banner|…`, including inside an already-selected
`<main>`. The GPA died because its container's class contained "banner".

**Root cause: one abstraction, two incompatible jobs.** `main_content` has exactly two callers.
`classify_page` needs site chrome gone or it counts the site's links instead of the page's — that is
why the stripping was written, and it was right for that caller. `readable_text` needs the page's
content. Extraction inherited a function built to throw content away. `content_for_reading` now serves
reading: it keeps forms and asides, keeps a container whose class merely mentions a chrome word, drops
only what is never content, and drops nav/header/footer only when bulky (the 800-character rule
`html_to_text` already used). `main_content` is untouched, so classification cannot move.

**The demo golden did not change at all, and that is the finding behind the finding.** The synthetic
corpus is plain prose in plain `<p>` tags, so it cannot exhibit this failure — a regression suite built
entirely on it was structurally incapable of catching the thing that was costing every real claim.

**Plan V2-30: the ninth scope question, `qualification` (`254cf21`).** §1 lists nine scope questions a
requirement must answer; `ClaimScope` had eight. `qualification` was missing — and the benchmark's own
`Scope` already had it, so the measurement asked a question the model could not answer. Built by a
subagent in a worktree and integrated here; the reasoning below is its finding, verified by me before
integration.

It is non-compensatory by construction: every `ClaimScope` method iterates `SCOPE_DIMENSIONS`, so
adding the dimension to that tuple was the whole of the comparison change — no new comparison logic
exists. The vocabulary is `page_classifier.QUALIFICATION_NAMES`, made public and used by both, so a
second drifting list cannot appear; a test holds them together.

**The finding worth keeping: a qualification named as a *yardstick* is not the page's scope.**
Groningen's demo page says "a secondary school diploma **equivalent to** the Dutch VWO". The first
version of the reader recorded eleven demo claims as scoped to VWO — turning a rule addressed to
everyone whose diploma *compares* to the VWO into a rule for VWO holders. That is the pipeline
inventing an equivalence, the one thing this repository forbids outright. A comparison guard, shaped
like the existing negation guard, now refuses it. Verified by hand across seven sentences: "equivalent
to"/"comparable to" → nothing; "holding the Dutch VWO diploma" → VWO; "the Kazakh attestat" →
attestat; two names in one page → nothing, by the existing `_single()` rule.

`baccalaur` is deliberately unmapped on its own: "International Baccalaureate" and the French
"Baccalauréat" are different qualifications spelled almost alike, so IB is read only from its full
name.

**Golden hash, fourth re-capture, proved on this tree rather than the one the change was written
against** — the subagent's worktree was cut from `07de4d9`, eleven commits behind, so its proof and its
hash could not be reused. Mine: pre-change dump hashed to the constant it replaces (baseline
confirmed), **415 keys added, 0 removed**, all `"qualification": null`, all at the single path
`[*].claims[*].scope`, and stripping the key reproduces the old dump object-for-object. No value is
non-null. A new test pins the *reason* beside the hash: no page in the demo corpus states a
qualification of its own.

**Owner decision, parked (§7):** two pages scoped to different qualifications still classify as
`TRUE_CONFLICT`, because `ConflictKind` has no `DIFFERENT_QUALIFICATION` member and adding one touches
a stored contract. **Deliberately not done:** `requested_scope()` still asks only for an intake —
filling a qualification from the applicant profile would turn today's YES verdicts into UNKNOWN across
the demo, and that is a product decision, not a refactor.

**Run 35721950650 (`575a431`) says EXTRA-6 was a regression, and EXTRA-5 is blind where it matters
(`cb43c2a` + `c61bbaa`).** Both findings are about code I shipped this morning, and both were found by reading the
run rather than the metrics.

**EXTRA-6 is now off by default.** I shipped it saying it "can only shorten the programme list, so
recall may fall — that is the honest direction". The measurement disagrees: `programme_page_recall`
**4/10 → 1/10** and `programme_page_precision` **0.190 → 0.091**. Precision falling is the part that
settles it — the pass cut correct pages and kept junk (`account.you.ubc.ca`, an events page, a Master's
curriculum PDF for a bachelor's query). The predicate is wrong for search-sourced pages in a way I
cannot yet name, so the pass and its tests stay and `CONFIRM_SEARCH_PROGRAMMES = False` turns it off
until a capture says what it does. Verified the numbers myself from the artifact before acting.

**EXTRA-5 lost its records in exactly the cases it exists for.** `_record_page_outcomes` ran once,
after the candidate loop, over a plain local list — so any exception inside the loop discarded every
diagnosis. Five of ten cases recorded nothing, including `warsaw` (83 requests) and `hku` (42). Records
are now filed as each adapter returns them, so a case killed by a budget or a wall clock keeps what it
learned. This is the same class of mistake as "a measurement that cannot fail loudly": the diagnostic
was silent precisely when consulted.

**What the diagnostic did buy, and it is worth the trip:** `toronto`'s zero is not an extraction
failure at all. Every one of its six records is `fetch-failed`, HTTP 403, and its raw file shows
`pages_checked: 24, pages_failed: 22` — `robots.txt` included. The whole origin refuses us. That case
had looked like "read 23 pages, claimed nothing" for two runs. Elsewhere the dominant categories are
`no-pattern-match` and `classifier-rejected`, with quotable reasons ("classified as navigation; no
requirement can be read from this kind of page").

**Open, not acted on** (needs the next run, or an owner call — recorded so it is not re-discovered):
the scholarship and government adapters contribute no page outcomes at all, so the funding stage is
invisible; the per-case JSON writes `CAPTURE_IN_PROGRESS` for wall-clocked cases while `capture.json`
records the truth; NTU's Tuition Grant claim asserts the grant applies to an international applicant
while its own excerpt is about Singapore citizens, and lands under an `unmapped.*` key where the
scorer cannot see it; and four cases show `pages_checked: 59` against a budget of 60 **before**
verification starts, which would mean discovery, not extraction, is eating the run.

**Plan V2-33: a faculty or programme restriction is recorded, and asked about (`3bb6a06`).** §6
decomposes `faculty_restrictions` and `programme_restrictions` separately. `program_restrictions`
existed as a **declared field nothing ever set** — the fourth of that kind on this branch — and there
was no faculty field at all, so "open to students in the Faculty of Engineering" was recorded as
applying to everyone. (`SCHOLARSHIP_PROGRAM_RESTRICTION` is not that field's filler: it carries
*degree* applicability, as NTU's `{"degree": "bachelor"}` shows.)

Both are now read from the page's own sentence, deliberately narrowly — a restriction we invent
excludes a real applicant from real money, and one we miss becomes a question they are told to ask; the
two failures are not symmetrical. The eligibility check is **PENDING, never a pass and never a
refusal**: the applicant's faculty is not in the profile at all, and deciding a programme restriction
by comparing names is exactly the trap NTU taught this session. It propagates `applicant_eligible` to
`unknown`.

**The golden demo hash moved for the third time, and the proof is recorded beside it:** 0 removed
lines, 34 added, every addition the same new empty key on the demo's seventeen scholarships. No value
moved, and the new readers produced **nothing** on this corpus — correct, because no demo award page
states such a restriction, and a reader that invented one would be the bug.

**Self-review of the day's ten commits, and three defects in my own work (`cf95a59`).** Ten steps
shipped against a live pipeline in one session is exactly when a reviewer is needed and there isn't one,
so I read the whole diff back adversarially. Three findings, all mine, all from today:

1. **The page memo held every university's HTML for the whole run.** EXTRA-8's memo is keyed by URL and
   lived for the adapter's lifetime, which is the run — so a twenty-candidate run would hold up to
   ~300 pages of raw HTML to save re-reading at most fifteen. It is now bound to the university being
   worked on and dropped when that changes. The cost is stated in a test rather than hidden: rows are
   not guaranteed to be grouped by university, so coming back to one reads it again.
2. **A docstring that described the code I decided not to write.** `_confirm_added_programs` still said
   it judged "the catalogue walk and the search provider", after I narrowed it to search alone. A
   comment that describes the rejected design is worse than none.
3. **The unchecked tail past `MAX_PROGRAM_CANDIDATES_CHECKED`.** Newcomers beyond the cap stay in the
   list unconfirmed — the hole EXTRA-6 exists to close, left half open. `MAX_PAGES_PER_CATEGORY` keeps
   `selected` far below the cap in practice, so this is documented at the line that decides which way
   the doubt falls rather than changed: losing a lead unread is the worse failure.

**EXTRA-8: a funding page is read once per run, not once per programme (`82530e1`).** Reading the six
case logs I had not opened showed that all four budget-killed cases — `delft`, `groningen`, `hku`,
`ubc` — died in the **same line**: the page budget ran out inside `WebScholarshipAdapter.find`, called
from the funding stage. Four copies of one traceback.

`_stage_funding` calls `find(cand, prog)` once per **programme**, so a university with two programmes
read its scholarship index and every award page twice; NTU's twelve claims are six, then the same six
again, same URLs, differing only in `program`. Funding could spend up to 2 × (3 indexes + 12 awards)
of a 60-read budget before assessment began — and §8's index walk had just raised that ceiling. The
adapter now memoises **pages** for its own lifetime. Claims stay per programme, because a claim carries
the programme it was built for and reusing one would mislabel it; a page that failed is not remembered
as an answer, so a flaky page is tried again. `pages_checked` counts real reads now, so the number the
applicant sees stops double-counting.

Honest limit: `Fetcher` already caches the bytes, so in production this saves a cache lookup and a
re-parse, not network traffic. What it buys is the benchmark budget — the thing that killed four of ten
cases — and an honest count.

**EXTRA-7: an FAQ page is not a scholarship, however it spells "FAQ" (`769ba57`).** Reading NTU's
twelve claims — the only real claims in run 35697105238 — four were an award named **"FAQs on
scholarships"**, stamped `CONFLICTING` because the same page's prose ("the scholarship will be withdrawn
if you change your degree programme") then produced a second claim saying that award did not exist. Two
per programme, so **a third of every claim the ten-university run produced came from one FAQ page**.

The cause is the plural: `_FAQ` was `\bf\.?a\.?q\.?\b`, which matches "FAQ" and not "FAQs" — there
is no word boundary between the `q` and the `s`. Reproduced offline before changing anything;
`classify_page` returned `scholarship_award 0.85, named award 'FAQs on scholarships'`. It now returns
`scholarship_faq` with no subject.

**This is the third plural bug here** — `waivers` and `scholarships` were the others — so the tests
cover the pattern (FAQ, FAQs, F.A.Q., "frequently asked question(s)"), that a real award still reads as
one, and that a word merely starting with those letters ("Faqir Memorial Scholarship") does not.

**EXTRA-5 is proved end to end, and the budget label is honest (`49856d6`).** Two small things, both
about not shipping a diagnostic that lies.

First: EXTRA-5 reads per-page outcomes by parsing them back out of the run's own diagnostics, and
nothing checked that the **production runner** still writes that exact line. If it ever stops, the
capture records `[]` and says nothing — silently, which is the failure this diagnostic exists to end.
`test_a_real_run_writes_lines_the_capture_parser_understands` drives a real demo run through
`ResearchRunner` and asserts the parser finds records, all in the frozen five-category vocabulary.

Second: the workflow said "60 fetches" and the budget does not bound fetches. It bounds `Fetcher.get`
calls, and one read can issue several requests — `groningen` made 98 under a budget of 60. The label
now says "page reads", the column is headed `http`, and the log states the difference, because a
reader comparing two runs needs to know which of the two numbers moved.

**EXTRA-6: the programme filter now sees what search adds (`e955e7c`).** Chasing Toronto's zero led to
`live_discovery.discover`'s ordering: step 4 confirms programme candidates by reading them — the filter
that exists because live runs offered "bachelor-open-day", "campus-tour" and a student newsletter as
programme pages — and step 6 asks the search provider. So **everything Phase 1 contributes arrived
unconfirmed**, and Phase 1 is what moved `programme_page_recall` 1/10 → 4/10. A step 7 now applies the
same predicate to the pages search added, reading only the newcomers, so no confirmed page is paid for
twice — the fetch budget is the binding constraint on seven of ten cases.

**Two things this cost, both worth more than the fix.** First, the pass initially judged the catalogue
walker's output too, and `test_r5_js_json_payload_yields_programs` went red: the walker deliberately
trusts a university's own catalogue listing and keeps a BSc **Mathematics** for a computer-science
applicant. I narrowed the pass rather than rewrite another campaign's contract, and parked the question
in §7. Second, four of my five new tests passed for the wrong reason: the stub `FetchResult` set
`content` and not `text`, so every page it served read as empty and every page was "correctly" refused.
`FetchResult` carries both; a stub that fills one is a stub that proves nothing.

**EXTRA-5: the capture now says why a case produced nothing (`5826b0c`).** `Observation.page_outcomes`
keeps the runner's own five per-page verdicts, filled in the same `finally` that reads the claim rows so
a budget-killed case still records what it read; the workflow prints the counts per case. The field is
defaulted and the first test is that the certified capture still validates unchanged.

**Read the run's own per-case files, and the headline changes again (artifact 10680503688, downloaded
and analysed 2026-09-22).** `claim_recall 0/62` is not "extraction is weak". It is this:

| case | fetches | programme_urls | ranked_urls | claims | ended |
|---|---|---|---|---|---|
| ntu | 28 | 3 | **40** | **12** | complete |
| toronto | 23 | 3 | **0** | **0** | complete |
| kaist | 46 | 3 | 1 | **0** | complete |
| delft | 53 | 3 | 3 | 0 | page budget |
| groningen | 98 | 3 | 4 | 0 | page budget |
| hku | 52 | 3 | 1 | 0 | page budget |
| ubc | 57 | 3 | 0 | 0 | page budget |
| aalto | 2 | 0 | 0 | 0 | wall clock |
| vienna | 94 | 0 | 1 | 0 | wall clock |
| warsaw | 80 | 0 | 0 | 0 | wall clock |

**Every claim in the entire run came from one university.** Nine of ten produced zero — including
`toronto` and `kaist`, which finished with no error, found three programme URLs each, and still filed
nothing. So every Phase 2 and Phase 3 metric in that table is a measurement of NTU, and the two scope
mismatches are literally NTU's two claims. That also means my own "wrong_scope_claim_rate is now one
owner decision" is true and much smaller than it sounded: it is one decision about **one university**.

Two further facts from the same files, both worth keeping:
- **The fetch budget does not bound fetches.** `groningen` made 98 HTTP requests under a budget of 60,
  and `vienna` 94: the counter wraps `Fetcher.get`, and one `get` can issue several requests (redirects,
  the browser tier, PDFs). The budget bounds *reads*, not *traffic*, and the workflow's label
  ("60 fetches") says otherwise.
- **`ranked_urls` and claims move together.** The only case with a full ranked list is the only case
  with claims. `toronto` has three programme URLs and an empty ranked list — so the thing that feeds
  extraction is not what `programme_urls` reports, and a case can look successful in the summary while
  the pipeline read nothing.

**The full metrics table from run 35697105238, copied here because the CI log expires in 14 days —
and it moves the headline.** I reported the scope numbers first because that is what the run was for.
The rest of the table says something larger, and it is not good news:

| metric | run 35697105238 |
|---|---|
| `programme_page_recall` | **4/10** (certified 1/10, yesterday 3/10) |
| `programme_page_precision` | 4/21 |
| `claim_adjudication_rate` | 2/12 |
| `claim_precision` | **0/2** |
| `claim_recall` | **0/62** |
| `critical_field_coverage` | **0/210** |
| `scholarship_discovery_recall` | **0/3** |
| `scholarship_applicability_recall` | 0/7 |
| `primary_source_rate` | 12/12 |
| `recall_at_5/10/20` | 1/9 |

**Retrieval is improving and extraction is not following it.** The run found the right programme page
in 4 cases of 10 — four times the certified baseline — and produced **twelve claims in total across ten
universities**, matching none of the 62 labels and filling none of the 210 critical fields. Phase 1
moved the page; nothing after it is reading the page.

**And the budget is now the binding constraint: 7 of 10 cases ran out**, against 5 of 10 yesterday —
`groningen`, `delft`, `ubc`, `hku` on pages, `aalto`, `vienna`, `warsaw` on wall clock. Only `toronto`,
`ntu` and `kaist` finished. Every number above is therefore a **floor**, measured on a cohort that
mostly stopped early, and the three completed cases are the only ones where the pipeline was allowed to
finish.

This also puts a price on the step I shipped an hour ago: **§8's index walk spends fetches**, and the
fallback spends one more. It cost nothing on the demo, but on a cohort where seven cases already
exhaust the budget, the next capture must be read with that in mind — if `scholarship_discovery_recall`
does not move, the walk is not paying for its fetches and belongs behind the budget check, not in front
of it.

**Phase 3 §9: the plan no longer tells the applicant to do the impossible (`6fbb7bf`).**
`_order_steps` sorted by lead time and never read `depends_on`, so the numbered plan could put
"notarize the translation" above "get the translation". It is a topological order now, with longest
lead time as the tiebreak, so the demo's order is byte-identical (nothing in it depends on anything).
A cycle keeps every step and is appended last rather than silently resolved.

**And a finding in my own previous step:** §9's flagship dependency, `admission offer letter`, names a
**milestone, not a list item** — no document on the checklist carries that name. My first cut resolved
dependencies against the list and dropped the rest, which would have made the one dependency the
product actually produces disappear from the applicant's view entirely. Now the split is explicit: an
unresolvable dependency cannot order anything (it would stall the plan behind a step that does not
exist) and is still printed beside its step, because an applicant who is not told to wait will not wait.

**Phase 3 §9: a required document records what its page covered (`8c6337f`).** §9 ends with "store
source and scope for each required document"; `DocumentItem` stored the source and dropped the scope,
although the adapter had already read one for the claims from the same page. `DocumentItem.scope` now
carries it, omitted from the payload when nobody recorded one exactly as `Claim.scope` is, so no stored
checklist changes shape. One reading, two consumers: the demo's Toronto documents now say they are
about Fall 2027 / 2026-27, and they still name no programme or university, because the reader refuses
to write those dimensions. Recording only — refusing a document whose page is about another programme,
and showing the scope, come after, in that order, as they did for requirements.

**MEASURED 2026-09-22, live, run 35697105238** (branch at `6c55f14`, Exa, 60 fetches / 90 s — the same
budgets as run 35655438326, so the two are comparable). **The prediction held.** Scope mismatches fell
**5 → 2**, and the three "read the wrong page" cases (an open day, a "preparing for a bachelor" page, a
visual-studies degree) are gone: EXTRA-3 stopped claiming an event heading as a programme. What is left
is exactly the one problem EXTRA-1 named and nothing since has addressed — **NTU's naming**, both
remaining mismatches, both `programme (differs)`:

| | certified | run 35655438326 | run 35697105238 |
|---|---|---|---|
| scope mismatches | 5 | 5 | **2** |
| of those, `programme (differs)` | 5 | 5 | 2 |
| `wrong_scope_claim_rate` | 5/5 | 3/3 | **2/2 — still 1.0** |

**The rate is still 1.0 and that is not a contradiction.** It is a *rate*: the denominator fell with the
numerator, because a claim that is no longer made is no longer scored. The count is what moved, and the
count is what the diagnostic was built to show. One of the two survivors is the ontology's own strong
alias ('Bachelor of Computing (Hons) in Computer Science' vs 'Computer Science') — reported, not
counted, because whether the scorer compares programme identity or strings is the owner decision parked
in §7. Answer that one and this metric is 1/2 by definition rather than by pipeline work.

**The run's last step failed, and it was my bug (`67db24d`).** `scope_report --json` serialised with
`m.__dict__`, and `Mismatch` is a slotted dataclass, so the step died *after* printing the report —
taking "Show what moved" and the per-case outcomes with it. `asdict()` now, and a test drives the CLI
rather than the function, because the CLI is the part nothing exercised. Third time a result has been
lost between producing it and reporting it (§9): the report was correct and the run still went red.

**Phase 3 §8: a funding index is read as discovery, not thrown away (`67db24d`).** The adapter read one
index page and dropped everything behind it: a link the classifier called `scholarship_index` — an
international funding page, a faculty funding page — was fetched, rejected and discarded, and the awards
it named were never seen. The page was already paid for. `find` now walks a small queue of indexes
(depth 1, at most three index pages, the same cap of twelve award pages, one dedupe set), harvests the
awards behind an index instead of discarding it, and falls back to the programme page **as an index
only** when the scholarship page is unknown or names no award. An index still never becomes a
scholarship: only a page the classifier calls `scholarship_award` is parsed. Demo golden byte-identical
— the synthetic corpus has no index behind its index, which is exactly why this was invisible until the
spec was read again. Also fixed the mypy error `486a6ff` left on the branch
(`tests/test_document_dependencies.py` passed a `str` where `DegreeLevel` was expected); mypy is back to
0 errors.

**KAIST is seeded (owner data, 2026-09-22).** Диас verified and supplied the pages; the registry entry now carries `program_catalog` = `cs.kaist.ac.kr/content?menu=188`, `program_page` = `menu=318` (Undergrad Req.), `scholarships` = `menu=42`, and `admissions` = the intl-undergraduate ApplicationTimeline, with `seeds_verified_on: 2026-09-22`. **`cs.kaist.ac.kr` is now a recognised KAIST host** — the fix the last search probe said was missing, and the reason KAIST's programme page was unreachable. One supplied page, the Undergraduate Curriculum Roadmap (`menu=320`), has **no seed category to live in** (the registry has six and they are full); it is not lost, the walker reaches it from the same host, and swapping it for `menu=318` is a one-line owner decision. The retrieval effect is unmeasured until a live probe runs (§7). Phase 3 §10: `claim_verifier.states_a_requirement_without_settling_it` + a rule in `ClaimBuilder`. The guide lists conditional wording as grounds for escalation and **nothing checked it**: a page saying applicants are *typically* expected to have IELTS 6.5 produced a `VERIFIED_CURRENT` claim, and a verified claim the applicant misses is a hard filter — a university eliminated on a hedge. Such a claim keeps its value and excerpt, drops to `NEEDS_OFFICIAL_CLARIFICATION` and records **which word** unsettled it. **The rule is scoped to the claim's own sentence, and that cost a false positive to learn:** the first version read the whole excerpt, and the demo's deadline claim came back "conditional" because a credential-evaluation sentence sat beside it in the same 160-character window. An excerpt is a window, not a sentence. A value that cannot be located keeps today's status — missing a hedge leaves the product where it is, inventing one downgrades a requirement never in doubt — with one safe exception: an excerpt that *is* a single sentence, which covers boolean claims like "an interview may be required". Demo byte-identical. 10 tests. Phase 3 §9: `DocumentItem.depends_on` is filled for the first time — a third declared-and-never-set field. The guide's own example is the one that can now be recorded honestly: a scholarship submission waits for the **admission offer letter** when the award page says an offer is required, which only became readable in this session. Recorded as a phrase, not an item id, because the offer letter is issued by the university after a decision and is not one of the checklist's own items. Empty when the award never mentioned an offer: a guess about someone's paperwork order is worse than a gap. 3 tests, on the NUS fixture — the Toronto award page I reached for first yields no documents at all, which the test caught before it could pass for the wrong reason. Demo byte-identical. Phase 3 §7: `funding.roll_up_availability` — the guide's rule, deterministic and in the domain. The version inside the scholarship adapter **ignored `opportunity_exists` and `award_current_for_intake` entirely**, and both fields were declared and never set anywhere: an award whose page calls it discontinued could roll up to *available for this intake*. Withdrawal language is now read (`discontinued`, `no longer offered`, `suspended`, `not being awarded`) and sets both, plus a `scholarship_exists: false` claim quoting the line. The asymmetry the guide asks for is kept: `award_current_for_intake` need only be **not no** for a yes, because most pages never state a cycle. **A rule I wrote and then removed on evidence:** a positive "is/are offered" pattern read Delft's *"30 awards are offered each year"* as a statement about this cycle. A count sentence is not that, the roll-up needs nothing from it, so there is no positive branch — pinned by a test asserting the pattern's absence. Demo byte-identical after the removal. 12 tests. Phase 3 §4: `awards_needing_a_test_the_programme_made_optional` + an `UnresolvedQuestion` from the funding stage. The guide names the trap and the product walked into it: an applicant reads *test-optional* on the admissions page, skips the SAT, and loses the **award** rather than the offer — the two pages are published by different offices and neither mentions the other. The question names the award, suggests the scholarships office and is **not** blocking: it is a timing warning, not a barrier. Silence about a policy is not a test-optional policy, so a programme publishing no policy names nothing. Demo byte-identical. 4 tests. Phase 3 §3: `ClaimType.ENGLISH_TEST_WAIVER`, an extractor, and an eligibility rule. The pipeline read only **fee** waivers; the sentence that says an applicant needs no English test at all was dropped entirely, and for a Kazakhstani applicant from an English-medium school it is the decisive line on the page. Recorded as **the page's own sentence**, not a boolean: "a waiver exists" is useless to someone who cannot tell whether it covers them. A published waiver makes the English minimum non-eliminating — consistent with the module's own rule that absent data never eliminates, and whether a waiver covers this applicant is exactly absent data — while the check itself stays visible as NEEDS_OFFICIAL_CLARIFICATION with the conditions quoted. Two of my own patterns were wrong on first probe and fixed before shipping: `waivers` (plural) was unmatched, and the fee-waiver negation read "you do not need to submit IELTS if…" — a waiver in plain words — as a refusal of one. Demo: **byte-identical**, the corpus has only fee waivers. 4 tests. Phase 3 §6: `Scholarship.offer_required` and `financial_need_required`, with claim types and extractors. Found by reading the guide's list against the schema: everything else it names was already decomposed, these two were not, and `faculty_restrictions` still is not (no honest extractor — recorded here rather than faked). Both default to `unknown` and are refused unless the page says so outright: an applicant who assumes an offer is needed applies too late, one who assumes it is not may never apply. **"Merit-based" alone is not a denial of need-based** — many awards are both — so only an explicit "regardless of financial need" reads as no. Demo: additive, 0 removed, and **one real claim appears** — NUS's Financial Aid page says the award depends on demonstrated financial need, a fact the product used to drop. 4 tests. Plan V2-30, **visible half**: the shortlist's requirement list now renders `published_scope` as a quiet line under the explanation — shown when the page said, absent when it did not, because silence about who a rule covers must never read as "everyone". `RequirementCheck` gains the field in `src/types.ts`; two component tests cover both directions. Frontend gates: typecheck, lint, **190 tests**, build — all green. This is the first frontend change of the session. Plan V2-30 (Phase 3, first half): `RequirementCheck.published_scope` — the page's own terms beside the number ("published for intake Fall 2027, population international"). Phase 3's question is *does this exact rule apply to this exact applicant*, and a number alone cannot answer it. Empty for a page that stated nothing **and** for a claim predating scope: both mean "this line can tell you nothing", and the difference between them belongs in the evidence rather than in an invented phrase. Demo: **additive**, 121 added lines, 0 removed — 74 checks scoped to `Fall 2027`, 6 of them also to international applicants, the rest honestly empty. 4 tests. Plan V2-23 completion: `ConflictKind.MORE_SPECIFIC_SOURCE`. The guide's own example — a university-wide IELTS 6.5 beside a programme's 7.0 — is two true rules at different levels, and my first pass classified it `TRUE_CONFLICT`. Now an adjacent specificity pair (`program_intake`/`program` against `university_admissions`, or the two programme levels) explains the difference, **after** the stated-scope check, so two populations still win over two levels. Two pages of the *same* specificity disagreeing stays a true contradiction. The drafted question is worded per kind: with a contradiction the applicant asks which value is right, here they ask which one governs their application. **Behaviour deliberately unchanged** — the claims keep today's `CONFLICTING` stamping, because the guide would have the specific rule stay usable while `test_two_official_pages_disagreeing_produce_one_conflict` says otherwise, and that is the owner's call (§7). Demo golden re-captured, **not additively**: three fields on one conflict — kind, question, resolution rule — and nothing else. 4 tests. Plan V2-20 exit criterion: `app/domain/evidence_queries.py` — `supporting`, `scoped_to`, `stale`, `conflicting`, `unknown_for`, `superseded_history`, `live`. One function per question the phase guide lists. **Every one returns claims, never a verdict** — the product's promise is that a user can see the evidence, and a function answering "yes, IELTS 6.5" instead of "these two pages say so" is where a system starts asserting. `unknown_for` is the exception and returns the missing *types*: there is nothing to show for a fact nobody established, and an empty list would hide the gap inside a successful-looking answer. `scoped_to` admits only `YES`, so it cannot undo V2-23 one layer down. No SQL, no migration, and the docstring says why: indexed scope columns are premature while nothing queries by scope in production and while V2-20's own SourceSnapshot/ClaimVersion model is half-built. Found while writing it: `claims.superseded_at` lives on the **row**, not the claim document, so a history sorted from claims alone is ordered by read time — written down rather than papered over. 12 tests, module at 100%. V2-30: `prefilter(..., reject_irrelevant_kinds=False)` — the prefilter can now drop URLs `classify_url` already calls IRRELEVANT (publications, person and organisation profiles, datasets, theses). Found by checking rather than assuming: `is_excluded_path` returns **False** for every one of them, so a publication page reached the ranking on equal terms with a programme page — which is what the probe kept seeing (Aalto's top result a publication, KAIST's an organisation profile). **Off by default**, and a test asserts the default: §12 allows a discovery change only when the benchmark improves, this one cannot be measured without a live capture, and an unmeasured rejection is the silent recall loss that rule exists to prevent. 3 tests. V2-29: `page_classifier._program_name` refuses a heading that announces an **event or an instruction**, even when it contains a degree word. Straight from V2-27's diagnostic: Groningen's `Bachelor's Open Day` and Delft's `Preparing for a bachelor` were read, classified as programme pages, and became `programme.exists` claims that the benchmark scored as wrong-scope claims about Computing Science and Computer Science and Engineering. A degree word says a page is *about* degrees, not that it *is* one. The rule is written from those two real titles plus the usual event words, and a test pins that ordinary programme names — including `Bachelor of Arts, Visual Studies`, the third wrong page, which is a real programme and a retrieval failure rather than a classification one — still pass. Demo golden unchanged; the corpus contains no such page. V2-24a: `app/domain/change_detection.py` — `ChangeKind` (unchanged / value_changed / added / removed), `Reading`, `classify_changes`, `is_material`, `summarise`; logged on every re-extract. Claims pair on `(claim_type, subject_key)` — what makes two claims the same statement — and compare on normalised values, so a reworded sentence, a re-read timestamp, `1400.0` against `1400` and a list in another order are all **not** changes. The comparison input is a `Protocol`, not `Claim`: my first version rebuilt a `Claim` from a persisted payload, validation failed on a row written by an older schema, and inside the re-extract's single transaction **that took the supersession down with it** — three contract tests went red and caught it. Describing history must never be able to break it; there is now a test in those words. **No behaviour change**: supersession is still per URL, per the T32 contract (§7 carries the proposal to change it). 13 tests, module at 100%. V2-28: `ontology.fields_named_in(title)` and `titles_name_same_programme(a, b) -> Verdict`. A title names a field *inside a sentence about a degree*, so the alias match runs over the whole phrase while staying exact — nothing is inferred from a title merely resembling a field name, and related terms stay out (or `data science` would name computer science). On the five real mismatches: NTU's `Bachelor of Computing (Hons) in Computer Science` vs the label `Computer Science` is **YES**, one programme under two names; `Bachelor of Science in Mathematical and Computer Sciences` is **UNKNOWN**, because the vocabulary has no plural entry and inventing one would merge a joint degree into a single-subject one; the three wrong-page titles are UNKNOWN; `BSc Data Science` against Computer Science is **NO**. `scope_report` now prints these **beside** the rate and never inside it. 6 + 2 tests. V2-27: `evaluation/research/scope_report.py` — every scope mismatch named by dimension and by shape (`silent` / `differs` / `unrecorded`), walking the same predictions the scorer walks so it cannot describe a different population than the rate does. Wired into the capture workflow. **It refuted my own hypothesis on first run**, which is the whole point of building it: I expected `silent` on `intake` (the page not saying), and the frozen capture answers **5/5 `differs` on `programme`** — three cases read the wrong page entirely (`Bachelor's Open Day`, `Preparing for a bachelor`, `Bachelor of Arts, Visual Studies`) and two are NTU's **right** programme under its full official title (`Bachelor of Computing (Hons) in Computer Science` against the label `Computer Science`). So `wrong_scope_claim_rate` is mostly a **retrieval** failure and partly a **programme-name resolution** failure — plan V2-22 applied to programmes — and not a scope-reading failure at all. 6 tests. V2-22b: `app/adapters/discovery/registry_identities.py` — the registry the owner maintains, read a second way: as `InstitutionIdentity` rows keyed by **registrable domain** rather than by name, since a name changes with the language it is written in. Four tests are as much **data tests** as code tests and will fail on a bad registry entry: every institution resolves from its own homepage and every seed; no two institutions share a domain; every institution resolves from its own name; and KAIST resolves through `cs.kaist.ac.kr`, which is only true because of the owner's 2026-09-22 seeds. An entry with no URL at all identifies nothing and is skipped rather than given a key invented from its name — that would hide the data error. Still nothing rewired: `university_key` keeps every caller. 20 tests, both modules at **100%**. V2-22a: `app/domain/entity_resolution.py` — `InstitutionIdentity`, `Resolution`, `resolve_institution`, `same_institution`, `Basis`. A ladder of evidence, strongest first: a registrable domain the registry records, then an **exactly recorded** alias, then nothing. Never a similarity score. Every answer carries its basis and the exact evidence, because the guide requires resolution to be **auditable**. Two unresolved things are never the same institution — "both unknown" is not a match. `dedupe.university_key` is untouched and nothing is rewired yet (V2-22b), so the demo cannot move. 13 tests, module at **100%**. **Alias data is an owner task**, like a verified seed: the registry holds no aliases, and this module reads them rather than inventing them — a test pins that (`test_nothing_here_invents_an_alias`). V2-20b: `claims.superseded_at` and `claims.superseded_by_id` (migration `c5d01b7e4f83`). Supersession already kept the old row; what history could not answer was **when** a value stopped being current and **which** value took over. `reextract_page` now writes both, in the same transaction as the status flip — the time is recorded, never inferred later from `updated_at`, which moves for unrelated reasons. The successor is matched on `(claim_type, subject_key)`. **A superseded row with no successor is a finding, not a gap**: it means the page no longer states this at all — the one case the re-extract path exists to preserve — and it is pinned by its own test with a page whose requirements are "being revised". `ON DELETE SET NULL` on the successor link, so a purge can never take a history row with it, verified on PostgreSQL. Deliberately **not** built: a separate `ClaimVersion` table — a claim row already is its version, with `accessed_at` as its start and `superseded_at` as its end, and splitting that would migrate all existing evidence for a query nobody makes yet. V2-20a: `SourceSnapshot` — one row per (page, content hash) with the validators seen alongside it and `first_seen_at` / `last_seen_at`, written by `SourcePage.record` in the same flush so no caller can update a page and forget the version it saw. Metadata only, never a body. A page that reverts to earlier content is **the same content seen again**, not a third version — documented decision, pinned by a test; the intermediate version keeps its own row, so the order of events survives. Migration `a1f3c8d75e29` on `d9c4e7a21b83`: one head before, one head after, exact-inverse downgrade, round-trip and CASCADE verified on **PostgreSQL**. Demo golden unchanged, as predicted — the demo's discovery adapter has no page recorder at all. 9 tests in `tests/test_source_snapshots.py`. V2-26: **a Phase 2 exit criterion is met** — "conflict reasons distinguish true conflict from different scope". `ConflictKind` (true conflict + one per scope dimension: population, residency, intake, academic year, degree) on `Conflict.kind`; `classify_conflict` compares the claims' recorded scopes. Two pages that both state a dimension and state it differently are **not contradicting** — a home fee and an overseas fee are two correct numbers — so such a conflict stays visible with its kind and its claims are **not** stamped `CONFLICTING`, which would have stopped either from ever being used. **Unknown is never rounded into "different"**: a scope nobody recorded stays a true conflict, because a wrongly-dismissed conflict costs the applicant a decision while a wrongly-kept one costs a question. Demo: exactly one added line, `"kind": "true_conflict"` on Delft's programme-vs-admissions disagreement — right answer, both pages state the same intake. 4 tests. V2-25: `web_scholarships`, `web_costs`, `web_documents` and `web_government` read scope too, so no adapter is grandfathered any more. Demo: **127 claims now say `population: international`** — the scholarship gain the write-ahead predicted, and the most expensive wrong answer this product can give is now the one it records a scope for. Government pages come back empty, as predicted and as they should: a post-study-work rule is national. The run **also found a reader bug**: Toronto's award says it is "worth CAD 89,000 per year for 2024/25" on a 2026/27 page, and a bare year range was read as the page's year — putting that award's deadline, coverage and renewal rules under 2024/25. A year now needs a marker beside it (`academic year`, `entry`, `intake`, …), exactly as a month does. Golden re-captured with the same proof: **0 removed lines of 2651 changed**, every addition inside a `scope`; no result, bucket, check or value moved. V2-24: a declined claim becomes a **question the applicant can send to an admissions office**. `OutOfScopeClaim` (type, page, `ClaimScope.explain`'s reason, and whether anything else answered that requirement) rides on `EligibilityOutcome`; `runner._stage_assess` turns each into an `UnresolvedQuestion` on the result — the existing channel, so API, export and frontend needed no new field. `blocking` is true only when nothing else answered that requirement. The refused claim stays in the evidence list; it is set aside, not deleted. Demo byte-identical (nothing is declined there). 4 tests, one of them end to end through `_stage_assess` on a real demo run. V2-23: `app/domain/eligibility.py` **acts** on scope. `requested_scope(claims)` builds what the run asked (the intake only — the academic year on a claim is the *server's* default, not a request, and demanding it made every real page fall to UNKNOWN). Applied inside `_first`/`_confirmed`, so no requirement type can skip it: a page stating a **different** intake is not used as the answer at all (it stays persisted as evidence), a page **silent** on it may inform the assessment but **may not be a hard filter** — an unscoped page is not strong enough to end someone's application — and a page that **says** who it is for outranks one that does not, ahead of specificity. Claims with `scope is None` (pre-V2-22) behave exactly as before, same seam as V2-22b. **Demo: byte-identical**, and that is the result, not luck — every demo page states the requested intake, so the rule bites only where a page says something else or says nothing. 6 tests in `tests/test_eligibility.py`. V2-22b: `evaluation/research/mapping.evidence_scope(raw, ...)` — the capture's evidence scope now comes from the **page**, via the claim's recorded `scope`, with `None` for a dimension the page was silent on. Before this, `live.py` and `map_claims.py` built it from the **request**: `intake` was `"fall 2027"` on all ten cases of the frozen capture because that is what the profile asked, and `academic_year` was the runner's default. The benchmark was comparing a label against our own question — which is why the baseline README could say a scope-match failure is "not five human-confirmed errors" without knowing why. The request-side fallback is kept for a claim with **no** `scope` key (pre-V2-22, which every frozen capture is full of), and re-scoring `baseline/capture.json` is byte-identical — checked. **The measured rate is still 5/5 and cannot move here:** that needs a fresh live capture, and `Fetcher` has no network in this container (§7 owner/CI task). 3 tests in `tests/test_research_mapping.py`. V2-22: `app/adapters/scope_reader.py` — `read_scope(text, *, title="")`, the only thing that fills `Claim.scope`, wired into `web_requirements` and carried by `ClaimBuilder(scope=...)`. It reads five of the nine dimensions (degree, intake, academic_year, population, residency) and **refuses the other four in writing**: university/faculty/programme have a stronger answer in V2-17's identity work, and nationality has no phrase family that can tell "applicants from Kazakhstan" from "applicants from partner universities". Two refusals do the work: silence stays silent, and **ambiguity is silence too** — a page naming both EU/EEA and international applicants is scoped to neither. Demo effect, measured: 128 of 173 demo claims now carry a real scope (`Fall 2027`, 11 of them also `international`), 45 honestly empty. 18 tests in `tests/test_scope_reader.py`, module at **100%**. The golden demo hash was re-captured once, after proving the drift additive (0 removed lines of 1903 changed; every addition a key inside a claim's new `scope`) — see §8 and §9. V2-21b: `Claim.scope: ClaimScope | None`, **no migration** — `ClaimRow.payload` is a JSON column holding the claim whole, so the field lands there by itself; `alembic heads` stays the single `d9c4e7a21b83`. A `@model_serializer` omits the key entirely when no scope was recorded, so every claim written before this field keeps a byte-identical payload — which a golden-hash regression test checks and which caught the change when the field was first added. V2-21: `app/domain/claim_scope.py` — `ClaimScope` and `RequestedScope` over the nine dimensions the spec names, `covers() -> Verdict`, `contradictions`, `gaps`, `narrower_than`, `explain`, `from_mapping`. **Silence is not agreement**: a page that never says who it is for returns `UNKNOWN`, not `YES` — the move that `wrong_scope_claim_rate` 5/5 is made of. 28 tests, module at 100%. V2-13e: **Phase 1 is wired into the live pipeline.** `LiveDiscoveryAdapter._add_search_results` appends web-search programme pages to `selected[PageCategory.PROGRAM_PAGE]` after whatever the sitemap and walker found, using the adapter's own `Fetcher` for the hop. **Dormant unless `UNIMATCH_SEARCH_PROVIDER` is set** — the factory raises on `none` and that is caught, so a deployment without a key runs byte-identically. Proof: the whole pre-existing suite passes unchanged. A guard test caught a docstring naming the benchmark path from production and it was reworded, not weakened. V2-22a: `live_discovery.is_seed_host(url)` + a `registry_seed_host` ranking signal. The registry already records each institution's homepage and seed URLs with a `seeds_verified_on` date — the verified metadata §12 sanctions — and it names `future.utoronto.ca` while never naming `utm.` or `utsc.`. **Best single change of the session:** cases-at-rank-1 **2 → 4**, Toronto #19 → **#4**, Warsaw #5 → **#1**, HKU #6 → **#1**, UBC #2 → **#1**, Groningen and Delft each up one, ceiling still 10/10, two runs agreeing. A signal, never a rejection. V2-13d: `RankedCandidate.found_by` — which query families surfaced each URL (§11, never built until now). Used immediately: **Toronto's regression is not the new query family** — that family is one of the two that *found* the correct page. Five of the seven candidates above it are **other campuses of the same university** (UTM, UTSC), which the prefilter rightly keeps and the ranking has no reason to demote, because nothing in the pipeline knows a campus is a different place to apply to. Third mis-attribution this session, first one caught immediately. V2-11b: one `natural_language` query family — the request as a sentence, with the degree named in words *including its cycle wording* and no search operators. **Ceiling 9/10 → 10/10**, Warsaw returns, cases-at-rank-1 1 → 2, confirmed by two near-identical runs. Cost, stated not hidden: Toronto #8 → #19, Aalto −2, Delft −1, and 60 queries per run instead of 50. V2-13c: `_DEGREE_SLUGS` learns the Bologna cycle forms (`s1`/`s2`/`s3`, `first-cycle`, `i-stopnia`, `licence`, `magister`, …), so Warsaw's `IN/S2-INF` is read as a **master's** page and rejected by the bachelor prefilter — eight such rejections per run. A correctness fix, not a ranking one. Also **re-baselined**: the shipped configuration measures **9/10** today, not the 10/10 of a few runs earlier, and the difference is provider-side (see below). V2-13b: `page_classifier.classify_url(url)` — what a URL alone says a page is, added beside `classify_page` so the retrieval code does not grow a second copy of those patterns. The ranking signal that uses it is **measured and not enabled** (`rank_candidates(..., rank_by_page_kind=False)`): two runs gave Toronto **+11** and KAIST +2 and cost Warsaw its place, ceiling 10/10 → 9/10. `RetrievalReport.hop_entry_points_unreachable` now separates *no host qualified* from *the host refused the connection* — HKU's zero was the second. V2-16d: **the retrieval ceiling reaches 10/10.** The hop ships as *additive coverage*: the search list is truncated first and hop candidates extend it, entry points are host roots scored by what runs degrees (a host naming the field, then an admissions host; a lab or publication repository is never opened), and a page both generators found keeps its search position and gains `also_found_by_hop`. KAIST goes from unreachable to #30. Three earlier designs were measured and rejected first; all four runs and what each taught are in `SEARCH_PROBE.md`, with the hop result committed as `baseline/search_probe.exa.hop.json`. V2-16c: `discover_candidates` gains an injected `fetch: FetchPage | None` (default `None`, so the hop is **off**) and `hop_entry_points`; the report carries `hop_entry_points` / `hop_candidates`; the probe gains `--hop`. **Measured and not shipped:** fusing the hop as an equal generator moved the ceiling 9/10 → **8/10** and pushed NTU from #1 to #12, UBC #2 → #16, Aalto out of the top 25 entirely. §12 says a discovery change is good only if the benchmark improves, so it stays off. The negative result and the three things to try next are in `SEARCH_PROBE.md`. V2-16b: `app/adapters/search/navigation.py` — `links_from`, `navigation_candidates`, `NavigationLink`, `MAX_LINKS_PER_PAGE`, `DEFAULT_HOP_LIMIT`. One hop through a site's own navigation, emitted as `Generator.CATALOGUE_WALKER` for fusion. **Validated against KAIST's real front page: `content?menu=188` went from unreachable to rank 3.** 21 tests, module at 100%. **MEASURED 2026-09-21, live, 50 queries:** the Phase 1 retrieval path with Exa reaches the signed correct programme page in **9/10** cases, up from **1/10** on the frozen capture. Zero cases retrieve nothing (was 3). Our ranking puts the correct page first in **2**, so a reranker now has **7** cases of headroom where V2-14 measured none — `RERANKER_CEILING.md` is marked superseded for this path and `SEARCH_PROBE.md` carries the new numbers, the per-case table and the two failure shapes. `evaluation/research/search_probe.py` (+ `baseline/search_probe.exa.json`) reproduces it; 14 tests, 100%, none touching the network. V2-10b: `app/adapters/search/exa.py` — `ExaSearchProvider` behind the V2-10 seam. POST `api.exa.ai/search` with `type=auto`, `numResults` (capped at 25), `includeDomains`, `contents.highlights`; every failure becomes `SearchUnavailable`; no retries; response body capped at 1 MiB; the endpoint goes through `network_policy.check_url`. `config.py` gains `exa_api_key: SecretStr` and refuses to start with `exa` selected and no key. 27 tests in `tests/test_exa_provider.py`, module at 100%, none touching the network. **Default is still `UNIMATCH_SEARCH_PROVIDER=none`** pending the §7 decision. V2-17: `app/domain/programme_identity.py` (the rule — `Verdict`, `ProgrammeIdentity`, `IdentityState`, `ScopeState`, `identity_state`, `scope_state`, `applies_to_requested_intake`, `unresolved`, `refuted`, `explain`) and `app/adapters/search/identity.py` (`verify_candidate`, reading the six dimensions from stated evidence only). Identity and scope are separate; `UNKNOWN` is never a match and never a failure; `applies_to_requested_intake` returns a `Verdict`, not a bool. 32 tests in `tests/test_programme_identity.py`, both modules at 100%. V2-16: `app/adapters/search/fusion.py` — `Generator` (seven sources), `GENERATOR_WEIGHTS`, `SourcedCandidate`, `Attribution`, `FusedCandidate` (`agreement`, `best_rank`, `provenance`), `fuse(streams, *, top_k, weights)`. Reciprocal Rank Fusion, so nothing incomparable is ever added; every attribution survives into the output; a candidate filed under the wrong generator is refused. 23 tests in `tests/test_fusion.py`, module at 100%. V2-15: `app/adapters/search/site_search.py` — `detect_surfaces` for the nine §7 families, `SiteSearchSurface` (kind, endpoint, query parameter, provenance, evidence, detected-at), `search_url` with bounded pagination, `MAX_PAGES = 5`, `MAX_RESPONSE_BYTES = 2 MiB`, `NEEDS_CREDENTIALS`. Passive network-log evidence outranks markup inference, off-domain and administrative surfaces are discarded, and a key-bearing surface is flagged with its key deliberately unread. 36 tests in `tests/test_site_search.py`, module at 100%. V2-14: **the reranker comparison was not built, because the measurement says it would measure nothing.** `evaluation/research/ceiling.py` (+ CLI), `baseline/ceiling.reviewed.json` and `RERANKER_CEILING.md` record it: against the certified corpus and the frozen capture, the correct programme page is in the candidate set for **1/10** cases, the current ranking already has that one at position 1, so **headroom for any reranker is 0**. Three cases retrieved nothing at all. 13 tests in `tests/test_reranker_ceiling.py`, module at 100%. V2-13: `app/adapters/search/prefilter.py` (§5 chain over `SearchResult`s, every rejection recorded with its reason) and `retrieval.py` (self-contained BM25, named deterministic signals, `rank_candidates`, `discover_candidates`, `RetrievalReport`). It **reuses** `live_discovery`'s `canonical_url` / `same_institution` / `names_other_degree_level` / `looks_like_catalogue` rather than writing a second copy; one public `is_excluded_path` was added there for the same reason. 29 tests in `tests/test_hybrid_retrieval.py`; package at 100% across all seven modules. V2-12: `app/adapters/search/ontology.json` (versioned `2026-09-21.1`, six field concepts and all four degree levels) and `ontology.py` — `canonical_field`, `is_equivalent`, `retrieval_candidates`, `degree_aliases`, `ontology_version`, `Relation`, `RetrievalCandidate`. Equivalence and retrieval expansion are separate functions returning different things, so a related concept can never come back from the equivalence one. 29 tests in `tests/test_ontology.py`; package still 100%. V2-11: `app/adapters/search/intent.py` — `DiscoveryIntent` (six fields, none of them about the applicant), `from_profile` as the single sanctioned conversion, `queries_for` rendering the §4 families under a bounded `DEFAULT_QUERY_BUDGET = 6`, `QueryPrivacyError`, and `redacted_audit_record`. 27 tests in `tests/test_discovery_intent.py`, one per forbidden item in the spec's list; `app/adapters/search/` is at 100%. Also made `test_a_slow_parse_does_not_block_an_unrelated_request` deterministic — see §9. V2-10: the search seam ships in `backend/app/adapters/search/` — `base.py` (`SearchResult`, `SearchResponse`, the `SearchProvider` Protocol, `SearchError`/`SearchProviderNotConfigured`/`SearchUnavailable`), `fake.py` (offline, corpus-driven, stamps `provider="fake"`), `__init__.py` (`get_search_provider`, `KNOWN_SEARCH_PROVIDERS`), plus `Settings.search_provider` defaulting to `none` with `_validate_search`. 22 tests in `tests/test_search_provider.py`, 100% coverage of the new package. Nothing is wired into discovery: query generation is V2-11 and fusion is V2-16. V2-01: **the corpus is certified.** `ground_truth.reviewed.json` (`2026-09-21.reviewed`) carries `human_verified` + reviewer **Диас** + `2026-09-21` on 10/10 cases, and `metrics.reviewed.json` is the first report in this project produced **without `--allow-drafts`**, `provisional: false`. Acceptance record in `backend/evaluation/research/ACCEPTANCE.md`; two new tests pin the gate (`test_the_reviewed_corpus_is_signed_and_scores_strictly`, and `test_certification_changes_no_measured_value`, which forbids a signature from ever moving a number). The owner's answer also settled the Aalto adjudication in the affirmative; it is recorded as a decision in that case's notes with the reasoning it overrides preserved. Draft7 applies the **owner's first human review of the corpus** — 62/220 known fields, 10/10 identities, two cases changed. Aalto's identity moves from the Finnish tietotekniikka page to the English-taught Computer Engineering major, because the requested scope is an international applicant and the Finnish route is not open to one in English; whether Computer Engineering satisfies a *computer science* request is left open for the reviewer, not asserted, on the same grounds draft2 refused Data Science. HKU gains `programme.faculty = "School of Computing and Data Science"` and its exact degree title, Bachelor of Engineering in Computer Science. Programme precision/recall are unchanged at 1/9 and 1/10 — the Aalto URL move neither gained nor lost a match against the frozen capture. Still 0/10 `human_verified`, because the schema requires a reviewer name and date and no AI may invent either. Draft6 resolves the Delft exact programme identity from the official tudelft.nl page — the last `unknown` of ten, carried since draft2 — taking programme identities to **10/10** at 61/219 known fields and 0/10 human signoffs. One field changes; no label, no frozen artifact and no production file is touched. Its two programme numbers *fall* (precision 1/8→1/9, recall 1/9→1/10) because a tenth answerable case and a ninth judgeable prediction enter the denominators against the same frozen capture: arithmetic, not a retrieval regression, and REVIEW_DRAFT6.md says so in those words. Draft5 is published in `a4cd5b3` (gpt-6-astra) — 61/219 known/total fields, 9 programme identities, 0 human signoffs, NTU qualification and conditional `english_evidence.*` minima plus the Toronto Kazakhstan credential, with separate report/worksheet/VERSIONS row and the replay test parametrised over `.draft5`. It was committed `wip:` because its gates had not finished; claude-opus-5 ran them on 2026-09-20 and they are green (§6), so draft5 is released. Its content is recovered gpt-6-astra work, not a second implementation. `3f7e467` publishes draft4 with exact Aalto CS identity/primary Finnish teaching language and Groningen NIS qualification equivalence/CS mathematics requirement: 56/215 known/total fields, 9 programme identities, 0 human signoffs. Separate metrics and complete human-review worksheet; 57 focused tests. `2f56a46` publishes lossless draft3 document projection (52/212 known/total fields), reversible manifest, separate report and review worksheet; 55 focused tests. `5403630` adds explicit offline award/document identity mapping and replay; `00e107f` keeps unknown policies unanswered, adds the human review worksheet and brings focused coverage to 51 tests. `7356d9e` published draft2: 46/206 known labels, 8/10 exact programme URLs, 0/10 human signoffs; separate replay report with programme precision/recall 1/8 and 27 benchmark tests. Frozen draft1/capture are unchanged. `d917259` integrated all 15 Markdown documents plus original manifest and navigation/task card; pushed. `5d2a3ed` write-ahead V2-01 baton; pushed. All 16 archive entries verified byte-for-byte after transfer; original untracked ZIP removed. 51f9512 pushed schema, offline scoring, bounded live capture, 10 draft cases, 14 tests and container isolation. `a243a46` pushed checkpointed HTTP/PDF counters, candidate ranks and evidence validation. `1187cd0` published direct claim mapping, compact baseline capture/metrics/report and human review queue. `d0a2fb4` fixes JSON type equality; 25 benchmark tests and both full CI matrices pass. Draft PR: https://github.com/wpalish/ashyq-apply/pull/14. Human certification remains outstanding.


The original recovery entries below are historical provenance. Preserve their hashes and ancestry;
the first seven predate `AGENTS.md` and lack the required `Agent:` trailer, so do not rewrite them to
manufacture compliant history. [0.4] was committed before [0.3].

| Task mapping | Existing hash | Observed change |
|---|---|---|
| [0.1] | `f23407f` | Profile priorities, privacy field and weights override; profile tests. |
| [0.2] | `ea33051` | Priority/ROC weights module and ranking tests. |
| [0.4] | `3eefdcd` | Bucket enum and ranking/result schemas. |
| [0.3] | `0f46079` | Ranking v2 domain implementation, scoring changes and tests; inherited T3 issue (§7). |
| [0.5] | `0b8d97f` | Assessment from stored attributes, ranking config, bucket model/migration and pipeline tests. |
| [0.6] | `e1d8078` | Rerank, result sorting/filtering and balanced shortlist API; pipeline helpers and API tests. |
| [0.7] | `c924410` | Profile-field documentation and ADR 0003; ADR changes I4 interpretation without recorded owner resolution. |
| [0.8] recovery | `61df0db` | Preserving checkpoint: eight frontend files + relay sources, one red test named in the message. |
| [0.8] baton | `0bedc38` | Baton to claude-opus-5; §1/§2/§4/§5/§6/§11 reconciled with the real tree and real gate numbers. |
| [0.8] | `2f2e484` | Bucket assertion scoped to its own cell; frontend unit suite 141/141. |
| [0.8] | `d675cfe` | `CONTRACT["Bucket"]` and `bucket` on `/api/vocabulary`; 892 backend tests. |
| [0.8] | `0affab6` | Preferences disclaimer restored, per-table captions, e2e helper opens the set-aside sections; 67 e2e passed. |
| [0.8] fix-forward | `c220095` | Re-applied the orphaned shortlist-width fix after PR #2 merged. |
| [0.8] handoff | `d6e59d5` | Published PR #6 and pointed §5 at review, then `[1.1]`. |
| [0.8] review fix | `4a7171c` | Merged current main, restored the independent Confirmed column, protected longest-chip geometry, regenerated screenshots, and passed current gates/re-review. |
| GLM c1 sync | `25f5954` | Merged `origin/main@7b1fce0` into the local campaign candidate without conflicts; original `e533d62` preserved as `audit/glm-c1-e533d62`. |
| T10 follow-up | `7f364cf` | PostgreSQL regression proved a stale payment poll committed a provider journal entry; `worker.py` now turns a failed fenced retry transition into `LeaseLost`, rolling back the whole payment transaction. |
| T18 Kazakhstan domains | `135138a` | Treats `edu.kz` as a multipart public suffix, so `admissions.nu.edu.kz` belongs to `nu.edu.kz`; regression test included. |
| T18 live programme fit | `02d648c` | Fetched programme pages must match the applicant's level and subject; prevents MSc/unrelated BSc leads consuming the verification limit ahead of BSc Computer Science. |
| T29 production wiring | `8d2fa10` | Live runs now use the hardened `CatalogRenderer` and persist walker fetch metadata through `SourcePage.record`; decoder recursion and oversized JSON labels fail closed/bounded. |
| T30 measurable harness | `388ae98` | Canary reports separate programme/category numerators, source-page and fetch-tier counts, walker metrics, timestamped outputs and explicit batch selection. |
| T30 catalogue repair | `5c42934` | Malformed/PDF catalogue bytes can no longer abort the entire walk; lxml falls back to the stdlib parser and a minimal `<f/{>` regression pins the failure. |


### Security audit, 2026-09-09 (branch `task/security-audit-hardening`)

| Finding | Severity | Hash | Change |
|---|---|---|---|
| Forgeable payment webhook (hardcoded `test-secret` / empty-key HMAC) | Critical | `885abfd` | Both providers refuse to verify with no secret; no fallback secret; `validate_runtime` refuses payments without one, refuses `fake` in production, and requires ≥16 chars plus an API key there. |
| Transcript parse blocked the event loop; endpoint unlimited | High | `016da44` | `run_in_threadpool` + a new `upload` limiter group; the two `conversions/*` routes now require a principal. |
| SMTP STARTTLS with `CERT_NONE` | High | `c840dd9` | `ssl.create_default_context()`; `smtp_password` becomes `SecretStr`. |
| `needs_rehash` never called; reset token survived a password change; scrypt `maxmem` capped the cost schedule | Medium | `03ad016` | Rehash on login, burn live reset tokens on change, size `maxmem` from the parameters. |
| CSV/XLSX formula injection | Medium | `77e877e` | `export.tabular.neutralize` on every cell of all three sheets. |
| Block bypass on `GET /api/social/people/{user_id}` | Medium | `1a2ee72` | Symmetric block check, 404 like a stranger's. |
| `/metrics` 500 on a non-ASCII bearer token | Low | `0610e17` | Compare bytes; plus a test locking the whole header policy across every response shape. |
| `SourceLink` rendered an unvalidated `href` | Low | `84f0b43` | `isSafeHref`; non-http(s) sources render as text. |
| SECURITY.md described intent, not the controls | — | `b96845f` | Payments, accounts and mail, exports sections rewritten to what holds. |

### Robots and stalled responses, 2026-09-23 (after run 19 = run id 35861235523 on `7b67f01`)

Run 19: claim_recall held at 2/62 (precision 2/9, wrong_scope 2/9). Vienna's footer walk is gone
(pre-search reads are now informatik/studieren). Aalto still lost 90 s — not to a Crawl-delay: its
`get #1` (robots.txt) *started and never finished*; httpx's timeout bounds each read, not the exchange.

| Change | Hash |
|---|---|
| `ROBOTS_CRAWL_DELAY` outcome (a long delay is not a refusal); `Fetcher(max_crawl_delay=)`; source scanner passes `None` and waits delays out | `a8a7ad3` |
| robots.txt load bounded to 15 s in total (then "unavailable", remembered); each page attempt bounded to 2× timeout, not retried | `5cd493d` |
| Run 20 (35890139634): deadline held but Aalto's whole host is silent to the runner (robots 50 s, then sitemap); KAIST admission host 50 s. A host that stalled once fails fast for the rest of the run; attempt deadline 1× timeout | `551c2ef` |
| Run 21 (35894685440): Aalto now completes (1 claim) under fail-fast. KAIST www/cs hosts (1–2 s in run 20) each cost ~30 s: `check_url` ran blocking `getaddrinfo` on the event loop, so no deadline could fire. Resolution now in a thread, 10 s deadline; stalled check before resolving. Also `0d85a6d`: page budget counts network reads only (VERSIONS.md) | `3e5e352` |
| From the owner's deep-research report: robots.txt 5xx / network failure / stall now = complete disallow (RFC 9309 §2.3.1.4; was "allowed"); 4xx stays "no restrictions". Per-origin robots locks | `92ac782` |
| Same report: up to 3 validated addresses per hop, 5 s connect each, only connect failures fall through; Host/SNI unchanged | `5f86976` |

Report items NOT done, needing the owner: dedicated live-benchmark runner with a fixed public IP + rDNS + bot page
(GitHub's shared Azure egress is a suspect, unproven); Finnish Studyinfo/Konfo public API adapter; Korea sources
(Study in Korea; `apply.kaist.ac.kr` named by the report, unverified by us). Not yet done, no decision needed:
per-phase fetch tracing (DNS/TCP/TLS/headers/body) — next.

**Run 23 (35899295750, `d181e99`): 9 of 10 cases complete (run 21: 4).** Only UBC ran out of wall clock
(funding stage). claim_recall 1/62 (run 19: 2/62), claim_precision 1/9, programme_page_recall 4/10 (was 1/10),
wrong_scope 3/9. The binding constraint has moved: of 9 claims carrying the certified value, **8 are
`other_page`** — right value, quoted from an official page other than the one the reviewer cited, so not
supported (support_report). Whether another official page of the same university may support a label is a
scorer-definition question for the owner. Also seen: Aalto's `programme.exists` came from a research-paper
title ("Arguments for and Approaches to Computing Education…"), and scope_report lists it as the same programme
as 'Tietotekniikka' "by strong aliases" — looks like a false alias match; to investigate.

**Run 24 (35905039431, `eee37ac`, RFC 9309 + multi-address):** same as run 23 — 9/10 complete (UBC wall
clock), claim_recall 1/62, 8 of 9 value-correct claims other_page. No case lost to the stricter robots rule;
the oracle's KAIST scholarship pages now read `robots.txt unreachable (ConnectTimeout)` → disallowed, as the
RFC requires. Sibling-page rule `2603351` and research-output classifier `ccc07d7` land in run 25.

**Run 25 (35909275111, `ccc07d7`): claim_recall 5/62 (strict same-page 1/62), claim_precision 6/8**
(run 23: 1/62, 1/9). The sibling-page rule accounts for four facts. Aalto's research-paper claim is now
`classifier-rejected` (Aalto files 0 claims: its real programme page still is not reached — 9 fetch
failures). 8/10 complete: UBC (funding stage) and HKU (scholarship pagination, zh-hant/zh-hans copies)
ran out of wall clock. Open: Groningen deadline scope mismatch (label non-EU/EEA; the live page now lists
01 May for every population — the page may have changed since certification; labels are not ours to edit).

**Run 26 (35913127890, `d7a20e8`): claim_recall 3/62 (strict 1/62), precision 4/5.** HKU now completes
(translated-copy skip); KAIST files 4 claims (0 before). But Groningen ran out of wall clock at t=90 s
on the same ~97 reads that finished inside the clock in runs 23–25, and its 5 claims went with it — the
drop from 5/62 is that case, not a regression in extraction. Groningen spends ~50 reads before search on
faculty home pages (`/cf`, `/feb`, `/gmw`, `/let`, `/museum`) from the navigation fallback. Moving search
earlier is the obvious lever and is **not** taken: `_add_search_results` records that interleaving was
measured and cost whole cases. Options for the owner: a larger per-case wall clock for the benchmark
(production has no 90 s cap of this shape), or a measured experiment with search-before-navigation.

**Budget and order experiments, 2026-09-24 (both on `c5290be`/`3431768`, one run each):**

| Run | Setting | complete | claim_recall | strict same-page | programme_page_recall | recall@5 | reads (delft/ubc/warsaw) |
|---|---|---|---|---|---|---|---|
| 26 | 90 s, default order | 8/10 | 3/62 | 1/62 | 3/10 | 1/10 | 53/46/63 |
| 27 (35948537073) | **120 s**, default order | **10/10** | **6/62** | 2/62 | **5/10** | 1/10 | 55/55/65 |
| 28 (35949580173) | 90 s, **search first** | **10/10** | **6/62** | 2/62 | 4/10 | **3/10** | 39/31/55 |

Same recall either way. Search-first reaches it inside 90 s with far fewer reads and ranks the right page
higher, but Warsaw (2→0 claims) and KAIST (4→0) filed nothing — not scored facts, but lost evidence, the
same shape of loss that got interleaving rejected before. One run each is noise-sized (Groningen alone
swings 5 facts). Recommendation to the owner: benchmark default 90→120 s (harness only, production has no
such cap); keep SEARCH_BEFORE_NAVIGATION off until a second paired run explains Warsaw/KAIST.

**Paired repeat, 2026-09-24, both at 120 s on `2c492af` (owner: 120 s default, `2c492af`):**
run 29 (35954240254, default order) and run 30 (35954242214, search first) — both 10/10 complete,
claim_recall 6/62, strict 2/62, precision 7/9. Default order: programme_page_recall 5/10, recall@5 1/10.
Search first: 4/10, recall@5 3/10, ~25% fewer reads. KAIST's zero was noise (search-first KAIST 4 claims
this time, default-order KAIST 0); Warsaw files nothing under search-first in both runs (its 2 claims are
not certified facts). Verdict: no difference in scored facts across four runs; SEARCH_BEFORE_NAVIGATION
stays off (the measured default keeps one more programme page), and the flag stays for later measurement.

**Run 31 (35956516997) zero-claim page listing (`74cda21`) says why:** Vienna's admission-procedure page
and HKU's admissions home were classified *news* on a sidebar heading — fixed `cf1cbeb` (title and first
heading only). HKU's programme page (`www.admissions.hku.hk/.../computing-and-data-science`) is
classified *unknown* and files nothing — not yet diagnosed (page not reachable from the sandbox). Aalto:
robots.txt ReadTimeout → whole site disallowed (RFC-correct); the only page left is the research-portal
paper, correctly rejected. KAIST: admission host robots.txt ConnectTimeout → disallowed.

**Run 32 (35958818912, news fix):** Vienna's admission page is no longer news but was left *unknown* —
fixed `6e7d4ff` ('Admission procedure' in the admissions vocabulary). Toronto filed nothing this run:
`future.utoronto.ca` answers **HTTP 403** to every request (a refusal, not a network fault — recurring in
earlier runs too), and `utm.utoronto.ca` robots.txt timed out → disallowed. A 403 is the site's explicit
answer; it is not retried and not worked around.

**Run 33 (35961069742) rejection detail:** HKU programme page title 'Computing and Data Science | Admissions
Office', no decisive signals — a faculty listing. Degree titles in brackets ('Bachelor of Engineering
(Computer Science)') were not read by `full_degree_titles`; now they are (`29a2c2a`) — a *suspected* cause,
unconfirmed. `04a37a4` adds text length and the degree titles found to every rejection, which the next
capture will use to confirm or rule it out.

**Run 35 (35965530771) confirms HKU's cause:** its page has 4977 chars and lists 'Bachelor of Engineering in
Computer Science' — the bracket theory (`29a2c2a`, kept: harmless and correct) was not it. `_listed_programme`
compared against `program.name` = 'Computing and Data Science' (the faculty page's title). Now the requested
field counts too — `fbad784`.

**Run 36 (35968336185):** HKU files its programme-exists claim (listing fix works). Vienna now ran out of
the 120 s clock (its admissions page is accepted and walked; not yet diagnosed). UBC ran out reading eight
Canadian-students award pages for a Kazakh applicant — skipped for plain foreigners, `dda17f3`.

Run 37 (35971288445, on 457b2c0): 10/10 cases complete inside 120 s; UBC now skips its
`canadian-students` award pages as intended. claim_recall 2/62 (same-page 1/62): delft and ntu
programme.exists only. Vienna is a navigation miss, not a clock or pattern miss: the deadline fact
lives on `aufnahmeverfahren.univie.ac.at/en/computer-science` and the programme page is
`studieren.univie.ac.at/en/bachelordiploma-programmes/computer-science-bachelor-with-entrance-exam-procedure/`
(linked from `/en/degree-programmes/bachelordiploma-programmes/` as "Computer Science (Bachelor - with
entrance exam procedure)"); discovery spent 63 reads without selecting it, and requirements only reads
program.url + admissions_url. `_APPLICATION_PERIOD` matches that page's text offline. Next: see which
discovery stage drops that link (needs a CI trace; the sandbox cannot reach sites through the Fetcher).

Runs 38–40 (51296dd, 164f118, 6fab51c), Vienna: claim_recall stayed 2/62. The CI capture now prints,
for every zero-claim case, the read trail plus discovery's selection and the catalogue walker's
candidates/outcomes. Findings: (1) navigation kept the first three programme links, not the
strongest (fixed in 164f118, tested; did not move Vienna, whose programme page is found by the
walker, not by navigation); (2) the walker walks at most two catalogues ("Degree programmes",
"Choice of degree"); its strongest lead, "Bachelor/diploma programmes", classifies as a single
programme (title reads as a name), fails the subject check and was dropped — the only page that
names Computer Science. Fix in the next commit: the walker descends into one such lead
(`WALKER_MAX_DESCENTS = 1`) when it reads as a catalogue or its URL looks like one. Still open for
the deadline fact: it lives on `aufnahmeverfahren.univie.ac.at/en/computer-science`, which
requirements does not read (only program.url + admissions_url).

Run 41 (35991678662, on 687113d): claim_recall 3/62 (was 2). Vienna now confirms
`/en/bachelordiploma-programmes/computer-science-bachelor-with-entrance-exam-procedure/` and files
programme.exists; its deadline is still missing (it lives on aufnahmeverfahren.univie.ac.at). Cost: UBC
and HKU hit BENCHMARK_PAGE_BUDGET_EXHAUSTED (the descent read 20 more leads). Next commit caps the
descended walk at `WALKER_DESCENT_TOP_N = 5` leads.

Run 42 (35994920559, on 7fe2337): 10/10 complete, claim_recall 3/62 held. Vienna's deadline is
certified `status: unknown` (the published cycle is 2026, not the fall 2027 intake), so not filing one
is correct. Next: Groningen's certified page is `rug.nl/bachelors/computing-science`; the ontology
lists "computing science" as a strong alias of computer science but discovery matched field words
literally. Next commit reads fields through `with_strong_aliases` (strong aliases only; related
concepts never match).

Runs 43–44 (e7379dd, a8f64da): claim_recall 3/62 held, 10/10 complete; Vienna files 4 claims in 43.
Groningen: the walker descended into `rug.nl/bachelors`, which is itself an index (alphabet, in-english,
by-subject); the programme links are one level below. Next commit: descents tracked per chain (depth ≤
`WALKER_MAX_DESCENTS = 2`, total ≤ `WALKER_MAX_DESCENT_READS = 3`), deeper lists walked before the next
top-level catalogue. Warsaw: the walker reads en.uw.edu.pl menus only; the certified programme page is
on informatorects.uw.edu.pl (not yet reached).

Run 45 (36003951574, on 7e7f91f): claim_recall 3/62, programme_page_recall 3/10 (was 2/10), 10/10
complete. Groningen's second descent went to `/bachelors?lang=nl` (a language copy) instead of
`/bachelors/alphabet`, which does link `/bachelors/computing-science/`. Next commit: a language copy
of a walked page is not a new list, and a read page directly below the catalogue is a descent lead when
no lead reads as a catalogue (`_descent_lead`).

Run 46 (36007972261, on f39b206): claim_recall 5/62 (was 3), claim_precision 6/8, 10/10 complete.
Groningen reaches `rug.nl/bachelors/computing-science` via `/bachelors` → `/bachelors/alphabet` and
files deadline + programme.exists (both same_site). One Groningen deadline claim is recorded for
EU/EEA where the certified row is non-EU/EEA (the page's table lists both; wrong_scope, not wrong value).

Run 47 (36012276603, on 9350064): 5/62 held. Every case reports "search added nothing via exa;
offered: none" and each search call takes ~0.1 s — search is contributing nothing anywhere (Warsaw,
HKU, UBC have only catalogues). Next commit logs each failed query's reason and adds query/failed/
rejected counts to the trace line, to tell a refused key or quota from an empty index or the prefilter.

Run 48 (36016512038, on a6f2dc3): 5/62 held. Root cause of "search offered nothing": every Exa query
answers HTTP 402 (Payment Required) — the account's credits are spent. All six query families fail
for every case, so search has contributed nothing since the balance ran out. OWNER ACTION: top up the
Exa account (or rotate the key in the repository secret). Nothing in code can fix a 402.

2026-09-24: Tavily added as a second search provider (`app/adapters/search/tavily.py`, same contract as
Exa: hint-only snippets, fail closed, no retries). The capture workflow prefers Tavily when the secret
`UNIMATCH_TAVILY_API_KEY` is set, then Exa, then none. OWNER ACTION: add that repository secret; the
key was given in chat and is never committed.

Runs 49–50 (Tavily live): 49 gave claim_recall 6/62, programme_page_recall 5/10 (was 3), precision
8/12; 50 gave 5/62, precision 6/10, UBC out of wall clock. Toronto crashed both times: bs4's lxml
builder raises ValueError on a malformed attribute (`{x="1"`) on its scholarships page — fixed in
879c929 (`app/adapters/html_parse.parse_html`, lxml → html.parser → empty soup, used at all 7 call
sites). Wrong-scope claims from my strong-alias change: Vienna "Business Informatics", HKU "Computing
and Data Science". Next commit: an alias matches a title only when every other word is filler
(level/form words); the applicant's own field words still match inside longer titles.
Scorer note (not changed): HKU university "The University of Hong Kong" vs "University of Hong Kong"
counts as a scope difference.

Run 51 (36040801960, on 9d4eaba): 5/62, precision 6/10; Toronto now completes (0 claims, 403);
Vienna's Business Informatics gone; UBC out of wall clock again. HKU still files programme.exists for
"Computing and Data Science" (a search lead named after its URL slug confirms itself). Next commit:
when the requested name is only discovery's URL-slug placeholder, the page subject must also name the
applicant's field (`_named_after_its_url` + `matches_field_text`). A broader version removed the demo's
Melbourne "Computing and Software Systems" existence claim (golden drift, a removal) — narrowed so the
golden is byte-identical.

Run 52 (36046148794, on a33629d): claim_recall 7/62 (best so far), precision 10/13, wrong_scope 3/13,
programme_page_recall 6/10, 10/10 complete (UBC and Toronto finish; Toronto files 2 claims via search
leads). Remaining wrong-scope claims: UBC "Computer Science (BA)" for a certified BSc; Toronto
"Computer Science Topic Courses" (a UTM calendar section read as a programme); HKU a page read as
master. Scorer-side string differences (Delft/NTU/Vienna titles, HKU "The University of") are matched
by identity and not counted as wrong.

Run 53 (36066263881, on eb3e3bc): claim_recall 6/62, precision 8/11, programme_page_recall 4/10,
10/10 complete. Toronto's "Topic Courses" claim is gone (Toronto now 0 claims); HKU now records
"BEng in Computer Science" (the right programme; university string "The University of" still differs).
Run-to-run variance with Tavily is visible (programme_page_recall 6/10 → 4/10 with no discovery change),
so single-run deltas of ±1 fact are not evidence; compare over two runs before attributing a change.
Open: UBC "Computer Science (BA)" vs certified BSc; Warsaw 0 claims.

Run 54 (36070050028, on db7f838): 5/62, precision 6/9, UBC out of wall clock. Search by registrable
domain now reaches informatorects.uw.edu.pl for Warsaw, but its top offers were one course's page
("Introduction to computer science I", /courses/view) and a news item; /programmes-all/IN came third.
Next commit excludes single-course URLs (`/courses?/(view|details?)`) in `_URL_EXCLUSIONS`.

Run 55 (36072768171, on 2cf6ad8): 5/62, precision 6/9; Groningen hit the page budget (search reads
added), UBC finished with 0 claims. Live results now swing 5–7/62 with Tavily's answers.

STAGE LEDGER — every scorable fact (31 of 62; the other 31 need a claim type or an identity binding,
see expressibility) and why it is or is not scored, as of runs 52–55:
- Scored (live, when discovery reaches the page): groningen deadline, groningen programme.exists,
  vienna programme.exists, delft programme.exists (identity), ntu programme.exists,
  hku programme.exists (run 53+, "BEng in Computer Science"), ubc programme.exists (BA vs certified
  BSc: counted wrong-scope; both degrees exist, the profile does not choose — not "fixed" by guessing).
- Reachable, extraction gap: ubc ielts.subscores — "no part less than 6.0" extracts on the quoted text
  and the scorer already maps a floor to the four-band map, yet the full page yields no subscore claim;
  cause not established without the full page (open).
- Certified as unknown/null, correctly not claimed: vienna deadline (published cycle is 2026, not
  fall 2027), groningen tuition (certified value null).
- Blocked by the site, not the pipeline: aalto (3 facts) and kaist (14 facts) — robots.txt does not
  answer, RFC 9309 ⇒ disallowed; toronto (3 facts) — HTTP 403 on future.utoronto.ca.
- JS-rendered: warsaw programme.exists — search now reaches informatorects.uw.edu.pl/en/programmes-all/IN
  but it serves 446 characters without a browser; the certified IN/S1-INF page was not offered.
Owner-level options for the blocked 20: permission/API from the universities, official aggregators
(Studyinfo, Study in Korea), a browser tier for JS pages, a fixed-IP crawler.

2026-09-25, GitHub Actions is out of minutes (owner: "0 минут"): every workflow job fails in ~4 s with
no runner since 00:43 UTC, so run 56 (90d0121) never ran. Offline work meanwhile: two award claim
types, `scholarship_living_allowance` → `coverage.living` and `scholarship_duration` → `duration`
(NTU Nanyang S$6,500/year, "normal programme duration"); expressibility ceiling 31 → 34 of 62; see
VERSIONS.md. `parse_money` read S$/HK$/C$/A$/NZ$ as USD — fixed, with KRW/HKD/NZD. Bond not added:
the corpus value carries a basis and populations no pattern can read honestly. Scholarship discovery
is still 0/3 live; these fields score only once the award page is reached (open, needs Actions).

Run 57 (36112077422, on 5aa1e78; Actions restored): 5/62, precision 6/8; Groningen out of wall clock;
KAIST files 4 claims, Warsaw 1, NTU 10. The funding-pages block shows why scholarship discovery is 0/3:
NTU reads its bursaries index first, its 21 links fill all 12 award slots, then the scholarships index
("17 award links followed") gets no room and the Nanyang page is never read — the "followed" count was
misleading. Next commit ranks pending award links from every index together (named scholarships
first, bursaries/financial aid last) within the same 12-page budget, and the outcome says how many
links were actually queued.

Claude, 2026-09-25, runs 58–59: 6/62 (precision 7/9), then 5/62 (6/8; UBC hit the wall-clock budget).
NTU's queued award links were all fetched. The problem was the ranking. All twelve slots went to FAQs,
graduate, current-student, exchange and teaching-award pages, so the Nanyang Scholarship link was never
read. `_award_priority` now ranks those after awards for incoming applicants (a tuple key). Run 60 checks it.

Claude, 2026-09-25, run 60: 6/62, precision 7/11. NTU filed 18 claims, but the Nanyang Scholarship page
was still not read. Its link sits under /scholarships/freshmen, and that page was rejected as "not an award
page". Change: a page that links three or more awards under its own path is now read as an index (within
the index budget). Research, innovation, fellowship and staff-award pages also rank after awards for
incoming applicants.

Claude, 2026-09-25, run 61: 5/62, precision 6/9 (UBC hit the wall-clock budget again; NTU 16 claims).
/scholarships/freshmen is still rejected, so its award links are not filed beneath its own path. A rejected
page's outcome now lists its award-link count, how many sit below it, and a sample of them, so the next fix
comes from evidence rather than a guess.

Claude, 2026-09-25, run 62: 5/62, precision 6/8.
- NTU /scholarships/freshmen: 18 award links, none below it. They are the site-wide menu, the same on
  every NTU page, so the Nanyang Scholarship link is not in the static HTML (likely JS-rendered). This joins
  the browser-tier owner decision; no further HTTP-side fix.
- UBC (runs 59, 61, 62) ran out of wall clock mid-funding and lost everything, because claims are collected
  in run_to_decision's finally and the parent's subprocess kill never reaches it. The harness child now stops
  itself 5 s before the kill (asyncio.wait_for), keeps the claims already filed, and still reports
  BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED. Harness only; production is untouched.

Claude, 2026-09-25, runs 63–64: 4/62 (5/8), then 6/62 (8/11).
- The soft stop works: in run 64, UBC hit the clock and kept 2 claims.
- Groningen hit the clock in both runs with 0 claims. The full trail (now printed for budget cases) shows
  the walker confirmed /bachelors/computing-science at t=53s. It then kept walking the remaining catalogues:
  science-shops projects, the faculty home pages and the museum, until the kill.
- Fix: the walk stops at the first walk that confirms a programme. The descent test was updated to pin this.
  The golden demo is unchanged.

Claude, 2026-09-25, run 65: 7/62 (ties best), precision 8/11. All 10 cases completed; Groningen got its 5
claims back. Vienna 4→2 claims, and the two lost were a scorer-"neither" wrong-host duplicate, not a fact.
UBC ielts.subscores: the oracle's extraction on the certified page yields 4 claims and no subscore. The
same excerpt alone extracts 6.0 locally, so something else on the full page pre-empts it. The oracle now
names the claims it got, so run 66 will show what.

Claude, 2026-09-25, run 66: 6/62, precision 7/9. UBC hit the clock again but kept 2 claims.
UBC ielts.subscores is not an extraction gap. The certified page yields exactly
{listening, reading, speaking, writing: 6.0}. The oracle compared maps with str(), so the different key
order read as "value missing". The scorer itself uses json.dumps(sort_keys=True) and was never affected.
The oracle now compares the same way (test added). What is left for UBC is the live run reaching that page
within its clock.

Claude, 2026-09-25: UBC's clock. In run 66 the walker's homepage root (http://you.ubc.ca/) read about 20
menu links (Indigenous, Contact us, the CLF terms page) from t=25 s to t=68 s. A site root is not a
catalogue, so its signal-less leads are now dropped as walker_no_signal. The T29 contract still reads
signal-less leads on a real catalogue page. Golden demo unchanged; test added.

Claude, 2026-09-25, run 67: 5/62, precision 5/7. The oracle now recovers 8 facts, UBC ielts.subscores
among them (the key-order fix). UBC completed with 0 claims: search did not reach its programme page
(Tavily variance), and the menu reads were still there. Cause: every menu link sits directly under the site
root, so five or more count as a "repeating list" and bypassed the site-root rule. On a home page the
repeating bonus no longer applies. Test extended to five menu siblings.

Claude, 2026-09-25, run 68: 5/62, precision 5/7.
- Tavily answers HTTP 432 (plan usage limit) to every query, so search is off for the whole cohort. This
  explains part of the drop since run 65. It needs the owner: a new key or plan, or another provider. Runs
  until then measure navigation only.
- UBC's menu reads come from walking the catalogue https://you.ubc.ca/programs (a JS page whose static HTML
  is only the site menu), not from the home page. The walker scores those menu links 2 ("Canadian students",
  "International students", "Applying to UBC"), so the signal-less and site-root rules never apply. Next:
  look at why score_link gives a menu label a positive score. Not changed yet.

Claude, 2026-09-25: UBC menu, fixed. The score 2 on the menu links was the repeating-list bonus: every item
sits one level below the root, so five or more counted as a list. A page one level below the root now has
no list parent, and a signal-less link to one is dropped as walker_no_signal even on the catalogue's host.
Links that name the applicant's subject still score by label (Toronto's /data-computer-science). Golden
demo unchanged. Search remains off (Tavily 432) until the owner renews it.

Claude, 2026-09-25, run 69: 5/62, precision 5/7, no case worse than run 68. Tavily still answers 432 (36
times this run), so search is off. UBC's top-level menu reads are gone. The walker now reads the next menu
level (ubc-life/*, tours-events/*), because /programs is a JS catalogue whose static HTML is navigation only.
Without search or the browser tier, UBC's programme page is not reachable, and more menu rules would be
whack-a-mole. Runs are held until the owner renews search (a new Tavily key or plan, or Exa credits).
Navigation-only runs spend Actions minutes and measure little.

Claude, 2026-09-25, run 70: Serper live (the owner added the secret). 6/62, precision 6/9. UBC still hit
its clock: search runs after the walker, and the walker read /programs' second-level menu for ~50 s. A
catalogue page where no link carries a programme signal is now not walked at all (js_no_program_list).
Test added, golden demo unchanged.
Owner's deep-research report received (evidence-first engine: schema completeness, an EvidenceDocument
with tables, claim-slot link expansion, goal-aware Playwright, bounded LLM span proposer). Waiting for the
owner's go before starting V2-30A. Note: our Fetcher already follows RFC 9309 (4xx robots = allowed,
5xx or unreachable = disallowed); the brief's wording was imprecise, not the code.

Claude, 2026-09-25, V2-30A (schema completeness; the owner said "делай как лучше" to the deep-research plan):
- The representability ceiling rose from 34 to 49 of 62 (28 without bindings).
- New claim types: intake_term, program_faculty, admission_route, credential_requirement,
  subject_requirement, other_language_minimum, english_evidence_minimum, scholarship_bond,
  document_by_completion. scholarship_offer_required is now mapped.
- Structured keys are built only from slug-valued fields the claim names; a claim missing a field stays
  unmapped. No extractor emits these types yet: this sets the ceiling, not recall.
- The 13 facts left need identity bindings, one owner decision each: Groningen secondary_diploma,
  translation, course_descriptions; Toronto supplemental_application; HKU entrance scholarship; NTU
  Nanyang essay/referee.
Golden demo unchanged.

Claude, 2026-09-25: the owner's adversarial review found that no production adapter passed the verifier its
context (page_text, page_type, allowed_domains). ClaimBuilder runs only the checks it has context for, so
the verbatim and official-domain checks were silently skipped for every claim. Only value ranges ran.
- Requirements, costs, scholarships and documents now pass page_text and allowed_domains; government passes
  page_text. Fixture pages pass no domains, because they are official by construction
  (verification_domains).
- Requirements also passes page_type. On the catalogue-listing existence path (the T29 contract) the
  page-type check is lifted explicitly; the verbatim and domain checks still apply there.
- The demo shows zero rejections and the golden demo is byte-identical.
- Run 72 checks live rejections.
The review's other points agree with the deep-research report (DocumentIR, tables, a source graph instead
of two targets, a content-deficit browser trigger instead of <400 chars, verifier reject telemetry). Its
RFC 9309 point is already met on this branch.

Claude, 2026-09-25: Jev (TypeSafe) behind a decision seam, shadow only (analysis/v2/07, Experiment 2; the
owner's Jev report).
- app/adapters/decisions: the DecisionModel protocol (Noul/Choice), a fake, and TypeSafe pinned to
  jev-1.13.0. It fails closed to the heuristics.
- link_ranker reorders only link ids the code gave it: it cannot invent a URL or delete a lead.
- The benchmark prints "jev shadow: gold programme rank heuristic=X model=Y" per case. Nothing the run reads
  changes.
- Config: UNIMATCH_DECISION_PROVIDER / UNIMATCH_TYPESAFE_API_KEY, environment only.
- This adds a new egress (the owner supplied the key). The state carries field, degree and public links,
  no applicant data.
- Pending: the owner adds the UNIMATCH_TYPESAFE_API_KEY repo secret. The key pasted in chat is not in the
  repo and should be rotated after testing.

Owner, 2026-09-23: robots.txt may be bypassed **only** when almost no other route remains. Not used;
order is: other allowed pages / hosts → official registries → honest UNKNOWN with the official link.

## 4. Half-done / uncommitted at the moment of writing

### Prompt C recovery audit — gpt-6-astra, 2026-09-06 10:54 UTC

At `fix/shortlist-columns@d6e59d5`, before this session changed anything, `git status`, `git diff`,
and `git diff --cached` were all empty. Therefore the current recovery set contained **zero files**
to classify as finished, half-finished, or junk; no `wip:` checkpoint and no stash were warranted.
After `git fetch --all --prune`, `origin/main` advanced from `2be6b55` to `85352b5` through PRs #4/#5.
The resulting PR conflict was only this shared handoff file. It is being resolved with a normal merge
(no rebase/force), preserving both histories; the other staged paths are the exact `origin/main`
merge input, not abandoned cut-off work.

### Historical `[0.8]` recovery audit

Audit started **2026-09-05 18:31:27 UTC**. Read `git status --short --untracked-files=all`,
`git ls-files --others --exclude-standard`, `git diff -- docs/screenshots`, and `git diff --cached`.
The index is empty. All 36 screenshot paths have binary differences; no screenshot is staged.
Untracked files do not appear in ordinary `git diff`: their actual text was inspected and template/
duplicate hashes compared. At audit start: **44 tracked modifications = 36 screenshots + 8 frontend;
30 untracked files outside independent worktrees = 22 workflow/source files + 8 docs/v2 copies**.
The frontend audit agent owns the detailed review of all eight frontend diffs; its verdicts are pending.
No path is classified as junk. "Coherent source" means preservable source material, not approved
requirements, validated experiments, or accepted implementation.

### Frontend [0.8], per file — verdict from `git diff` (claude-opus-5, 2026-09-06)

Read every diff. All eight are one coherent change: the shortlist reads the v2 ranking instead of the
v1 sum. Typecheck, lint and the production build are green on this tree; one unit test is red and is
named below. **Finished code** = compiles, is used, and its behaviour is covered.

| Path | Verdict | What it is |
|---|---|---|
| `frontend/src/types.ts` | finished | `Bucket`, `PriorityGroup`, `AxisScore`, `RankingV2`, `RerankIn`, `BalancedShortlist`; `ProgramResult.ranking` / `catalog_attributes` / `catalog_attributes_source`, plus `size_fit` / `campus_fit` which the backend always sent and TS never declared. |
| `frontend/src/api/client.ts` | finished | `api.rerank(runId, body)` and `api.shortlist(runId)` over the [0.6] endpoints. |
| `frontend/src/lib/format.ts` | finished | `bucketTone`, `FIT_DISCLAIMER`, `ratio()`, `percent()`, bucket meanings. No bucket entered `STATUS_LABEL`: `humanize()` already renders them and the vocabulary test requires a real shortening. |
| `frontend/src/lib/store.tsx` | finished | `rerank()` and a `shortlist` that follows the rows through one effect, so no call site has to remember to refresh it. |
| `frontend/src/screens/ShortlistScreen.tsx` | finished | Match / Confirmed / Bucket columns, default sort `key` with an id tie-break, the balanced-shortlist panel with its notes, and OUT_OF_BUDGET / NEEDS_CLARIFICATION / EXCLUDED as collapsed sections under the ranked table. The large diff is one table extracted into `renderTable()` and reused by all four places. |
| `frontend/src/screens/PreferencesScreen.tsx` | finished | "What matters more?" — six ranked cards with up/down buttons, `weights_override` in the advanced spoiler, and "Recompute the shortlist" calling `rerank`. |
| `frontend/src/components/ResultDetail.tsx` | finished | `Axes` panel: per-axis value, weight, reason and state; knock-out reasons; falls back to the v1 breakdown when a row has no `ranking`. |
| `frontend/src/screens/ShortlistScreen.test.tsx` | **half-finished — one red test** | Four new cases. `shows the match, what is confirmed, and the bucket` fails: `getByText('Plausible')` matches twice, because `PLAUSIBLE_FIT` and the `PLAUSIBLE` bucket both render as "Plausible". The assertion is ambiguous; the component is not wrong. Fix by scoping the query to the `[data-label="Bucket"]` cell. |

No junk. Nothing stashed. The screenshots and the `docs/v2` duplicates stay out of the snapshot, exactly
as the previous inventory ruled.

### Workflow and source bundle — intended recovery snapshot

| Path | Verdict | Reason / treatment |
|---|---|---|
| `.github/PULL_REQUEST_TEMPLATE.md` | Finished/coherent source document or source artifact | Relay review checklist; matches supplied template. Include in explicit snapshot allowlist. |
| `AGENTS.md` | Finished/coherent source document or source artifact | Root relay rules; matches analysis/agents/AGENTS.md. Include in explicit snapshot allowlist. |
| `CLAUDE.md` | Finished/coherent source document or source artifact | Claude-specific relay instructions; matches template. Include in explicit snapshot allowlist. |
| `analysis/AI_TASK_BRIEF.md` | Finished/coherent source document or source artifact | Canonical task brief and fixed decisions; inherited I4/T3 conflict remains (§7). Include in explicit snapshot allowlist. |
| `analysis/ANALYSIS.md` | Finished/coherent source document or source artifact | Historical v1 algorithm audit; reported counts are historical, not current gates. Include in explicit snapshot allowlist. |
| `analysis/DEPLOYMENT_SECURITY_LEGAL.md` | Finished/coherent source document or source artifact | Source planning memorandum; preserve as supplied, no legal/deployment validation claimed. Include in explicit snapshot allowlist. |
| `analysis/DESIGN_agentic_search.md` | Finished/coherent source document or source artifact | Agent research architecture source and rationale. Include in explicit snapshot allowlist. |
| `analysis/README.md` | Finished/coherent source document or source artifact | Index connecting the analysis source bundle. Include in explicit snapshot allowlist. |
| `analysis/SPEC_matching_v2.md` | Finished/coherent source document or source artifact | Canonical detailed spec; same unresolved literal T3 conflict (§7). Include in explicit snapshot allowlist. |
| `analysis/TWO_AGENT_WORKFLOW.md` | Finished/coherent source document or source artifact | Relay design memorandum; includes historical checkout observations. Include in explicit snapshot allowlist. |
| `analysis/agents/AGENTS.md` | Finished/coherent source document or source artifact | Distributed root-rule template; byte-identical to root at audit start. Include in explicit snapshot allowlist. |
| `analysis/agents/CLAUDE.md` | Finished/coherent source document or source artifact | Distributed Claude template; byte-identical to root. Include in explicit snapshot allowlist. |
| `analysis/agents/HANDOFF.md` | Finished/coherent source document or source artifact | Unmodified initial baton template; coherent template, stale as live state. Include in explicit snapshot allowlist. |
| `analysis/agents/KICKOFF_PROMPTS.md` | Finished/coherent source document or source artifact | Supplied prompts A–D; C governs this recovery. Include in explicit snapshot allowlist. |
| `analysis/agents/PULL_REQUEST_TEMPLATE.md` | Finished/coherent source document or source artifact | Distributed PR template; byte-identical to installed copy. Include in explicit snapshot allowlist. |
| `analysis/agents/handoff_check.py` | Finished/coherent source document or source artifact | Distributed diagnostic script; byte-identical to installed copy, inspected, not edited. Include in explicit snapshot allowlist. |
| `analysis/reference/ranking_v2.py` | Finished/coherent source document or source artifact | Executable formula reference; arithmetic also exhibits the T3 contradiction; not a fresh gate result. Include in explicit snapshot allowlist. |
| `analysis/scripts/01_discovery_sensitivity.py` | Finished/coherent source document or source artifact | Historical v1 discovery/rescoring experiment; source preserved, not executed. Include in explicit snapshot allowlist. |
| `analysis/scripts/02_score_components.py` | Finished/coherent source document or source artifact | Historical v1 score decomposition experiment; source preserved, not executed. Include in explicit snapshot allowlist. |
| `analysis/scripts/03_climate_sensitivity.py` | Finished/coherent source document or source artifact | Historical v1 climate experiment; not yet a v2 acceptance check. Include in explicit snapshot allowlist. |
| `docs/process/HANDOFF.md` | Finished/coherent source document or source artifact | Live baton was identical to initial template; reconciled by this recovery audit. Include in explicit snapshot allowlist. |
| `scripts/handoff_check.py` | Finished/coherent source document or source artifact | Installed read-only relay diagnostic; UTF-8 runtime invocation required locally (§9). Include in explicit snapshot allowlist. |

### Frontend — provisional until the dedicated audit returns

| Path | Verdict | Scope / next evidence |
|---|---|---|
| `frontend/src/api/client.ts` | Half-finished frontend [0.8] | API client additions for rerank and balanced shortlist. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/components/ResultDetail.tsx` | Half-finished frontend [0.8] | Ranking axis presentation. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/lib/format.ts` | Half-finished frontend [0.8] | Fit/coverage/bucket display helpers. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/lib/store.tsx` | Half-finished frontend [0.8] | Ranking/shortlist state and actions. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/screens/PreferencesScreen.tsx` | Half-finished frontend [0.8] | Priority order, advanced weights and rerank controls. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/screens/ShortlistScreen.test.tsx` | Half-finished frontend [0.8] | Updated shortlist unit expectations; acceptance coverage pending audit. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/screens/ShortlistScreen.tsx` | Half-finished frontend [0.8] | Ranking columns, buckets and balanced shortlist. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/types.ts` | Half-finished frontend [0.8] | Ranking and API payload types. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |

### Duplicate source bundle — preserve outside the recovery snapshot

| Path | Verdict | Reason / treatment |
|---|---|---|
| `docs/v2/AI_TASK_BRIEF.md` | Finished/coherent source copy | Diff against analysis copy changes only reference launch path from ../analysis/ to ../../analysis/; preserve this difference, do not silently normalize. Preserve untracked outside snapshot. |
| `docs/v2/ANALYSIS.md` | Finished/coherent source copy | Byte-identical to analysis/ANALYSIS.md. Preserve untracked outside snapshot. |
| `docs/v2/DESIGN_agentic_search.md` | Finished/coherent source copy | Byte-identical to analysis/DESIGN_agentic_search.md. Preserve untracked outside snapshot. |
| `docs/v2/SPEC_matching_v2.md` | Finished/coherent source copy | Byte-identical to analysis/SPEC_matching_v2.md. Preserve untracked outside snapshot. |
| `docs/v2/reference/ranking_v2.py` | Finished/coherent source copy | Byte-identical to analysis/reference/ranking_v2.py. Preserve untracked outside snapshot. |
| `docs/v2/scripts/01_discovery_sensitivity.py` | Finished/coherent source copy | Byte-identical to analysis/scripts/01_discovery_sensitivity.py. Preserve untracked outside snapshot. |
| `docs/v2/scripts/02_score_components.py` | Finished/coherent source copy | Byte-identical to analysis/scripts/02_score_components.py. Preserve untracked outside snapshot. |
| `docs/v2/scripts/03_climate_sensitivity.py` | Finished/coherent source copy | Byte-identical to analysis/scripts/03_climate_sensitivity.py. Preserve untracked outside snapshot. |

`backend/app/schemas/profile.py:225` mentions `docs/v2/AI_TASK_BRIEF.md` in a comment.
This is a documentary reference, not a runtime dependency; the canonical `analysis/AI_TASK_BRIEF.md`
is included. No duplicate is required to execute [0.8]. If a later concrete reference dependency
requires a duplicate, add that exact path to §5 before staging it; do not bulk-add `docs/v2`.

### Pre-existing screenshots — each preserved outside the recovery snapshot

The coordinating recovery task reports that these modifications existed before initial [0.1].
Their presence cannot be attributed to the frontend cut-off. Binary diff inspection establishes
changed assets, not a reason to discard them; no visual acceptance review is claimed.

| Path | Verdict / treatment |
|---|---|
| `docs/screenshots/01-profile.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/02-preferences.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/03-progress-running.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/04-progress-complete.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/05-shortlist.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/06-university-detail-funding.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/07-university-detail-requirements.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/08-funding-comparison.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/09-sources-conflicts.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/10-approved.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/11-documents.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/12-export.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/01-profile.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/02-preferences.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/03-progress-running.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/04-progress-complete.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/05-shortlist.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/06-university-detail-funding.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/07-university-detail-requirements.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/08-funding-comparison.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/09-sources-conflicts.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/10-approved.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/11-documents.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/12-export.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-1024.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-1440.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-320.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-768.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/theme-dark.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/theme-light.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-1024.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-1440.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-320.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-768.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/theme-dark.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/theme-light.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |

`.claude/worktrees/payments-phase-1/` and `.claude/worktrees/social-module/` are independent user
repositories, reported as directory entries by parent Git. Their contents are excluded from this
inventory; do not traverse, stage, stash, reset or otherwise modify them. They are not junk.

This writer changes only `docs/process/HANDOFF.md`; no optional long audit file was needed.
No branch, commit, push or stash has been performed by this writer.

## 5. NEXT STEP — exact and executable

Write-ahead (claude-opus-5, 2026-09-23, V2-32): **starting per-population tuition.** `extract_costs`
takes the first tuition figure on a page, and many European fee pages list a statutory EU/EEA fee
beside a much higher non-EU/EEA institutional fee, so an international applicant can be shown the
lower one. Same shape as the deadline fix (`7c25df2`): a tuition table naming at least two populations
yields one claim per row (`subject_key` and scope population). `web_costs` builds tuition `Money` with
`amount` = the highest row (a cost is never understated) and `range_low`/`range_high` = the rows, which
`domain/costs` already sums and the funding gap already reports as a range. It records one note naming
every row. The population is still never inferred. Files: `extraction.py`, `cost/web_costs.py`, a new
test file; golden demo re-proved.

Write-ahead (claude-opus-5, 2026-09-20, V2-10): **starting V2-10 — the search provider interface**,
per `analysis/v2/02_EXECUTION_PLAN.md` (Phase 1) and `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §1.
Its whole point is "no provider lock-in", so this task is a seam, not a retrieval feature: nothing is
wired into discovery here, because fusion is V2-13 and query generation is V2-11.

Scope, exactly:
- `backend/app/adapters/search/base.py` — frozen `SearchResult` (url, title, snippet, provider, rank,
  retrieved_at) and `SearchResponse`, a `SearchProvider` Protocol with the spec's
  `async def search(*, query, domains=(), max_results=10)`, and the error types.
- `backend/app/adapters/search/fake.py` — `FakeSearchProvider`, offline and deterministic, built from
  an explicit caller-supplied corpus. It never invents a result and stamps `provider="fake"` on every
  one, so a fake row can never be mistaken for a real retrieval.
- `backend/app/adapters/search/__init__.py` — `get_search_provider()`, the only way to obtain one.
- `backend/app/config.py` — `search_provider` defaulting to `"none"`, validated like payments is:
  an unknown name is refused at startup, and `"fake"` is refused in production.
- `backend/tests/test_search_provider.py` — new.

Three rules from `12_AGENT_DO_AND_DONT.md` are enforced structurally rather than by comment, and each
gets a test: search results are **discovery hints, never evidence**; `app.domain` may not import the
search package (the seam holds only if the ban is checked); and with no provider configured
`get_search_provider()` **raises** rather than returning something empty, because a silent "no results"
is exactly the hidden fallback that file forbids. The signature also takes a `query: str` and no
profile, so applicant PII cannot structurally reach a provider — V2-11 will build the query itself.

Write-ahead (claude-opus-5, 2026-09-20, V2-11): **starting V2-11 — the query generator**, per
`analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §2 and §4. The task is "no unnecessary applicant PII", so
the deliverable is a narrow type plus the proof that nothing else can get through it.

Scope, exactly, all in `backend/app/adapters/search/intent.py` and `tests/test_discovery_intent.py`:
- `DiscoveryIntent` — frozen, and it holds only the dimensions §2 permits: institution, domain, degree,
  field, optional intake, and an optional generic `international` / country marker used only for a
  country-specific public requirements page. There is no field for anything else, so a caller cannot
  smuggle data by populating one.
- Validation that rejects a value which *looks like* applicant data even in an allowed field — an `@`,
  a run of digits long enough to be a score or a phone number, a currency marker. The V2-10 signature
  stops a profile object reaching a vendor; this stops somebody formatting one into a string, which is
  the failure the structural guarantee cannot catch.
- `DiscoveryIntent.from_profile(...)` as the single sanctioned conversion, copying an explicit allowlist
  and dropping everything else, so callers do not each invent their own.
- `queries_for(intent, *, budget)` rendering the §4 families (`site:<domain> "<field>" "<degree>"`,
  programmes, courses, undergraduate, admissions, scholarships, country requirements) into a **bounded**
  list — §4 says do not explode aliases into unlimited queries — each carrying its family name.
- `redacted_audit_record(...)`, because §2 ends with "log a redacted query audit record".

Tests: one per forbidden item from the spec's list — name, exact scores, GPA, budget, family
contribution, email, phone, transcript content — each feeding a fully populated profile through
`from_profile` and asserting the rendered queries contain none of it. Plus budget enforcement and audit
redaction. No provider is called; V2-11 produces strings, V2-13 consumes them.

Write-ahead (claude-opus-5, 2026-09-21, V2-12): **starting V2-12 — the field and degree ontology**,
per `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §3.

The whole value of this task is one distinction the spec states and this repository has already paid
for twice by hand: **`strong_aliases` are the same thing; `related_not_equivalent` are retrieval
candidates and never automatic matches.** Draft2 refused Data Science as Aalto's computer science on
exactly that ground, and draft7 left Computer Engineering open rather than asserting it. The ontology
must make the wrong call hard to write, not just discouraged — so equivalence and retrieval-expansion
are different functions returning different things, and a related concept can never be returned from
the equivalence one.

Scope:
- `backend/app/adapters/search/ontology.json` — the data, versioned, mirroring the
  `institution_registry.json` precedent. Concepts carry `strong_aliases`, `related_not_equivalent` and
  optional non-English aliases with a language tag, so the multilingual shape exists from day one even
  where only English is populated.
- `backend/app/adapters/search/ontology.py` — loader plus `canonical_field`, `is_equivalent`,
  `retrieval_candidates`, `degree_aliases`, and the ontology version. It lives in adapters, not domain,
  because reading a file is I/O and `app/domain/` does none (AGENTS.md §6).
- `backend/tests/test_ontology.py`.

It is deliberately not wired into `queries_for`: bounded alias expansion is V2-13's decision, and §4
warns against exploding aliases into unlimited queries. Non-English aliases are kept to ones that are
not in doubt; a guessed alias silently matches the wrong programme, which is the same class of error as
a guessed fact.

Write-ahead (claude-opus-5, 2026-09-21, V2-13): **starting V2-13 — hybrid candidate retrieval**, per
`analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §4–§6. This is the task that joins the three previous ones
and the first that can move the **1/10** baseline.

**Finding before coding: §5's prefilter mostly already exists.** `live_discovery.py` already has
`canonical_url` (fragment, tracking params, default port, trailing slash), `registrable_domain` /
`same_institution` (multipart suffixes, so `edu.kz` works), `_URL_EXCLUSIONS` (news, events, jobs,
media), `degree_level_named` and `names_other_degree_level`. Writing a second copy in the search package
would be the per-source duplication `12_AGENT_DO_AND_DONT.md` warns about, and the two would drift.
V2-13 therefore **reuses** them and adds only what is missing: scheme rejection, PDF detection (§9 says
a PDF can be a real handbook, so it is flagged and kept, not dropped), deduplication that keeps the best
rank, and a rejection record per URL so §4's "telemetry" is real.

Scope:
- `backend/app/adapters/search/prefilter.py` — the §5 chain over `SearchResult`s, returning kept
  candidates *and* every rejection with its reason.
- `backend/app/adapters/search/retrieval.py` — a small self-contained BM25 (no new dependency) over
  title + snippet + URL words, a hybrid score combining it with the deterministic signals, and
  `discover_candidates(provider, intent, ...)` running queries → provider → prefilter → rank → top K.
  Every candidate carries the signals that produced its score, because an unexplainable ranking cannot
  be debugged against the benchmark.
- one public predicate added to `live_discovery.py` so the search package does not reach into a private
  name.
- `backend/tests/test_hybrid_retrieval.py`.

Per §6, **only the deterministic layer and BM25 ship here.** Embeddings, a cross-encoder, Jev and an LLM
are left as a documented seam: §6 says not to deploy them all automatically, and each needs its own
benchmark run to justify its cost. Alias expansion stays inside `DEFAULT_QUERY_BUDGET` (§4).

Write-ahead (claude-opus-5, 2026-09-21, V2-14): **V2-14 is "reranker benchmark: current scorer vs
cross-encoder vs optional Jev/LLM". Before building any of that, I measured whether a reranker could
help at all — and it cannot.**

The frozen capture records `ranked_urls`, the real candidate set the current pipeline produced on the
bounded canary. The certified corpus records the correct `programme_urls`. Intersecting them answers
the only question that matters before spending money on a cross-encoder: *is the right page anywhere in
the set a reranker would reorder?*

Measured, canonicalising both sides: **1/10.** Only NTU's correct page appears in its candidate set, and
it is already at **position 1**. Four cases (warsaw, ubc, kaist, and toronto's set of one) retrieved
nothing usable at all.

So the current ranking is already perfect on what it retrieves, the 1/10 recall is **entirely a
retrieval failure**, and no reranker — BM25, cross-encoder, Jev or LLM — can move a single case. Buying
or deploying one now would be measurable waste.

This step therefore delivers the measurement rather than the rerankers: a reproducible
`evaluation/research/ceiling.py` with a CLI, a `RERANKER_CEILING.md` recording the numbers and what
they license, tests, and a §5/§7 redirect of the roadmap. That is what a benchmark is *for* — V2-01
spent seven drafts and a human signature making exactly this kind of answer trustworthy.

Write-ahead (claude-opus-5, 2026-09-21, V2-15): **starting V2-15 — detection of a university's own
public search or catalogue surface**, per `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §7. Chosen
because V2-14 proved the gap is retrieval and this is the only retrieval work that needs **no paid
key**: three cases in the capture retrieved nothing, and several of those sites expose a search their
own visitors use.

Scope — `backend/app/adapters/search/site_search.py` and `tests/test_site_search.py`:
- `SiteSearchSurface` (kind, endpoint, query parameter, provenance, evidence, detected-at) and
  `detect_surfaces(html, base_url, *, network_urls=())` for the §7 families: plain HTML form, JSON
  endpoint, WordPress REST, Drupal views, Algolia, Elastic/OpenSearch, Solr, GraphQL, custom catalogue.
- `search_url(surface, query, page)` that builds a request URL with **bounded pagination**.

§7's rules are enforced, not commented:
- **Passive before active.** A surface seen in a browser network log outranks one inferred from HTML,
  and detection never probes — it reads what is already in front of it.
- **Only the site's own endpoints.** An endpoint on another registrable domain is discarded, reusing
  `same_institution` rather than a second copy.
- **No credential is ever extracted.** Algolia and Elastic put a search key in page JavaScript. Even
  though it is a public search-only key, this records `requires_credentials=True` and stores *nothing*,
  because a key in a repository is a key in a repository. A human decides whether to use those.
- **No authenticated or administrative surface**, whatever it looks like.
- Caps for body size and pagination live as named constants, so the bound is visible rather than
  implicit.

Detection returns candidates. Fetching them stays with `Fetcher`, so robots, rate limits, the PII guard
and SSRF protection are untouched. Fixtures are synthetic and labelled as such — no captured page from
a real university is committed pretending to be one.

Write-ahead (claude-opus-5, 2026-09-21, V2-16): **starting V2-16 — fusion and provenance**, per
`02_EXECUTION_PLAN.md` Phase 1: "merge search/sitemap/registry/site-search results with source
attribution". This is the piece that makes the previous five useful.

The design decision worth recording: **fusion is by rank, not by score.** A BM25 score, a sitemap
position and a registry entry's confidence are not on one scale, and adding or averaging them produces
a number with no meaning that would nonetheless order the list. Reciprocal Rank Fusion uses only each
generator's own ordering, needs no calibration between sources, and degrades sensibly when one
generator is missing — which matters here, because `web_search` is absent until the owner picks a
provider and `site_search` is absent for any site that has no search.

Scope — `backend/app/adapters/search/fusion.py` and `tests/test_fusion.py`:
- `Generator` (registry, manual seed, cache, sitemap, catalogue walker, site search, web search) with an
  explicit weight table: a curated registry entry is better evidence than a web result, and saying so
  in a named constant is better than burying it in an ordering.
- `SourcedCandidate` / `FusedCandidate`, where the fused row keeps **every** generator that found it and
  the rank each gave it. Agreement between independent generators is the most useful signal fusion
  produces and it must survive into the output, not be collapsed into one number.
- `fuse(streams, *, top_k)`, deduplicating on `canonical_url` so the same page from three generators is
  one row with three attributions.

No generator is invented: fusion consumes what already exists and what V2-13/V2-15 produce. Nothing is
wired into `runner.py` in this step.

Write-ahead (claude-opus-5, 2026-09-21, V2-17): **starting V2-17 — programme identity verification**,
per `04_PHASE_1_DISCOVERY_ENGINE.md` §10. Chosen because it attacks the corpus's *other* headline
failure — `wrong_scope_claim_rate` **5/5** against `primary_source_rate` **13/13**, i.e. the pipeline
reads official pages correctly and then applies them to the wrong population, year or programme — and
because it needs no provider key and no live authorisation.

§10's instruction is blunt: **"Do not collapse identity into one fuzzy score."** Six dimensions, each
`YES` / `NO` / `UNKNOWN`: does the page establish a programme exists, is it the right university, the
right degree level, does the field match, is the programme active, is the requested intake supported.

The design decision this step turns on: **identity and scope are separated, and `UNKNOWN` never
becomes a match.**

- The four *identity* dimensions (exists, university, degree, field) decide whether this is the right
  programme at all.
- The two *scope* dimensions (active, intake) decide whether a claim read from that page may be applied
  to the requested intake. They are exactly where `wrong_scope_claim_rate` 5/5 comes from.
- `applies_to()` returns a `Verdict`, **not a bool**. A bool would force `UNKNOWN` into `True` or
  `False`, and both are wrong: an unverified dimension is not a failed one (brief invariant I4) and
  must not silently become a pass either. This is the same rule §7 already resolved for ranking, applied
  to discovery.

Scope — `backend/app/domain/programme_identity.py` (the rule, pure, no I/O, as §10 requires it to live
in domain code) and `backend/app/adapters/search/identity.py` (reading the dimensions from what a
candidate actually shows), plus `tests/test_programme_identity.py`. A dimension the page does not state
is `UNKNOWN`; nothing is inferred to fill a gap.

Write-ahead (claude-opus-5, 2026-09-21, V2-10b): **the owner picked Exa and registered.** Writing the
adapter behind the V2-10 seam.

**A rule conflict is being raised, not resolved unilaterally.** `AGENTS.md` §6, listed as not negotiable
by either agent: *"Do not weaken `Fetcher` (robots, rate limit, PII guard); no network outside it."*
A search provider is network outside `Fetcher`. The V2 roadmap the owner approved requires one
(`04_PHASE_1_DISCOVERY_ENGINE.md` §1), so the two documents disagree. Per §6 the conflict goes to §7
and the owner decides; it is **not** silently settled here. The adapter is therefore written but
**off by default** — `UNIMATCH_SEARCH_PROVIDER` stays `none`, and nothing reaches the network until the
owner sets it. Why `Fetcher` is the wrong instrument for this one call, and what replaces each of its
three guarantees, is argued in §7.

Scope:
- `backend/app/adapters/search/exa.py` — `ExaSearchProvider` satisfying the V2-10 protocol. POST
  `/search` with `type`, `numResults`, `includeDomains`, `contents.highlights`; maps the response to
  `SearchResult` / `SearchResponse`; maps every transport and HTTP failure to `SearchUnavailable` so a
  degraded run stays visible as degraded rather than as a run that found less.
- The host is checked through the existing `network_policy` before the call, the response body is
  capped, redirects are not followed, and there are no retries — a provider quota error must not be
  multiplied by three.
- `config.py`: `exa_api_key: SecretStr` like every other credential, `"exa"` added to
  `KNOWN_SEARCH_PROVIDERS`, and `_validate_search` refusing to start with `exa` selected and no key.
- Tests drive a mocked `httpx` transport. `AGENTS.md` §6: tests never call the internet.

The key is never read by this session, never written to a file, and never logged — only
`EXA_API_KEY` / `UNIMATCH_EXA_API_KEY` at runtime.

V2-22 is done: requirement claims now record what their page stated about who it covers, and the demo
proves it end to end (128 of 173 claims scoped, 45 honestly empty).

**NEXT, exact and executable.**

**Re-run the capture** (`benchmark-capture`, branch `claude/greeting-16wj2z`) once V2-29 is on the
branch: two of the five `programme (differs)` mismatches — the open-day page and the preparing-for
page — should stop being claimed at all, which is visible in the diagnostic without any metric being
redefined. That is the honest test of this fix, and it needs a human to press the button (§7).

**NEXT, exact and executable.**

Write-ahead (claude-opus-5, 2026-09-22, **Phase 3 §8**): **an index page is discovery, so read it as
one instead of throwing it away.** §8 says "scholarship index is discovery, not award proof" and lists
several candidate generators; today `WebScholarshipAdapter.find` uses exactly one — the university's
scholarship index — and every link off it that the classifier calls `scholarship_index` (an
international-funding page, a faculty funding page) is **fetched, classified, discarded with an error,
and its awards never seen**. The page is already paid for; the awards on it are simply dropped.

Scope, all in `app/adapters/scholarship/web_scholarships.py` plus tests:
- walk a small queue of index pages instead of one, depth 1, at most three indexes and the existing cap
  of twelve award pages, with one global dedupe set so no page is fetched twice;
- a followed page classified `scholarship_index` has its own award links harvested (it cost nothing
  extra — it is the page we already fetched and dropped);
- when the scholarship index is unknown or links no award at all, fall back to the programme page **as
  an index only**, never as an award, because that is the one generator §8 names that is already in
  hand;
- `_award_links` stops applying its own cap of twelve so the caller can cap the total; the cap itself
  does not change.

Deliberately **not** done: web search restricted to official domains, and government funding sources
(§8's remaining generators). Both spend live fetches, and 5 of 10 benchmark cases already run out of
budget — measuring that trade needs the capture number, not a guess. Nothing here spends a fetch the
current code did not already spend, except the fallback, which only runs where today's code produces
nothing at all.

Write-ahead (claude-opus-5, 2026-09-22, **Phase 3 §9**): **a required document says who it is for.**
§9 ends with "store source and scope for each required document". `DocumentItem` stores the source
(`source_url`, `claim_ids`) and **no scope** — so a document list read off a general admissions page and
one read off the programme's own page are indistinguishable on the record, which is the same failure
Phase 2 fixed for requirements. The adapter already computes the page's scope (it passes one to
`ClaimBuilder`); the checklist simply drops it.

Scope, exactly:
- `DocumentItem.scope: ClaimScope | None`, omitted from the payload when None, exactly as `Claim.scope`
  is, so no stored checklist changes shape;
- `web_documents` passes the scope it already read to every item it builds from that page;
- tests: a document from a programme page carries the programme, one from a general admissions page
  does not invent one, and the field survives a round trip.

Not in this step: acting on it (refusing a document whose page is about another programme) and showing
it. Recording first, acting second, was the order that worked for requirements, and it is the order the
phase guide itself uses.

Write-ahead (claude-opus-5, 2026-09-22, **Phase 3 §9, the ordering half**): **the checklist's own
order can tell the applicant to do the impossible.** §9 says a document may depend on another action and
names three: offer letter before scholarship submission, translation before notarization, credential
evaluation before final review. `depends_on` has been populated since `486a6ff` — and `_order_steps`
sorts by lead time alone and never reads it. So the numbered plan the applicant is shown can put
"notarize the translation" above "get the translation", which is worse than no order, because a
numbered list is an instruction.

Scope, in `app/adapters/documents/web_documents.py` plus tests:
- `_order_steps` becomes a topological order with **longest lead time first as the tiebreak**, so the
  existing behaviour survives wherever nothing depends on anything — which is most of the demo;
- a dependency naming a document that is not on the list is ignored rather than dropping the step: the
  step is real, the reference is not;
- a cycle is reported, never silently reordered — the steps in it are listed last with the cycle named,
  because inventing an order between two documents that each wait for the other is a guess about the
  applicant's real deadline risk.

Not in this step: turning `depends_on` into a blocking rule in the assessment. Order is advice; a
blocked application is a verdict, and it needs the same "silence is not agreement" treatment
requirements got.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-5**): **make the capture say why a case produced
nothing.** Nine of ten cases in run 35697105238 filed zero claims and the capture cannot say why for a
single one of them: `Observation` records what was predicted and never what was read and rejected. The
runner already files a per-page outcome for every page it touches — fetch-failed / unreadable /
classifier-rejected / no-pattern-match / fetched-ok — and `scripts/canary_discovery.py::page_outcomes`
already parses them back out. The capture throws them away, so the one question that matters ("Toronto
found three programme URLs, read 23 pages and filed nothing — which of those five things happened?")
cannot be answered without re-running with the network, which nobody here has.

Scope:
- `evaluation/research/schema.py` — `PageOutcome` (category, url, page_type, detail, characters) and
  `Observation.page_outcomes`, defaulted so the frozen certified capture still validates unchanged;
- `evaluation/research/live.py` — fill it from the run in the same `finally` that already reads the
  claim rows, so a case that dies on its budget still records what it managed to read;
- a test that the frozen `capture.json` still loads, because a schema change that breaks the certified
  corpus is worse than no diagnostic.

This is EXTRA-1's pattern, and EXTRA-1 is the only thing this session did that changed what I believed:
measure why, not what. Nothing about ranking, extraction or budgets should be touched until this run
says which of the five outcomes is dominant — including my own §8 index walk, whose fetch cost is now a
real risk with seven of ten cases out of budget.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-6**): **the programme filter runs before the two steps
that find most programmes.** Chasing Toronto's zero (three programme URLs, 23 pages read, no claims)
led to `live_discovery.discover`'s own ordering. Step 4 confirms programme candidates by reading them —
the filter whose comment says it exists because live runs offered "bachelor-open-day", "campus-tour"
and a student newsletter as programme pages. Steps 5 and 6 are the catalogue walk and web search, and
**they run after it.** So every programme page Phase 1 contributes — the contribution that moved
`programme_page_recall` from 1/10 to 4/10 — reaches the candidate **unconfirmed**. Toronto is the
clearest case: its `ranked_urls` at confirmation time were empty, meaning the filter ran on nothing,
and the three programme URLs it finished with arrived afterwards, unchecked. EXTRA-3 patched this
class of error downstream in extraction; this is where it starts.

Scope, in `app/adapters/discovery/live_discovery.py` plus tests:
- a second confirmation pass after step 6, over **only the pages added since the first one**, so a page
  already confirmed is not re-read and the fetch cost is one read per genuinely new page — a page the
  requirements adapter was going to read anyway;
- `_confirm_programs` keeps its exact signature, because the benchmark capture patches it by name to
  record `ranked_urls`, and a diagnostic that stops recording is worse than the bug;
- tests: a search-supplied open-day page is refused, a search-supplied real programme page survives,
  and an unreadable site still keeps its leads rather than losing them silently.

Risk, stated up front: this can only *reduce* the programme list, so `programme_page_recall` may fall
if the classifier refuses a page the label calls correct. That is the honest direction — a wrong
programme page produces wrong requirements — but it is a number to watch, not to assume.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-7**): **one regex produced a third of the run's
claims, and all of them were wrong.** Reading NTU's twelve claims — the only real claims in run
35697105238 — four are `scholarship_exists` with the subject **"FAQs on scholarships"**, stamped
`CONFLICTING`, two per programme. The page is NTU's scholarship FAQ. The classifier has a
`SCHOLARSHIP_FAQ` type precisely for it, and `_FAQ` is `\bf\.?a\.?q\.?\b`, which matches "FAQ" and
**not "FAQs"**: there is no word boundary between `q` and `s`. So the FAQ page classified as
`scholarship_award`, the award name became "FAQs on scholarships", and its prose ("the scholarship will
be withdrawn if you change your degree programme") produced a second claim saying the award does not
exist. Two claims from one page contradicting each other is exactly what `CONFLICTING` is for; both are
rubbish.

Reproduced offline before touching anything: `classify_page` on that title returns
`scholarship_award 0.85, named award 'FAQs on scholarships'`.

Scope: the plural in `_FAQ`, a test per form (FAQ, FAQs, F.A.Q., "frequently asked question(s)"), and a
test that an FAQ page never becomes an award. This is the **third** plural bug in this repository —
`waivers` and `scholarships` were the others — so the test names the pattern, not just the case.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-8**): **funding is where the budget dies, and it reads
the same pages twice.** Every one of the four budget-killed cases in run 35697105238 — `delft`,
`groningen`, `hku`, `ubc` — died in the **same place**: `BENCHMARK_PAGE_BUDGET_EXHAUSTED` raised inside
`WebScholarshipAdapter.find`, from the funding stage. Their logs are four copies of one traceback.

And the adapter reads the same pages once per programme. `_stage_funding` loops over rows (a row is a
programme), constructs one adapter, and calls `find(cand, prog)` per row — so a university with two
programmes reads its scholarship index and every award page **twice**. NTU's claims are the proof: six
claims, then the same six again, same URLs, same subjects, differing only in `program`. Funding can
therefore spend up to 2 × (3 indexes + 12 awards) reads of a 60-read budget before assessment begins —
and §8's index walk, which I shipped this morning, made that ceiling higher.

Scope, in `app/adapters/scholarship/web_scholarships.py` plus tests:
- the adapter memoises fetched pages for its own lifetime (one run), so the second programme re-parses
  rather than re-reads;
- claims stay **per programme** — the memo holds pages, not claims, because a claim carries the
  programme it was built for and reusing one would mislabel it;
- `pages_checked` counts real reads, so the number the applicant sees stops double-counting.

Honest scope limit: `Fetcher` already caches the bytes, so in production this saves parsing and a
cache lookup, not network traffic. What it actually buys is the benchmark budget — which is the thing
that killed four of ten cases — and an honest `pages_checked`.

Write-ahead (claude-opus-5, 2026-09-22, **plan V2-33**): **an award restricted to a faculty or a
named programme says nothing today.** §6 lists `faculty_restrictions` and `programme_restrictions` as
separate decisions a scholarship must decompose into. `Scholarship.program_restrictions` exists as a
**declared field nothing ever sets** — the fourth of that kind found on this branch — and there is no
faculty field at all. `SCHOLARSHIP_PROGRAM_RESTRICTION` is not the gap it looks like: it carries
*degree* applicability, as NTU's `{"degree": "bachelor", "applies": "yes"}` shows.

So an award page saying "open to students in the Faculty of Engineering" or "for students of the BSc
Data Science programme" is recorded as applying to everyone, and shown to an applicant it excludes.

Scope:
- `Scholarship.faculty_restrictions`, beside the `program_restrictions` that already exists;
- the adapter reads both from eligibility prose, in the same evidence-only style as the citizenship
  reader: the page's own sentence or nothing;
- `_scholarship_eligibility` gains a check that is **PENDING, never a refusal and never a pass**. The
  applicant's faculty is not in the profile at all, and deciding a programme restriction by comparing
  names is precisely the trap NTU taught this session — "Bachelor of Computing (Hons) in Computer
  Science" against "Computer Science". So a restriction the page states becomes an open question that
  propagates `applicant_eligible` to `unknown` and reaches the applicant as something to ask, rather
  than a verdict this pipeline cannot honestly reach.

Not in this step: matching the restriction against the applicant's programme. That needs the programme
identity decision parked in §7, and guessing it is worse than asking.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-9**): **the extractor is handed a page with the
requirements deleted from it.** An external deep-research review proposed a hypothesis I had not
listed — representation loss before extraction — and it is correct. Verified in code and then
demonstrated:

    page: <main> with <form> holding the IELTS line, <aside class="key-facts"> holding the deadline,
          <div class="requirements-banner"> holding the GPA, plus one marketing sentence
    readable_text() returns: "BSc Computer Science\n\nThe programme lasts three years."

`readable_text()` — used by **every** extractor — routes through `page_classifier.main_content()`, which
decomposes `form`, decomposes `aside`, and decomposes **any element whose class or id matches**
`nav|menu|breadcrumb|header|footer|sidebar|skip|cookie|banner|social|share|toolbar`, including inside an
already-selected `<main>`. The GPA above died because its container's class contained "banner".

**Root cause, stated more precisely than the review did:** `main_content()` has exactly two callers and
they want opposite things. `classify_page` needs site chrome gone, or it counts the site's links instead
of the page's — one award page linked to six others from its menu and was classified as an index, which
is why the stripping was written. `readable_text` needs the page's **content**, and a requirement is
quite often inside a `form` or an `aside`. One abstraction, two incompatible jobs; the deletion was
right for the caller it was written for and destructive for the one that inherited it.

Scope:
- a separate reading variant for extraction: keep `form` and `aside`, keep the `<main>` scoping, drop
  only what is never content (`script`, `style`, `noscript`, `svg`, `iframe`), drop true chrome tags
  only when large (the rule `html_to_text` already uses), and narrow the class/id hint to tokens that
  cannot plausibly name content;
- `classify_page` keeps `main_content` exactly as it is — its behaviour must not move, and the tests
  that pin classification are the proof;
- the demo golden will move, and this time it may move by **gaining claims**, which is the intended
  effect and must be shown claim by claim rather than waved through as "additive".

This is the first change on this branch aimed at `claim_recall 0/62` itself rather than at the
machinery around it.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-10**): **separate "never found the page" from "could
not read the page", in one run.** `claim_recall 0/62` has never distinguished the two, and every fix so
far has been aimed at a guess about which it is. The certified corpus already contains the oracle: **73
labels carry an exact source URL and a verbatim excerpt**, human-reviewed.

`evaluation/research/oracle.py` fetches each certified source URL **directly, with no discovery at
all**, runs the real classifier and the real extractors on it, and files one verdict per certified
fact:

| verdict | meaning |
|---|---|
| `recovered` | the extractor produced this key with this value |
| `value_missing` | the page's readable text contains the certified excerpt, and no claim came out |
| `text_missing` | the certified excerpt is **not in** the readable text at all |
| `fetch_failed` | the URL could not be read |

That splits the causes cleanly, because fetching the labelled URL removes discovery from the question
by construction: `text_missing` is representation loss or dynamic content (EXTRA-9's territory, and
H1), `value_missing` is the patterns (H2), and a high `recovered` count with a still-zero live
`claim_recall` would prove the problem is navigation (H3).

It speaks the scorer's own language: claims are normalised through `mapping.normalize_claim`, the same
function the metric uses, so an oracle "recovered" means the same thing a benchmark hit means.

Constraints kept: evaluation-only (production never reads ground truth); live by explicit opt-in, like
the search probe; offline tests drive it through `fixture://` pages so CI needs no network.

First use, deliberately: measure what EXTRA-9 actually bought. It is the first change aimed at the zero
itself, and "the demo golden did not move" is not evidence either way — the demo cannot exhibit the
failure.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-11**): **test the extractors against the certified
corpus' own wording.** The oracle needs a live run; this needs none. Every certified excerpt is a
sentence a human confirmed appears on an official page, so an extractor that cannot read the excerpt
certainly cannot read the page. Three misses found by running them:

| source | the corpus' own words | produced |
|---|---|---|
| UBC | "no **part** less than 6.0" | overall only — the per-section minimum is dropped |
| NTU | "Overall 6, Writing 6,speaking 6" | overall only — both named sections dropped |
| NTU | "1250 for redesigned SAT" | **nothing** |

Two are fixable now and one is not:
- `_IELTS_SUB` knows `score|band|component|section` and not `part`. UBC's wording is the corpus';
  adding it is a vocabulary gap, not a design change.
- `_SAT_MIN` requires "SAT" **before** the number. `_IELTS_OVERALL` already has a reversed
  alternative for exactly this; SAT has none, so "1250 for redesigned SAT" reads as nothing.
- The third is a **contract gap, not a pattern gap**, and I will not paper over it: the certified value
  is a per-section map, `{"overall": 6, "writing": 6, "speaking": 6}`, and `ielts_min_subscore` holds a
  single number. Collapsing three named sections into one floor would be converting a value silently,
  which this repository forbids. Recorded in §7 for the owner.

Why this matters more than its size: the phase guide calls checking only the overall band **"the single
most common error in this work"** — an applicant with 7.0 overall and 6.0 writing fails a 6.5 per-band
requirement. On UBC we commit exactly that error today.

Write-ahead (claude-opus-5, 2026-09-22, **EXTRA-12**): **the classifier calls the right programme page
a catalogue, and the allow-list then refuses to read it.** Run 35754594232's per-page records, the
diagnostic built this morning, name the cause for five of the ten cases:

| case | page | classified |
|---|---|---|
| groningen | `rug.nl/bachelors/computing-science` | `program_catalog` |
| delft | `tudelft.nl/…/bachelors/cse` | `program_catalog` |
| toronto | `utm.utoronto.ca/…/computer-science` | `program_catalog` |
| vienna | `studieren.univie.ac.at/en/admission-procedure` | `news` |
| kaist | four admissions pages | `unknown` |

**Groningen's is the certified corpus' own URL** — the page its human reviewer read. The pipeline finds
it, fetches it, and the classifier rejects it as a catalogue, so `ACCEPTS["requirements"]` never lets an
extractor near it. Not discovery, not the patterns, not representation: **capability gating on a
misclassification**. I dismissed this cause twice.

The line responsible:

    if _PLURAL_PROGRAM_HEADING.match(identity) or _CATALOG.search(low_head) or program_links >= 5:
        return PROGRAM_CATALOG

Link counting runs **before** the page's own identity is read, so a page headed "BSc Computing Science"
that links to five other programmes — every real programme page does — is a catalogue before anyone
looks at its heading.

**The funding branch of the same file already learned this.** It calls a page an index on a listing
heading, or on several award links, or on links out *"with no award identity of its own"*. The
programme branch never got the third clause.

Scope: a heading that is plural or catalogue-shaped still settles it, because that is the page saying
what it is. Otherwise link count may only decide when the page has **no single programme name of its
own** — the funding branch's rule, applied to programmes. Tests both ways, and the golden demo will
say whether the demo's catalogues move.

Write-ahead (claude-opus-5, 2026-09-22, **the six owner decisions**): **Диас approved all six §7
recommendations on 2026-09-22** ("делай по рекомендациям"). They are taken in order of measured value,
one step each, because four of them change a stored contract:

1. **The scorer compares programme identity, not strings.** `scope_matches` uses `==` on every
   dimension; the `programme` dimension now asks `ontology.titles_name_same_programme`, which already
   exists and returns a `Verdict`. Only `YES` is a match — `UNKNOWN` stays a non-match, because a
   benchmark that scores "we could not tell" as a hit measures nothing. This is the largest single
   key in the corpus (`programme.exists`, 11 of 74).
2. **A claim type per English section**, so NTU's certified `{"overall": 6, "writing": 6,
   "speaking": 6}` has somewhere to live. Collapsing to a floor stays forbidden.
3. **`DIFFERENT_QUALIFICATION` in `ConflictKind`** — "the Abitur route requires X" and "the attestat
   route requires Y" are two scopes, not a contradiction.
4. **A programme-specific rule stays usable when a university-wide one disagrees**, the broader one
   kept rather than deleted, as the phase guide says. Today both are stamped `CONFLICTING`, so neither
   can support a decision, and `test_two_official_pages_disagreeing_produce_one_conflict` encodes that
   deliberately — it gets rewritten with the behaviour, not around it.
5. **The catalogue walker uses the same predicate as everything else**, so a BSc Mathematics stops
   surviving for a computer-science applicant. This rewrites part of the T29 contract test, with the
   owner's word for it.
6. **An unchanged claim is no longer superseded**, only its `accessed_at` refreshed, so a re-render
   stops writing a generation of history that repeats the live rows. This contradicts the T32
   supersession-per-URL contract, again with the owner's word.

**Two §7 items are deliberately NOT taken, and this is not an oversight.** Whether "Mathematical and
Computer Sciences" is equivalent to "Computer Science", and which KAIST page belongs in the
`program_page` slot, are **assertions about facts**, not choices about design. Inventing an equivalence
is the one thing this repository forbids outright, and it is why V2-31 waits for the owner's sources.
They stay his.

**STATE, 2026-09-22 morning.** Phase 2 is complete against its exit criteria (see
`docs/process/PHASE_2_ACCEPTANCE.md`). Phase 3 has §3, §4, §6 and §7 done; §1's visible half is done
(`published_scope`); §2 (Kazakhstan qualification rules) is **owner data** and untouched by design; §5
(costs) was already satisfied; §8–§10 are not started. Plan V2-22's resolver is built and unwired on
purpose.

**~~Do this first, and it needs a human: re-run `benchmark-capture`.~~ Done, 2026-09-22, run
35697105238 — and the prediction held: mismatches 5 → 2 (§3).** Three of them were the wrong-page cases
and they are gone. What remains is **one owner decision, not one line of code**: both survivors are
NTU's programme name, and the scorer compares strings (§7). Until that is answered,
`wrong_scope_claim_rate` cannot fall below 1.0 no matter what the pipeline does — so treat it as
answered-when-answered and work the queue below, which no longer depends on it.

0. **Act on what EXTRA-1 measured, not on what anyone assumed.** The wrong-scope rate is *not* a
   scope-reading failure: 5/5 mismatches are `differs` on `programme`. Two sub-problems, in order of
   cheapness:
   a. **NTU's two cases are a naming problem, not a retrieval one** — the page states the full official
      title and the label states the short one. That is plan V2-22 (entity resolution) applied to
      *programmes*: canonical programme, aliases, and a resolver that may only match on recorded
      evidence. `resolve_institution` is the shape to follow.
   b. **Three cases read the wrong page** (an open-day page, a "preparing for a bachelor" page, a
      visual-studies degree). That is retrieval, and it is what Phase 1's ranking is for. Re-measure it
      with the diagnostic in hand before touching the ranking again.

1. ~~Re-measure.~~ **Done: 5/5, unchanged, and structurally unable to change** — the strict score runs
   against a capture frozen on 2026-09-20, before a claim could carry a scope. Reading that capture is
   what found V2-22b (the capture recorded the request as the page's answer). **The number cannot move
   until someone re-runs the live capture with network**, which this container does not have; that is an
   owner/CI task, listed in §7.
2. ~~Make the assessment consult `covers()`.~~ **Done (V2-23).** It refuses an out-of-scope claim and
   disarms an unscoped one. The 5/5 still cannot be re-measured without a live capture (see 1).
3. ~~Surface it to the applicant.~~ **Done (V2-24)**: each refusal is an `UnresolvedQuestion` naming the
   page, the reason and a contact, blocking only when nothing else answered.
4. ~~Extend the reader to the other four adapters.~~ **Done (V2-25).** Old item text for reference:
   extend the reader to the other four claim-producing adapters (`web_scholarships`, `web_costs`,
   `web_documents`, `web_government`) once (1) says what the first one was worth. Scholarships are the
   likeliest win: eligibility prose states populations more often than requirements prose does.
3. Open items unchanged: KAIST's registry seed (owner data task, §7); page-kind as a prefilter concern.

**The live capture now has a button (claude-opus-5, 2026-09-21).** The owner asked whether I could run
it on his machine; I cannot — this session has no access to it, and `Fetcher` has no network here. So
the run moved to CI: `.github/workflows/benchmark-capture.yml`, `workflow_dispatch` only, never on push
(it fetches live university pages). It captures, scores **strictly** against `ground_truth.reviewed.json`,
prints a certified-vs-this-run table in the log and uploads capture + metrics as an artifact. **It
commits nothing** — a new baseline is a human decision. Needs one repository secret,
`UNIMATCH_EXA_API_KEY`; without it the run still completes but measures discovery *without* web search,
and the log says so rather than letting the numbers look comparable.

**Numbering note (read before the write-aheads below).** My task labels after V2-21 drifted from
`analysis/v2/02_EXECUTION_PLAN.md`. Mapping, so the plan stays the source of truth:

| My label | Plan item | What it was |
|---|---|---|
| V2-21, V2-21b | **V2-21 Scope model** | `ClaimScope` and carrying it on a claim |
| V2-22, V2-22b, V2-25 | *(no plan item — implementation of V2-21)* | filling the scope from pages; fixing the capture |
| V2-23, V2-24 | *(no plan item — use of V2-21)* | acting on scope, and telling the applicant |
| V2-26 | **V2-23 Conflict model v2** | separating contradiction from different scope |

**Second correction, 2026-09-21 (mine, again).** After reconciling once, I drifted a second time and
labelled non-plan work `V2-27`…`V2-30` — and the plan's own **V2-30 is "Requirements scope
verification"** in Phase 3, which I have not touched. To stop this recurring: **work that is not a plan
item is labelled `EXTRA-n` from here on.** The commits keep the labels they were pushed with (history
is not rewritten); this table is the map.

| My label | Really | What it was |
|---|---|---|
| V2-27 | EXTRA-1 | scope diagnostic: which dimension failed, and why |
| V2-28 | EXTRA-2 | a programme title read as a title, not a term |
| V2-29 | EXTRA-3 | an event heading is not a programme |
| V2-30 | EXTRA-4 | optional prefilter rejection of irrelevant page kinds |
| V2-24a | **plan V2-24**, first half | material-change classification |
| V2-20a/b, V2-22a/b | **plan V2-20 / V2-22** | as the plan names them |

Plan items still open in Phase 2: **V2-20 (SourceSnapshot / ClaimVersion)**, **V2-22 (entity
resolution)**, **V2-24 (change detection)**. From here I use the plan's numbers.

**Budget exhaustion is part of every one of these numbers.** On the *frozen* capture, 5 of 10 cases
ran out of budget (Aalto and Toronto on pages, Warsaw/UBC/KAIST on wall clock), and NTU — one of the
two "wrong programme name" cases — is also the only case that produced 10 claims. A recall number from
a run where half the cohort stopped early is a floor, not a measurement of the pipeline's ceiling. The
capture workflow now prints this table **last**, because the metrics JSON pushed the per-case lines out
of run 35655438326's log tail and I could not read them afterwards.

**MEASURED 2026-09-21, live, run 35655438326** (branch, Exa, 60 fetches / 90s per case, the frozen
baseline's own budgets). Honest reading, headline first:

| metric | certified capture | this run |
|---|---|---|
| `wrong_scope_claim_rate` | 5/5 | **3/3 — unchanged at 100%** |
| `programme_page_recall` | 1/10 | **3/10** |
| `programme_page_precision` | 1/9 | 3/18 |
| `recall_at_5/10/20` | 1/10 | 1/9 |
| `primary_source_rate` | 13/13 | 11/11 |
| `claim_adjudication_rate` | 5/13 | 3/11 |

**The metric all of Phase 2 was built for did not improve.** Not one claim scored a matching scope. The
denominator shrank; the rate is still 1.0. Retrieval did improve — 1 → 3 exact programme pages — and
that is Phase 1's effect, invisible on the frozen capture.

A hypothesis, stated as one: `scope_matches` needs the recorded scope to **equal** the label's. V2-22b
replaced a request-side value that could match by luck (`intake: "fall 2027"` on every claim) with what
the page actually says, which is usually nothing. That makes the measurement honest and can only leave
the match rate flat or lower it. Before acting on that, the next step measures *which dimension* fails.

Write-ahead (claude-opus-5, 2026-09-21, **V2-27**): **say which dimension of which claim is wrong.**
`wrong_scope_claim_rate` has reported a number and never a reason, so every attempt to move it is a
guess. A new `evaluation/research/scope_report.py` walks the same adjudicable predictions the scorer
walks and prints, per mismatch: the case, the claim key, the dimension, the label's value, the recorded
value, and which of three shapes it is — **silent** (the page did not say), **differs** (it said
something else), or **unrecorded** (nobody read a scope at all). Evaluation-side only; production never
reads it. The capture workflow runs it after scoring, so a run explains itself in its own log.

Write-ahead (claude-opus-5, 2026-09-21, **plan V2-20, exit criterion**): **the evidence questions the
phase guide says the product must answer.** The guide lists them outright — which evidence supports a
requirement for a programme and intake; which claims are stale; which are conflicting; which facts are
still unknown; which claims changed. Every one of them is answerable today only by reading rows by
hand.

Scope, exactly, in a new `app/domain/evidence_queries.py`: pure functions over a list of claims —
`supporting`, `stale`, `conflicting`, `unknown_for`, `superseded_history`, `scoped_to` — each returning
claims, never booleans, so a caller can show the evidence rather than a verdict.

**Deliberately no SQL and no migration.** The obvious alternative is indexed scope columns on
`claims`, and it would be premature twice over: nothing queries by scope in production yet, and the
phase guide's own answer to persistent scoped knowledge is the SourceSnapshot/ClaimVersion model that
V2-20 has only half-built. A pure function over the claims a run already loads answers the guide's
questions now and prejudges nothing; if a query ever needs an index, these functions say exactly which
one.

Write-ahead (claude-opus-5, 2026-09-21, **V2-24a**): **tell a real change from a re-render.**
Plan item V2-24, first half.

The pipeline already does the cheap half of change detection: conditional GET, then a content hash, so
a page that has not changed costs one request and nothing else. What it cannot do is the guide's next
question — *material* change. `reextract_page` supersedes **every** live claim over a re-read URL and
appends the fresh ones, even when every value came back identical. A page that merely re-rendered
therefore produces a full generation of superseded rows saying exactly what the live ones said.

Scope, exactly, in a new `app/domain/change_detection.py`:
- `ChangeKind` — `UNCHANGED`, `VALUE_CHANGED`, `ADDED`, `REMOVED`.
- `classify_changes(before, after)` — pairs claims on `(claim_type, subject_key)`, which is what makes
  two claims the same statement, and compares normalised values.
- `is_material(changes)` — true when anything but `UNCHANGED` is present.
- `source_scanner` logs the classification on every re-extract.

**Deliberately no behaviour change.** Skipping supersession for unchanged claims is the obvious next
move and it would break `test_a_forced_page_change_supersedes_old_and_appends_new_in_one_commit`, which
encodes the T32 contract: supersession is per source URL, and a page that now yields nothing supersedes
anyway. That contract was written deliberately by another campaign; replacing it is an owner decision,
so this step produces the evidence and §7 carries the proposal.

Write-ahead (claude-opus-5, 2026-09-21, **V2-22a**): **institution identity by evidence, not by
resemblance.** Plan item V2-22 (entity resolution), first half.

Today an institution's identity is `dedupe.university_key(name, country)`: normalise, drop noise words,
**sort the remaining tokens into a set**, join. That is a fuzzy matcher wearing a deterministic coat.
Two consequences, both of them the thing the phase guide forbids:

- *"Technische Universiteit Delft"* and *"Delft University of Technology"* are the same institution and
  get different keys, so the same university can enter a run twice.
- Any two names that reduce to the same token set in the same country merge **silently**, because a
  sorted set has no order and no evidence behind it. The guide's words: do not merge because names are
  merely similar.

Scope, exactly, in a new `app/domain/entity_resolution.py`:
- `InstitutionIdentity` — canonical key, canonical name, country, the domains that are evidence for it,
  and recorded `aliases` / `former_names` (both may be empty).
- `resolve_institution(...) -> Resolution` with the evidence ladder, strongest first: a **registrable
  domain** we already hold and have verified; then an **exactly recorded alias**; then nothing.
  Never a similarity score, never a token-set collision.
- `Resolution` carries `identity | None`, a `basis` (`domain` / `alias` / `unresolved`) and the exact
  evidence string, because the guide requires entity resolution to be **auditable** — a merge nobody
  can explain is the failure, not the merge itself.
- `dedupe.university_key` stays exactly as it is, and nothing is rewired in this step. A resolver that
  no caller trusts yet is the right size for one step; replacing the key everywhere is V2-22b, after
  this one is measured against the registry.

**The alias data is an owner task, not mine.** The registry holds `name`, `homepage` and verified
`seeds` — no aliases at all. I will read domains from what is already verified and leave `aliases` /
`former_names` empty, exactly as `seeds_verified_on` is left to a human. Filling them with names I
believe to be right would be the same forged signature as writing a KAIST seed myself.

Demo effect: **none**. Nothing calls the resolver yet.

Write-ahead (claude-opus-5, 2026-09-21, **V2-20b**): **a superseded claim says when it stopped being
current and what replaced it.**

Supersession already exists and works: `jobs/source_scanner.reextract_page` flips every live claim over
a re-read URL to `SUPERSEDED` and appends the fresh ones beside them, in one transaction. What the
history cannot answer is the two questions the guide's `ClaimVersion` is for — *when* did this stop
being true, and *which* value took over. Today a superseded row carries only its old `accessed_at`,
and the only link between the was and the became is that they share a URL.

Scope, exactly, in `app/models/research.py` + one migration:
- `claims.superseded_at` — when this row stopped being live. Set in the same transaction that flips the
  status, never guessed afterwards from `updated_at`.
- `claims.superseded_by_id` — the claim row that took over, FK to `claims.id`, **ON DELETE SET NULL**
  for the same reason `source_page_id` is: a purge must never take a history row with it.
- The successor is matched on `(claim_type, subject_key)` within the page being re-read. **A superseded
  claim with no successor is not a bug and must not be filled in with a guess**: it means the page no
  longer says this at all, which is exactly the case the re-extract docstring already calls the one
  thing that must never be lost.
- `reextract_page` sets both.

Not in scope, deliberately: `valid_from`/`valid_to` as a separate interval, and a `ClaimVersion` table
of its own. A claim row already *is* its version — it has `accessed_at` as its start and now
`superseded_at` as its end — and splitting that into a second table would be a migration of all
existing evidence for no query anyone makes yet. If a query does appear, the columns are already the
shape that table would need.

Demo effect: **none** expected — nothing supersedes in a demo run, which never re-reads a page.

Write-ahead (claude-opus-5, 2026-09-21, **V2-20a**): **SourceSnapshot — what a page said, and when.**

`SourcePage` already exists and is deliberately one mutable row per URL: the page's *current* state,
with the ETag, Last-Modified and content hash that let the next visit ask "changed?" without
downloading. What does not exist is the other half the phase guide names: a record of the versions a
page has actually been observed at. Today a page that changes overwrites its own hash and the previous
observation is gone, so "what did this page say when we claimed that?" has no answer.

Scope, exactly:
- `app/models/source_page.py`: `SourceSnapshot` — page id, content hash, the validators seen with it,
  http status, `first_seen_at` / `last_seen_at`.
- One row per (page, content hash), upserted: re-observing the same content updates `last_seen_at`
  rather than adding a row. **Decision, stated because it is arguable:** a page that reverts to earlier
  content is the same content seen again, not a third version. The order of events survives in each
  row's `last_seen_at`, and the intermediate version keeps its own row.
- `SourcePage.record` writes the snapshot in the same flush, so no caller can record a page's metadata
  and forget the version it saw. Metadata only — never a body, exactly as the page table's policy says.
- One Alembic revision on `d9c4e7a21b83`; one head before, one head after; an exact-inverse downgrade;
  round-trip tested on SQLite **and** PostgreSQL, as `TestT32MigrationRoundTrip` already does.

Demo effect: **none**. Snapshots are written on the live path only (the demo's discovery adapter has no
page recorder at all), so the golden must not move. If it does, something is recording on the demo
path that should not be.

Write-ahead (claude-opus-5, 2026-09-21, V2-26): **a conflict now says what kind of conflict it is.**
This is a Phase 2 exit criterion in the guide's own words — "conflict reasons distinguish true conflict
from different scope" — and it is the first thing `ClaimScope` makes possible that nothing else could.

Today two different values of the same claim type are a contradiction, full stop. Often they are not:
one page publishes the fee for home students and another for overseas students, one is the 2026 cycle
and one the 2027. Calling that a contradiction teaches the applicant to distrust a correct answer, and
it is the same mistake as treating silence as agreement — a scope difference read as a disagreement.

Scope, exactly:
- `ConflictKind` in `app/domain/enums.py`: `TRUE_CONFLICT` plus one `DIFFERENT_<dimension>` per scope
  dimension the guide names (population, intake, academic year, residency, degree).
- `app/domain/conflicts.py`: classify each group by comparing the claims' **recorded** scopes. Two
  claims that both state a dimension and state it differently are not contradicting; they are rules for
  different people or different years.
- A non-true conflict **does not stamp its claims `CONFLICTING`**. They are both correct. It stays
  visible, with its kind and a question worded for what it actually is.
- Claims with no recorded scope keep today's behaviour exactly: `TRUE_CONFLICT`, stamped as now.

`Conflict.kind` is a new field, so the demo payload gains a key — the demo has exactly one conflict
(Delft's programme page vs its admissions page, both stating the same intake), so it should classify as
`TRUE_CONFLICT` and nothing else should move. Additive proof before the hash, as always.

Write-ahead (claude-opus-5, 2026-09-21, V2-25): **the other four claim-producing adapters read scope
too.** §5 step 4. `web_requirements` has done so since V2-22; `web_scholarships`, `web_costs`,
`web_documents` and `web_government` still produce claims with no scope at all, which V2-23 then treats
as pre-V2-22 and judges exactly as before. Half the pipeline is honest and half is grandfathered.

Scope, exactly: `scope=read_scope(text, title=...)` on each of the four builders, using each adapter's
own already-extracted page text and title. No new reader logic — if a dimension needs a phrase family
these pages use and requirements pages do not, that is a separate, measured change.

Expectations, stated before running:
- **Scholarships should gain the most.** Eligibility prose names populations ("open to international
  students", "for EU/EEA applicants") far more often than requirements prose does, and a scholarship
  claimed for the wrong population is the most expensive wrong answer this product can give.
- **Government pages should gain nothing, and that is correct.** A post-study-work rule is a national
  rule; it has no intake and no programme, and the reader will rightly return an empty scope.
- **Costs pages may gain a residency** ("home fee status" / "overseas fee status"), which is exactly
  the dimension a fee figure needs and the one place `residency` was built for.

Demo effect: unknown, and this time it may legitimately move — a scholarship claim that gains a scope
the request cannot match stops being a hard filter. Look at the dump case by case before re-capturing,
per the guard's wording, and report what moved rather than only the hash.

Write-ahead (claude-opus-5, 2026-09-21, V2-24): **tell the applicant when an answer was withheld for
scope.** §5 step 3, and the first part of this phase a person can see.

V2-23 refuses a claim whose page is about another intake. Right now that refusal is *silent*: the claim
stays in the evidence list, the requirement simply goes unanswered, and nothing says why. Silence about
a refusal is its own version of the failure this phase is about — the applicant cannot act on a gap
they cannot see.

Scope, exactly:
- `app/domain/eligibility.py`: a frozen `OutOfScopeClaim` (claim type, source url, the reason in
  `ClaimScope.explain`'s words, and whether anything else answered that requirement), collected once per
  evaluation and carried on `EligibilityOutcome`.
- `app/pipeline/runner.py`: each one becomes an `UnresolvedQuestion` on the result — the existing
  channel, so the API, the export and the frontend need no new field. `blocking=True` only when nothing
  else answered that requirement, because a requirement answered by another page is not a blocker.
- The question is a question, not a verdict: it names the page, the intake it is about, and the intake
  that was asked, and it is phrased so the applicant can send it to an admissions office as is.

Expected demo effect: **none**. Every demo page states the requested intake, so nothing is declined and
no question is produced. If the golden moves, something declined a claim it should not have — look
before re-capturing.

Write-ahead (claude-opus-5, 2026-09-21, V2-23): **make the assessment refuse a claim whose page says
it is about something else.** This is §5 step 2 — where the 5/5 actually lives. V2-22 records a scope;
nothing yet *acts* on one, so an out-of-scope fact is still stated as the answer.

The rule, in `app/domain/eligibility.py`, applied where a claim is chosen (`_first`) rather than at each
of the dozen call sites, so no requirement type can be forgotten:

- `ClaimScope.covers(requested) is NO` — the page states a different intake or year than the one asked
  about — **the claim is not used for that requirement at all.** It stays persisted and visible as
  evidence; it just stops being the answer to a question it was not about.
- `UNKNOWN` (the page did not say) — the claim **is** used, because refusing it would throw away almost
  every real page, but it **may not be a hard filter**: it cannot eliminate a candidate. An unscoped
  page is not strong enough to end someone's application.
- `YES` outranks `UNKNOWN` in `_first`'s existing ordering, ahead of specificity, so a page that says
  who it is for beats one that does not.
- A claim with no recorded scope at all (`scope is None`, everything written before V2-22) behaves
  exactly as it does today. This is the same bug-compatible seam as V2-22b, for the same reason.

`RequestedScope` is built from what the run actually asked: the claim's own request-side `intake` and
`academic_year` meta. Population is **not** derived — the applicant's citizenship plus a university's
country would give it, but `evaluate_program` is not told the university's country, and inventing the
applicant's status at an institution is the exact move this whole phase exists to stop.

Expect the demo golden to move again, and this time **not additively**: a refused claim changes a
result. If it moves, look at the diff case by case before re-capturing, and record what changed and why
— the guard's wording (V2-22) now requires exactly that.

Write-ahead (claude-opus-5, 2026-09-21, V2-22b): **stop the benchmark capture from recording the
question as the page's answer.**

Re-measuring first, as §5 said to (step 1, done): `wrong_scope_claim_rate` is **5/5**, byte-identical to
`metrics.reviewed.json`, and it *could not* have moved — the strict score runs against a frozen capture
taken on 2026-09-20, before a claim could carry a scope at all.

Reading that capture found the same bug on the measurement side, which is worth more than the number.
Every prediction's `evidence.scope` is built in `evaluation/research/live.py` (and `map_claims.py`) from
the **request**: `intake` is `"fall 2027"` on all ten cases because that is what the profile asked for,
`university` is the candidate's name, `academic_year` is the runner's default. None of it was read from
the page. So the benchmark has been comparing a label against our own question, and a scope-match
failure there never meant a human-confirmed wrong fact — the baseline README says as much in its own
row, without knowing why.

Scope, exactly:
- one helper in `evaluation/research/mapping.py` that builds an `Evidence` scope from a raw claim;
- it prefers the claim's recorded `scope` (V2-22) for every dimension it states, and emits `None` for a
  dimension the page was silent on — a gap, not the requested value;
- it falls back to the request-side `intake` / `academic_year` fields **only when the claim carries no
  `scope` key at all**, i.e. was written before V2-22. That fallback is bug-compatible on purpose, so a
  re-score of the frozen capture stays exactly reproducible, and it is documented as such.
- `live.py` and `map_claims.py` both call it, so the two paths cannot drift again.

What this cannot do: **move the measured rate**. That needs a fresh live capture, and `Fetcher` has no
network in this container (§9). The capture re-run is an owner/CI task; until it happens the honest
statement is that 5/5 describes a capture taken before any of this existed.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-21b): **putting `ClaimScope` on `Claim`.**

**No migration is needed, and that is a finding rather than a shortcut.** `ClaimRow.payload` is a JSON
column holding the serialised claim whole; a new optional field on the pydantic model lands there by
itself. `alembic heads` is one (`d9c4e7a21b83`) and stays one because nothing is added to it.

Deliberately *not* adding a queryable `scope` column: nothing queries by scope yet, and the phase
guide's own answer to persistent scoped knowledge is the V2-20 SourceSnapshot / ClaimVersion model,
which is a design decision of its own. Adding a column now would prejudge it.

Scope — `app/schemas/claim.py`: an optional `scope: ClaimScope | None`, defaulting to `None`, which
means *nobody recorded the scope* and is distinct from a `ClaimScope()` that recorded it as empty. The
existing `program` / `intake` / `academic_year` fields stay exactly as they are: nothing reads the new
field yet, so nothing may depend on it, and removing them would break every extractor at once.

Acceptance: the full suite passes untouched, and a round-trip through the payload JSON preserves the
scope — a field that does not survive persistence is a field that does not exist.

V2-21 ships the type and its rule; nothing consults it yet, deliberately.

**NEXT, exact and executable.**

1. **Carry a `ClaimScope` on `Claim`.** Today scope lives in `program` / `intake` / `academic_year`
   and in free-text `notes`, which the spec forbids. The migration is additive — a nullable scope
   alongside the existing fields — and the existing fields stay until something reads the new one, so
   no extractor breaks. One Alembic revision, and §6 requires exactly one head before and after.
2. **Then make the extractor fill it** from what a page actually states, refusing to infer: the same
   discipline as `verify_candidate`, which is already written and tested next door.
3. **Then re-measure `wrong_scope_claim_rate`**, which is the only thing that proves any of this. It
   has been 5/5 since the corpus was certified and nothing has moved it.
4. Open items unchanged: KAIST's registry seed (owner data task, §7); page-kind as a prefilter concern.

**The honest shape of the remaining work:** Phase 1 made the pipeline find the right page. Phase 2 is
what stops it saying something untrue about that page. Neither is visible to an applicant until both
are done — a correct requirement for the wrong year is still wrong.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-21): **making a claim's scope a first-class thing**, per
`05_PHASE_2_EVIDENCE_GRAPH.md` "Claim scope". This is the direct attack on `wrong_scope_claim_rate`
**5/5** — the corpus's other headline failure and the one Phase 1 could never fix, because retrieval
and scope are independent holes.

What the benchmark actually measured: every claim the pipeline produced was the right fact about the
**wrong population, year or programme**. A requirement published for non-EU/EEA applicants in the
2026 cycle was stated as the answer for fall 2027.

Why it happens today: `Claim` carries `program`, `intake`, `academic_year`, `subject_key` and a
`SourceSpecificity`, and everything else about *who a rule applies to* lives in free text `notes`.
The spec says that in as many words: **do not encode critical scope only inside free-text notes.**
And an unstated dimension is currently treated as "applies to everyone", which is exactly backwards.

Scope — `backend/app/domain/claim_scope.py` (pure, no I/O, the rule belongs in domain):
- `ClaimScope` with the nine dimensions the spec lists — university, faculty, programme, degree,
  intake, academic year, population, nationality, residency — each explicitly `None` for UNKNOWN.
- `RequestedScope`: what was actually asked for.
- `ClaimScope.covers(requested) -> Verdict`, reusing V2-17's `Verdict`: **YES** only when every
  dimension the claim states matches the request, **NO** when any stated dimension contradicts it, and
  **UNKNOWN** when the claim is silent on something the request names. Silence is not agreement.
- `narrower_than` so conflict resolution can prefer the more specific claim, aligned with the existing
  `SourceSpecificity` order rather than replacing it.

Nothing is wired into extraction or ranking in this step. The type and its rule come first, exactly as
V2-17 did; wiring a rule nobody has agreed on is how the last two sessions lost runs.

V2-13e is done: **the owner can now see this working**, which was not true of anything before it.

**How to see it — the exact steps, for the owner.**

1. Pull the branch of PR #15 (`claude/greeting-16wj2z`).
2. Set two environment variables — never in Git:
   `UNIMATCH_SEARCH_PROVIDER=exa` and `UNIMATCH_EXA_API_KEY=<key>`.
3. Run the app as usual. Discovery now consults web search in addition to the sitemap and catalogue
   walker, and the run's trace says per institution how many programme pages search added.
4. Leave the variables unset and everything behaves exactly as it does on `main` today.

**A caveat that must be said before it disappoints anyone.** Retrieval improves; the *claims* built
from those pages do not, because `wrong_scope_claim_rate` is still 5/5 and Phase 2 has not started.
Better pages in, same scope errors out. Expect to see discovery finding the right programme pages more
often — not correct requirements for fall 2027.

**NEXT, exact and executable.**

1. **Phase 2, and specifically V2-21 (scope model).** Phase 1 is complete and measured; the corpus's
   other headline failure has never been touched, and it is now the whole remaining gap between "finds
   the right page" and "tells an applicant something true".
2. KAIST's registry seed (a small owner data task, §7).
3. Retry page-kind as a prefilter concern against the new baseline.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-13e): **connecting `discover_candidates` to
`LiveDiscoveryAdapter`.** The owner asked when they can see this working; the answer is that they
cannot yet, because every Phase 1 module is measured on a bench and called by nothing. This is the
wiring.

Also worth recording: the owner was told by another tool that task "2.18" makes it visible. **There is
no V2-18.** `02_EXECUTION_PLAN.md` numbers V2-00…V2-17 and then V2-20…V2-46, and no numbered task in
it is the wiring — the plan assumes it and never names it. Hence this one.

Design, following what was measured rather than what seems sensible:
- search results are **appended** to `selected[PageCategory.PROGRAM_PAGE]`, never interleaved. V2-16d
  measured the alternative: a coverage generator that competes with a ranked one costs cases.
- **off unless configured.** `get_search_provider()` raises `SearchProviderNotConfigured` on the
  default `none`, and that is caught and treated as "no search layer", so a deployment without a key
  runs byte-identically to today. That is the same dormant-seam pattern `page_recorder` uses two
  attributes above.
- the hop's page reader is the adapter's own `Fetcher`, so robots, rate limits, the PII guard and SSRF
  protection all apply exactly as before. The §6 exception covers the provider call only.
- a provider failure degrades the run, never ends it: discovery keeps whatever the sitemap and walker
  found.

Acceptance: the existing suite must stay green **unchanged** with no provider configured — that is the
proof this is dormant — and `seed_demo.py`'s order must still match brief §5.7, because this is the
first change on the branch that touches the live pipeline at all.

**Correction, and it matters more than the change itself.** The previous entry said the campus fix
"needs data this repository does not hold" and put it to the owner. **That was wrong.** The data was
already committed, already human-verified, and already loaded by the discovery code. Three ranking
experiments were rejected before this one, and all three were attempts to *infer from a URL* what a
verified record already *stated*. The rule: **look for the data before declaring it missing**,
especially when the guide names the place it would live.

**NEXT, exact and executable.**

1. **KAIST is the one case the seed signal costs** (#26 → #26–30): its correct page is on
   `cs.kaist.ac.kr`, which Toronto-style seeds do not name. Adding a verified `cs.` seed to KAIST's
   registry entry is the *data* answer and needs a human check of that URL, exactly as
   `seeds_verified_on` implies. That is a small, well-defined owner task, not a code change.
2. **Six cases are still not first.** Aalto (#17–20) and KAIST are the deep ones; both are
   not-a-programme-page problems the rejected page-kind experiment aimed at. Retry it **as a prefilter
   concern**, now that the seed signal has changed the baseline it would be measured against.
3. Untouched by all of Phase 1: `wrong_scope_claim_rate` 5/5.

V2-13d shipped provenance and used it: **Toronto is a wrong-campus problem, not a query problem.**
No fix is shipped — the cause is named and the fix needs data this repository does not hold.

**NEXT, exact and executable.**

1. **V2-22 — campus entity resolution, and it needs registry data.** A request naming
   "University of Toronto" should not be answered with UTM's or UTSC's page, and the pipeline has no
   way to express that: `verify_candidate`'s `university` dimension says YES to any host on the
   registrable domain. §12 sanctions exactly the data needed — university-specific knowledge is allowed
   as **verified registry metadata**, never as code. The shape is a campus list per institution in
   `institution_registry.json`, with the main/central host marked; the shape to avoid is a rule in the
   ranking that says "if the host starts with `utm`, penalise".
   **This needs the owner**: a campus list is human-checked data about real institutions, and the same
   standard that governs the corpus governs it — no invented entries.
2. **Then re-measure**, both numbers, two runs.
3. Untouched by all of Phase 1: `wrong_scope_claim_rate` 5/5.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-13d): **recording which query family found each candidate**,
because Toronto's #8 → #19 regression cannot be diagnosed without it and guessing at it would be the
third time this session that a plausible story turned out to be wrong.

`04_PHASE_1_DISCOVERY_ENGINE.md` §11 asks for exactly this and it was never built: every candidate
should keep `discovered_by`, `provider`, `query_or_parent_url` and `rank`. The report names which
families *ran*; nothing says which family produced which row.

Scope — `app/adapters/search/retrieval.py`: `RankedCandidate.found_by`, the families that surfaced
that URL, filled while the query loop runs and carried through the prefilter and the ranking. The
`SearchResult` contract is untouched: a provider reports what it returned, and which of our queries
asked for it is our bookkeeping, not theirs.

Then use it: one targeted run on Toronto to see which family surfaced its correct page at #8 and what
the new family displaced. No fix is written before that answer exists.

V2-11b shipped and the ceiling is back to **10/10**, this time with the cause understood rather than
observed: five of six query families were one shape, and a neural index reads a query for meaning, so
five variations of an operator query are one query asked five times.

**NEXT, exact and executable.**

1. **Toronto is the open regression.** It dropped #8 → #19 when the sixth family joined, consistently
   across both runs. Diagnose before adding anything else: which family surfaced it at #8, and what the
   new one displaced. `RetrievalReport.queries_run` already names every family, so a per-family record
   of which query found each candidate is the missing telemetry and is worth adding first.
2. **Query cost rose 20%** (50 → 60 per run) because the sixth family now fits the budget where a fifth
   used to. If a fetch or spend budget ever tightens, `DEFAULT_QUERY_BUDGET` is the dial and this trade
   is the thing to revisit.
3. **Entity resolution (V2-22)** for wrong-campus misses, unchanged and still untried.
4. Untouched: `wrong_scope_claim_rate` 5/5.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-11b): **adding one query family phrased as a person would
phrase it**, following the only concrete lead left from V2-13c.

The evidence: Exa returns Warsaw's `IN/S1-INF` at **rank 1** for
`University of Warsaw computer science first cycle programme S1-INF` and **not at all** for our
`site:uw.edu.pl "computer science" "bachelor"`. All five current families share one shape — a `site:`
operator plus quoted terms — which is keyword-search syntax. A neural index reads a query for meaning,
and five variations of one shape are one query asked five times.

Scope — `app/adapters/search/intent.py`: a `natural_language` family rendering the intent as a plain
sentence (institution, degree in words, field, and the cycle wording the ontology knows). The existing
families are untouched, `site_prefix` is untouched, and the budget is untouched — this **replaces
nothing**, it adds one shape inside the same `DEFAULT_QUERY_BUDGET`, so the cost per case does not
move.

Acceptance, stated first, and per §9 **two runs before believing any small move**:
- the ceiling must be ≥ 9/10 and Warsaw should return; and
- cases-at-rank-1 must not fall below the current 1.
Dropping `site:` wholesale was already measured and rejected; this is the narrower version of the same
hypothesis, which is why it is worth one more measurement rather than an argument.

V2-13c shipped the cycle slugs. Two other changes were measured and rejected, and **two earlier
statements in this file were wrong and are corrected**:

- **Toronto's +11 was not the page-kind signal.** With that signal explicitly off, Toronto still
  returns at #8 in three consecutive runs. It moved between runs and stayed; the cause is unknown.
- **The 10/10 ceiling is not currently reproducible, and no code change explains it.** Warsaw's
  `IN/S1-INF` is absent from what our queries retrieve in *every* configuration tried, including ones
  that do not touch its URLs. A direct probe settles it: Exa returns that exact page at **rank 1** for
  a natural-language query naming the cycle, and not at all for `site:uw.edu.pl "computer science"
  "bachelor"`. The page is indexed; our query shape does not reach it.

**A benchmark against a live third-party index measures that index too.** Do not compare against a
baseline older than a few runs — re-measure it in the same session as the change, or drift gets
attributed to code. This is now §9.

**NEXT, exact and executable.**

1. **Warsaw is a query-shape problem and is the most concrete lead left.** The winning query named the
   cycle in plain language. `queries_for` already has a `site_prefix` switch and its families are
   fixed; a family that states the degree in natural language ("first cycle", "undergraduate degree")
   is worth measuring. Dropping `site:` wholesale was already tried and cost more than it gained.
2. **Entity resolution (V2-22)** for the wrong-campus misses, unchanged and untried.
3. **Page-kind as a prefilter concern**, not a ranking one, unchanged.
4. Untouched: `wrong_scope_claim_rate` 5/5.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-13c): **teaching `degree_level_named` the cycle
conventions European catalogues actually use.**

Found while diagnosing V2-13b: Warsaw's catalogue writes the bachelor as `IN/S1-INF` and the master as
`IN/S2-INF`. `_DEGREE_SLUGS` lists `msc`, `master`, `graduate` and their kin, sees neither, and the
prefilter let a **master's page reach the top of a bachelor search**. This is the same class of error
as `wrong_scope_claim_rate` — the right fact about the wrong population — and the prefilter is exactly
where it should have been stopped, because a wrong degree level is already a rejection there.

`S1`/`S2` is not a Warsaw quirk. It is the Bologna cycle numbering, written as `S1`/`S2` in Polish
catalogues (`studia pierwszego/drugiego stopnia`), as `I stopnia` / `II stopnia` in prose, and as
"first cycle" / "second cycle" in English. A numeric convention defeats a word list everywhere it is
used.

Scope — `app/adapters/discovery/live_discovery.py`, the shared reader every generator uses:
- extend `_DEGREE_SLUGS` with the cycle forms, keeping the existing word slugs untouched;
- require a path-segment boundary as the existing matcher already does, so `s1` inside an unrelated
  token cannot fire — a two-character slug is exactly where a loose match would do damage.

Risk stated plainly: this widens a rule the live pipeline already depends on, so the whole suite is
the acceptance test, and the probe is re-run to check Warsaw.

V2-13b is **measured and not enabled**, and the honest state of ranking is: one clear win available
(Toronto +11) that currently costs a case, and a defect found underneath it.

**NEXT, exact and executable.**

1. **The real finding from this step, worth more than the signal:** Warsaw's top result became
   `.../IN/S2-INF` — the **master's** programme — and the prefilter did not reject it, because that URL
   names no recognisable degree level. `names_other_degree_level` reads slugs like `msc`/`master`; a
   catalogue that encodes the cycle as `S1`/`S2` defeats it. That is a wrong-degree-level candidate
   reaching the top of a bachelor search, which is the same class of error as
   `wrong_scope_claim_rate`. Fix the degree reader first; it may also explain why Warsaw lost its
   place.
2. **Then retry page-kind as a *prefilter* concern, not a ranking one.** A research-output page is not
   a weak candidate, it is the wrong kind of page, and rejections are counted and explained where a
   score adjustment is not. Re-enable only with a run holding the ceiling at 10/10.
3. **Entity resolution (V2-22)** for the wrong-campus misses, unchanged.
4. Untouched: `wrong_scope_claim_rate` 5/5.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-13b): **teaching the ranking what kind of page it is
looking at.** Retrieval is done — ten of ten reachable — and ranking is the only retrieval problem
left: two cases at rank 1, Aalto's correct page at #19 behind *a research publication*, KAIST's at #30
behind an organisation profile.

`app/adapters/page_classifier.py` already distinguishes `PROGRAM_DETAIL`, `PROGRAM_CATALOG`, `NEWS`,
`NAVIGATION` and `IRRELEVANT`, and the retrieval path has never consulted it. That is the gap: the
ranking scores words and ignores what the page *is*.

Scope — `app/adapters/search/retrieval.py`:
- a `page_kind` signal from `classify_page(url=...)`, positive for a programme detail or catalogue page,
  negative for news, navigation and irrelevant, neutral for unknown;
- classification from the URL alone, because ranking happens before anything is fetched. A URL-only
  verdict is weaker than one made on the page body, which is why it adjusts a score rather than
  rejecting a candidate — the prefilter is where rejections belong.

Also, one honest telemetry fix from the last run: `hop_entry_points` cannot currently tell *no host
qualified* from *the host refused the connection*. HKU shows 0 and the cause is the second — its hosts
score correctly and `admissions.hku.hk` resets the connection from this container. Two different facts
deserve two different counters.

Acceptance, stated before the run: Aalto and KAIST must move **up**, and no case may move down by more
than the ±1 the provider's own variance explains (§9).

V2-16d is **shipped, and it is the first change on this branch that improved the benchmark**:
retrieval ceiling **9/10 → 10/10**, no case moved down by the hop. Still off by default —
`discover_candidates(fetch=None)` — because production must pass a `Fetcher`-backed reader and
`Fetcher` cannot reach the network in this container (§9).

**NEXT, exact and executable.**

1. **Ranking, which is now the only retrieval problem left.** Ten cases reachable, two at rank 1.
   Two named causes from `SEARCH_PROBE.md`: wrong campus or faculty (UBC Okanagan for Vancouver,
   Toronto Mississauga for St George) → V2-22 entity resolution and a `university` dimension finer than
   "same registrable domain"; and not-a-programme-page (Aalto #19, KAIST #30) → the retrieval path
   never consults `page_classifier`.
2. **Two loose ends from the run**, both cheap: HKU opened **no** entry point at all
   (`hop_entry_points: 0`) — either every candidate host scored below zero or the fetches failed; and
   the probe should run twice per configuration, because Exa is not deterministic and ±1 position is
   noise (§9).
3. **Wire it into `runner.py`** — still the step that turns all of this into product behaviour, and
   still needs a `Fetcher` that works plus owner authorisation for a live pipeline run.
4. Untouched by any of this: `wrong_scope_claim_rate` 5/5.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-16d): **PR #15 is open** for everything up to here
(https://github.com/wpalish/ashyq-apply/pull/15). It supersedes draft #14, which this branch contains.

Now step 1 of the three V2-16c left: **hop candidates are appended after the search list, never
interleaved with it.** The measured reason is in `SEARCH_PROBE.md`: fusing them as equals cost a whole
case and pushed six correct pages down, because a navigation list is layout, not relevance.

The rule this encodes: a **coverage** generator may add pages a ranked generator never found, and may
never displace one it placed. Agreement is still kept — a page both generators found keeps both
attributions and its search position.

Acceptance, stated before the run so it cannot be rationalised afterwards:
- the ceiling must reach **10/10**, or at minimum rise above 9/10; and
- **no case may move down** from its search-only position (NTU #1, Vienna #1, Delft #2, UBC #2,
  Groningen #3, HKU #5, Warsaw #1, Aalto #19, Toronto #19).
If either fails, this does not ship either, exactly as V2-16c did not.

V2-16c is **measured and deliberately not shipped**: the hop as an equal generator makes the benchmark
worse. The mechanism is committed, tested and off by default; the reason it is off is written down with
its numbers.

**NEXT, exact and executable — in this order, each re-measured before the next.**

1. **Append, do not interleave.** Hop-only candidates go *after* the search list, keeping agreement
   where both generators found a page. Expect the ceiling to reach 10/10 with no case moving down; if a
   case moves down, that expectation was wrong and the change does not ship either.
2. **Choose entry points by kind, not by search rank.** KAIST stayed unreachable with the hop on
   because its top search results are `pure.kaist.ac.kr` research profiles, so the hop opened those
   instead of `cs.kaist.ac.kr/` — the page whose navigation demonstrably contains the answer (V2-16b,
   rank 3). `page_classifier` already tells a department root from a research profile and the retrieval
   path does not consult it.
3. **Only then** consider a fusion weight for the hop, and only if a measurement asks for one.

Standing rule this step earned: **a navigation list is not a ranking.** Link order on a page is layout.
Feeding it to RRF as though it were relevance is what caused the regression.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-16c): **fusing the navigation hop into
`discover_candidates` and re-running the live probe**, to find out whether the retrieval ceiling goes
from 9/10 to 10/10 and whether the seven misplaced cases move up.

The obstacle is §9's environment fact: `Fetcher` cannot reach the network in this container, and the
hop needs its entry points fetched. **The fix is not to weaken `Fetcher`.** `discover_candidates` takes
an injected `fetch` callable instead:

- production passes a `Fetcher`-backed one, so robots, rate limits, the PII guard and SSRF protection
  are exactly as before and §6 is untouched;
- tests pass a fake, so no test goes near the network;
- the **evaluation probe** passes a proxy-aware one of its own. That is legitimate precisely because
  `evaluation/` is not production and never ships — the same reason it may hold ground truth that
  production must never read.

Bounded: at most `DEFAULT_HOP_ENTRY_POINTS` entry points per case, one hop deep, no recursion, and a
fetch failure drops that entry point rather than ending the run. Search results and hop candidates are
merged through V2-16's `fuse`, so a page both generators find keeps both attributions — which is the
agreement signal fusion exists to produce.

Then: re-run `python -m evaluation.research.search_probe --live` and record the new numbers beside
9/10 and 2-at-rank-1.

V2-16b is implemented, green, and **validated against a real page rather than a fixture** — which is
the only reason it works. The hand-written smoke test passed first time and KAIST's real navigation
failed three separate ways (§9). Each is now a test.

**NEXT, exact and executable.**

1. **Fuse the hop into the retrieval path and re-run the probe.** `discover_candidates` returns search
   results only; the hop has to fetch each search-found entry point through `Fetcher` and feed
   `navigation_candidates` into `fuse` beside the search results. Then re-run
   `python -m evaluation.research.search_probe --live` and see whether the ceiling goes **9/10 → 10/10**
   and whether the seven misplaced cases move up. That is the measurement this step was for.
2. **`Fetcher` cannot reach the network in this container** (§9). Wiring the hop needs a fetch, so
   either run that step where `Fetcher` works, or teach `Fetcher` to honour `HTTPS_PROXY` — the latter
   is a real change to a security-critical module and wants its own task and review, not a drive-by.
3. Then the ranking work from the previous §5 entry: entity resolution for wrong-campus misses (UBC
   Okanagan, Toronto Mississauga) and consulting `page_classifier` for not-a-programme-page misses.

Previous write-ahead (claude-opus-5, 2026-09-21, V2-16b): **adding a navigation-hop generator**, after
investigating KAIST — the one case the live probe could not reach.

**Evidence, gathered before deciding anything.** Four query shapes were tried against KAIST
(site-restricted, domain-filtered, subdomain-filtered, and Korean). None returns
`cs.kaist.ac.kr/content?menu=188`. But the department root `cs.kaist.ac.kr/` comes back first or second
in almost every one, sibling CMS pages (`?menu=200`, `?menu=318`, `?menu=320`) are in the index, and
fetching the root shows the target **linked directly from its navigation** under the text 교육, with
`/education/undergraduate` as a word-bearing alias for the same section.

**So the general lesson, not a KAIST lesson:** web search indexes what is linkable and word-bearing and
reliably finds *entry points*; structural traversal does not care about words in a URL. They fail
differently, which is exactly why V2-16 has several generators. The answer to an opaque site is not
better queries — it is one hop through the site's own navigation, matching link text against the
ontology. `live_discovery.matches_field_text` already exists for precisely this: it was written when
Toronto's programme sat at `/data-computer-science` behind the link text "Data & Computer Science".

Scope — `backend/app/adapters/search/navigation.py` and `tests/test_navigation_hop.py`:
- `links_from(html, base_url)` — every same-institution link with its text, deduplicated and bounded.
- `navigation_candidates(html, base_url, intent, *, limit)` — the links whose *text* or URL names the
  requested field or degree, scored so a word-bearing alias outranks an opaque one, each carrying the
  parent URL it was found on so provenance survives (§11: `query_or_parent_url`).
- Emitted as `Generator.CATALOGUE_WALKER` `SourcedCandidate`s so V2-16's fusion merges them with search
  results and attribution is kept.

Bounded: one hop, a capped number of links per page, and no fetching — this module reads HTML it is
given. Fetching the entry point stays with `Fetcher` per the amended §6.

The Exa adapter works against the live API and the retrieval question is **answered**: web search
raises the ceiling from 1/10 to 9/10. Details, per-case table and caveats in
`backend/evaluation/research/SEARCH_PROBE.md`.

**NEXT, exact and executable — and the order has changed because the measurement changed.**

1. **Fix ranking, not retrieval.** Nine cases have the answer in the candidate set and seven of them
   show something else at the top. Two distinct causes, both actionable now:
   - **Wrong campus or faculty** (UBC Okanagan for Vancouver, Toronto Mississauga for St George). Same
     registrable domain, so the prefilter is right to keep them; they are the wrong *entity*. V2-22
     (entity resolution) and a finer `university` dimension in `verify_candidate` than "same domain".
   - **Not a programme page at all** (Aalto's top hit is a research publication, KAIST's an
     organisation profile). The retrieval path does not consult `page_classifier`, and the ontology's
     `related_not_equivalent` terms are not pushing neighbours down hard enough.
2. **Tuning is now legitimate.** `SIGNAL_WEIGHTS` and the BM25 constants were frozen while headroom was
   zero. There is a signal now; tune against `search_probe.exa.json` and re-run the probe, not against
   intuition.
3. **V2-14 becomes worth doing** once (1) is exhausted — a reranker has seven cases to win.
4. **KAIST is the one unreachable case.** `cs.kaist.ac.kr/content?menu=188` is a query-string CMS page
   with no words in its URL: the worst shape for lexical *and* neural retrieval. Worth a look; §12
   forbids a per-university hack.
5. **Still untouched by all of this:** `wrong_scope_claim_rate` 5/5. Retrieval and scope are separate
   holes and only one has moved.

**NEXT — one owner decision, then one measurement.**

1. **Owner: settle the `AGENTS.md` §6 network rule** (§7 below). Until then the provider stays `none`
   and nothing calls out.
2. **Then, in one step:** set `UNIMATCH_SEARCH_PROVIDER=exa` and `UNIMATCH_EXA_API_KEY` in the
   environment (never in Git), wire `discover_candidates` → `fuse` → `verify_candidate` into the
   discovery stage, and run a **bounded** canary with owner authorisation, as every previous live run
   had. Budget it explicitly: 10 cases × `DEFAULT_QUERY_BUDGET` 6 = ~60 queries per full run.
3. **Then measure both numbers and record them beside the before-values:** strict scoring against
   `ground_truth.reviewed.json` (programme recall 1/10, claim precision 0/5, wrong-scope 5/5) and
   `python -m evaluation.research.ceiling` (ceiling 1/10, headroom 0). The ceiling is the honest test of
   whether retrieval actually improved; recall alone can move for the wrong reasons.
4. Per `04_PHASE_1_DISCOVERY_ENGINE.md` §12, a discovery change is only good if the benchmark improves,
   and explicitly **not** acceptable if recall rises through an exploded fetch budget or with material
   false positives. Record fetch count, cost and latency alongside.

V2-17 is implemented and green (§6).

**NEXT, exact and executable.**

1. **V2-21 — the scope model** (`05_PHASE_2_EVIDENCE_GRAPH.md`): programme / degree / intake /
   population / nationality / academic year as a first-class thing a claim carries, rather than the
   free-text `scope` dict the corpus uses today. V2-17 decides whether a *page* may speak for the
   requested intake; V2-21 is what a *claim* carries when it may not. Together they are the
   `wrong_scope_claim_rate` 5/5 fix. Needs no key and no authorisation.
2. **When the provider key arrives** (the owner is registering now): write the adapter behind the
   V2-10 seam, wire `discover_candidates` and `fuse` into the discovery stage, run a bounded canary
   with owner authorisation, then re-measure **both** numbers — strict scoring against
   `ground_truth.reviewed.json` and `python -m evaluation.research.ceiling`. Recommended first
   provider and the reasoning are in §7.
3. `verify_candidate` is not called by the pipeline yet either. It belongs in the same wiring step as
   (2), because a verdict nobody consults changes no measurement.

V2-16 is implemented and green (§6). **Phase 1's parts are now all built and none is wired in.**
V2-10 (provider seam), V2-11 (queries), V2-12 (ontology), V2-13 (retrieval), V2-15 (site search) and
V2-16 (fusion) exist with 100% coverage each; `runner.py` still calls none of them, and the benchmark
numbers are exactly what they were before this branch started.

**NEXT, exact and executable — and this is a decision point, not just a task.**

The honest reading of this branch: six well-tested components, zero measured improvement, because the
two things that would produce a measurement both need the owner.

1. **Wire fusion into the live discovery stage and run a bounded canary.** This is the step that turns
   the branch into a number. It touches `runner.py` and the discovery stage, so it is the first change
   here that can regress the demo oracle — run `seed_demo.py` against brief §5.7 as well as the gates.
   Then re-measure both: strict scoring against `ground_truth.reviewed.json`, and
   `python -m evaluation.research.ceiling`. A live canary needs owner authorisation, as every previous
   one did.
2. **Or pick a search provider first** (§7), since three benchmark cases retrieved nothing and web
   search is the generator most likely to fix that. Needs a key outside Git and an accepted data policy.
3. **Or leave Phase 1 here and take V2-17 / V2-21**, which need neither authorisation nor a key and
   attack the corpus's other failure, `wrong_scope_claim_rate` 5/5.

My recommendation is (3) while (1) and (2) wait on you: it is the only one of the three that can make
measurable progress without a decision, and scope is half the total failure.

V2-15 is implemented and green (§6). Detection only: nothing fetches a detected surface yet, and
`Fetcher` remains the only thing that touches the network.

**NEXT, exact and executable.**

1. **V2-16 — discovery fusion and provenance** (`02_EXECUTION_PLAN.md`, Phase 1). It is now the piece
   that makes the previous five useful: merge candidates from the registry, sitemaps, the catalogue
   walker, a site-search surface and (when a provider exists) web search, into one ranked list where
   every candidate remembers which generator produced it. `RetrievalReport` and `SiteSearchSurface`
   already carry provenance, so the shape is there.
2. **Then wire fusion into a bounded canary and re-measure.** Two numbers matter and both are recorded:
   strict scoring against `ground_truth.reviewed.json`, and
   `python -m evaluation.research.ceiling` — the ceiling is the one that says whether retrieval
   actually improved, and it was 1/10 with zero headroom before any of this.
3. **V2-17 / V2-21** remain the other open hole (`wrong_scope_claim_rate` 5/5) and need no provider.

Still blocked on the owner: the search provider key (§7 below). V2-15 was chosen precisely because it
needed no key; a site-search surface is a real retrieval channel for the three cases that found
nothing.

**NEXT, exact and executable.** Everything below is retrieval or scope; nothing is ranking.

1. **The owner decision that unblocks the most:** pick a search provider for the V2-10 seam (the guide
   suggests Brave, Exa, Tavily, Parallel). It needs a paid key and an approved data policy, so it is
   not an AI's call. Until then Phase 1 can be built but not measured — three cases in the capture
   retrieved literally nothing, and a web search is the cheapest thing that would have found them.
2. **V2-15 — university internal search adapters** (§7). Buildable offline against fixtures: detect the
   public search or catalogue surface a site already exposes (HTML form, JSON endpoint, WordPress REST,
   Drupal views, Algolia, Elastic, Solr, GraphQL). Rules from §7 are non-negotiable — public endpoints
   only, no auth bypass, Fetcher's network/PII/SSRF policy preserved, provenance recorded, body sizes
   capped, pagination bounded. This is the retrieval work that needs **no** paid key, so it is the best
   next step if the provider decision is going to take time.
3. **V2-16 — fusion and provenance**, then **V2-17 — identity verification** and **V2-21 — the scope
   model**. V2-17/V2-21 attack the corpus's *other* headline failure: `wrong_scope_claim_rate` 5/5
   against `primary_source_rate` 13/13. Retrieval and scope are two independent holes and both are open.
4. **Re-run the ceiling after any retrieval change**:
   `python -m evaluation.research.ceiling --dataset evaluation/research/data/ground_truth.reviewed.json
   --capture evaluation/research/baseline/capture.json`. The day headroom exceeds zero, V2-14 becomes
   worth building, and `RERANKER_CEILING.md` is the before-number it gets judged against.

**Forbidden until that measurement changes:** deploying or paying for a cross-encoder, Jev or an LLM
reranker, and tuning `SIGNAL_WEIGHTS` or the BM25 constants. Both would be fitting noise against a
ceiling of zero. Phase 1's retrieval path now exists end to end behind the fake
provider: intent → bounded queries → provider → prefilter → BM25 + signals → ranked candidates, with
rejection counts, the ontology version and failed queries in the report.

**It has not moved the baseline, and cannot yet.** `UNIMATCH_SEARCH_PROVIDER` is `none`, no real
adapter exists, and nothing in `runner.py` calls `discover_candidates`. The 1/10 number stands until
both change. Do not report Phase 1 as an improvement to anything.

**NEXT, exact and executable.**

1. **Wire it in and measure.** The only honest next step is a benchmark run: add a real adapter behind
   the V2-10 seam (owner picks the provider — Brave, Exa, Tavily and Parallel are the guide's
   suggestions; this needs a paid key, so it is an owner decision, not an AI one), then call
   `discover_candidates` from the discovery stage and score strictly against
   `ground_truth.reviewed.json`. Record `ontology_version` and the rejection counts beside the recall
   number. Until a provider exists, the fake makes every test honest and every measurement impossible.
2. **Do not tune weights before that run.** `SIGNAL_WEIGHTS` and the BM25 constants are deliberately
   untuned; tuning them against intuition rather than the benchmark is decoration, and the benchmark is
   the thing V2-01 spent seven drafts making trustworthy.
3. **Remember what the baseline actually said.** `wrong_scope_claim_rate` is 5/5 and
   `primary_source_rate` is 13/13: the pipeline reads official pages fine and then applies them to the
   wrong population, year or programme. Better retrieval does not fix that — V2-17 (programme identity
   verification) and V2-21 (scope model) do.
4. Optional and cheap: one PR for V2-10 → V2-13. They are one coherent seam with no callers, which is
   the easiest thing to review that this branch will ever contain. Phase 1's three preparatory pieces — the provider seam (V2-10),
the query generator (V2-11) and the ontology (V2-12) — are all in place and none of them calls another
yet. That is correct: V2-13 is the consumer that joins them.

**NEXT, exact and executable.**

1. **V2-13 — hybrid candidate retrieval**, `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §4–§5. This is
   the first task that can move the **1/10** programme-page recall, and the first that joins
   `queries_for` to a `SearchProvider` with `retrieval_candidates` bounding the alias expansion. §4 is
   explicit that alias expansion must stay inside a query budget; `DEFAULT_QUERY_BUDGET` and
   `retrieval_candidates`' match-first ordering exist for exactly that.
2. **Measure it strictly.** Every retrieval change is scored against `ground_truth.reviewed.json` with
   no `--allow-drafts`, and the ontology version goes into the report — a recall number without the
   vocabulary that produced it cannot be explained six weeks later.
3. **Aim at `wrong_scope_claim_rate 5/5`, not only at recall.** The baseline says the pipeline reads
   official pages fine (`primary_source_rate` 13/13) and then applies them to the wrong population,
   year or programme. More candidates alone will not fix that; V2-17 (identity verification) and V2-21
   (scope model) are where it is fixed, and V2-13 should not paper over it by retrieving more.

Consider opening one PR for V2-10 + V2-11 + V2-12 before starting V2-13: they are one coherent seam,
nothing depends on them yet, and that is the cheapest moment to review them.

**NEXT, exact and executable.**

1. **V2-12 — the field and degree ontology**, `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §3.
   Canonical concepts with `strong_aliases` and, separately, `related_not_equivalent` — the spec is
   explicit that a related programme is a *retrieval candidate*, never an automatic match, and this
   repository has already made that mistake's opposite twice on purpose (draft2 refusing Data Science
   for Aalto, draft7 leaving Computer Engineering open). Keep a version field on the ontology; support
   multilingual aliases in the shape even if only English is populated now.
2. **Then V2-13 — hybrid candidate retrieval**, the first step that can move the 1/10 baseline. It is
   what finally joins `queries_for` to a `SearchProvider`. Score every attempt strictly against
   `ground_truth.reviewed.json`.
3. **Open a PR** for the V2-10 + V2-11 pair when convenient; they are one coherent seam and review
   better together than apart.

**NEXT, exact and executable.**

1. **Open a PR for V2-10** and set §2 to `ready-for-review`. It is a self-contained seam with no caller,
   which is the right size to review before anything depends on it.
2. **V2-11 — the query generator**, `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §2. Build a
   `DiscoveryIntent` (institution, degree, field, optionally intake, optionally a generic
   `international`/`Kazakhstan` marker for a country-requirements page) and render it to a query string.
   The privacy list is explicit and short: no name, no scores, no GPA, no budget, no family
   contribution, no contact details, no transcript content. Put a test per forbidden item that feeds a
   populated profile through and asserts the rendered query contains none of it — the structural
   guarantee in V2-10 stops a profile *object* reaching a provider, it cannot stop somebody formatting
   one into a string.
3. **Then V2-12 (ontology) → V2-13 (hybrid retrieval)**, which is the first step that can actually move
   the 1/10 baseline. Score every attempt against `ground_truth.reviewed.json` strictly.

Historical: V2-01 is accepted. The baseline it establishes is deliberately unflattering and is the point of the
whole exercise: **programme-page recall 1/10, claim precision 0/5, claim recall 0/62, wrong-scope claim
rate 5/5, critical-field coverage 0/210.** The current pipeline finds the right programme page for one
university in ten and every claim it produces is the right fact about the wrong population, year or
programme. Never quote these as a product result.

**NEXT, exact and executable.**

1. **V2-10 is now unblocked** — it was gated on V2-01 acceptance and nothing else. It is the
   provider-neutral `SearchProvider` with a fake adapter; its card is `analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md`
   and the execution order is `analysis/v2/02_EXECUTION_PLAN.md`. Read both before writing code, and
   branch per AGENTS.md §4.
2. **Beat 1/10, and prove it against this baseline.** Any discovery change must be scored with the same
   frozen capture or a fresh bounded capture, against `ground_truth.reviewed.json`, strictly. The
   `wrong_scope_claim_rate` of 5/5 is the most actionable signal in the report: the pipeline is not
   failing to read pages, it is failing to check that what it read applies to the requested scope.
3. **Certification is of a version, not of the corpus.** 158 fields are still UNKNOWN — the Kazakhstan
   fall-2027 intake, fees, general SAT/IELTS policy. A draft that adds them needs its own signature from
   a named human on a dated worksheet; do not extend the reviewed dataset in place.

Previous write-ahead (claude-opus-5, 2026-09-20, certification): **the owner has signed the corpus.** They
reviewed draft7, answered "всё правильно" to the two open questions in §7 — which settles the Aalto
adjudication in the affirmative, accepting the English-taught Computer Engineering major as satisfying
the requested computer science — and supplied the reviewer identity: **Диас, 2026-09-21**.

This step therefore does what six drafts could not: copies draft7 to `ground_truth.reviewed.json`,
sets `review.status: "human_verified"`, `reviewer: "Диас"`, `verified_on: "2026-09-21"` on all ten
cases, and runs the scorer **without `--allow-drafts`** — the strict gate at `metrics.py:37` that has
refused every version so far. Adds `metrics.reviewed.json` from that strict run, an `ACCEPTANCE.md`
recording who signed what and when, the VERSIONS row, the README status change from IN PROGRESS, both
`parametrize` extensions, and a new test asserting strict scoring now *succeeds* on the reviewed
dataset while still refusing every draft. Frozen draft1–draft7, the capture and production code stay
untouched. The Aalto decision is recorded in that case's notes as the owner's call, with the reasoning
it overrides, so a later reader can see it was decided rather than assumed.

Draft7 is published and green (§6).

**NEXT, exact and executable.** Three items; (1) is the only one that can unblock acceptance.

1. *Signatures — owner-blocking, cannot be AI-done.* The owner has now actually reviewed the corpus and
   approved eight of ten cases, but `review.status` is still `draft` everywhere because `schema.py:42`
   requires `reviewer` and `verified_on` and no AI may supply them. **Ask the owner for a reviewer name
   and a date, then set `status: "human_verified"`, `reviewer`, `verified_on` on the eight approved
   cases** in a new dataset version. Aalto must not be signed until the Computer Engineering vs computer
   science question is answered; HKU wants a second pair of eyes because its new labels were authored
   from the review itself. After ten signatures, run strict scoring with no `--allow-drafts`.
2. *Aalto adjudication.* Put the open question to the owner in one line: does the English-taught Computer
   Engineering major count as the requested computer science, or does the case revert to `unknown`?
   Both answers are defensible; neither is an AI's to pick.
3. *Remaining evidence (AI-doable, independent of the above).* Resolve the Kazakhstan fall-2027 intake,
   tuition/mandatory fees, and general SAT/IELTS policy for the cases still holding them UNKNOWN, in a
   new draft built the same way. Take only values whose page states the requested scope — draft6 refused
   Delft's 15 January and draft7 refused Aalto's €12 000 and its 7–22 January 2027 window on exactly this
   rule. Extend both `parametrize` lists in `backend/tests/test_research_benchmark.py`.

Previous write-ahead (claude-opus-5, 2026-09-20, draft7): **the owner performed the first real human review of
draft6 and returned two corrections plus an approval of everything else.** Both corrections were checked
against the primary sources and both are right:

1. **Aalto — wrong programme for the requested scope.** The Finnish `tietotekniikka` page is a real page
   and its "Finnish" teaching language is a true fact about it, but the requested scope is an
   *international* bachelor applicant, and that route is not open in English. Aalto's English-taught
   bachelor route is the **Aalto Bachelor's Programme in Science and Technology**, whose CS-adjacent major
   is **Computer Engineering** (`https://www.aalto.fi/en/study-options/computer-engineering-bachelor-of-science-and-master-of-science-technology`,
   heading "Computer Engineering, Bachelor of Science and Master of Science (Technology)", instruction
   English, €12 000/year for non-EU/EEA, next English application period 7–22 January 2027).
   Draft7 moves the identity there. It does **not** silently assert that Computer Engineering equals the
   requested "computer science": that page says the major combines information technology and electrical
   engineering, and draft2 already refused the same equivalence move for Data Science. The equivalence is
   recorded as an open question for the reviewer, and the Finnish route is kept as the separate thing it
   is.
2. **HKU — missing faculty, and the programme title was approximate.** The owner gives
   "School of Computing and Data Science", and the page confirms it: the school offers
   **Bachelor of Engineering in Computer Science**, not a programme titled bare "Computer Science".
   Draft7 adds `programme.faculty` and tightens the recorded title.

Draft7 is built exactly as draft6 was (copy, bump version, regenerate metrics through the documented
CLI, new REVIEW_DRAFT7.md and REVIEW_WORKSHEET_DRAFT7.md, VERSIONS row, README repoint, both
`parametrize` lists extended). It touches only the Aalto and HKU cases; frozen draft1–draft6, the
capture and production code stay untouched. The owner approved the other eight cases, but **no case is
marked `human_verified` in this commit**: the schema needs a reviewer name and a date, and inventing
either is the one thing this corpus exists to prevent. The name is being asked for separately.

Draft6 is published and green (§6): `delft.programme_urls` / `programme_status` now carry
`https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-and-engineering`,
and all ten programme identities are resolved.

**NEXT, exact and executable.** Two independent tracks; neither needs the other.

1. *Evidence (AI-doable now).* Resolve, in a NEW `draft7` dataset built the same way draft6 was:
   the Kazakhstan fall-2027 intake date, the tuition/mandatory-fee figures, and the general SAT/IELTS
   policy for the cases still holding those UNKNOWN. Take **only** values whose page states the
   requested scope; a 2026-exercise deadline or an unscoped numerus-fixus rule must stay UNKNOWN, as
   draft6 refused Delft's 15 January. Copy `ground_truth.draft6.json` → `.draft7`, bump
   `version`/`dataset_version`, regenerate metrics through the documented CLI, add `REVIEW_DRAFT7.md`
   and `REVIEW_WORKSHEET_DRAFT7.md`, add the VERSIONS row, repoint the README, and extend both
   `@pytest.mark.parametrize` lists in `backend/tests/test_research_benchmark.py` (lines 321 and 331)
   with `".draft7"`.
2. *Acceptance (owner-blocking, cannot be AI-done).* V2-01 cannot be accepted until **ten real human
   reviewer names and dates** sit in the worksheet and strict scoring runs without `--allow-drafts`.
   Verification is 0/10 and has been through six drafts. No amount of further AI annotation moves it.
   Until then no version of this corpus may be called a benchmark result, and V2-10 does not start.

Previous write-ahead (claude-opus-5, 2026-09-20, draft6): draft5 is released and green (§6). The single
blocker §5 has named since draft2 is the Delft exact programme identity, the last `unknown` of ten.
The OCW alias gpt-6-astra kept hitting is not the programme page; the official one is
`https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-and-engineering`,
heading "Bachelor of Computer Science and Engineering", reachable and read 2026-09-20. Draft6 will do
exactly one thing: resolve `delft.programme_urls` / `programme_status` with that primary source, taking
programme identities to 10/10. It copies draft5 to `ground_truth.draft6.json`, regenerates
`metrics.draft6.json` through the documented offline CLI, adds `REVIEW_DRAFT6.md` and
`REVIEW_WORKSHEET_DRAFT6.md`, adds the VERSIONS row, repoints the README, and parametrises the replay
tests over `.draft6`. It copies **no** admission requirement, deadline, fee or language label: the
deadline on that page is a selection deadline of an academic year the requested fall-2027 scope does not
establish, and the numerus fixus/Maths B statements are unscoped to the requested intake. Frozen
draft1–draft5, the capture and production code stay untouched, all ten signature blanks stay blank, and
strict scoring must still refuse the corpus. Human verification stays 0/10.

Previous write-ahead (claude-opus-5, 2026-09-20): gpt-6-astra published draft5 in `a4cd5b3` and was cut off
before its gates finished, so the commit is still marked `wip:`. This session runs the gates gpt-6-astra
could not, records the numbers in §6, and releases draft5 — it writes **no** new dataset, report or
worksheet and changes no production code. Recovery found nothing half-written: the tree was clean, the
index empty, nothing stashed, and `a4cd5b3` is one coherent commit whose every claim is pinned by a
passing test. Draft5 is therefore continued, not re-done.

Next after this release — unchanged from what gpt-6-astra left, and still the blocking step:
resolve the exact Delft programme URL (its OCW-linked official alias has now errored twice) and the
remaining Kazakhstan fall-2027 intake, fee and general SAT/IELTS evidence, in a NEW dataset version.
Keep conditional `english_evidence.*` minima separate from academic entry requirements; keep the Aalto
Finnish-route identity distinct from English Data Science; preserve the generic Attestat UNKNOWN.
Then review the award/document aliases, finalize the applicable field inventory, adjudicate
support/currentness/conflicts independently, obtain **ten real reviewer/date signoffs** — the worksheet
is not a signature — and only then run strict scoring without `--allow-drafts`. No V2-10 until V2-01 is
accepted. Human verification is 0/10 and no version of this corpus may be called a benchmark result.

Draft4 is published in 3f7e467; current review packet is backend/evaluation/research/REVIEW_WORKSHEET_DRAFT4.md (56 known fields). Next: resolve exact Delft programme URL and remaining Kazakhstan qualification, fall 2027 intake, fee and SAT evidence in a NEW dataset version. Keep Aalto Finnish-route identity distinct from English Data Science; preserve generic Attestat UNKNOWN despite the scoped Groningen NIS labels. Review exact award/document aliases, finalize applicable field inventory, and independently adjudicate support/currentness/conflicts. Obtain ten real reviewer/date signoffs, then run strict scoring without --allow-drafts. No V2-10 until V2-01 acceptance. Older steps below are historical.

Draft3 document projection is published in 2f56a46: seven records -> thirteen fields, with lossless manifest and separate metrics. Next: resolve Delft/Aalto exact programme identity and Kazakhstan qualification/intake/fee/SAT gaps from primary sources into a NEW dataset version; use REVIEW_WORKSHEET_DRAFT3.md as the current 52-field review packet. Review real award/document identity aliases, finalize applicable field inventory and independently adjudicate support/currentness/conflicts. Obtain ten actual human reviewer/date signoffs before strict benchmark acceptance. No V2-10 until V2-01 is accepted.

Explicit offline identity mapping shipped in 5403630 and UNKNOWN handling in 00e107f; draft3 now aligns explicit .required/.maximum_words labels while retaining conditional alternatives. REVIEW_WORKSHEET_DRAFT2.md remains a frozen historical packet; use draft3 for current review. Review the three draft identity bindings and add aliases only after exact source/name checks; FAQs/Tuition Grants must not map to Nanyang Global. Resolve the remaining official-source gaps below, adjudicate full evidence and obtain actual human signoffs. Frozen draft1/draft2 and capture remain immutable. V2-10 still follows V2-01 acceptance only.

Draft2 annotation and separate offline report are prepared in backend/evaluation/research/REVIEW_DRAFT2.md. Next: resolve Delft/Aalto exact programme identity; complete Kazakhstan qualification, SAT, deadline/fee and document labels without transferring other-year/programme policies; replace generic unresolved families with a reviewed field inventory; review the implemented award/document identity bindings and align atomic label/value conventions; adjudicate full support/currentness/conflicts. Preserve frozen draft1 and capture. Obtain actual human reviewer/date for all ten cases, publish a newly versioned reviewed dataset, then run from backend: python -m evaluation.research --dataset <reviewed-dataset.json> --capture evaluation/research/baseline/capture.json --out ../artifacts/reviewed-metrics.json (strict, no --allow-drafts; refresh capture/adjudication where required). Human verification is 0/10. Only after V2-01 acceptance: V2-10 provider-neutral SearchProvider with a fake adapter. Older steps below are historical.


1. **Review and merge PR for `task/security-audit-hardening`.** Nine commits, backend + frontend +
   SECURITY.md. Reproduce the three proofs by checking out `main` and running the new tests there:
   `tests/test_payment_webhook.py::TestAnUnconfiguredSecretIsNotASecret`,
   `tests/test_transcript_import.py::TestTheUploadCannotStallTheService::test_a_slow_parse_does_not_block_an_unrelated_request`,
   `tests/test_social_moderation.py::TestBlocking::test_a_block_hides_the_card_from_the_direct_route_too`.
   All three fail on `main` and pass on the branch.
2. **Operational, before any deployment that takes money:** set `UNIMATCH_APIPAY_WEBHOOK_SECRET` (≥16
   characters, outside Git) and `UNIMATCH_PAYMENTS_PROVIDER=apipay`. The API now refuses to start
   otherwise, which is the intended behaviour, not a regression.
3. Then return to the queue in §10 as codex left it: T26's contract, T30's registry 19→60, T31 blocked
   on a provider. Nothing in this branch touches them.

The steps codex left, unchanged and still next after this review:

1. Resolve T26's contract before code: either authorize the API/frontend/ingestion paths needed for a
   real News vertical slice, or explicitly reduce acceptance to a storage-only foundation.
2. For T30 registry 19→60, supply/approve a 41-institution candidate list with official seeds and run
   bounded validation batches. Do not add entries that fail the frozen ≥2/4-category rule.
3. Keep T31 blocked until a provider, secrets outside Git and data-policy acknowledgement exist.
4. Update GitHub Actions dependencies away from Node-20-based action releases before GitHub removes
   the compatibility shim. Do not buy a provider or deploy application infrastructure implicitly.

## 6. Gate status at last run

Phase 3 §10, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 222 files; `pytest --cov=app --cov-fail-under=92` exit 0, **1957 collected**, 0
failed, coverage **94.61%**. Demo golden unchanged.

Phase 3 §9, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 221 files; `pytest --cov=app --cov-fail-under=92` exit 0, **1947 collected**, 0
failed, coverage **94.60%**. Demo golden unchanged.

Phase 3 §7, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 220 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1944 collected**, 0 failed, coverage **94.60%**. Demo golden unchanged.

Phase 3 §4, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 219 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1932 collected**, 0 failed, coverage **94.62%**. Demo golden unchanged.

Phase 3 §3, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 219 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1928 collected**, 0 failed, coverage **94.62%**. Demo golden unchanged.

Phase 3 §6, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 219 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1924 collected**, 0 failed, coverage **94.66%**. `GOLDEN_DEMO_SHA256` re-captured a sixth
time, additively.

Plan V2-30, gates run by claude-opus-5 on 2026-09-22, read in full: `ruff check` exit 0 (it failed
first on a Yoda condition in my own new test, fixed before pushing); `ruff format --check` exit 0, 219
files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92` exit 0, **1920
collected**, 0 failed, coverage **94.68%**. `GOLDEN_DEMO_SHA256` re-captured a fifth time, additively.

Plan V2-23 completion, gates run by claude-opus-5 on 2026-09-21, read in full: `ruff check` exit 0;
`ruff format --check` exit 0, 219 files; `mypy app tests evaluation` clean; `pytest --cov=app
--cov-fail-under=92` exit 0, **1916 collected**, 0 failed, coverage **94.68%**. `GOLDEN_DEMO_SHA256`
re-captured a fourth time — the first one that is not additive, with the three changed fields named
beside the constant.

Plan V2-20 exit criterion, gates run by claude-opus-5 on 2026-09-21, read in full: `ruff check` exit 0;
`ruff format --check` exit 0, 219 files; `mypy app tests evaluation` clean; `pytest --cov=app
--cov-fail-under=92` exit 0, **1912 collected**, 0 failed, coverage **94.67%**.

V2-30, gates run by claude-opus-5 on 2026-09-21, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 217 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1903 collected**, 0 failed, coverage **94.65%**.

V2-29, gates run by claude-opus-5 on 2026-09-21, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 217 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1900 collected**, 0 failed, coverage **94.66%**. Demo golden hash unchanged.

V2-24a, gates run by claude-opus-5 on 2026-09-21, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 216 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1896 collected**, 0 failed, coverage **94.66%**.

V2-28, gates run by claude-opus-5 on 2026-09-21, read in full: `ruff check` exit 0; `ruff format
--check` exit 0, 214 files; `mypy app tests evaluation` clean; `pytest --cov=app --cov-fail-under=92`
exit 0, **1883 collected**, 0 failed, coverage **94.61%**.

V2-27, gates run by claude-opus-5 on 2026-09-21, the way CI runs them and read in full: `ruff check`
exit 0; `ruff format --check` exit 0, 214 files; `mypy app tests evaluation` clean over 214 files;
`pytest --cov=app --cov-fail-under=92` exit 0, **1875 collected**, 0 failed, coverage **94.62%**.

V2-22b, gates run by claude-opus-5 on 2026-09-21, the way CI runs them and read in full: `ruff check`
exit 0; `ruff format --check` exit 0, 212 files; `mypy app tests evaluation` clean over 212 files;
`pytest --cov=app --cov-fail-under=92` exit 0, **1869 collected**, 0 failed, coverage **94.62%**.

V2-22a, gates run by claude-opus-5 on 2026-09-21, **the way CI runs them and read in full** (see the
§9 lesson about `| tail -1`): `ruff check` exit 0; `ruff format --check` exit 0, 211 files already
formatted; `mypy app tests evaluation` clean over 211 files; `pytest --cov=app --cov-fail-under=92`
exit 0, **1864 collected**, 0 failed, coverage **94.60%**. One alembic head, `c5d01b7e4f83`.

V2-20b, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1852 collected**, 0 failed, coverage
**94.58%**. `alembic heads`: one, now **`c5d01b7e4f83`**. Both new behaviours (lineage recorded; no
successor when the page stopped saying it) are covered by tests that drain the real job queue against
PostgreSQL, not by unit stubs. Demo golden unchanged — a demo run never re-reads a page.

V2-20a, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1848 collected**, 0 failed, coverage
**94.56%**. `alembic heads`: one, now **`a1f3c8d75e29`** (was `d9c4e7a21b83`) — the first migration this
session. PostgreSQL round-trip and the CASCADE behaviour are covered by tests that run against the real
database, not SQLite standing in for it. Demo golden hash unchanged.

V2-26, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1839 collected**, 0 failed, coverage
**94.55%**. `GOLDEN_DEMO_SHA256` re-captured a third time: **one added line, zero removed**, the proof
recorded beside the constant.

V2-25, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1835 collected**, 0 failed, coverage
**94.53%**. `GOLDEN_DEMO_SHA256` re-captured a second time, with the additive proof recorded beside it.
One of my own V2-24 tests failed **only in the full suite** and passed alone — it picked "the first
result row" and result ids are random, so it sometimes chose a result with no deadline claim. Fixed by
selecting deterministically; see §9.

V2-24, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1833 collected**, 0 failed, coverage
**94.53%**. Demo golden hash unchanged, as predicted in the write-ahead: nothing in the demo corpus is
declined, so no question is produced there.

V2-23, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1829 collected**, 0 failed, coverage
**94.52%**. The demo golden hash is **unchanged** — the rule is a no-op where a page states the intake
that was asked for, which is every page in the demo corpus.

V2-22b, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy over `app` and
`evaluation`; `pytest --cov=app --cov-fail-under=92` exit 0, **1823 collected**, 0 failed, coverage
**94.51%**. Re-scoring the frozen `baseline/capture.json` against `ground_truth.reviewed.json` produces a
report identical to `metrics.reviewed.json` — `wrong_scope_claim_rate` **5/5**, as it must be until a new
capture exists.

V2-22, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1820 collected**, 0 failed, coverage **94.51%**;
**18** tests in `tests/test_scope_reader.py`; `app/adapters/scope_reader.py` at **100%**.
`alembic heads`: one, `d9c4e7a21b83`, unchanged — still no migration; the scope rides in the JSON payload.
`GOLDEN_DEMO_SHA256` moved once, deliberately, with the additive proof recorded beside it (§8, §9).
No benchmark number changed yet, and none should have: this step *records* scope, it does not yet use it.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-21b, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1804 collected**, 0 failed, coverage **94.48%**.
`alembic heads`: one, `d9c4e7a21b83`, unchanged — no migration was needed.
The demo golden-hash guard failed on the first attempt and is green now without re-capturing it.

V2-21, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1798 collected**, 0 failed, coverage **94.46%**;
**28** tests in `tests/test_claim_scope.py`; `app/domain/claim_scope.py` at **100%**.
No benchmark number changed and none could: nothing reads the new type yet.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-13e, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1770 collected**, 0 failed, coverage **94.44%**.
**The acceptance here is that nothing changed**: every pre-existing test passes untouched with no
provider configured, which is what "dormant" has to mean. `seed_demo.py` was not re-run — it needs a
migrated database and this container has no working `Fetcher`; the demo path does not reach
`_add_search_results` without a provider, and CI runs the demo oracle on the PR.
Baseline unchanged: ceiling **10/10**, correct-at-rank-1 **4**.

V2-22a, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1767 collected**, 0 failed, coverage **94.51%**.
**Fifteen live runs this session.** New baseline, two agreeing runs: ceiling **10/10**,
correct-at-rank-1 **4** (was 2), committed as `baseline/search_probe.exa.hop.json`.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-13d, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1762 collected**, 0 failed, coverage **94.49%**.
**Thirteen live runs this session**; the last was one targeted Toronto run (6 queries) rather than a
full probe, because provenance made a full run unnecessary. Baseline unchanged: ceiling **10/10**,
correct-at-rank-1 **2**.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-11b, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1759 collected**, 0 failed, coverage **94.49%**.
**Twelve live runs this session.** Current baseline, shipped configuration, two near-identical runs:
ceiling **10/10**, correct-at-rank-1 **2**, 60 queries per run. Committed as
`baseline/search_probe.exa.hop.json`.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-13c, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format (193 files);
mypy (193 source files); `pytest --cov=app --cov-fail-under=92` exit 0, **1758 collected**, 0 failed,
coverage **94.49%**. The whole suite is the acceptance test here, because the cycle slugs widen a rule
the live pipeline already depends on.
**Ten live runs this session**, 50 queries each. Current baseline, shipped configuration:
ceiling **9/10**, correct-at-rank-1 **1**, committed as `baseline/search_probe.exa.hop.json`.
Rejected by measurement: page-kind ranking (ceiling 9/10, Warsaw lost) and dropping the `site:` prefix
(Aalto −6, three cases −1, rank-1 count 2 → 0).
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-13b, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format; mypy;
`pytest --cov=app --cov-fail-under=92` exit 0, **1746 collected**, 0 failed, coverage **94.49%**.
**Three more live runs, 50 queries each** (eight in total this session). Page-kind ranking with
positive hints: ceiling 9/10, four cases down. Negative hints only, twice, identical both times:
ceiling **9/10**, Toronto **#19 → #8**, everything else unchanged, Warsaw lost. Not enabled.
HKU's `hop_entry_points: 0` diagnosed: its hosts score correctly (`admissions.hku.hk` = 2) and the
site resets the connection from this container.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-16d, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format (193 files);
mypy (193 source files); `pytest --cov=app --cov-fail-under=92` exit 0, **1742 collected**, 0 failed,
coverage **94.54%**.
**Four live runs, 50 queries each.** Search only **9/10**; hop fused as an equal **8/10**; hop appended
inside the same budget **9/10** (contributing nothing); hop as additive coverage with scored entry
points **10/10**, KAIST #30, nothing moved down by the hop. HKU reads 5 → 6 in every hop run with
`hop_candidates: 0`, i.e. provider variance, not the hop.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-16c, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format;
mypy; `pytest --cov=app --cov-fail-under=92` exit 0, **1734 collected**, 0 failed, coverage **94.39%**.
**Two live runs, 50 queries each.** Search only: ceiling **9/10**, correct-at-rank-1 **2** — this is the
committed baseline. With `--hop`: ceiling **8/10**, and six of nine correct pages moved down. Not
shipped; `fetch` defaults to `None`.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-16b, gates run by claude-opus-5 on 2026-09-21. All green: ruff check and format (193 files);
mypy (193 source files); `pytest --cov=app --cov-fail-under=92` exit 0, **1734 collected**, 0 failed,
coverage **94.50%**; **21** tests in `tests/test_navigation_hop.py`; module at **100%**.
**Validated live against `https://cs.kaist.ac.kr/`:** 110 same-institution links kept, and
`content?menu=188` — the one case the search probe could not reach at all — comes back at **rank 3**,
with `/education/undergraduate` at 2.

Live probe + gates, claude-opus-5, 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (191 files); mypy (191 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1713 collected**, 0 failed, coverage **94.46%**;
`evaluation/research/search_probe.py` at **100%**. One Alembic head, `d9c4e7a21b83`.
**Live run:** 50 queries, 5 per case, 10 cases, zero provider failures, no case over the 25-result cap.
Retrieval ceiling **9/10** (was 1/10), correct-at-rank-1 **2**, cases with no candidates **0** (was 3).
This is a retrieval-only measurement: nothing is wired into `runner.py`, no claim was extracted, and no
strict-scoring number changed.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-10b (Exa adapter), gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite.
All green: ruff check and format (190 files); mypy (190 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1699 collected**, 0 failed, coverage **94.46%**;
**27** tests in `tests/test_exa_provider.py`; `app/adapters/search/exa.py` at **100%**.
One Alembic head, `d9c4e7a21b83`. **No live Exa call has been made** — every test uses a mock
transport, and the provider is `none` by default. No benchmark number changed.
`tests/test_search_provider.py::test_every_known_name_is_one_this_build_can_actually_build` failed as
designed when `exa` joined the set, and was updated deliberately.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-17, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (188 files); mypy (188 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1672 collected**, 0 failed, coverage **94.42%**;
**32** tests in `tests/test_programme_identity.py`; both new modules at **100%**.
One Alembic head, `d9c4e7a21b83`.
A test caught a real defect while it was being written: "There is no intake in 2027" matched the
*positive* intake pattern, so a page's denial read as its confirmation — the exact mechanism that
manufactures a wrong-scope claim. The negative check now runs first and a test pins the order (§9).
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-16, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (185 files); mypy (185 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1640 collected**, 0 failed, coverage **94.34%**;
**23** tests in `tests/test_fusion.py`; `app/adapters/search/fusion.py` at **100%**.
One Alembic head, `d9c4e7a21b83`. No benchmark number changed: fusion is not called from the pipeline.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-15, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (183 files); mypy (183 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1617 collected**, 0 failed, coverage **94.29%**;
**36** tests in `tests/test_site_search.py`; `app/adapters/search/site_search.py` at **100%**.
One Alembic head, `d9c4e7a21b83`. No benchmark number changed: detection is not yet called anywhere.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-14, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (181 files); mypy (181 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1581 collected**, 0 failed, coverage **94.23%**;
**13** tests in `tests/test_reranker_ceiling.py`; `evaluation/research/ceiling.py` at **100%**.
One Alembic head, `d9c4e7a21b83`.
**Measured, and it is the point of the step:** reranking ceiling **1/10**, already-first **1**,
headroom **0**, cases with zero candidates **3**. A test pins the committed
`ceiling.reviewed.json` against a fresh computation, so the finding cannot rot silently.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-13, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (180 files); mypy (180 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1568 collected**, 0 failed, coverage **94.23%**;
**29** tests in `tests/test_hybrid_retrieval.py`; `app/adapters/search/` at **100%** across all seven
modules. One Alembic head, `d9c4e7a21b83`.
No benchmark number changed and none could: no provider is configured and nothing calls the new path.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-12, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (177 files); mypy (177 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1539 collected**, 0 failed, coverage **94.12%**;
**29** tests in `tests/test_ontology.py`; `app/adapters/search/` at **100%** across all five modules.
One Alembic head, `d9c4e7a21b83`.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-11, gates run by claude-opus-5 on 2026-09-21, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (175 files); mypy (175 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1510 collected**, 0 failed, coverage **94.09%**;
**27** tests in `tests/test_discovery_intent.py`; `app/adapters/search/` at **100%** across all four
modules. One Alembic head, `d9c4e7a21b83`.
The first full run of this step was **red**: `test_a_slow_parse_does_not_block_an_unrelated_request`
failed at 0.56s against its own 0.5s margin. Unrelated to V2-11 and not a product defect — it was a
wall-clock assertion under container load. Rewritten to prove the property deterministically instead of
loosening the number (§9); passes repeatedly, and a real regression still fails it.
PostgreSQL and E2E not run locally — CI runs both on the PR.

V2-10, gates run by claude-opus-5 on 2026-09-20, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (173 files); mypy (173 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1483 collected**, 0 failed, coverage **94.02%**
(up from 93.97%); **22** tests in `tests/test_search_provider.py`; `app/adapters/search/` at **100%**.
Frontend re-run and green: typecheck, lint, 188 unit tests, build 366.79 kB js / 66.11 kB css.
One Alembic head, `d9c4e7a21b83`. `ruff` rejected a Yoda condition (SIM300) in the new test file and
`ruff format` reflowed it; both fixed before commit.
PostgreSQL and E2E not run locally — CI runs both on the PR.

Certified corpus, gates run by claude-opus-5 on 2026-09-20, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (169 files); mypy (169 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1461 collected**, 0 failed, coverage **93.97%**;
**66** focused V2-01 tests. Frontend untouched by this step. One Alembic head, `d9c4e7a21b83`.
The strict command — `python -m evaluation.research --dataset .../ground_truth.reviewed.json
--capture .../capture.json --out .../metrics.reviewed.json`, **no `--allow-drafts`** — exits 0 and
writes `provisional: false`. Every `draft*` dataset still raises under the same command, pinned by
`test_drafts_cannot_be_reported_as_human_verified`.
Baseline: programme precision 1/9, recall 1/10; claim precision 0/5, recall 0/62; wrong-scope claim
rate 5/5; critical coverage 0/210; primary-source rate 13/13; claim adjudication 5/13; support
adjudication 0/13. `metrics.reviewed.json` and `metrics.draft7.json` agree on every metric and field,
pinned by `test_certification_changes_no_measured_value`.
PostgreSQL and E2E not run locally — CI runs both on PR #14.

Draft7, gates run by claude-opus-5 on 2026-09-20, Linux / CPython 3.12.3 / SQLite. All green:
ruff check and format (169 files); mypy (169 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1458 collected**, 0 failed, coverage **93.97%**;
**63** focused V2-01 tests. Frontend untouched. One Alembic head, `d9c4e7a21b83`.
62/220 known fields, 10/10 identities, **0/10 human signoffs**; programme precision 1/9, recall 1/10;
claim precision 0/5, recall 0/62; critical coverage 0/210.
`test_published_baseline_replays_exactly_without_network[.draft7]` reproduces `metrics.draft7.json`
exactly with sockets blocked; strict scoring still refuses the corpus. `ruff format` had to be run once
on `tests/test_research_benchmark.py` after the parametrize list grew past the line limit.
PostgreSQL and E2E not run locally — CI runs both on PR #14.

Draft6, gates run by claude-opus-5 on 2026-09-20, Linux / CPython 3.12.3 / SQLite. All green:
`ruff check` pass; `ruff format --check` pass (169 files); `mypy` pass (169 source files);
`pytest --cov=app --cov-fail-under=92` exit 0, **1456 collected**, 0 failed, coverage **93.96%**;
**61** focused V2-01 tests pass. Frontend is untouched by draft6 and its gates were green the same day
(188 unit tests, build 366.79 kB js / 66.11 kB css). One Alembic head, `d9c4e7a21b83`.
Draft6 measures 61/219 known/total fields, **10/10** programme identities, **0/10 human signoffs**;
programme precision 1/9, recall 1/10; claim precision 0/5, recall 0/61; critical coverage 0/210.
`test_published_baseline_replays_exactly_without_network[.draft6]` reproduces `metrics.draft6.json`
exactly with sockets blocked, and strict scoring still refuses the corpus. PostgreSQL and E2E were not
run locally — CI runs both on PR #14.

Draft5 at `a4cd5b3`, gates run by claude-opus-5 on 2026-09-20 (the run gpt-6-astra was cut off during).
All green, Linux / CPython 3.12.3 / SQLite:

| Gate | Result |
|---|---|
| `ruff check app tests` | **pass** |
| `ruff format --check app tests` | **pass** — 169 files |
| `mypy app tests` | **pass** — 169 source files |
| `pytest --cov=app --cov-fail-under=92` | **pass** — exit 0, 1454 collected, 0 failed, coverage **93.96%** |
| focused V2-01 suites (benchmark + mapping + projection) | **pass** — **59** tests |
| `npm run typecheck` / `npm run lint` | **pass** |
| `npm test -- --run` | **pass** — 188 tests, 20 files |
| `npm run build` | **pass** — 366.79 kB js / 66.11 kB css |
| `alembic heads` | one head, `d9c4e7a21b83` |

Draft5 measures 61/219 known/total fields, 9/10 programme identities, **0/10 human signoffs**.
Programme precision 1/8, recall 1/9; claim precision 0/5, recall 0/61; critical coverage 0/210 — only
the last two denominators move from draft4, because the capture is the frozen one and this is an
annotation change, not a pipeline run. `test_published_baseline_replays_exactly_without_network[.draft5]`
reproduces `metrics.draft5.json` exactly with sockets blocked, and
`test_drafts_cannot_be_reported_as_human_verified` still refuses draft5 under strict scoring. The
frontend tree is byte-identical to green draft4 (`git diff 3f7e467 a4cd5b3 -- frontend/` is empty); its
gates were re-run anyway and pass. PostgreSQL and E2E were not run locally — CI runs both on PR #14.

Draft4 at 3f7e467: both complete CI runs SUCCESS (push 35535269941, PR 35535272542). SQLite/PostgreSQL 1452 passed each; SQLite app coverage 93.96%. Frontend 188 unit tests, 75 E2E passed/1 skipped and 6 auth E2E passed; security/containers green. Local Ruff lint/format and mypy pass (178 files); 57 focused tests pass. Exact offline replay passes and strict scoring rejects unverified cases. Programme precision 1/8, recall 1/9; claim precision 0/5, recall 0/56; critical coverage 0/206. Prior datasets/capture and other labels remain unchanged; operations identical. Production tree matches origin/main. Initial focused command had a nonexistent filename and was corrected before the successful run. Final handoff edits documentation only.

Draft3 at 2f56a46: both full CI runs SUCCESS, push 35519935738 and PR 35519937454. SQLite 1450 passed, 93.97% app coverage; PostgreSQL 1450 passed. Frontend 188 unit tests, 75 E2E passed/1 skipped and 6 auth E2E passed; security/container gates pass. Ruff lint/format and mypy pass (178 files); 55 local focused benchmark/mapping/projection tests pass. Seven document records losslessly project into 13 fields; 52/212 labels known, 0/10 human verified. Separate frozen-capture report: programme precision/recall 1/8, claim precision 0/5, recall 0/52, coverage 0/203. Only the last two aggregate denominators change from draft2; operations are identical. Strict scoring rejects draft3 without human certification. Production and frozen draft1/draft2 artifacts remain unchanged. Final handoff changes documentation only.

Identity mapping at 00e107f: both full CI runs SUCCESS (push 35518890037, PR 35518891993). SQLite 1446 passed, 93.96% app coverage; PostgreSQL 1446 passed; frontend 188 unit tests, 75 E2E passed/1 skipped and 6 auth E2E passed; security/containers passed. Ruff lint/format and mypy pass (177 files); 51 local focused benchmark/mapping tests pass. Actual saved NTU sidecar maps 10 raw claims to 10 predictions with 6 explicitly unmapped scholarship claims; final separate replay metrics and operations exactly match draft2. Earlier runs 35518736322/35518738766 were superseded and deliberately cancelled. Frozen corpora/captures/reports and production code unchanged. Final handoff changes documentation only and completes the 46-fact worksheet with conditions, source links and ten blank signatures.

Draft2 at 7356d9e: both complete CI runs SUCCESS, push 35503487143 and PR 35503488677. SQLite 1422 passed, 93.96% app coverage; PostgreSQL 1422 passed; frontend 188 unit tests, 75 E2E passed/1 skipped and 6 auth E2E passed; security/container gates pass. Local Ruff lint/format and mypy pass (174 files), 27 focused benchmark tests pass, and frontend typecheck/lint/build/188 tests pass. A diagnostic adapters run passed 71 tests. The redundant local full backend run was deliberately stopped after both full CI matrices passed (at >75%, no observed failures); it is not claimed as a completed local gate. Strict scoring rejects draft2 without human certification. Production app tree remains identical to origin/main. This final handoff changes documentation only.

V2-01: both CI runs at d0a2fb4 SUCCESS: push 35488937175 and PR 35488963787. SQLite 1420 passed, 93.97% app coverage; PostgreSQL 1420 passed; security/containers and frontend jobs passed. This final handoff changes documentation only. Local publication step: 25 benchmark tests pass, Ruff check/format and mypy pass (174 files). All 25 focused benchmark tests also pass with the PostgreSQL harness. No failing code gate remains. Frontend typecheck/lint/188 unit/build pass. pip-audit: no known vulnerabilities. npm audit: 2 moderate vulnerabilities, below high gate. Local initial SQLite run: 1394 passed, one KZT fixture encoding failure, 93.33%; same test passes with PYTHONUTF8=1, no production edits. Linux CI above passes both full matrices. Demo migrated in isolated database; Groningen first, UBC OUT_OF_BUDGET verified in stored results. One Alembic head d9c4e7a21b83. Local E2E: 75 passed, one skipped; auth E2E: 6 passed. Temporary LF launcher and generated screenshots restored. Prior numbers below are historical.
 (numbers, not adjectives)

Local runs by claude-opus-5, 2026-09-09, on `task/security-audit-hardening`.
Codex's C2 gate numbers for `main@04a3058` are in git history at `edf546d`; this table is the
historical security-audit run; current V2 evidence is above.

| Gate | Result |
|---|---|
| `ruff check app tests` | **pass** |
| `ruff format --check app tests` | **pass** — 166 files |
| `mypy app tests` | **pass** — 166 source files |
| `pytest --cov=app --cov-fail-under=92` | **pass** — **1395 passed**, coverage **93.96%** |
| `npm run typecheck` | **pass** |
| `npm run lint` | **pass** |
| `npm test -- --run` | **pass** — 188 tests, 20 files |
| `npm run build` | **pass** — 366.79 kB js / 66.11 kB css |
| `pip-audit -r requirements.txt` | **pass** — no known vulnerabilities |
| demo oracle (`seed_demo.py`, throwaway database) | **pass** — Groningen #1, UBC present; ordering unchanged |

E2E (`npm run e2e`, `npm run e2e:auth`) was **not** run locally — ports 5173/8099 and a browser install;
CI runs both on the PR.

## 7. Blockers / questions for the owner

### RESOLVED 2026-09-23 — the owner approved every recommendation ("Разрешаю твои рекомендации")
Implemented in this order, each with its own gates and commit (hashes in §3):
1. **Bindings:** the three draft identity bindings are approved; live scoring maps with them.
2. **Language key:** one key, `programme.language`; Aalto's label is renamed to it, and
   `program_exists`' stated teaching language is mapped onto it.
3. **HKU:** a school or listing page may confirm **existence only**, and only when it names the
   requested programme by a full degree title that the ontology's strong aliases equate with it.
4. **Support direction:** a quote is supported when ours lies inside the reviewer's, **or** the
   reviewer's lies inside ours and ours is at most 300 characters.
5. **Date → season:** only when the page states the programme's own start date; September–November →
   fall.

### OPEN — what claim_recall is allowed to count (2026-09-23, claude-opus-5)
The live ceiling is 14 of 62 (see §3). Each of these moves it, and each is an identity or definition
call, so none is mine to make:
1. **Review the three draft identity bindings and let live scoring use reviewed ones** (+14 NTU and
   KAIST scholarship facts).
2. **One key for teaching language.** Labels use both `programme.language` (Vienna, Warsaw) and
   `programme.teaching_language.primary` (Aalto). `program_exists` already carries the page's teaching
   language, so mapping it is cheap once there is one key. Mapping it also adds predictions to stored
   captures, which moves published denominators and needs a VERSIONS note.
3. **HKU:** the certified programme source is a school page that lists programmes. Should a listing
   that names "Bachelor of Engineering in Computer Science" confirm existence? The adapter's rule
   today is that only a programme's own page may.
4. ~~Vienna deadline~~ **withdrawn (claude-opus-5, 2026-09-23): my error.** The label's status is
   `unknown`, with the note "Published entrance-exam cycle is 2026, not a confirmed fall 2027
   deadline", so it is not in claim_recall's denominator at all. Nothing to decide.
5. **Which way "supported" contains.** The scorer requires our excerpt to lie inside the reviewer's
   (`evidence.excerpt in e.excerpt`). Reviewer excerpts are minimal, so a correct claim quoting the
   whole sentence is never supported, and claim_recall stays 0 whatever extraction does. Accepting the
   reverse (the reviewer's words inside ours) is a definition change: every published baseline would
   need regenerating plus a VERSIONS note. The `support_report` step shows the effect before anyone
   decides. Run 13: 0 of 6 value-correct claims are supported today; 2 would be under the reverse
   direction.

**RESOLVED 2026-09-22 — the six decisions below were approved by the owner ("делай по
рекомендациям") and implemented (see §3: `5d6b75d`, `38104d2` and the entries around them). The text is
kept as the record of what was asked.**

**Owner decision: may a programme-specific rule stay usable when a university-wide rule disagrees?**
The phase guide says yes — a general rule and a specific one may both be true, the specific one is
preferred for assessment, and the broader one is kept rather than deleted. Today both are stamped
`CONFLICTING`, which means neither can support a decision, and
`test_two_official_pages_disagreeing_produce_one_conflict` encodes that deliberately. The
classification is in (`MORE_SPECIFIC_SOURCE`); the behaviour is one small change plus that test's
rewrite, and it changes what an applicant is told, so it waits for you.

**Owner decision, not urgent: should an unchanged claim still be superseded?** V2-24a can now tell a
material change from a re-render. Today `reextract_page` supersedes every live claim over a re-read
URL, so a page that merely re-rendered leaves a full generation of history repeating what the live rows
already say. Skipping supersession for `UNCHANGED` claims (and only refreshing their `accessed_at`, so
freshness still advances) would keep history meaningful — but it contradicts the T32 contract that
supersession is per source URL, which `test_a_forced_page_change_supersedes_old_and_appends_new_in_one_commit`
encodes deliberately. I will not quietly rewrite another campaign's contract; say the word and it is a
small change plus that test's rewrite.

**Owner decision — now the whole metric, no longer "not urgent": should the scorer compare programme
*identity* instead of programme *strings*?** After run 35697105238 there are **two** scope mismatches
left, both NTU's name, and one of them is a strong alias. This single decision is now the difference
between `wrong_scope_claim_rate` 2/2 and 1/2; no further pipeline work moves it. `wrong_scope_claim_rate` counts NTU's `Bachelor of Computing (Hons) in Computer Science`
as a wrong-scope claim against a label reading `Computer Science`. By the ontology's own strong
aliases those name one programme. Changing the comparison would change what the benchmark *means*, so
I built the evidence and left the number alone: `scope_report` prints such cases separately, marked
"reported, not counted". Two ways to settle it, both yours: adjudicate the label (write the full
official title into the corpus, re-signed), or accept identity comparison as the scorer's rule.

**Owner decision, surfaced by EXTRA-11: a per-section English minimum has nowhere to live.** NTU's
certified value is `{"overall": 6, "writing": 6, "speaking": 6}`; `ielts_min_subscore` holds one
number. Collapsing them to a floor converts a value silently, which this repository forbids, so the
named sections are currently dropped. Fixing it means either a claim type per section or a mapped
value — both change a stored contract, so it waits for you.

**Owner decision, surfaced by V2-30: should two pages scoped to different qualifications be a
conflict?** They classify as `TRUE_CONFLICT` today, because `_KIND_BY_DIMENSION` has no
`DIFFERENT_QUALIFICATION` member. "The Abitur route requires X" and "the attestat route requires Y" are
not a contradiction — they are two scopes — but adding an enum value touches a stored contract, so it
waits for you.

**Owner decision, surfaced by EXTRA-6: may the catalogue walker keep a neighbouring subject?** The
walker confirms its own candidates and, under the T29 contract, trusts a university's own catalogue
listing: `test_r5_js_json_payload_yields_programs` asserts that a BSc **Mathematics** entry survives for
an applicant who asked for computer science. The step-4 filter would refuse it
(`profile_rejects` compares the subject). I found this by making the new pass judge the walker's output
too, watched that test go red, and narrowed the pass rather than rewrite another campaign's contract.
Say the word and the walker uses the same predicate as everything else.

**Owner data, also not urgent:** the ontology has no plural entry for `computer sciences`, so NTU's
`Mathematical and Computer Sciences` resolves to UNKNOWN. That is the safe answer — a joint degree is
not a single-subject one — but if you judge them equivalent, it is one line of ontology data with your
name on it.

**KAIST seed: delivered 2026-09-22.** No longer a blocker. One open, low-stakes question: `menu=320`
(Undergraduate Curriculum Roadmap) was supplied but has no category left — say the word and it replaces
`menu=318` as `program_page`.

**The live capture now has a button** (`benchmark-capture` workflow), but the workflow only becomes
runnable once PR #16 is merged: GitHub registers a `workflow_dispatch` only from the default branch.

### RESOLVED — the owner approved a bounded exception to `AGENTS.md` §6 (2026-09-21)

The owner answered **yes**: a configured search provider behind the `app/adapters/search` seam may call its vendor API directly. `AGENTS.md` §6 has been **amended to say so**, because an unamended "not negotiable" rule with a live exception is worse than either answer. The exception is bounded to that seam; fetching any page a provider returns still goes through `Fetcher`, and no other network path is exempt. The owner also authorised using the current Exa key for this measurement work and will rotate it afterwards.

The argument, kept for the record:

### (historical) The conflict as it was put

Two documents the owner approved disagree, so per §6 this is raised rather than decided.

`AGENTS.md` §6: *"Do not weaken `Fetcher` (robots, rate limit, PII guard); no network outside it."*
`analysis/v2/04_PHASE_1_DISCOVERY_ENGINE.md` §1 requires a provider-neutral `SearchProvider`, which is
by definition an HTTP call to a vendor.

Why `Fetcher` is the wrong instrument for this one call, and what replaces each guarantee it gives:

- **robots.txt** governs crawling a site's pages. It does not govern an API the vendor sells access to
  and which is called under a contract. Applying it here would mean asking `api.exa.ai/robots.txt` for
  permission to use a key we paid for.
- **Rate limiting** is the provider's quota, enforced by the provider. The adapter adds its own bounds:
  `numResults` capped at 25, no retries at all, a 15-second timeout, and `DEFAULT_QUERY_BUDGET` of 6
  queries per institution.
- **The PII guard** is replaced by something stronger and earlier: V2-11 makes it structurally
  impossible for applicant data to reach a provider — `search()` takes a query string, `DiscoveryIntent`
  has no field for an applicant, and its values are validated against emails, grades, currency and long
  digit runs. There is a test per forbidden item.
- **SSRF / egress**: kept. The endpoint goes through the same `network_policy.check_url` the rest of the
  service uses, redirects are not followed, and the response body is capped at 1 MiB.

**The question:** approve this as a bounded, documented exception to §6 for search providers only — in
which case §6 should be amended to say so, since an unamended "not negotiable" rule with a live
exception is worse than either — or reject it, in which case Phase 1's web-search generator is dead and
`04_PHASE_1` §1 should be struck from the roadmap. Either answer is workable; the current state is not.

Nothing is enabled meanwhile: `UNIMATCH_SEARCH_PROVIDER` defaults to `none`, and with `exa` selected
and no key the service refuses to start rather than reporting every search as finding nothing.

### Recommended provider, and why (2026-09-21, claude-opus-5)

Exa, on its free tier, chosen and registered by the owner. A full benchmark run is ~60 queries, so cost
is not the deciding factor — engineering time per adapter is, and the V2-10 seam makes switching a
configuration change. The reason to prefer a neural index: this project's existing generators (sitemap,
catalogue walker) are structural and keyword-shaped, and they find the right page for one institution
in ten. A new generator is only worth its code if it fails *differently*.


### OPEN — Phase 1 is now blocked on one purchase (2026-09-21, claude-opus-5)

The V2-14 ceiling measurement says the 1/10 recall is entirely a retrieval failure and that no
reranker can win a single case. Retrieval is what needs work, and the cheapest large step is a web
search provider behind the V2-10 seam — three of ten cases retrieved *no candidates at all*, which a
search engine would almost certainly have fixed.

That needs a provider chosen, a paid key held outside Git, and its data policy accepted. All three are
owner decisions. `UNIMATCH_SEARCH_PROVIDER` stays `none` until then, which is a supported
configuration, not a broken one.

V2-15 (university internal search) is the retrieval work that needs no key, and is the recommended
next step if the provider decision will take time.


### RESOLVED — both questions from the draft6/draft7 review (owner, 2026-09-21)

The owner answered "всё правильно" to both and supplied the reviewer identity **Диас / 2026-09-21**.
That accepts Aalto's English-taught Computer Engineering major as satisfying the computer-science
request, and certifies all ten cases. The Aalto decision is the one place in this corpus where a human
overrode the conservative reading; it is recorded as such in the case notes, and revisiting it returns
that case to `unknown`. The questions as they were put:

### (historical) OPEN — two questions from the owner's draft6 review (2026-09-20, claude-opus-5)

1. **Does Aalto's English-taught Computer Engineering major satisfy a request for *computer science*?**
   Aalto describes it as combining information technology and electrical engineering. Draft2 refused to
   treat Data Science as computer science on the same reasoning, so answering "yes" here without a
   decision would be inconsistent. If the answer is no, the Aalto case goes back to
   `programme_status: unknown` and Aalto has no English-taught CS bachelor for this applicant — which is
   itself a useful finding. Not an AI's call.
2. **A reviewer name and a date.** Eight cases are approved and cannot be recorded as such without them.
   This is the single thing standing between V2-01 and acceptance.


### V2 reconciliation, 2026-09-20 (acceptance still incomplete)
- Startup base and origin/main were b267b337; task HEAD is recorded in section 1. PR #13 is OPEN (crawler offload); no merge or overlapping production edits. PRs #11/#10/#1 also remain open.
- Original checkout has modified HANDOFF, untracked research schemas/tests and package-lock.json; preserved untouched in `task/1.1-research-contracts`. Its 2026-09-17 local notes report 51 schema tests and a KZT test failure; these are not merged baseline facts.
- Isolated V2 worktree starts from main. Five unpushed payment commits in sibling worktree are outside scope.
- Future pack country-name queries conflict with preferences_only I3; retain current privacy contract pending owner decision. Future field ontology treats software engineering as related whereas existing spec lists it under CS; no ontology change here.
- Human review cannot be impersonated by an AI. Prepare evidence-backed draft cases; acceptance needs an actual human reviewer. This blocks final dataset certification, not harness work.


### OPEN — residual security risks found and deliberately left alone (2026-09-09, claude-opus-5)

Listed so the next holder does not rediscover them and assume they were missed. None is a defect in
this branch; each is a judgement the owner may want to revisit.

1. **`job.last_error` is shown verbatim** to a workspace owner through `/api/admin/jobs`. Capped at
   4000 characters, scoped to that tenant's own runs, and the route argues for it explicitly — but a
   driver exception can carry connection detail. Low.
2. **`--forwarded-allow-ips=*` on Fly** (`fly.toml`, `Dockerfile.fly`) with
   `UNIMATCH_TRUST_PROXY_HEADERS=true`. Correct behind the edge; anything that reaches the app port
   directly on the private network can invent an `X-Forwarded-For` and walk around the per-address
   limiter. Pre-existing and documented as a trade-off.
3. **`GET /api/social/messages/{user_id}` writes** (marks the thread read) and the session cookie is
   `SameSite=Lax`, so a top-level navigation carries it. Impact is a read receipt; noted, not fixed.
4. **`fly.toml` sets no `UNIMATCH_EMAIL_SENDER`.** Production refuses to start on `console`, so the
   deploy fails until SMTP is configured as a secret. The guard working, not a bug — but it will look
   like one at 3am.
5. **Session cookie could use the `__Host-` prefix** (it already satisfies every condition). Not done:
   renaming the cookie invalidates every live session and the name is configurable.
6. Egress residuals (Chromium's own DNS resolution, browser-internal redirects) were already recorded
   in `SECURITY.md` §Known residual risks and still stand.


### RESOLVED — I4 / T3 wording vs the approved formula (2026-09-06, owner-delegated)

The owner was shown the conflict and delegated the call ("делай так как считаешь правильным").
**Resolution: the formula stands as approved; T3's literal wording does not.** Recorded here so the
next agent does not reopen it.

- D1 (weighted geometric mean over known axes) and D2 (coverage separate, γ = 0.5) are final and were
  not reopened. The implementation matches `analysis/reference/ranking_v2.py::aggregate`.
- Literal T3 — "known → UNKNOWN never lowers fit" — cannot hold for **any** honest aggregation over
  known axes: fit is a mean, so removing an axis above the mean lowers it and removing one below it
  raises it. The only way to satisfy the literal wording is to impute unknown axes at or above the
  current mean, i.e. to score a university on data nobody verified. That is the one thing this product
  refuses to do, and imputation is rejected in `docs/adr/0003-noncompensatory-ranking.md`.
- The invariant that **is** true, and is what I4 exists to protect (brief P6): *an unverified axis is
  never scored against a row.* It leaves `fit` entirely and lowers `coverage` only, which
  `sort_key = fit · coverage^γ` then discounts. `test_an_unknown_axis_is_never_scored_as_a_failed_one`
  pins exactly that, and `test_an_unknown_axis_lowers_coverage_by_exactly_its_weight_share` pins the
  second half of T3 verbatim.
- Not changed: brief, spec, reference implementation, ADR, or any committed formula. The wording of
  I4/T3 in `analysis/AI_TASK_BRIEF.md` §4/§8 and `analysis/SPEC_matching_v2.md` §10.1 is now known to
  be stronger than the model it describes; leave the documents alone and read them through this note.

### Open

- **GLM completion claim is superseded.** Its code contribution is real and locally green, but only
  5/24 task cards were integrated. T18's declared T08/T13/T16/T17 dependencies are unmet; T25/T26 are
  backlog; live NU verification completeness is 0%; provider-backed search/LLM and deploy do not exist.
- **Evidence provenance is only partly machine-verifiable.** All five acceptance packets pass
  `check_team.py packet`, but that command checks shape/non-empty strings, not the identity of runtime
  agent IDs or the semantic authenticity of logs. Published `ai-team/` has 31 files with absolute
  `/Users/wpalish` paths; the owner explicitly accepted them as forensic evidence. No
  secret-like material was found by the audit scan.
- **Public deployment still needs a separate release-security pass.** Staging currently permits the
  console reset-mail sender, and browser egress hardening in the separate master-fix worktree has not
  been reconciled into this branch. Do not call the current candidate deployment-ready.

- **PR #6 recovery review (2026-09-06, gpt-6-astra + independent subagent): addressed locally.**
  P1: the first patch folded coverage into Match, removing the brief's independent Confirmed column
  and its screen-reader column semantics. The review fix restores a distinct `<th>/<td>` and uses an
  explicit ten-column width budget. P2: the original overlap had no regression assertion; the new
  Playwright check stresses the actual chip with `Well placed`, proves at 1440 px that its right edge
  stays before Decision, keeps the button group inside its cell, and rejects table overflow. P2: §3/§6 and the PR evidence
  were stale after PRs #4/#5; this recovery refreshes them on `origin/main@85352b5`. The findings were
  also posted to PR #6. Final independent re-review approved the corrected staged diff with no
  remaining direct-scope findings; refreshed GitHub CI remains before owner merge.
- **Resolved by PR #4:** `task/docker-stack-verification` itself remains stale, but all of its wanted
  content except the independently re-applied shortlist fix reached `main` through `docs/catch-up`.
  Do not rebase or merge that old branch; branch deletion is housekeeping for the owner.
- The `[0.1]`–`[0.7]` commits still carry no `Agent:` trailer (they predate `AGENTS.md`). Merged as
  they are; do not rewrite that history.

## 8. Contract changes since the brief (append-only; the other agent reads this before coding)

Evaluation-only addition: identities.py validates source/name bindings; mapping.py splits award/document facts; map_claims.py writes hashed offline mapping reports or separate replay captures. No production API/schema or migration change.

V2-01: evaluation-only Pydantic schema and JSON corpus/capture/metric contracts under backend/evaluation/research; separate offline scorer and opt-in bounded live CLI. Evidence excerpt_truncated prevents shortened publication snippets from creating automatic support. Production models/API/domain unchanged; app tree hash 5c98f59a1f56eaa22e6cd76546ef3039e2e2eee5 matches b267b337. No migration; head d9c4e7a21b83.

| Date | Task | Change (path · field/signature) | Why |
|---|---|---|---|
| 2026-09-05 | setup | Brief §1 counts are stale: main now has **818** backend tests (not 785), **19** institutions in `institution_registry.json` (not 10), `domain/transcript.py`, i18n scaffolding in `frontend/src/lib/i18n.ts`, and `types.ts` grew. Anchors in the brief (`_stage_verify` L344, `_stage_assess` L722, `_update_result` L973, `ExplainableScore` L166, `UnresolvedQuestion` L96) are still correct. | keeps the brief honest without rewriting it |


| 2026-09-05 | [0.1] f23407f | `schemas/profile.py`: `PriorityGroup` six literals; `Preferences.priorities=[]` with uniqueness validation, `research_privacy="preferences_only"`; `ApplicantProfileIn.weights_override=False`; default priorities constant | Observed committed schema; not acceptance. |
| 2026-09-05 | [0.2] ea33051 | `domain/priorities.py`: priority/ROC axis weights module | Observed committed weighting source. |
| 2026-09-05 | [0.4] 3eefdcd | `domain/enums.py::Bucket`: WELL_PLACED, PLAUSIBLE, AMBITIOUS, OUT_OF_BUDGET, NEEDS_CLARIFICATION, EXCLUDED | Six committed portfolio categories. |
| 2026-09-05 | [0.4] 3eefdcd | `schemas/result.py::AxisScore`: axis/value/state/weight/reason/evidence_claim_ids; `RankingV2`: fit/coverage/sort_key/gamma/axes/unknown_axes/not_applicable_axes/knocked_out_by/bucket/bucket_reason/weights_source/version/disclaimer | Observed serialized ranking contract. |
| 2026-09-05 | [0.4] 3eefdcd | `ProgramResult.ranking`, `catalog_attributes`, `catalog_attributes_source`; `preference_score` retained | Stored attributes permit recalculation; v1 remains represented. |
| 2026-09-05 | [0.3] 0f46079 | `domain/ranking_v2.py` and `domain/scoring.py` changes | Geometric ranking and portfolio implementation; unresolved T3 semantics (§7). |
| 2026-09-05 | [0.5] 0b8d97f | `config.py::Settings.ranking_version=2`, `ranking_gamma=0.5` (`UNIMATCH_RANKING_VERSION`, `UNIMATCH_RANKING_GAMMA`) | Committed config defaults. |
| 2026-09-05 | [0.5] 0b8d97f | `ProgramResultRow.bucket`; migration `a4d1c7e58b92` from `e7c4a91b6f20`, adds non-null `program_results.bucket` string(40), server default empty, index `ix_results_bucket` | Observed ninth revision; do not rewrite an existing main migration. |
| 2026-09-05 | [0.6] e1d8078 | `pipeline/runner.py::apply_fit_labels`, `store_result`; `POST /api/runs/{run_id}/rerank` | Request priorities/preferences/funding/weights/gamma (0–2)/persist(false); response rows/gamma/weights_source; persisted audit action `results_reranked`. |
| 2026-09-05 | [0.6] e1d8078 | `GET /api/runs/{run_id}/results`: bucket filter, sort key/fit/coverage/gap/deadline (default key) | Observed list API additions. |
| 2026-09-05 | [0.6] e1d8078 | `GET /api/runs/{run_id}/shortlist`: chosen/notes/quotas; defaults size=10, min_well_placed=2, min_plausible=4, max_ambitious=3, max_per_country=3 | Observed balanced-list API; rejected rows omitted. |
| 2026-09-06 | [0.8] | `/api/vocabulary` gains `bucket` (six values); `tests/test_frontend_contract.py::CONTRACT` gains `Bucket` → `types.ts` must keep the union in step | The contract test demands every contracted type be readable at runtime, so the UI never hard-codes a bucket string. |
| 2026-09-05 | recovery | Historical setup row above is retained append-only, not revalidated as current test counts/line anchors; [0.8] frontend contracts are uncommitted and under separate audit | Keeps history without upgrading old claims to acceptance. |
| 2026-09-07 | T10 audit | `worker.py`: failed fenced retry after a non-terminal payment poll raises `LeaseLost`; provider journal/order changes roll back with the transaction | A stale worker must commit no money-adjacent writes. |
| 2026-09-07 | T18 audit | `live_discovery.py`: `edu.kz` multipart suffix; `_confirm_programs(..., profile)` filters fetched pages by requested level and subject | Live NU run otherwise selected an MSc and Mathematics ahead of BSc Computer Science. |
| 2026-09-09 | security audit | `config.py`: new `upload_rate_limit_per_minute=6`; `smtp_password` is now `SecretStr` (call sites need `.get_secret_value()`); `validate_runtime` gains `_validate_payments`, and `MIN_WEBHOOK_SECRET_CHARS=16` is module-level | New limiter group and payment startup guards. |
| 2026-09-09 | security audit | `export/tabular.py`: new public `neutralize(value)`, applied to every exported cell | Formula injection. |
| 2026-09-09 | security audit | `payments/errors.py`: new `UnconfiguredWebhookSecret`; `get_provider()` no longer defaults the fake's secret | A missing secret is now an error, not a default. |
| 2026-09-09 | security audit | `frontend/src/components/primitives.tsx`: new exported `isSafeHref(url)` | Non-http(s) sources render as text. |
| 2026-09-21 | V2-22a | New `app/domain/entity_resolution.py`; nothing calls it yet | Purely additive. `dedupe.university_key` keeps every existing caller until V2-22b measures the replacement. |
| 2026-09-21 | V2-20b | `claims.superseded_at`, `claims.superseded_by_id` (FK to `claims.id`, ON DELETE SET NULL); `alembic heads` moves to `c5d01b7e4f83` | Additive: both nullable, both empty on every existing row. A NULL successor on a superseded row means the page no longer says it — do not backfill it. |
| 2026-09-21 | V2-20a | New table `source_snapshots`; `alembic heads` moves to `a1f3c8d75e29`; `SourcePage.record` also writes a snapshot when it has a content hash | Additive. No existing row, column or payload changes. A fetch with no content hash records no version. |
| 2026-09-21 | V2-26 | `ConflictKind` in `app/domain/enums.py`; `Conflict.kind` (defaults to `TRUE_CONFLICT`); a non-true conflict no longer stamps its claims `CONFLICTING` | Additive on the payload (one key). Behaviour change only where two claims state differing scopes — previously both were poisoned. |
| 2026-09-21 | V2-25 | All five claim-producing adapters set `scope`; `GOLDEN_DEMO_SHA256` re-captured (second time) | Additive again — proven before the hash moved. A bare year range no longer scopes a page; it needs a marker beside it. |
| 2026-09-21 | V2-24 | `EligibilityOutcome.out_of_scope: list[OutOfScopeClaim]`; results gain `UnresolvedQuestion`s for declined evidence | Additive on both. No new API or frontend field — the questions ride the existing `unresolved` channel. |
| 2026-09-21 | V2-23 | `eligibility._first` / `_confirmed` take a `RequestedScope`; a claim whose recorded scope contradicts the request is not used, and one silent on it cannot be a hard filter | Behaviour change for claims that have a recorded scope only. `scope is None` is untouched. The requested scope holds the intake and nothing else: the academic year on a claim is a server default. |
| 2026-09-21 | V2-22b | `evaluation/research/mapping.evidence_scope`; `live.py` and `map_claims.py` build an evidence scope through it | A capture taken from now on records what the page stated, not what the run asked for. Claims with no `scope` key keep the old request-side behaviour on purpose, so frozen captures re-score identically. |
| 2026-09-21 | V2-22 | `ClaimBuilder(scope=...)`; `web_requirements` claims now carry a `scope` object in their persisted payload; `GOLDEN_DEMO_SHA256` re-captured once | The drift was proven additive before the hash moved (0 removed lines, every addition inside a claim's `scope`), and that proof is recorded beside the constant. A claim without a scope still serialises byte-identically. |
| 2026-09-21 | V2-21b | `app/schemas/claim.py`: `Claim.scope: ClaimScope | None = None`, omitted from serialisation when `None` | No migration: `ClaimRow.payload` is JSON. `None` (nobody recorded one) and `ClaimScope()` (a page that stated none) are different facts — do not collapse them. |
| 2026-09-21 | V2-21 | `app/domain/claim_scope.py`: `ClaimScope`, `RequestedScope`, `SCOPE_DIMENSIONS` (nine), `covers() -> Verdict`, `contradictions`, `gaps`, `narrower_than`, `explain`, `from_mapping` | `covers()` returns a `Verdict`; coercing it to a bool at a call site reintroduces the wrong-scope failure. Nothing reads it yet. |
| 2026-09-21 | V2-13e | `LiveDiscoveryAdapter._add_search_results(...)`; programme pages from search are appended to `selected[PageCategory.PROGRAM_PAGE]` | **The first change on this branch that touches live pipeline behaviour.** Dormant unless `UNIMATCH_SEARCH_PROVIDER` is set. |
| 2026-09-21 | V2-22a | `live_discovery.is_seed_host(url)`; `SIGNAL_WEIGHTS["registry_seed_host"]` | Reads `institution_registry.json`'s homepage and seeds. Adding a verified host to an entry changes ranking — it is data with a `seeds_verified_on` date, so it needs a human check like the corpus. |
| 2026-09-21 | V2-13d | `RankedCandidate.found_by: tuple[str, ...]`; `rank_candidates(..., found_by=...)` | Discovery provenance per §11. A hop candidate has an empty `found_by` and carries `found_by_navigation_hop` in its signals instead. |
| 2026-09-21 | V2-11b | `intent.py`: new `natural_language` family and `_degree_in_words`; the family list is now six | Adds a shape, replaces nothing. Costs one more query per case — check `DEFAULT_QUERY_BUDGET` before adding a seventh. |
| 2026-09-21 | V2-13c | `live_discovery._DEGREE_SLUGS`: Bologna cycle forms added to every level; `queries_for(..., site_prefix=True)` | A shared rule every generator reads. `site_prefix=False` was measured and is worse — the switch stays for the next provider. |
| 2026-09-21 | V2-13b | `page_classifier.classify_url(url) -> PageType`; `rank_candidates(..., rank_by_page_kind=False)`; `RetrievalReport.hop_entry_points_unreachable` | `classify_url` is URL-only and deliberately negative-only. The ranking signal is off; re-enable only with a run holding the ceiling at 10/10. |
| 2026-09-21 | V2-16c | `retrieval.py`: `discover_candidates(..., fetch=None, hop_entry_points=3)`, `FetchPage`; `RetrievalReport.hop_entry_points` / `.hop_candidates` | The hop is **off** unless a caller passes `fetch`. Production must pass a `Fetcher`-backed reader. |
| 2026-09-21 | V2-16b | `app/adapters/search/navigation.py`: `links_from`, `navigation_candidates`, `NavigationLink`, `MAX_LINKS_PER_PAGE`, `DEFAULT_HOP_LIMIT` | Reads HTML it is handed; fetches nothing. Emits `Generator.CATALOGUE_WALKER` candidates for `fuse`. |
| 2026-09-21 | probe | `evaluation/research/search_probe.py`: `probe_case`, `run`, CLI `python -m evaluation.research.search_probe --live` | Evaluation tooling; refuses to run without `--live` and a key. Re-run after any retrieval or ranking change. |
| 2026-09-21 | V2-10b | `app/adapters/search/exa.py`: `ExaSearchProvider`, `EXA_SEARCH_URL`, `MAX_RESULTS_PER_QUERY`, `MAX_RESPONSE_BYTES`, `DEFAULT_SEARCH_TYPE`; `config.py`: `exa_api_key: SecretStr`, `exa` in `KNOWN_SEARCH_PROVIDERS` | Off by default. Highlights live only in `SearchResult.snippet` and may never be cited — fetch the page through `Fetcher` first. |
| 2026-09-21 | V2-17 | `app/domain/programme_identity.py`: `Verdict`, `ProgrammeIdentity`, `IdentityState`, `ScopeState`, `IDENTITY_DIMENSIONS`, `SCOPE_DIMENSIONS`; `app/adapters/search/identity.py`: `verify_candidate` | Six dimensions, never one score. `applies_to_requested_intake()` returns a `Verdict` — do not coerce it to a bool at a call site, that reintroduces the wrong-scope failure. |
| 2026-09-21 | V2-16 | `app/adapters/search/fusion.py`: `fuse`, `Generator`, `GENERATOR_WEIGHTS`, `SourcedCandidate`, `Attribution`, `FusedCandidate`, `RRF_K` | Rank fusion, never score fusion — a BM25 score and a sitemap position are not comparable. Weights are trust, not quality, and are untuned on purpose. |
| 2026-09-21 | V2-15 | `app/adapters/search/site_search.py`: `detect_surfaces`, `search_url`, `SiteSearchSurface`, `SiteSearchKind`, `Provenance`, `NEEDS_CREDENTIALS`, `MAX_PAGES`, `MAX_RESPONSE_BYTES` | Detection only — fetching stays with `Fetcher`. Never probes, never reads a page's API key, never leaves the institution's registrable domain. |
| 2026-09-21 | V2-14 | `evaluation/research/ceiling.py`: `compute_ceiling`, `CeilingReport`, `CaseCeiling`, CLI `python -m evaluation.research.ceiling` | Evaluation tooling, never production. Re-run after any retrieval change; `baseline/ceiling.reviewed.json` is pinned by a test. |
| 2026-09-21 | V2-13 | `app/adapters/search/prefilter.py`: `prefilter`, `PrefilterOutcome`, `PrefilteredCandidate`, `RejectedCandidate`, `Rejection`, `ALLOWED_SCHEMES`; `retrieval.py`: `discover_candidates`, `rank_candidates`, `RankedCandidate`, `RetrievalReport`, `SIGNAL_WEIGHTS`, `tokenize`; `live_discovery.py` gains public `is_excluded_path` | The retrieval path. Reuses the existing URL helpers deliberately — a second copy would drift. Only the deterministic layer and BM25 ship; embeddings, cross-encoder, Jev and LLM stay a seam per §6. |
| 2026-09-21 | V2-12 | `app/adapters/search/ontology.py` + `ontology.json` (version `2026-09-21.1`): `canonical_field`, `is_equivalent`, `retrieval_candidates`, `degree_aliases`, `ontology_version`, `Relation`, `RetrievalCandidate` | Vocabulary for retrieval. `is_equivalent` consults strong aliases only; `related_not_equivalent` terms are candidates and never matches. Bump the file's `version` with any vocabulary change. |
| 2026-09-21 | V2-11 | `app/adapters/search/intent.py`: `DiscoveryIntent` (`institution`, `domain`, `degree`, `field`, `intake_year`, `population_marker`) with `from_profile` / `without_intake`; `DiscoveryQuery`; `queries_for(intent, *, budget, families)`; `QueryAuditRecord` + `redacted_audit_record`; `QueryPrivacyError`; `DEFAULT_QUERY_BUDGET = 6`; `ALLOWED_POPULATION_MARKERS = {international, Kazakhstan}` | Query generation takes an intent, never a profile. Adding a field to `DiscoveryIntent` is the change that needs reviewing. |
| 2026-09-20 | V2-10 | new package `app/adapters/search/`: `SearchResult`, `SearchResponse`, `SearchProvider` Protocol (`async search(*, query, domains=(), max_results=10)`), `SearchError` / `SearchProviderNotConfigured` / `SearchUnavailable`, `get_search_provider()`, `KNOWN_SEARCH_PROVIDERS`; `FakeSearchProvider(corpus, *, now, fail_with)` | The provider seam. No caller yet; import `get_search_provider`, never an adapter. |
| 2026-09-20 | V2-10 | `config.py`: `search_provider: str = "none"` (`UNIMATCH_SEARCH_PROVIDER`); `validate_runtime` gains `_validate_search` | An unknown name is refused at startup; `fake` is refused in production. `none` is a supported configuration, not a misconfiguration. |
| 2026-09-09 | security audit | `security.py`: `SCRYPT_R`, `SCRYPT_P`, `_maxmem(n, r)`; `routes_metrics` compares bytes | scrypt cost schedule and the 500-on-non-ASCII bearer. |

## 9. Traps and lessons (things that cost a session; keep them)

V2-01: set PYTHONUTF8=1 on Windows for text fixtures; do not modify evaluation schemas while a live batch is running (parent and child processes can import different versions). Instrumented baseline segments and restart are recorded in baseline/README.md. Scope matching is deliberately literal; missing/different names count as conservative match failures, not human-confirmed wrong facts.

- **A synthetic fixture corpus cannot catch a markup bug.** The demo corpus writes requirements as
  prose in `<p>` tags, so the golden hash — the strongest regression guard in this repository — stayed
  byte-identical while every extractor was being handed pages with the requirements deleted out of
  them. When fixtures are written by the same hand as the parser, they share its blind spot. Any
  fixture meant to protect extraction has to be shaped like the real thing: forms, asides, tables,
  class names that mean nothing.
- **"It can only remove wrong things" is a hypothesis, not a safety argument.** I shipped EXTRA-6
  reasoning that confirming search results could only shorten the programme list, so a recall drop
  would be honest. It dropped recall 4/10 → 1/10 **and** precision 0.19 → 0.09: it cut correct pages
  and kept a sign-in page and a Master's PDF. A filter's direction of error is a measurement, not a
  deduction from its intent — and precision is the number that tells you which way it actually went.
- **Check the plural. Every time.** Three bugs in this repository now: `waivers` unmatched against
  `waiver`, `scholarships` against `scholarship`, and `FAQs` against `\bf\.?a\.?q\.?\b`. The last one
  produced a third of the claims in a ten-university live run, all of them false, and stamped them
  `CONFLICTING` so they looked like a data problem at the source rather than a bug here. When a regex
  matches an English noun, write the `s?` and a test for it in the same edit.
- **A stub that fills one field of a result proves nothing.** `FetchResult` carries both `content` and
  `text`, and the adapters read `.text`. A test stub that set only `.content` served every page as
  empty — so four tests asserting "this page is refused" passed while refusing *blank pages*, and the
  one test asserting a good page survives was the only one that failed. When a new stub makes most
  tests pass immediately, check that the one which should fail does.
- **Test the entry point, not only the function behind it.** `scope_report` had nine tests and every
  one called `scope_mismatches()` directly. Its `--json` flag — the one thing only the workflow uses —
  serialised a slotted dataclass with `m.__dict__` and raised `AttributeError` on the live run, *after*
  the report had printed, so a correct diagnostic still turned the run red and hid the two steps behind
  it. A CLI is production code. If CI runs it, a test runs it.
- **A measurement that cannot fail loudly is worse than no measurement.** The first live capture run
  (Actions run 35651884644) printed a full metrics table that was **not the measurement**: the scoring
  step had died with `FileNotFoundError` (the capture writes into a timestamped subdirectory, which the
  workflow did not read back), `| tee` returned 0 so the step went green, and the comparison globbed
  `metrics.*.json` and picked a **committed draft report** to print under the heading "this run". Three
  separate mistakes, each harmless alone, together producing confident nonsense. The fix: `pipefail`,
  `test -f` before use, the capture's own printed path, and the new report named exactly rather than
  globbed. **Generalise the `| tail -1` lesson below: never let a pipe or a glob stand between a result
  and the thing that reports it.**
- **Never read a gate through `| tail -1`.** `ruff format --check` prints `Would reformat: <file>`
  *above* its summary line, so a one-line tail shows "208 files already formatted" while the command
  exits 1. I shipped an unformatted file and CI caught it on PR #16. The gate's exit code is the
  result; the summary line is not. Read the whole output, or check `$?`.
- **"The first row" is not a selection when ids are random.** A V2-25 gate run failed on a test I wrote
  in V2-24, which passed on its own every time: it took `.order_by(id).first()` of the demo's results
  and assumed that row had a deadline claim. Ids are random hex, so which row that is varies with the
  run. **A test that picks a row must pick it by something the test actually needs.**
- **Rigour that disarms the product is not rigour.** V2-23's first cut required a page to match the
  requested intake *and* academic year. Every demo page states the intake and none states the year, so
  every hard filter in the demo silently disappeared — a university stopped being excluded by a minimum
  it genuinely fails. The year was never requested by anyone: it is `settings.academic_year`. **Check
  what a new rule does to the demo before believing it is strict rather than broken.**
- **A measurement can carry the same bug it is measuring.** `wrong_scope_claim_rate` sat at 5/5 through
  the whole of Phase 1, and the capture that produced it recorded the *requested* intake as the evidence's
  scope on every claim of every case. The rate was partly measuring our own question. **When a number will
  not move, read the artefact it is computed from before changing the code it is meant to grade.**
- **A month and a year are a date, not an intake.** The first draft of `scope_reader` matched any
  "September 2026", and the demo dump showed the result: 39 claims whose recorded intake was a
  *deadline* ("15 January 2027"). It was caught only because the golden-hash guard forced a look at the
  actual diff. A month now counts as an intake only with no day number in front of it and an intake
  word beside it; seasons ("Fall 2026") still count alone. **Look at what a new extractor produced, not
  just at whether the tests pass** — both readings passed every test written up to that point.
- **Re-capturing a golden hash is allowed only after proving the drift additive.** V2-22 legitimately
  changes the demo payload, which the guard's old wording did not permit at all. The answer was not to
  weaken the guard but to raise its bar: diff the two dumps, show 0 removed lines and every addition
  confined to the intended shape, and record that proof beside the constant. The wording now demands it.
- **A new optional field still changes the persisted payload, and a golden-hash test will say so.**
  Adding `Claim.scope` broke `test_the_demo_pipeline_payload_is_byte_identical_to_baseline` on the
  first try. That test permits re-capturing its hash only for documented masking shapes, which a new
  field is not, so the answer was to make the change genuinely additive: a `@model_serializer` omits
  the key when nothing recorded a scope. **Absent in the JSON now means exactly what `None` means in
  the model.** Re-capture a golden only when the test's own wording allows it.
- **The benchmark-path guard reads docstrings too.**
  `test_production_does_not_import_or_read_evaluation_answers` rejects any string constant under `app/`
  that names the benchmark directory — a comment citing a write-up there trips it. That bluntness is
  the point: production must not know where the answers live. Reword the comment; never relax the test.
- **Look for the data before declaring it missing.** Campus disambiguation was written off as needing
  data the repository did not hold. It held it: `institution_registry.json` records verified seed URLs
  per institution and names the host that publishes programmes. Three ranking experiments were rejected
  first, each trying to infer from a URL what a verified record already stated. When the guide names a
  place where institution-specific knowledge belongs, read that place first.
- **Without per-candidate provenance, every ranking story is a guess.** Three attributions this
  session were wrong — a gain credited to the wrong change, a loss credited to a signal that never
  touched the case, and a regression blamed on a query family that had actually *found* the answer.
  §11 asked for `discovered_by` / `query_or_parent_url` from the start; it was skipped, and the cost
  was several live runs spent testing stories instead of code.
- **Five variations of one query shape are one query.** Five of six families were `site:` plus quoted
  terms. Against a neural index that is a single question asked five times; adding one family phrased
  as a sentence — naming the degree in words, cycle wording included — reached a page the operator
  shape never returned. Vary the *shape*, not only the words.
- **A benchmark against a live third-party index measures that index too.** The retrieval ceiling read
  10/10 and, a few runs later, 9/10, with no code change between them that touches the case that
  moved — the provider simply stopped returning Warsaw's bachelor page for our queries. Re-measure the
  baseline in the same session as the change; anything older attributes drift to code. Two runs of a
  configuration before believing a small move, per the variance note below.
- **A URL says reliably what a page is *not*, and unreliably what it is.** Scoring `/programmes/` and
  `/admissions/` as positive hints promoted catalogue *index* pages over the specific programme asked
  for and cost four cases. Recognising research outputs, news and vacancies cost nothing and gained a
  case eleven places. Keep URL heuristics negative.
- **A degree level encoded as `S1`/`S2` defeats the degree reader.** Warsaw's catalogue writes the
  bachelor as `IN/S1-INF` and the master as `IN/S2-INF`; `names_other_degree_level` looks for
  `msc`/`master`-shaped slugs and sees neither, so a master's page passed the prefilter into a bachelor
  search. Any numeric cycle convention does this.
- **"Never displace" and "must add" cannot both hold inside one fixed budget.** The append-only hop
  looked correct and contributed *exactly nothing* for three consecutive live runs: search returned
  `top_k` candidates, the hop appended after them, and the final truncation cut every appended row off
  again. Truncate the ranked list first and let coverage extend it. Invisible in a unit test where the
  search list is short.
- **Search rank says which host search liked, not which host runs degrees.** Choosing hop entry points
  by rank opened KAIST's publication repository, a graphics lab and the sociology department, while
  `cs.kaist.ac.kr` sat sixth and was never opened. Score hosts by what they are.
- **Exa is not deterministic: one run cannot detect a one-position change.** HKU read 5 → 6 in four
  consecutive runs whose records show the hop contributed nothing to it. Compare ceilings and large
  moves; treat ±1 as noise unless two runs agree.
- **A navigation list is not a ranking, and fusing it as one loses measured ground.** Reciprocal Rank
  Fusion assumes each input orders its results by relevance. Link order on a page is layout. Fusing
  twenty navigation links — each restarting at rank 1 on its own page, at the same generator weight as
  web search — pushed correct pages from 1st to 12th and cost a whole case. A coverage generator must
  supplement a ranked one, never interleave with it.
- **A hand-written HTML fixture will pass while the real page fails.** V2-16b's smoke test, written
  by hand, found KAIST's programme link immediately. The real front page broke it three ways at once,
  and none of the three was visible in a fixture: (1) the anchor has **no text** — its label lives in a
  `navi="교육"` attribute, and a regex over `<a …>(.*?)</a>` swallowed the *next* anchor's attributes as
  if they were link text; (2) `facultyInteractiveComputing` contains `computing`, so substring matching
  put four staff pages above the programme — match terms as **words**, splitting camelCase too; (3) the
  same page was linked as both `http://` and `https://` and consumed two candidate slots, because
  `canonical_url` keeps the scheme (correctly, for the pipeline at large). Validate a parser against a
  page you did not write.
- **CJK has no word boundaries, so a short substring matches far too much.** Korean `학부`
  ("undergraduate") also matched 학부발전기금 (a development fund), 학부장 인사말 (the dean's greeting)
  and 학부동아리 (student clubs). Prefer whole words like 교육 / 교과과정 and test against the real
  navigation before adding a term.
- **`Fetcher` cannot reach the network in this cloud container.** Outbound HTTPS goes through
  `HTTPS_PROXY`, which `httpx` honours by default; `Fetcher` builds its own client and pins IPs, so it
  returns `NETWORK_UNAVAILABLE` for every URL while a plain `httpx.get` of the same page returns 200.
  An environment fact, not a product defect — do not "fix" `Fetcher` while chasing something else.
- **Check the negation before the confirmation, or a denial reads as a promise.** In V2-17's intake
  detection, "There is no intake in 2027" contains "intake … 2027" and matched the pattern meaning
  *this intake is offered*. The page said the opposite of what the code recorded, and the result would
  have been a requirement asserted for a year the university explicitly excluded. Any text rule with a
  positive and a negative form has this bug available; run the negative first and pin the order with a
  test written in the page's own words.
- **A wall-clock margin in a test is a flake waiting for a busy machine.**
  `test_a_slow_parse_does_not_block_an_unrelated_request` timed a health request and required it under
  0.5s against a 1.0s parse. On a loaded container it took 0.56s with the event loop never blocked, and
  the suite went red for no product reason. The fix was not a bigger number: hold the parser open on an
  `Event` until *after* the health response arrives, then assert the parse had not finished. Same
  property, no margin, and a genuine regression still fails it. Prefer an ordering proof over a
  duration whenever a test is about concurrency.
- **`backend/.venv` must be Python 3.12, and a fresh sandbox will not give you one.** On a cloud
  container the repo ships no venv and the default `python3` is 3.11; under it the *entire* backend
  suite errors at collection with `SyntaxError` on
  `app/adapters/discovery/live_discovery.py:512` (`type PageRecorder = ...`, a 3.12 statement) reached
  through `catalog_walker.py:38`. It looks like 1400 broken tests and is an interpreter mismatch.
  `/usr/bin/python3.12` exists: `rm -rf backend/.venv && python3.12 -m venv backend/.venv &&
  backend/.venv/bin/pip install -r backend/requirements-dev.txt`.
- **`pytest --cov` prints its coverage table after the pass/fail line**, so piping it through `tail -15`
  loses the test count. Redirect the whole run to a file, or count with
  `pytest --collect-only -q` (which prints `tests/<file>: <n>` per file, not a total — sum it).
- `seed_demo.py` raises `SchemaOutOfDate` until `UNIMATCH_DEMO_MODE=true alembic upgrade head` has run.
- `Fetcher(...)` takes `(cache_dir, *, delay_seconds, respect_robots, offline, cache_ttl_seconds, timeout, contact, corpus_dir)`; it has no `close()`, only `__aexit__`.
- `backend/setup.sh` needs `uv`; plain `python -m venv` + `pip install -r requirements-dev.txt` works. Without Playwright installed, run with `UNIMATCH_ENABLE_BROWSER_TIER=false`.
- E2E uses fixed ports 5173/8099 with `reuseExistingServer: true` — never two e2e runs on one machine.
- NU's normal admissions fetch currently yields only 42 readable characters and requires a safely
  hardened rendering/provider path for useful extraction. A `REACHED` canary is not a verified result;
  on 2026-09-07 it produced one programme-existence claim and 0% core completeness.
- Long-lived branches exist and are **not** part of this work: `claude/payments-phase-2` (74 commits ahead, conflicts with main in 12 files, adds 2 migrations off `c3a1f4e9b2d7` → merging it later will need one Alembic re-point), `social/community` (3 commits, merges clean, adds migration `f2a8c17d9e04`), `claude/production-completion` (Aug 30, superseded by main). Do not rebase them, do not branch from them.
- `README.md` still says "547 tests"; `docs/CURRENT_STATE.md` says 818. Trust pytest, not prose.
- Git author on recent commits is the owner's name for both agents — the `Agent:` trailer is the only reliable authorship signal. Always add it.


- `gh` is installed per-user via `winget install --id GitHub.cli --scope user`; it lands in
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_*bin\gh.exe` and needs a new shell to be on
  PATH. `gh auth login --with-token` **rejects** the token Git Credential Manager stores, because it
  validates `read:org` which that token lacks; the same token works as `GH_TOKEN` for `gh api` / `gh pr`.
  Load it without ever printing it:
  `export GH_TOKEN=$(printf 'protocol=https
host=github.com

' | git credential fill | sed -n 's/^password=//p')`.
- **Corrected 2026-09-06:** the note below is wrong. `backend/.venv/Scripts/python.exe` runs fine and
  produced every number in §6. Keep the rest of the note only as a reminder to record the interpreter.
- Recovery environment: the repository `backend/.venv` launcher refers to missing base Python
  `C:\Users\Dias\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none`
  (base-missing diagnosis supplied by coordinator; path read from `pyvenv.cfg`). Do not equate a launcher
  failure with a code/test failure. Record the coordinator's working interpreter and dependency setup
  in §6; do not silently repair global runtime/configuration in this documentation-only task.
- The first plain-runtime `scripts/handoff_check.py` call failed with `UnicodeEncodeError` under cp1251
  when printing an arrow. Coordinator verified `-X utf8` / `PYTHONIOENCODING=utf-8` succeeds.
  Use `& <verified-python.exe> -X utf8 scripts/handoff_check.py` from repo root (or set process-local
  encoding); no script-source fix is needed.
- The check script warns to push unpushed work, but here **never push main**: use the predecessor
  recovery branch relationship in §5. Its zero exit code is diagnostic completion, not green gates.
- Screenshot changes predate [0.1] according to supplied recovery context. Do not attribute them to
  the cut-off, regenerate them during inventory, stage them via `-am`, or call them disposable.
- Nested `.claude/worktrees/payments-phase-1` and `social-module` are independent user checkouts.
  Parent-repository "untracked" output does not authorize operations inside them.
- Seven `docs/v2` copies match `analysis` byte-for-byte; the brief has a different relative reference
  command. Keep these copies outside the snapshot unless a concrete reference need is documented.
- The legacy branch-ahead/conflict counts and line anchors above are historical template observations;
  this writer did not refresh those unrelated branches.

- **The demo database poisons the whole e2e suite once it grows, and it is not subtle.** On
  2026-09-06 a crowded `backend/data/unimatch.db` failed `journey.spec.ts` at its *first* assertion —
  "Who is applying" never renders, because the app restores the organisation's latest case instead of
  a blank profile — and that took five spec files' `beforeAll` down with it: `5 failed, 64 did not
  run`. Clean `main` reproduced it exactly, so it is nobody's regression. `rm backend/data/unimatch.db*`
  and re-run: the same suite is 73 passed / 1 skipped. Stop the API process first, or Windows refuses
  the delete with "Device or resource busy". Worth a real fix: restore should resolve a profile by the
  id this browser stored, never by "latest".
- `gh` is installed per-user via `winget install --id GitHub.cli --scope user`, landing in
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_*bin\gh.exe`. `gh auth login --with-token`
  **rejects** the token Git Credential Manager stores (it validates `read:org`, which that token lacks);
  the same token works as `GH_TOKEN` for `gh api` / `gh pr`. Load it without printing it:
  `export GH_TOKEN=$(printf 'protocol=https
host=github.com

' | git credential fill | sed -n 's/^password=//p')`.
- The repository `backend/.venv` works; an earlier note claiming its base Python is missing was wrong.
- A commit pushed to a task branch *after* the owner merges its PR does not reach main. Check
  `git merge-base --is-ancestor <sha> origin/main` before assuming your last commit shipped — that is
  how `14d556b` was orphaned.
- **Corrected again 2026-09-06:** in this Codex recovery,
  `backend/.venv/Scripts/python.exe` again points at the absent uv-managed base interpreter and does
  not start. Gates use Python 3.12.14 from the bundled Codex runtime with process-local
  `PYTHONPATH=backend/.venv/Lib/site-packages`; Ruff's standalone `.venv/Scripts/ruff.exe` still works.
  This is an environment fact, not a product failure; do not rewrite or repair the user's venv during
  a task recovery.

## 10. Queue (brief §6 order; do not reorder without the owner)

Owner-prioritized workstream: finish V2-01 labels, human review and baseline acceptance, then V2-10 provider-neutral SearchProvider with a fake adapter. Do not begin the rest of the roadmap or connect Jev. The older queue below remains historical context.

**Now: GitHub review of PR #7 after all release-gates complete.** PR #6 is already merged on
`origin/main@7b1fce0`. The separate brief queue below remains the repository sequence; the GLM
24-card campaign did not replace it and is not fully completed.

`[0.8]` → `[1.1]` → `[1.2]` → `[1.3]` → `[1.4]` → `[2.1]` → `[2.2]` → `[2.3]` → `[3.1]` → `[3.2]` → `[4.1]` → `[4.2]` → `[5]`

## 11. Session log (one line per session, newest last)

| Session (UTC) | Agent | From → to | Summary |
|---|---|---|---|
| 2026-09-05 | owner | `627d42d` → `627d42d` | workflow files created; no brief task started yet (historical template entry) |
| 2026-09-05 18:31:27 UTC | gpt-6-astra, delegated recovery inventory writer | `c924410` → `c924410` (HEAD unchanged) | Prompt C audit started using clock tool UTC; reconciled stale template, seven local predecessor commits and all 74 scoped dirty/untracked file paths; 2 nested repos excluded. HANDOFF only edited; gates/frontend review pending; branch/checkpoint/push/baton not yet performed. |
| 2026-09-06 | claude-opus-5 | `c924410` → `61df0db` | Prompt C recovery: reconciled the stale §1/§5 (the branch existed, the baton did not), audited all eight frontend diffs into §4, ran every gate into §6 (backend green, 891 tests / 92.56 %; frontend one red unit test), preserved the work in one allow-listed `wip:` checkpoint, took the baton. |
| 2026-09-06 | claude-opus-5 | `61df0db` → `0affab6` | Finished [0.8]: red test fixed, bucket vocabulary contracted, preferences disclaimer restored, per-table captions, e2e helper opens the set-aside sections. All gates green (892 backend / 141 unit / 67 e2e). §7 I4-T3 conflict resolved by owner delegation. Next: open the PR. |
| 2026-09-06 | claude-opus-5 | `9ee7078` → `9ee7078` | Installed `gh`, authenticated it from the stored git credential, opened **PR #2** for stage 0. Baton stays with nobody; next is review. |
| 2026-09-06 | claude-opus-5 | `f88f77d` → `fix/shortlist-columns` | Prompt A. Found PR #2 and #3 merged, `[0.8]`'s last commit `14d556b` orphaned outside the merge, Codex's docker branch 40 commits behind main and unlogged, and the e2e suite red on clean main from the §9 database trap. Re-applied the three shortlist hunks on the new base; 164 unit and 73 e2e green. |
| 2026-09-06 16:59:45 UTC | gpt-6-astra | `d6e59d5` → `4a7171c` + this handoff commit | Prompt C completed: initial tree was clean; fetched PRs #4/#5, merged `origin/main@85352b5` without rewriting history, reviewed PR #6, fixed separate-column semantics and longest-chip overlap coverage, regenerated screenshots, ran full gates, recorded the review on the PR, and took the baton. |
| 2026-09-07 11:28:28 UTC | codex | `e533d62` → `25f5954` | Audited the local GLM campaign, independently reran backend/frontend and ordinary E2E, preserved the original candidate as `audit/glm-c1-e533d62`, merged current `origin/main@7b1fce0`, and opened a fix-forward for the stale payment-reconcile commit defect already noted by GLM security. No push/deploy. |
| 2026-09-07 12:00:10 UTC | codex | `25f5954` → `02d648c` + final handoff | Fixed and PostgreSQL-tested stale payment rollback, fixed two live NU discovery defects, ran all backend/frontend/E2E/auth/dependency gates, and field-ran the bounded NU canary. Audit verdict: useful partial campaign, not completed project. Baton released; no push/main/deploy. |
| 2026-09-07 14:10:54 UTC | codex | `ab2e70a` → `96c1082` + final publication handoff | Owner explicitly authorized GitHub publication. Secret-scanned and committed all 133 ai-team evidence files plus the corrected audit, pushed `ai/c1/integration`, and opened PR #7. Release-gates started; no protected-main merge or application deploy. |
| 2026-09-08 03:38:21 UTC | codex | `9b362c8` → in progress | Took the C2 baton after verifying `origin/main@4d2125c` is the merge-base. Owner authorized T29 wiring, bounded T30 batches, T26, committing campaign evidence, and GitHub publication; T31 remains blocked on provider/secrets/data-policy acknowledgement. |
| 2026-09-09 19:20 UTC | claude-opus-5 | `edf546d` → `task/security-audit-hardening` | Owner asked for a security review of the repository instead of the next brief task. Audited auth, tenancy, payments, egress, uploads, exports, mail, crypto, headers and the frontend; proved three findings with tests that fail on `main`; fixed nine across 9 commits. Full gates green (1395 backend / 93.96% / 188 frontend / build / pip-audit). Residuals recorded in §7. Baton released; nothing merged to `main`, no deploy.
| 2026-09-20 UTC | claude-opus-5 | `a4cd5b3` → `a4cd5b3` + this release commit | Recovery after gpt-6-astra's token cut-off. The baton on `main` was 22 commits stale: the live task is V2-01, not the merged security audit. Tree was clean and `a4cd5b3` was one coherent draft5 commit, so nothing was re-done. Rebuilt `backend/.venv` on Python 3.12 (see §9), ran every gate gpt-6-astra could not finish — all green, 1454 backend tests at 93.96%, 59 focused, 188 frontend — and released draft5. Draft5 itself is gpt-6-astra's work, recovered from the previous session, not this writer's. V2-01 remains unaccepted at 0/10 human signoffs.
| 2026-09-20 UTC | claude-opus-5 | `a4cd5b3` → draft6 | Published draft6: resolved the Delft programme identity from the official tudelft.nl page, the last unresolved identity of ten, and took nothing else from that page because its deadline and numerus-fixus rules are unscoped to the requested fall 2027 intake. All gates green (1456 backend at 93.96%, 61 focused). V2-01 acceptance is now blocked on human signatures alone, not on more annotation.
| 2026-09-20 UTC | claude-opus-5 | draft6 → draft7 | Applied the owner's first human review. Verified both corrections against primary sources and both held: Aalto's identity was the wrong programme for an international applicant, and HKU was missing its school and exact degree title. Recorded them without asserting the Computer Engineering / computer science equivalence the owner's correction does not settle. Gates green (1458 backend at 93.97%, 63 focused). Acceptance now waits on a reviewer name and date, not on more annotation.
| 2026-09-20 UTC | claude-opus-5 | draft7 → reviewed | **V2-01 accepted.** The owner signed all ten cases (Диас, 2026-09-21) and settled the Aalto adjudication, so the corpus was certified and scored strictly for the first time: `provisional: false`. Recorded the acceptance, pinned the gate with two tests, and wrote down the baseline the pipeline must beat — programme recall 1/10, claim precision 0/5, every claim out of scope. Gates green (1461 backend at 93.97%, 66 focused). V2-10 is unblocked.
| 2026-09-20 UTC | claude-opus-5 | reviewed → V2-10 | Built the search provider seam: interface, offline fake, factory, config guard, 22 tests at 100% coverage of the new package. Three rules enforced by test rather than comment — a result carries no field a claim could be built from, `app/domain` may not import `app/adapters`, and an unconfigured provider raises instead of returning an empty response. Nothing wired into discovery yet. Gates green (1483 backend at 94.02%, 188 frontend).
| 2026-09-21 UTC | claude-opus-5 | V2-10 → V2-11 | Built the privacy-safe query generator: an intent type with no room for applicant data, value validation that catches a profile formatted into a string, bounded query families and a redacted audit record. One test per forbidden item in the spec's list. Found and fixed a test of my own that was passing for the wrong reason, and rewrote a flaky wall-clock concurrency assertion as an ordering proof. Gates green (1510 backend at 94.09%).
| 2026-09-21 UTC | claude-opus-5 | V2-11 → V2-12 | Built the ontology. Its one job is the boundary the corpus already drew by hand twice: computing science *is* computer science, data science and computer engineering are neighbours worth fetching and never automatic matches. Equivalence and expansion are separate functions so the wrong call is hard to write. Six concepts, four degree levels, six non-English aliases, versioned. Gates green (1539 backend at 94.12%, package at 100%).
| 2026-09-21 UTC | claude-opus-5 | V2-12 → V2-13 | Built hybrid retrieval. Found §5's prefilter already ~80% written in live_discovery and reused it instead of duplicating. Added BM25 without a dependency, named deterministic signals so every ranking explains itself, and rejection accounting so 'found nothing' and 'found forty news articles' stop looking identical. Shipped only the two cheapest layers of §6's stack. Gates green (1568 backend at 94.23%, package at 100%). The 1/10 baseline is unchanged and will stay so until a real provider is configured and the path is called.
| 2026-09-21 UTC | claude-opus-5 | V2-13 → V2-14 | Did not build the reranker comparison. Measured first whether reranking could help: the correct page is in the captured candidate set for 1/10 cases and the current ranking already has it first, so headroom is 0 and no reranker can win a case. Shipped the measurement, its CLI, the committed result and a test pinning it, plus a roadmap redirect — the 1/10 is entirely retrieval. Gates green (1581 backend at 94.23%).
| 2026-09-21 UTC | claude-opus-5 | V2-14 → V2-15 | Built detection of a university's own public search surface — the retrieval work that needs no paid key, chosen because V2-14 proved the gap is retrieval. Nine families, passive network evidence preferred over markup inference, nothing probed, off-domain and admin surfaces discarded, key-bearing surfaces flagged with the key left unread. All fixtures synthetic. Gates green (1617 backend at 94.29%, module at 100%).
| 2026-09-21 UTC | claude-opus-5 | V2-15 → V2-16 | Built fusion: Reciprocal Rank Fusion over seven generators, so no two incomparable scores are ever added, with every attribution surviving into the output because agreement between independent generators is the most useful thing fusion produces. Gates green (1640 backend at 94.34%). Phase 1 is now fully built and fully unwired — flagged to the owner in §5 as a decision point rather than continuing to add components.
| 2026-09-21 UTC | claude-opus-5 | V2-16 → V2-17 | Built identity verification: six dimensions per §10, identity separated from scope, UNKNOWN never a match and never a failure, and `applies_to_requested_intake` returning a verdict rather than a bool so 'we do not know' has somewhere to live. Found and fixed a negation-read-as-confirmation bug in intake detection while testing it. Gates green (1672 backend at 94.42%, both modules at 100%).
| 2026-09-21 UTC | claude-opus-5 | V2-17 → V2-10b | Owner chose Exa and holds a key. Wrote the adapter behind the V2-10 seam: fails closed, never retries, caps results and body size, keeps the egress policy, and keeps highlights out of anything that could cite them. Left it off by default and raised the AGENTS §6 'no network outside Fetcher' conflict in §7 rather than settling it alone. No live call made. Gates green (1699 backend at 94.46%, module at 100%).
| 2026-09-21 UTC | claude-opus-5 | V2-10b → live probe | Owner approved the §6 exception and authorised the key. Smoke-tested the adapter against the real API, then probed all ten benchmark cases: **retrieval ceiling 1/10 → 9/10**, zero cases now retrieve nothing, and a reranker went from zero headroom to seven cases. Wrote up the two remaining failure shapes (wrong campus, not-a-programme-page), marked RERANKER_CEILING superseded for this path, and reordered §5 to attack ranking instead of retrieval. 50 queries. Gates green (1713 backend at 94.46%).
| 2026-09-21 UTC | claude-opus-5 | live probe → V2-16b | Investigated KAIST before deciding anything: search finds its department root reliably and the programme is one navigation hop away, so the answer is a hop, not better queries or a per-university hack. Built it, and it failed on the real page three ways the fixture hid — attribute-as-text, substring-as-word, and http/https double counting. Fixed each, pinned each as a test, and `content?menu=188` went from unreachable to rank 3. Gates green (1734 backend at 94.50%).
| 2026-09-21 UTC | claude-opus-5 | V2-16b → V2-16c | Fused the hop into retrieval, measured it live, and **did not ship it**: the ceiling fell 9/10 → 8/10 and six correct pages moved down. Kept the mechanism behind an injected fetch that defaults to off, restored the search-only baseline, and wrote up why — a navigation list is layout, not relevance, so it must supplement a ranked generator rather than interleave with it. Gates green (1734 backend at 94.39%).
| 2026-09-21 UTC | claude-opus-5 | V2-16c → V2-16d | Opened **PR #15**. Then got the hop to pay: ceiling **9/10 → 10/10**, KAIST from unreachable to #30, nothing moved down. Took four measured runs and three rejected designs — fusing as an equal cost a case, entry points by search rank opened a lab and a repository, and appending inside the same budget was silently cut off every time. Each lesson is in §9 and SEARCH_PROBE.md.
| 2026-09-21 UTC | claude-opus-5 | V2-16d → V2-13b | Taught the ranking to ask what kind of page it is looking at. Toronto **+11**, KAIST +2, everything else unchanged — and Warsaw lost, twice, so **not enabled**. Kept `classify_url` as a capability and wrote down why the signal is off. The diagnosis found a better bug underneath: Warsaw's catalogue encodes the master's as `S2-INF`, which the degree reader cannot see, so a master's page reached the top of a bachelor search. Gates green (1746 backend at 94.49%).
| 2026-09-21 UTC | claude-opus-5 | V2-13b → V2-13c | Fixed the degree reader: Bologna cycle numbering (`S1`/`S2`) is now a degree level, so a master's page stops passing a bachelor prefilter. Measured and rejected two more changes, and **corrected two earlier claims of my own** — Toronto's +11 was not the page-kind signal, and the 10/10 ceiling is not reproducible because the provider stopped returning Warsaw's page, not because of any code. Re-baselined at 9/10. Gates green (1758 backend at 94.49%).
| 2026-09-21 UTC | claude-opus-5 | V2-13c → V2-11b | Added one query phrased like a person, following the Warsaw evidence. Ceiling **9/10 → 10/10**, Warsaw back, rank-1 cases 1 → 2, two runs agreeing. Toronto pays eleven places and a run costs 20% more queries — both written down rather than buried. Gates green (1759 backend at 94.49%).
| 2026-09-21 UTC | claude-opus-5 | V2-11b → V2-13d | Built the per-candidate query provenance §11 asked for and never got, then used it to diagnose Toronto in one 6-query run: the new query family was blamed and is in fact one of the two that found the correct page — five of seven candidates above it are other campuses of the same university. Named the cause, shipped no fix, and put the campus registry data to the owner. Gates green (1762 backend at 94.49%).
| 2026-09-21 UTC | claude-opus-5 | V2-13d → V2-22a | The owner asked why no fix was shipped. Correct question: the data was already in the repository. The registry's verified seeds name the host that publishes programmes, so a candidate there now outranks a sibling campus. Cases-at-rank-1 **2 → 4**, Toronto #19 → #4, Warsaw and HKU and UBC to #1, ceiling still 10/10, two runs agreeing. Best change of the session and available three attempts earlier. Gates green (1767 at 94.51%).
| 2026-09-21 UTC | claude-opus-5 | V2-22a → V2-13e | Wired Phase 1 into live discovery so the owner can actually see it: search results are appended after the sitemap and walker, the hop reads through the adapter's own Fetcher, and the whole thing is dormant without a provider — proved by the entire pre-existing suite passing untouched. Also told the owner plainly that there is no V2-18 and that better retrieval does not fix scope. Gates green (1770 at 94.44%).
| 2026-09-21 UTC | claude-opus-5 | V2-13e → V2-21 | Started Phase 2 on the failure Phase 1 could never fix. A claim's scope is now a first-class thing over the spec's nine dimensions, and a page that does not say who it is for answers UNKNOWN rather than yes — silence is not agreement. 28 tests, module at 100%, nothing wired yet on purpose. Gates green (1798 at 94.46%).
| 2026-09-22 UTC | claude-opus-5 | plan V2-20/22/23/30 + Phase 3 §3/§4/§6/§7 + EXTRA-1…4 | Overnight, owner asleep, autonomous. Closed Phase 2's exit criteria and started Phase 3. The night's most useful finding was a **refutation**: the scope diagnostic (EXTRA-1) showed the stuck metric is a *programme-name* failure, not a scope-reading one, so the work that would move it is retrieval and name resolution. Four rules I wrote were wrong and caught before shipping — a positive availability pattern reading a count sentence, a fee-waiver negation reading a waiver as a refusal, `waivers` unmatched in the plural, and a Claim rebuilt from a payload taking a supersession down with it. Five owner decisions are parked in §7, untouched. Gates green at every push (1944 at 94.60%), CI green including Playwright. |
| 2026-09-21 UTC | claude-opus-5 | V2-22a | Started plan V2-22: identity resolved by domain or by a recorded alias, with the evidence attached, never by resemblance. Left the alias data to the owner rather than inventing it. Also fixed a formatting failure CI caught that my own gate run had hidden behind `| tail -1` — §9. Gates green (1864 at 94.60%). |
| 2026-09-21 UTC | claude-opus-5 | V2-20b | Closed the claim half of plan V2-20: a superseded claim now says when it stopped being current and what replaced it, and says nothing when nothing replaced it. Refused to build a separate ClaimVersion table for a query nobody makes yet, and wrote down why. Gates green (1852 at 94.58%), one alembic head. |
| 2026-09-21 UTC | claude-opus-5 | V2-20a | First plan-numbered Phase 2 entity task: a page's observed versions now survive the page's own update. Reconciled my drifted task numbering with the execution plan in §5 first, so the plan stays the source of truth. Gates green (1848 at 94.56%), one alembic head. |
| 2026-09-21 UTC | claude-opus-5 | V2-26 | Classified conflicts by scope, meeting a Phase 2 exit criterion. Deliberately asymmetric: a difference must be *stated* to explain a disagreement away, because dismissing a real conflict is the expensive direction. Demo gained one line and nothing else. Gates green (1839 at 94.55%). |
| 2026-09-21 UTC | claude-opus-5 | V2-25 | Scope on the remaining four adapters. 127 claims gained `population: international`; government pages correctly gained nothing. Found and fixed a reader bug the demo exposed (a bare year range read as the page's year, from a figure's year on Toronto's award). Also fixed an order-dependent test of my own. Gates green (1835 at 94.53%). |
| 2026-09-21 UTC | claude-opus-5 | V2-24 | Made the refusal visible: a claim set aside for scope now produces a question naming the page and the reason, blocking only when nothing else answered. Tested end to end through `_stage_assess` on a real demo run, not just in the domain. Gates green (1833 at 94.53%). |
| 2026-09-21 UTC | claude-opus-5 | V2-23 | Made the assessment act on scope: refuse a claim whose page is about another intake, and never let a page silent on it eliminate a candidate. The first cut also demanded the academic year and quietly removed every hard filter in the demo; the demo dump is what caught it. Final rule is a no-op on the demo and byte-identical there. Gates green (1829 at 94.52%). |
| 2026-09-21 UTC | claude-opus-5 | V2-22b | Re-measured as instructed: 5/5, unchanged. Found why while reading the capture — its evidence scope was built from the request, so the benchmark compared labels against our own question. Fixed both capture paths through one helper, kept the pre-V2-22 fallback so frozen captures re-score identically (verified), and left the number where it is: it needs a live re-capture with network, which this container lacks. Gates green (1823 at 94.51%). |
| 2026-09-21 UTC | claude-opus-5 | V2-22 | Filled the scope from the page's own words. The reader refuses four of the nine dimensions in writing and treats ambiguity as silence. Its first draft read deadline dates as intakes in 39 demo claims; the golden-hash guard forced the look that caught it. The golden was re-captured once, after proving the drift additive, and the guard's wording now demands that proof. Gates green (1820 at 94.51%). The rate itself is unmoved and expected to be — using the scope is the next step. |
| 2026-09-21 UTC | claude-opus-5 | V2-21 → V2-21b | Put the scope on the claim. Found no migration was needed — the payload column is JSON — and kept `alembic heads` at one. A golden-hash guard caught the payload drift immediately; rather than re-capture a hash the test does not permit re-capturing, the field is now omitted when unrecorded, so absent in JSON means exactly what None means in the model. Gates green (1804 at 94.48%).

| 2026-09-20 | gpt-6-astra | b267b337 → V2-00 in progress | Startup/recovery, PR inventory, all pack files read; isolated worktree preserves existing dirty research work. |

V2-00 historical checkpoint: Ruff lint/format and mypy passed (166 files); subsequent full CI results are recorded in section 6. Alembic source graph: one head d9c4e7a21b83.


V2-01 provisional baseline: programme recall 1/6, precision 1/7; candidate recall @5/10/20 1/6; claim adjudication 5/13, support adjudication 0/13; critical coverage 0/150. Ten bounded runs, 520 HTTP attempts, 2 PDFs; three wall-clock and two page-budget failures. Full results and limitations: backend/evaluation/research/baseline/README.md. Human verification 0/10; no acceptance claim.

| 2026-09-20 | gpt-6-astra | b267b337 → d0a2fb4 + documentation handoff | Integrated V2 pack, isolated benchmark/capture, 25 focused tests, 1420 tests per DB and 93.97% coverage, committed provisional baseline; draft PR #14. Baton released. Human-verified cases 0/10; finish label/adjudication review before V2-10. |
| 2026-09-20 | gpt-6-astra | 3618a52 -> draft2 in progress | Resumed official-source annotation; preserve frozen draft1 baseline, no production changes. |

| 2026-09-20 | gpt-6-astra | 3618a52 -> 7356d9e + documentation handoff | Draft2 official-source annotation, separate offline replay, 27 benchmark tests, both full CI matrices green (1422 per DB, 93.96% coverage). Released baton; 0/10 human verified, V2-01 remains in progress. |

| 2026-09-20 | gpt-6-astra | 4ffa042 -> identity mapping in progress | Resumed V2-01; fetched clean synchronized branch, one Alembic head; explicit evaluation-only award/document mapping next. |

| 2026-09-20 | gpt-6-astra | 4ffa042 -> 00e107f + documentation handoff | Explicit source/subject mapping, separate replay CLI, UNKNOWN protection, 51 focused tests and both full CI matrices green (1446 per DB, 93.96% coverage). Human review worksheet published; 0/10 human certified, V2-01 in progress. Baton released. |

| 2026-09-20 | gpt-6-astra | 232ca1f -> draft3 in progress | Clean synchronized start, one Alembic head; lossless document-field projection and mapper alignment next. |

| 2026-09-20 20:12 UTC | gpt-6-astra | 232ca1f -> 2f56a46 + documentation handoff | Published lossless draft3 document projection, manifest, 52-field review worksheet and version comparison. Both full CI matrices pass (1450 tests per DB, 93.97% coverage); 55 focused tests. Baton released; human certification 0/10 and V2-01 still in progress. |

| 2026-09-20 20:15 UTC | gpt-6-astra | 952f71a -> source review in progress | Clean synchronized start, one Alembic head; exact programme and qualification evidence next. |

| 2026-09-20 UTC | gpt-6-astra | 952f71a -> 3f7e467 + documentation handoff | Published draft4 primary-source annotations and 56-field review worksheet; prior labels/capture immutable, production unchanged, human certification 0/10. Baton released. |

| 2026-09-20 UTC | gpt-6-astra | fd07e87 -> source review in progress | Clean synchronized start; one Alembic head. Continue remaining primary-source evidence after explaining V2-01 status to owner. |
