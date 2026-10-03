# Reference fact recovery — 2026-10-02

## Acceptance target

The owner asks to configure search against the reviewed facts. The unchanged
`2026-09-23.reviewed` development corpus contains **62 known facts**, with the
other 158 labels UNKNOWN. Neither catalogue counts nor a successful job is
acceptance. The offline command below exits **2** on missing cases, incomplete
captures, missing known facts or scored value/scope/support failures:

```sh
cd backend
.venv/bin/python -m evaluation.research.reference_acceptance \
  --capture PATH_TO_CAPTURE --out PATH_TO_ACCEPTANCE_REPORT
```

A pass concerns this fixed corpus only. Unadjudicated extra claims, currentness,
held-out generalization and public runtime acceptance remain separate. Original
reviewed gold and reviewed identity bindings are byte-identical to main.

## Measurements completed

All live comparisons use the configured Exa MCP provider, 300 seconds and at
most 60 non-cached page reads per case, HTTP only, production Fetcher policies.
HTTP wire attempts (robots/retries) are a separate counter. All profiles are
synthetic and all databases isolated. This is a controller diagnosis using the
previous expert findings; **no new blind expert trace is claimed**.

The ten-case baseline recovered **11/62** under the original exact identity
bindings. UBC recovered 3/3 but exhausted its budget; the acceptance command
correctly fails. This first series spans the recorded source revisions in its
per-case metadata; it is not relabelled as one exact-head release measurement.

| Case | Correct reviewed facts |
|---|---:|
| Groningen | 2/11 |
| Delft | 1/1 |
| Aalto | 0/2 |
| Vienna | 1/4 |
| Warsaw | 2/2 |
| UBC | 3/3, budget exhausted |
| Toronto | 0/4 |
| HKU | 1/4 |
| NTU | 1/21 |
| KAIST | 0/10 |

### ER-08: admissions are an independent evidence obligation

A programme classifier rejected the department's admission navigation before
verification. The new bounded route retains explicit undergraduate-admission
links from at most two already-selected catalogue roots. It adds at most two
extra admission pages, preserves existing slots and never turns the link into
a programme or a claim. Reads and claims retain normal Fetcher, official-site,
classifier, verbatim and scope guards. A quote saying undergraduate students
(English or Korean) may supply the claim's own degree; a department name or
mixed graduate/undergraduate sentence cannot.

The first arm reached the real page but scored **0/10** because the Korean
undergraduate scope was missing. This failed trial remains preserved. The
subsequent same-budget pair scored **0/10 off → 1/10 on**, with exact-page quote
support and 0/1 wrong-scope claims. A repeat of the narrowed rule recovered the
same fact. This is one recovered fact, not 10/10 or proof of a programme.

The initial broader admission-list arm exhausted Aalto's page budget while
adding no fact. It was narrowed to only the explicitly discovered obligation
links. The narrowed Aalto repeat completed with zero claims and no budget error.
NU's paired output retained the same claims. Both METU arms exhausted their
300-second wall clock with zero predictions: this is an availability limit,
not a positive held-out quality result. The full-cohort repeat is recorded below; do not infer broad accuracy from
these pilots.

### NTU: measurement repair, distinct from discovery improvement

The live pipeline already found the named Nanyang Global Scholarship at an
`/admissions/ug/scholarships/` URL. The old registry recognized only the earlier
`/admissions/undergraduate/scholarships/` URL. A separate Fetcher diagnostic of
that older URL followed its current redirect to `scholarships-and-awards`;
both current official pages explicitly name the same award. Exact source/name
aliases are recorded in `identity_bindings.2026-10-02.observed.json`.

The original signed file is unchanged. The added aliases are AI-observed
identities under the owner's calibration request, **not a new human signoff**.
They contain no expected values or applicability verdicts. The same frozen
capture re-scored with the observed aliases yields **16/62**. These five extra
credits are a mapping correction, not five newly discovered facts. Both scores
and Fetcher URL/title/body hashes are retained.

## Remaining work

The reference acceptance is still **FAIL**. The mapper can express only 51/62
known keys: ten document/award identities and one translation-condition field
have no supported mapping. Document collection also occurs after shortlist
approval; the pre-decision canary does not exercise it. Several returned values
carry narrower or more detailed conditions than the frozen label vocabulary.
Those differences require source-backed diagnosis, not removal of conditions
or rewriting the gold to make a score green. Funding eligibility, exact scope,
country credentials and unavailable sources remain part of ongoing recovery.

## Artifacts and automation

Committed reports, exact pilot captures and proof hashes:
`backend/evaluation/research/expert/data/runs.2026-10-02/`.
Raw captures, logs, Fetcher bodies and a manifest are retained under ignored
`artifacts/reference-facts-2026-10-02/`. Failed trials remain included.

GitHub rejected the benchmark-workflow edit because this OAuth connection lacks
`workflow` scope. The proposed workflow change is saved as
`artifacts/reference-facts-2026-10-02/workflow-proposal.patch`; the CLI gate works
locally. **Automatic GitHub enforcement has not been installed.** Ordinary CI
success must not be reported as a pass of the reference-fact acceptance.

## Exact-source full repeat (bc84ccf)

The repeat completed all ten observations on source `bc84ccfd11168db9124d088c49b80e9a99fdd54b`
and the observed-alias map: **13/62**. NTU is6/21 and KAIST1/10. Groningen lost
its two baseline credits because the 295-second child deadline fired after it
had read the correct programme but before discovery/verification finished.
Warsaw lost its two credits after the search provider began returning **HTTP429**;
Vienna also records that provider failure. UBC again exhausted its page budget.
This repeat is **not evidence of a full-cohort improvement**. Both positive and
negative outcomes are committed in `final.capture.json`/`final.acceptance.json`.

Further live probing is stopped after the provider throttle; no alternative API
key is configured locally. The owner was asked to configure provider access
through application secrets (no credential requested in chat). Work continues
offline on the first reproduced budget loss: a confirmed exact single-field
programme should not be followed by unnecessary alternative/PDF confirmation.

Final local source gates at this checkpoint: Ruff/format, mypy327, **2894 backend
passed /94.91%**; the10-test reference-acceptance suite including the subsequently
added exact-alias check also passed. Frontend232/type/lint/build and isolated
demo/one migration head passed. These do not override the failed reference gate.


## ER-09 offline budget experiment — not promoted

The opt-in `--finish-exact-single-field` requires the fetched page to be a
programme, its degree to match, and existing ontology identity to return YES
for the sole requested field. Listing titles and ambiguous/other-degree pages
cannot end confirmation early. Multiple requested fields keep their existing
shared exploration. The production constant remains **False**.

The five completed Groningen confirmation reads from the exact-source repeat
were replayed using their original Fetcher-cache bodies with zero network
calls. Off: five reads, including the same programme with an English query
parameter. On: one read, preserving the first official programme page.
Historical read-time sums were 23.8s and 2.1s; these are **not measured live
latency**, saved claim counts or a full frozen pipeline comparison. Search
result titles were not recorded and are blank in both replay arms. The sixth
read that hit the live deadline is not simulated. Body and log hashes are in
`er09.frozen-prefix.json`; replay source and raw log are retained in ignored
`artifacts/reference-facts-2026-10-02/er09/`.

Latest focused verification: **203 tests passed** across discovery, multi-field,
admission obligations and reference acceptance; Ruff/format and mypy327 pass.
The earlier full-suite result remains separately dated above. The reference
command still exits2 with **13/62**, capture errors and scored support/scope/value
failures. PR #41 remains draft, with no merge or deployment from this branch.

Next: after provider access is configured, run equal300s/60-read off/on captures
for Groningen and independent universities using the recorded experiment flag.
Before promotion, evaluate complete verified claims and source/scope regressions;
a saved read alone cannot pass acceptance. The remaining document/award mappings
and document-stage coverage also require source-backed work.


## ER-10 evidence durability — 2026-10-03 continuation

A completed requirement adapter result was held in memory while cost and
government adapters ran. A downstream interruption therefore erased already
extracted claims. The regression first failed with `NoResultFound` from an
independent database connection: no result had been committed.

The runner now checkpoints new rows after completed requirements and costs,
and commits each completed programme before reading the next. Partial and
final checkpoints share the existing campus, source hierarchy, freshness and
conflict checks. Partial results carry a blocking `research incomplete`
question and keep their default unknown/clarification verdicts. They do not
increment completed-programme counts. A successful final checkpoint replaces
partial evidence and removes the marker. Claim counters use replacement deltas.
A retry keeps a prior attempt's existing row intact until a full replacement
is ready, preserving earlier richer evidence and applicant notes. The existing
transactional worker-lease fence still controls every commit.

A paired offline replay used the same recorded Groningen programme response,
normal requirements extraction, an injected cost failure and two isolated
SQLite databases. Before: **1 read, 0 stored rows, 0 claims**. After: **1 read,
1 incomplete row, 3 stored claims, 0 completed programmes**. An independent
connection confirmed the committed state. No network calls, extra source URLs
or reviewed labels were used. This proves durability at that interruption,
not a new end-to-end reference-recall score. Raw page, script, failure log and
hashes are retained under `artifacts/reference-facts-2026-10-02/er10/`; structured
proof is `runs.2026-10-02/er10.frozen-durability.json`.

Seven dedicated regressions cover cost/government exceptions and cancellation,
retry deduplication and notes, preservation of existing full results, and
campus/freshness/hierarchy/conflict guards. The focused pipeline/government/job
suite passes78 tests; Ruff/format and mypy327 pass. Full backend **2910 tests
passed /94.92% coverage** (459.21s). Frontend232/type/lint/build pass. Isolated
demo preserves Groningen first and UBC OUT_OF_BUDGET; Alembic has one head
(d8e412c6a901).
Last full live acceptance remains13/62 onbc84ccf; no ER-10 live score is claimed.


## ER-11 document scope and explicit referee constraints — 2026-10-03

The normal document adapter was replayed offline on the two retained NTU HTML
responses from 2026-10-02. It previously copied `international` from a Tuition
Grant/bond paragraph into every document claim. Each submission clause now takes
its population from its own text and structural section headings. Other page scope
and the builder state are preserved. The role/exclusion are extracted only from
explicit unconditional appraisal instructions, with legacy string fallback.

Same-site redirects now retain the final URL in both claims and checklist rows;
cross-site redirects produce no document evidence. Four exact document identities
(two document names on two current NTU URLs) are in a new versioned binding file.
The reviewed bindings, prior observed bindings and signed gold are untouched.

| Offline variant | UG URL | Redirected old URL |
| --- | --- | --- |
| Old raw claims, old identities | 0/21 | 0/21 |
| Old raw claims, new identities | 0/21 (three wrong-scope fields) | 0/21 (old URL retained) |
| Repaired reader, new identities | 5/21 | 5/21 |

All five known document labels match in the repaired output: essay required,
maximum250words, referee required, school_teacher, relatives disallowed. The
unchanged NTU denominator includes16 other known facts not exercised by this
reader. Same-reviewed-page recall is0/21 because the official page URLs differ
from the old reviewed URL; the unchanged scorer's same-institution rule supplies
credit. There is no new human support/currentness adjudication. Exact source
quotes, metadata, body hashes, before/after claims and all three score reports
are in `er11.frozen-documents.json`.

Expressible known keys rise51→56/62; that is mapping capacity, not live recall.
Six remain unreachable: Groningen translation exception and course-description
conditions, Toronto supplemental application, and HKU entrance award identity/
application mode. Document collection occurs after shortlist approval; these five
matches must not be added to the latest pre-decision live score13/62. No new blind
capture or public release is claimed.

Focused98 tests, Ruff/format327, mypy327 and frontend232/typecheck/lint/build pass.
Full backend:2927 passed,94.94% coverage in414.05s. Isolated migrated demo
(with approved checklists) keeps Groningen first and UBC OUT_OF_BUDGET;
one Alembic head d8e412c6a901. Logs: /tmp/unimatch-er11-*.log.


## ER-12 explicit translation exception — 2026-10-03

A fresh normal-Fetcher read of Groningen's document page returned200. Its complete
clause exempts originals in English, Dutch, French or German and requires original
plus translation otherwise. The existing reader converted this into an
unconditional `Certified English translation of non-English documents`, which
inferred both English-only and certification. The page also explicitly permits
self-made translations for assessment.

The repaired reader preserves `required_unless_language_in` as a structured claim
and puts the condition in the visible checklist name, with the source clause in
format notes. It does not add certification or require a third-party translator.
Unparsed conditional translation text and mere permission to use translations
cannot fall through to the unconditional generic rule. Different stated language
lists stay separate; exact repeats are deduplicated. New identities are in
`identity_bindings.2026-10-03.conditions.json`; both older observed files remain
unchanged. Invalid lists/unknown identities/shapes remain unmapped.

`er12.frozen-translation.json` compares the old1c3db3e reader with the repaired
reader using the same saved page, same mapping and same new identity file:
**2/11→3/11**,25 raw claims on each arm. The translation exception is the one new
known fact matched, with source URL, quote and scope retained. Full Groningen
known-fact denominator11 is unchanged. This is explicit-source evaluator
replay; it is not a live discovery result. New expressibility ceiling57/62 is
mapping capacity; last full live result remains13/62.

Focused113 tests, Ruff/format/mypy328, frontend232/typecheck/lint/build and isolated
approved-checklist demo passed. Full backend:2942 passed,94.95% coverage
in460.51s; one Alembic head d8e412c6a901. Groningen remains first and UBC
OUT_OF_BUDGET in the isolated migrated demo. Logs: /tmp/unimatch-er12-*.log.

### Remaining source diagnosis

- Groningen's current document page is readable, but its extracted text/IR has no
  course-description or Kazakhstan NIS Grade12 clause. The two original known
  course-description labels stay unmet; absence is not a contrary answer.
- Toronto's current programme page is readable. `Supplemental Application / Required`
  is an HTML table row. The surrounding academic requirements picker includes
  Ontario/OSSD and multiple campuses; a future rule must preserve the applicable
  programme/qualification context and must not flatten it into every applicant.
- HKU `/node/891`: normal Fetcher could not read robots.txt (ConnectError), so it
  returned `robots_disallowed` under its fail-closed policy. No claim extracted,
  no retry/bypass or alternate identity used.

The three diagnostic provenance records are retained in
`remaining-documents.sources.json`; raw caches are under ignored
`artifacts/reference-facts-2026-10-03/remaining-documents/`.


## ER-13 source-qualified supplemental documents — 2026-10-03

Toronto's programme HTML has St.George/Ontario headings, followed by a school
system form whose hidden h2 labels replaced that context in the flattened outline.
Form-only hidden/control headings now leave the evidence context intact; genuine
accessible headings and working accordion headings remain. The table reader accepts
only an explicit supplemental-application / Required row under a matching programme
heading. Multiple campuses require an explicit choice; optional/conditional values,
foreign programmes and disconnected rows produce no obligation.

Qualification is preserved in the claim, visible checklist and evaluator; the
mapper previously silently discarded this existing scope field. Exact row/source
identity is versioned separately. Normal Fetcher replay of the saved page goes
from0 documents/claims to1 scoped document/claim, but **Toronto recall stays0/4**:
the section has no explicit degree level. The claim is marked for clarification;
requested bachelor degree is not substituted. Ontario Secondary School Diploma
(OSSD) scope must not be applied to every applicant.

The linked generic supplemental page confirms the programme/campus association.
The linked Arts&Science programme page returns a human-verification challenge with
HTTP200; its title and226-character response are recorded, with no extracted claim
or challenge bypass. `er13.frozen-supplemental.json` retains both linked-source
records, original page provenance and before/after output. Signed gold unchanged.

Focused77/Ruff/format/mypy330/frontend232/type/lint/build/demo pass; full backend
is running. First full attempt was interrupted to add the negative case for an
accessible heading beside unrelated evidence/form. It is not a completed gate.

Next bounded live diagnosis explicitly selects provider=none (catalogue/sitemap
walk only),300seconds/60reads per case for Groningen/Toronto/NTU. It does not retry
Exa429 and will not be mixed with the former provider-backed13/62 score.

### ER-13 completed gates and separate catalogue-only diagnosis

Source33804d0: backend2960 passed /94.94%; frontend232/type/lint/build, Ruff/format/mypy330 and isolated demo pass. Three cold runs independently used provider=none,300s/60 noncached Fetcher.get responses; no gold URLs injected. Groningen0/11 (140.0s), Toronto0/4 (50.8s), NTU1/21 (28.2s, one wrong-scope prediction). Captures, raw sidecars, logs and per-case immutable-gold scores are in `runs.2026-10-02/catalogue-only.2026-10-03`. This is not a paired improvement over Exa13/62. HTTP telemetry counts individual pinned requests, including redirects/robots, whereas the60 cap counts noncached get responses; Groningen88 HTTP requests does not mean88 budgeted pages. Toronto reads the relevant field index but descends elsewhere; investigate generic routing next.
