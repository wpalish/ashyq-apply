# Code review: product code changed on 2026-10-19

Reviewer: claude-opus-5. This review looks for correctness bugs only, not style.
Scope: `git diff $(git rev-list -n1 --before=2026-10-19T00:00 HEAD) HEAD -- backend/app frontend/src`,
which runs from base `84b2493d` to HEAD `5de8b6a3` on `claude/greeting-16wj2z` (55 files, about 24k lines,
of which 16k are KB JSON).

The review read these parts:

- **Knowledge base:** `app/knowledge/*` (the loader merge, staleness, claims, funding, `programme_name`
  and the requirement questions) and the kb-mode branch of `runner.py`.
- **Page classifier:** `page_classifier.py` (CL-2, the CH-1 heading and the labelled level).
- **Discovery:** `live_discovery.py` (UA-1, CH-1, CQ-1 through `combination_head.py`, SP-1, QT-1 and
  QT-1b/c with the TB-1 gate, LL-1) and CC-1 in `catalog_walker.py`.
- **Fetching:** `fetching.py` (the proxy, the robots rules, `time_admission`).
- **Supporting backend:** `url_canonical.py` and `message_keys.py`, plus the API annotation.
- **Frontend:** the i18n catalogue and message rendering (`messages.ts`, `i18n.ts`, `format.ts`,
  `ResultDetail`, the Shortlist, Funding and Compare screens).

No search provider was called, and no heldout case or quarantined document was opened.

## Findings

| # | Sev | Where (HEAD) | Bug | State |
|---|-----|--------------|-----|-------|
| F1 | high | `pipeline/runner.py:319`, `:2034` | A kb-mode recheck loops every minute, forever, once a KB fact is a year old | **fixed** |
| F2 | med | `knowledge/claims.py:480` | The build's fall-2027 staleness verdict is carried to every applicant's intake | **fixed** |
| F3 | med | `knowledge/__init__.py:85` | A summer intake is placed in the wrong academic year | **fixed** |
| F4 | med | `knowledge/claims.py:462`, `tests/test_knowledge_base.py` | KB runner tests are time-bombs (2027-10-20, 2028-01-01) | **fixed** |
| P1 | med | `pipeline/runner.py:155`, `:399` | The knowledge mode belongs to the deployment, not the run: a resumed or rechecked pre-switch live run switches mode | proposed |
| P2 | low | `knowledge/__init__.py:67` | `academic_year_end` reads a date or a "since" phrase as an academic year | proposed (needs a KB rebuild) |
| P3 | low | `knowledge/__init__.py:85` vs `runner.py:1864` | Two conventions for a "winter" intake | proposed (owner) |
| P4 | low | `knowledge/__init__.py:103` | A running academic year is called "past" from 1 January | proposed |
| P5 | low | `knowledge/claims.py:35` | `covers()` answers Software Engineering, Computer Engineering and Business Informatics applicants with CS-bachelor facts | proposed (scope) |
| P6 | low | KB data, `kb_build.py:525` | Stored "published for academic year X, not the fall 2027 intake's" reasons name the build intake | proposed |
| P7 | low | `catalog_walker.py:319` | CC-1 reads a slug of letters and a year (`fall2027`, `bsc2025`) as a course code | proposed |
| P8 | low | `knowledge/__init__.py:212` | Two small `merge_entries` gaps | proposed |
| P9 | info | `live_discovery.py:220`, `:1151` | The comments say "off" on two flags that are on | proposed (docs) |

### F1: a kb-mode recheck loop (fixed)

- **Input:** any kb-mode run on or after 2027-10-19, one year after the KB's `verified_on`.
- **Wrong output:** `_live_claim_moments` arms the recheck at `accessed + 365 d`. `accessed_at` is
  the KB's verification date, and a re-read of the same KB file never moves it. Once that moment has
  passed, two things go wrong:
  - `_kb_claim_is_stale` keeps every claim due, so each recheck re-runs verification through
    assessment for the whole run;
  - `earliest_recheck()` returns a moment in the past, and `worker._schedule_recheck` turns it into
    `now + 60 s`.

  Every kb run therefore re-runs about once a minute, forever. Separately, the recheck clock
  (`>= 365 d`) and `stale_reasons` (`> 365` whole days) disagree by one day. A recheck on day 365
  re-reads the same "current" verdict and re-arms in the past, so even without the loop above it
  spins for a whole day.
- **Fix:**
  - A KB claim is due only while the run still shows it `VERIFIED_CURRENT`; one already
    `POSSIBLY_STALE` has nothing to wait for, because a KB re-read cannot freshen it.
  - The moment is `accessed + (MAX_AGE_DAYS + 1) d` (`KB_RECHECK_AGE`), the first day
    `stale_reasons` calls the fact stale.
  - A run whose claims are all stale arms no recheck.
- **Tests:**
  - `test_kb_mode_recheck_waits_for_the_day_a_fact_turns_stale`: the moment is day 366, day 365 is
    not due, and a stale claim is never due.
  - `test_kb_mode_judges_staleness_on_the_kb_day`: a run with every claim stale has
    `next_recheck_at is None`.

### F2: the build's intake leaks into every applicant's staleness (fixed)

- **Input:** a spring 2027 (or summer 2027) applicant, together with any of the roughly 28 KB fees
  stored with that reason (2026/27 fees, MIT `qs2027-001` among them).
- **Wrong output:** `claims.answer` merged the fact's stored `stale_reasons`, which the build
  computed for its own intake: "academic year 2026/2027 is before the fall 2027 intake's 2027/28".
  As a result:
  - the applicant's own year's fee is shown `POSSIBLY_STALE`, with a reason about another intake;
  - the cost table is empty;
  - the funding gap says "for another academic year".
- **Fix:** `app.knowledge.carried_stale_reasons(fact, intake)` keeps every stored reason except an
  intake-relative one computed for a different intake, which `stale_reasons` recomputes for this
  applicant. A fall 2027 applicant sees exactly what they saw before. A fall 2028 applicant gets
  "before the fall 2028 intake's 2028/29" rather than the fall 2027 wording.
- **Tests:** `test_a_stored_reason_for_the_build_intake_does_not_stale_another_intake` and
  `test_a_stored_reason_that_names_no_intake_is_kept_for_every_intake`.

### F3: a summer intake is in the wrong academic year (fixed)

- **Input:** `intake_academic_year_start("summer 2027")`.
- **Wrong output:** it returned 2027, so a 2026/27 fee was "before the summer 2027 intake's 2027/28".
  The runner disagrees in two places:
  - `_TERM_START_MONTH` starts a summer term in May;
  - `applicant_academic_year` places summer 2027 in 2026/27.
- **Fix:** summer joins the academic year that began the autumn before, like winter and spring.
- **Test:** `test_a_summer_intake_joins_the_academic_year_that_began_the_autumn_before`.

### F4: KB runner tests are time-bombs (fixed)

`answer()` judged staleness on `datetime.now()` when the runner called it. The kb runner tests'
fixtures are dated 2026-10-19 and assert `VERIFIED_CURRENT`, a 2027/28 cost item, and "not as a
current yearly figure". Those assertions start failing on two dates:

- on 2027-10-20, when the facts pass 365 days;
- on 2028-01-01, when 2027/28 counts as past.

**Fix:** one seam, `app.knowledge.claims.kb_today()`. An autouse fixture in `test_knowledge_base.py`
pins it to the fixture day, and a new test shows the runner reads it (2027-10-21 gives a stale
IELTS claim). The product behaviour is unchanged.

### P1: knowledge mode is the deployment's, not the run's (proposed)

`self.kb_mode` comes from `settings.knowledge_mode` (default `kb`), and `run_to_decision` rewrites
`settings_snapshot` on every call. Two kinds of pre-switch live run now take the kb branch:

- **A resumed run** (after a crash or a lost lease). Its verification ran live but its funding runs
  in kb mode: `kb_scholarships` is built from live claims, and `_stage_discover` re-runs as
  `KnowledgeDiscovery`.
- **A rechecked run.** Its live claims are replaced by KB claims, or for a non-CS run by
  "No verified data yet" on every row.

**Proposal:** record `knowledge_mode` in the snapshot at the run's first start and honour the
stored value on resume. For a recheck of a live run in a kb deployment, the owner decides between
skipping the recheck and re-running the whole run from discovery in kb mode.

### P2: `academic_year_end` misreads free text (proposed)

The pattern `(20\d\d)\s*[/-]\s*(\d{2,4})` reads more than an academic year:

- "not stated (bachelor students entering on or after 2019-04-01)" gives 2004, so "is past"
  (Science Tokyo);
- "since winter semester 2017/18 (no academic year stated)" counts as past (Heidelberg);
- "(standing policy; … WS 2026/27)" counts as "before the intake" (FU Berlin).

These three wrong reasons are stored in `kb_cs_bachelor.json`. The facts are stale either way under
the build's "year not stated" rule, so only the reason text is wrong. That reason text also contains
"; ", so `message_keys` splits it into two unkeyed parts (the English is shown, which is safe).

**Proposal:** accept only consecutive years (end = start + 1), and return `None` for the build's
"not stated" / "no academic year stated" annotations.

**Rebuild the KB in the same change.** Fixing the parser alone makes `kb_refresh_diff` drop the
stored dated reason and recompute none, so a refresh would turn the Science Tokyo fee current. A
rebuild (`kb_build`, path `:561`) keeps the facts stale, because it re-adds "published for academic
year not stated…".

### P3: a winter intake has two conventions (proposed, owner decision)

- `intake_academic_year_start` and `_TERM_START_MONTH` read winter 2027 as January 2027, so in
  2026/27.
- `applicant_academic_year` (AY-1) reads it as Wintersemester 2027/28.

The two differ for every "winter" applicant. The cost table is labelled 2027/28 while the KB judges
fees against 2026/27.

### P4: "academic year past" from 1 January (proposed)

`end <= today.year` calls 2026/27 "past" from 2027-01-01. A spring 2027 applicant researching in
January is then refused their own year's fee. **Proposal:** call it past only from the end year's
autumn (`end < today.year or (end == today.year and today.month >= 9)`), and update `stale_policy`.

### P5: `covers()` is wider than the KB (proposed, scope)

`_CS_WORDS` contains "software", "informatic" and "computer". "Software Engineering", "Computer
Engineering" and "Business Informatics" applicants therefore get the CS bachelor's facts, under the
CS programme name, as if they were their programme's.

### P6: stored value-based reasons name the build intake (proposed)

12 reasons read "published for academic year X, not the fall 2027 intake's". These facts are stale
for most other intakes too, so the status is right but the text names the wrong intake. Either store
the intake separately or word the reason without it.

### P7: CC-1 rejects a year slug (proposed, discovery is frozen)

`_COURSE_CODE_START` (`[a-z]{2,4}\d{3,4}`) matches a last segment such as `fall2027` or `bsc2025`.
Such a link is hard-rejected as a course page. **Proposal:** exclude four digits that read as a
year, which `_YEAR_SEGMENT` already does for `courses/<year>`.

### P8: `merge_entries` gaps (proposed)

- Facts are compared on `verified_on` only, so a fact dated only by `accessed_on` loses to any dated
  fact.
- When neither file has a known programme, the import's programme block replaces the built file's,
  even when the built one holds an access-case note. No claim depends on it today.

### P9: comment drift (proposed)

The comments say `COURSE_LEAD_GUARD` is "Off by default" and `ABSTAIN_ON_UNREADABLE_ENTRY` is "off
until replayed", but both are `True`.

## Checked and found correct

- **Flag interactions:**
  - CL-2 needs CH-1 and logs a no-op when CH-1 is off.
  - The QT-1c twin gate goes through TB-1 (`time_refusal_now` returns "" outside a case clock; this
    is documented).
  - SP-1, CQ-1 and CH-1 run in that order inside `profile_rejects`.
  - UA-1 counts entry reads, and its `_settle_pending` guard is right.
- **Recovery loop:** with QT-1, `twin_due` / `twin_next` reads the twin once, after which SB-1 stops,
  and the reserve accounting goes through `note_recovery_read`.
- **Fetching:**
  - malformed URLs (`page_link`, `invalid_url_reason`, the `InvalidURL` catch in `get`, redirects);
  - the robots `disallows` rule, which only ever narrows, with ties going to Disallow;
  - the proxy path, which keeps TLS verification on;
  - the KB robots override, which is limited to exact URLs, makes a single attempt and is never used
    in the product.
- **KB data:** `answer()` on all 98 entries, 6 intakes and 3 dates raised no exception.
- **Message keys and frontend:**
  - every key is served and never stored, and the golden demo hash is unchanged;
  - `localStaleReason` and the backend split the reasons identically;
  - a missing key, translation or parameter falls back to the English;
  - RU/KK counts avoid plural forms.
- **Frontend:** the dynamic keys (`detail.tab.*`, `detail.docs.*` against the `completeness` union)
  all exist.

## Verification

- `tests/test_knowledge_base.py`, `test_message_keys.py`, `test_kb_imported_dev.py` and
  `test_kb_refresh.py` all pass.
- The recheck, golden and stale subsets of `test_freshness_regressions.py`, `test_worker.py` and
  `test_claims_and_conflicts.py` pass.
- ruff and mypy are clean on the changed files.
- The golden demo test passes, so the demo output is byte-identical. `seed_demo.py` still puts
  Groningen first.
- The full suite was not run (as instructed).
