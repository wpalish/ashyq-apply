# Assumptions

Decisions taken without asking, because each was safe, reversible, and blocking
progress. Grouped by what they affect, with the reasoning that produced them.

---

## Stack

**Python 3.12 provisioned with `uv`.** The machine had only Python 3.9, and the
specification asked for 3.12. `uv` was already installed, so it provisions a
3.12 toolchain into `backend/.venv` without touching the system Python.
*Reversible:* delete `backend/.venv`.

**Vite + React + TypeScript rather than Next.js.** The spec allowed either. This
application is a single-user local tool with no SEO surface, no server
rendering requirement and no routing beyond a nine-step linear workflow.
Next.js would have added a server runtime the product does not use. Vite gives
the same TypeScript strictness, unit tests and Playwright coverage the
Definition of Done requires, at 68.9 kB gzipped.

**Navigation is a state machine, not a router.** The workflow is strictly linear
and gated — you cannot read a shortlist that has not been produced. A router
would let a user deep-link into a screen with no data behind it. Disabled steps
say *why* they are disabled rather than disappearing.

**Hand-rolled store rather than a state library.** One context, one server, one
workflow. A store library would have added a dependency without removing code.

---

## Demo data

**Real institution names with invented figures.** The alternative — fictional
universities — would make the demo read as a toy and would not exercise the
dedupe logic that real naming variants ("The University of Melbourne" vs
"Univ. of Melbourne") demand. The mitigation is layered and deliberate:

- every corpus page carries a visible banner and a `<meta name="unimatch-fixture">` tag
- the fetcher serves them under a distinct `fixture://` scheme
- the UI badges every fixture source and shows a demo notice on the shortlist
- every exported row is stamped `DEMO FIXTURE (synthetic)` in a data-origin column
- the README says plainly that the numbers are invented

**The corpus is seeded to fail in specific ways.** Sixteen universities were
written to exercise one QA case each: a "full ride" that is only full tuition, a
per-band IELTS trap, an EEA-only award, a passed deadline, a cross-year award
amount, a university with no scholarship page, and one with no pages at all.
This is why the demo shows five different "unknown" states rather than a clean
table — the failure handling *is* the product.

**Forty candidates by default** (16 detailed + 24 catalogue-only), inside the
30–50 range the specification asked for. The catalogue-only entries are kept
rather than dropped, because "we found this university but could not verify
anything about it" is a real and useful result.

---

## Research and evidence

**A single `2026/27` academic year for the corpus**, with one deliberate
exception (Toronto's award quoted for 2024/25) that exists to prove the
cross-year refusal works.

**Source specificity is an ordered ranking**, and that order does real work in
two places: which value the conflict panel marks as preferred, and which value
eligibility actually enforces. These were briefly inconsistent during
development — eligibility used recency while the panel used specificity — which
would have let the UI recommend one value and the verdict use another.

**Freshness windows are per claim type**: 30 days for deadlines and intake
status, 120 for costs and award amounts, 180 for policies. Chosen because those
are the rhythms at which the underlying facts actually change. A stale claim is
downgraded to `POSSIBLY_STALE`, never discarded.

**An aggregator can never support a decision-grade claim.** `DECISION_GRADE_CLAIMS`
lists the sixteen claim types where this applies. A ranking may find a
university; it may not tell you its tuition.

**Excerpts are capped at 600 characters** and truncated rather than rejected, so
we store proof that a value was read without copying pages.

---

## Assessment

**Hard filters fire only on confirmed requirements.** A requirement is a barrier
only when its claim is `VERIFIED_CURRENT` or `POSSIBLY_STALE` *and* the applicant
has a value that misses it. Absent data, unverifiable data and test-optional
policies never eliminate a university. The asymmetry is intentional: a false
"you can't apply here" is far more costly than a false "check this one".

**No probability is ever produced.** `AdmissionsFit` has four ordinal values and
no numeric form. The preference score is a weighted sum of exposed components
with user-adjustable weights, and its schema carries a disclaimer that travels
with the number everywhere it is rendered.

**Missing data costs 3% of the score per absent field, capped at 25%.** Without
a penalty, a sparse profile would tie with a fully-verified equal match; with an
uncapped one, an unverifiable university would sink below genuinely bad options.

**A living stipend substitutes for a meal plan** in reaching
`FULL_RIDE_CONFIRMED`. Universities describe the same coverage both ways. Both
the classifier and the gap calculator apply this rule — they disagreed at one
point during development, which is a defect the tests now prevent.

**Stacking needs consent from both sides.** An award that says "may not be
combined" blocks stacking even when another award offers to stack. This was
initially one-sided and overstated available aid by several thousand dollars.

---

## Politeness and privacy

**robots.txt is honoured with no override.** There is no setting to disable it
in a supported way, and it gates the Playwright tier exactly as it gates plain
HTTP.

**Live discovery starts from a curated institution registry, not a search
engine.** A search query would carry applicant context to a third party. The
cost is coverage: adding an institution means editing a JSON file.

**Currency conversion uses a dated static snapshot.** A wrong-but-dated rate the
user can audit beats a live rate they cannot. The rate and its date travel with
every converted figure, and an unknown currency raises rather than being guessed.

**The audit log holds ids and action names only.** A test asserts that no name,
citizenship, test name or GPA appears in it, so the log can be shared without a
privacy review.

**Deletion is enforced by the ORM, not by `PRAGMA foreign_keys`.** A pragma is
per-connection and easy to lose; deletion is a privacy guarantee and must not
depend on one. This was found by a test that passed against the real database
and failed against a fresh engine.

---

## Interface

**Editorial "research dossier" direction.** The product's substance is evidence,
so the surface reads like a case file: a serif display face for structure, a
grotesque for dense data, a monospace for anything quoted from a source, warm
paper in light and deep ink in dark. Status colour is semantic — one hue per
product meaning — never decorative.

**A dense table, not a card grid.** The task is comparing thirty rows on the
same axes. Cards would make that impossible. Detail lives in an expandable
drawer with six tabs, because one row carries six different kinds of
information.

**Long status labels are shortened in the table only**, with the full phrase
always available as a tooltip. "Needs official clarification" is 29 characters
in a column competing with seven others.

**The decision column is pinned to the right edge.** It is the primary action
and must never be the first thing to scroll out of view.

**Screenshots are namespaced by Playwright project.** Both projects run the same
specs; without namespacing the mobile run silently overwrites the desktop
captures.

---

## Scope deliberately not built

- **Alembic migrations are configured but the schema is created directly.**
  There is exactly one schema version, so a migration chain would be ceremony.
  `SchemaVersion` stamps the version for a future upgrade path.
- **The job queue is in-process.** Correct for one applicant on one machine. Its
  interface is Celery's, so replacing it touches one file.
- **No authentication.** The tool is single-user and local. Adding auth without
  a stated deployment model would be speculative.
- **No portal automation of any kind.** Out of scope by the specification, and
  the boundary is stated in the UI rather than merely omitted.

## Payments

- **4990 ₸ is a placeholder.** It is the configured default for
  `UNIMATCH_CASE_UNLOCK_PRICE_KZT` and has not been confirmed as the price the
  product will launch at. It changes in `.env`, not in code.
- **The adapter has never spoken to ApiPay.** No merchant account exists yet.
  Every payment claim rests on contract tests written against ApiPay's
  published OpenAPI document, read on 2026-09-04 — not on an observed
  transaction. Field names, status vocabulary and the webhook body are as that
  document defines them; if the live service differs, the adapter is wrong.
- **Our own ApiPay tariff must stay active.** `tariff_inactive` is a 403 that
  stops every customer paying, and nothing in the product can work around it.
- **A free run is capped at 5 candidates.** Chosen so an unpaid case cannot
  cost a full crawl, not from a measurement of what converts.
- **Refunds are operated from the ApiPay dashboard.** The provider supports
  them; we deliberately built no UI for them in phase 1.
- **Organization subscriptions are built, as a quota rather than blanket
  access.** Phase 1 had reserved an organization-wide entitlement meaning "this
  school sees everything"; phase 2 removed it, because a quota grants the right
  to spend rather than the right to see. Anything written against that earlier
  shape is out of date.
- **The subscription price list is not in the product.** It only records what
  was sold. Nothing here quotes a school, and nothing validates that the number
  in `--cases` matches an invoice.
- **An expired term burns whatever quota it still held.** That is what "until
  the term ends" means; only exhaustion-then-renewal preserves value, and it
  does so by starting the next subscription rather than carrying anything over.
- **A school's term starts when it opens its first case, not when the invoice
  was paid.** A queued renewal cannot know its start date at sale time, and
  using two different rules for first and subsequent subscriptions would need
  two activation paths that must agree.
- **Two subscriptions sold in the same microsecond have undefined order.**
  Grants are manual CLI actions, so this cannot happen in practice; the tie is
  broken by a random id if it ever does.
