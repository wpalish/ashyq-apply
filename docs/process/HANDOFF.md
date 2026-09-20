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

**V2-11 — privacy-safe discovery query generator (in-progress).** V2-10's seam is committed. V2-01 was accepted 2026-09-21 and its record is below.
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

V2-10: the search seam ships in `backend/app/adapters/search/` — `base.py` (`SearchResult`, `SearchResponse`, the `SearchProvider` Protocol, `SearchError`/`SearchProviderNotConfigured`/`SearchUnavailable`), `fake.py` (offline, corpus-driven, stamps `provider="fake"`), `__init__.py` (`get_search_provider`, `KNOWN_SEARCH_PROVIDERS`), plus `Settings.search_provider` defaulting to `none` with `_validate_search`. 22 tests in `tests/test_search_provider.py`, 100% coverage of the new package. Nothing is wired into discovery: query generation is V2-11 and fusion is V2-16. V2-01: **the corpus is certified.** `ground_truth.reviewed.json` (`2026-09-21.reviewed`) carries `human_verified` + reviewer **Диас** + `2026-09-21` on 10/10 cases, and `metrics.reviewed.json` is the first report in this project produced **without `--allow-drafts`**, `provisional: false`. Acceptance record in `backend/evaluation/research/ACCEPTANCE.md`; two new tests pin the gate (`test_the_reviewed_corpus_is_signed_and_scores_strictly`, and `test_certification_changes_no_measured_value`, which forbids a signature from ever moving a number). The owner's answer also settled the Aalto adjudication in the affirmative; it is recorded as a decision in that case's notes with the reasoning it overrides preserved. Draft7 applies the **owner's first human review of the corpus** — 62/220 known fields, 10/10 identities, two cases changed. Aalto's identity moves from the Finnish tietotekniikka page to the English-taught Computer Engineering major, because the requested scope is an international applicant and the Finnish route is not open to one in English; whether Computer Engineering satisfies a *computer science* request is left open for the reviewer, not asserted, on the same grounds draft2 refused Data Science. HKU gains `programme.faculty = "School of Computing and Data Science"` and its exact degree title, Bachelor of Engineering in Computer Science. Programme precision/recall are unchanged at 1/9 and 1/10 — the Aalto URL move neither gained nor lost a match against the frozen capture. Still 0/10 `human_verified`, because the schema requires a reviewer name and date and no AI may invent either. Draft6 resolves the Delft exact programme identity from the official tudelft.nl page — the last `unknown` of ten, carried since draft2 — taking programme identities to **10/10** at 61/219 known fields and 0/10 human signoffs. One field changes; no label, no frozen artifact and no production file is touched. Its two programme numbers *fall* (precision 1/8→1/9, recall 1/9→1/10) because a tenth answerable case and a ninth judgeable prediction enter the denominators against the same frozen capture: arithmetic, not a retrieval regression, and REVIEW_DRAFT6.md says so in those words. Draft5 is published in `a4cd5b3` (gpt-6-astra) — 61/219 known/total fields, 9 programme identities, 0 human signoffs, NTU qualification and conditional `english_evidence.*` minima plus the Toronto Kazakhstan credential, with separate report/worksheet/VERSIONS row and the replay test parametrised over `.draft5`. It was committed `wip:` because its gates had not finished; claude-opus-5 ran them on 2026-09-20 and they are green (§6), so draft5 is released. Its content is recovered gpt-6-astra work, not a second implementation. `3f7e467` publishes draft4 with exact Aalto CS identity/primary Finnish teaching language and Groningen NIS qualification equivalence/CS mathematics requirement: 56/215 known/total fields, 9 programme identities, 0 human signoffs. Separate metrics and complete human-review worksheet; 57 focused tests. `2f56a46` publishes lossless draft3 document projection (52/212 known/total fields), reversible manifest, separate report and review worksheet; 55 focused tests. `5403630` adds explicit offline award/document identity mapping and replay; `00e107f` keeps unknown policies unanswered, adds the human review worksheet and brings focused coverage to 51 tests. `7356d9e` published draft2: 46/206 known labels, 8/10 exact programme URLs, 0/10 human signoffs; separate replay report with programme precision/recall 1/8 and 27 benchmark tests. Frozen draft1/capture are unchanged. `d917259` integrated all 15 Markdown documents plus original manifest and navigation/task card; pushed. `5d2a3ed` write-ahead V2-01 baton; pushed. All 16 archive entries verified byte-for-byte after transfer; original untracked ZIP removed. 51f9512 pushed schema, offline scoring, bounded live capture, 10 draft cases, 14 tests and container isolation. `a243a46` pushed checkpointed HTTP/PDF counters, candidate ranks and evidence validation. `1187cd0` published direct claim mapping, compact baseline capture/metrics/report and human review queue. `d0a2fb4` fixes JSON type equality; 25 benchmark tests and both full CI matrices pass. Draft PR: https://github.com/wpalish/ashyq-apply/pull/14. Human certification remains outstanding.


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

V2-10 is implemented and green (§6); the seam exists, nothing consumes it yet.

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
| 2026-09-20 | V2-10 | new package `app/adapters/search/`: `SearchResult`, `SearchResponse`, `SearchProvider` Protocol (`async search(*, query, domains=(), max_results=10)`), `SearchError` / `SearchProviderNotConfigured` / `SearchUnavailable`, `get_search_provider()`, `KNOWN_SEARCH_PROVIDERS`; `FakeSearchProvider(corpus, *, now, fail_with)` | The provider seam. No caller yet; import `get_search_provider`, never an adapter. |
| 2026-09-20 | V2-10 | `config.py`: `search_provider: str = "none"` (`UNIMATCH_SEARCH_PROVIDER`); `validate_runtime` gains `_validate_search` | An unknown name is refused at startup; `fake` is refused in production. `none` is a supported configuration, not a misconfiguration. |
| 2026-09-09 | security audit | `security.py`: `SCRYPT_R`, `SCRYPT_P`, `_maxmem(n, r)`; `routes_metrics` compares bytes | scrypt cost schedule and the 500-on-non-ASCII bearer. |

## 9. Traps and lessons (things that cost a session; keep them)

V2-01: set PYTHONUTF8=1 on Windows for text fixtures; do not modify evaluation schemas while a live batch is running (parent and child processes can import different versions). Instrumented baseline segments and restart are recorded in baseline/README.md. Scope matching is deliberately literal; missing/different names count as conservative match failures, not human-confirmed wrong facts.

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
