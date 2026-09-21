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

**Phase 1 retrieval measured against the certified corpus.** The owner approved the §6 exception and authorised the live probe; the Exa adapter works and the retrieval ceiling moved **1/10 → 9/10**. V2-01 was accepted 2026-09-21 and its record is below.
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

**MEASURED 2026-09-21, live, 50 queries:** the Phase 1 retrieval path with Exa reaches the signed correct programme page in **9/10** cases, up from **1/10** on the frozen capture. Zero cases retrieve nothing (was 3). Our ranking puts the correct page first in **2**, so a reranker now has **7** cases of headroom where V2-14 measured none — `RERANKER_CEILING.md` is marked superseded for this path and `SEARCH_PROBE.md` carries the new numbers, the per-case table and the two failure shapes. `evaluation/research/search_probe.py` (+ `baseline/search_probe.exa.json`) reproduces it; 14 tests, 100%, none touching the network. V2-10b: `app/adapters/search/exa.py` — `ExaSearchProvider` behind the V2-10 seam. POST `api.exa.ai/search` with `type=auto`, `numResults` (capped at 25), `includeDomains`, `contents.highlights`; every failure becomes `SearchUnavailable`; no retries; response body capped at 1 MiB; the endpoint goes through `network_policy.check_url`. `config.py` gains `exa_api_key: SecretStr` and refuses to start with `exa` selected and no key. 27 tests in `tests/test_exa_provider.py`, module at 100%, none touching the network. **Default is still `UNIMATCH_SEARCH_PROVIDER=none`** pending the §7 decision. V2-17: `app/domain/programme_identity.py` (the rule — `Verdict`, `ProgrammeIdentity`, `IdentityState`, `ScopeState`, `identity_state`, `scope_state`, `applies_to_requested_intake`, `unresolved`, `refuted`, `explain`) and `app/adapters/search/identity.py` (`verify_candidate`, reading the six dimensions from stated evidence only). Identity and scope are separate; `UNKNOWN` is never a match and never a failure; `applies_to_requested_intake` returns a `Verdict`, not a bool. 32 tests in `tests/test_programme_identity.py`, both modules at 100%. V2-16: `app/adapters/search/fusion.py` — `Generator` (seven sources), `GENERATOR_WEIGHTS`, `SourcedCandidate`, `Attribution`, `FusedCandidate` (`agreement`, `best_rank`, `provenance`), `fuse(streams, *, top_k, weights)`. Reciprocal Rank Fusion, so nothing incomparable is ever added; every attribution survives into the output; a candidate filed under the wrong generator is refused. 23 tests in `tests/test_fusion.py`, module at 100%. V2-15: `app/adapters/search/site_search.py` — `detect_surfaces` for the nine §7 families, `SiteSearchSurface` (kind, endpoint, query parameter, provenance, evidence, detected-at), `search_url` with bounded pagination, `MAX_PAGES = 5`, `MAX_RESPONSE_BYTES = 2 MiB`, `NEEDS_CREDENTIALS`. Passive network-log evidence outranks markup inference, off-domain and administrative surfaces are discarded, and a key-bearing surface is flagged with its key deliberately unread. 36 tests in `tests/test_site_search.py`, module at 100%. V2-14: **the reranker comparison was not built, because the measurement says it would measure nothing.** `evaluation/research/ceiling.py` (+ CLI), `baseline/ceiling.reviewed.json` and `RERANKER_CEILING.md` record it: against the certified corpus and the frozen capture, the correct programme page is in the candidate set for **1/10** cases, the current ranking already has that one at position 1, so **headroom for any reranker is 0**. Three cases retrieved nothing at all. 13 tests in `tests/test_reranker_ceiling.py`, module at 100%. V2-13: `app/adapters/search/prefilter.py` (§5 chain over `SearchResult`s, every rejection recorded with its reason) and `retrieval.py` (self-contained BM25, named deterministic signals, `rank_candidates`, `discover_candidates`, `RetrievalReport`). It **reuses** `live_discovery`'s `canonical_url` / `same_institution` / `names_other_degree_level` / `looks_like_catalogue` rather than writing a second copy; one public `is_excluded_path` was added there for the same reason. 29 tests in `tests/test_hybrid_retrieval.py`; package at 100% across all seven modules. V2-12: `app/adapters/search/ontology.json` (versioned `2026-09-21.1`, six field concepts and all four degree levels) and `ontology.py` — `canonical_field`, `is_equivalent`, `retrieval_candidates`, `degree_aliases`, `ontology_version`, `Relation`, `RetrievalCandidate`. Equivalence and retrieval expansion are separate functions returning different things, so a related concept can never come back from the equivalence one. 29 tests in `tests/test_ontology.py`; package still 100%. V2-11: `app/adapters/search/intent.py` — `DiscoveryIntent` (six fields, none of them about the applicant), `from_profile` as the single sanctioned conversion, `queries_for` rendering the §4 families under a bounded `DEFAULT_QUERY_BUDGET = 6`, `QueryPrivacyError`, and `redacted_audit_record`. 27 tests in `tests/test_discovery_intent.py`, one per forbidden item in the spec's list; `app/adapters/search/` is at 100%. Also made `test_a_slow_parse_does_not_block_an_unrelated_request` deterministic — see §9. V2-10: the search seam ships in `backend/app/adapters/search/` — `base.py` (`SearchResult`, `SearchResponse`, the `SearchProvider` Protocol, `SearchError`/`SearchProviderNotConfigured`/`SearchUnavailable`), `fake.py` (offline, corpus-driven, stamps `provider="fake"`), `__init__.py` (`get_search_provider`, `KNOWN_SEARCH_PROVIDERS`), plus `Settings.search_provider` defaulting to `none` with `_validate_search`. 22 tests in `tests/test_search_provider.py`, 100% coverage of the new package. Nothing is wired into discovery: query generation is V2-11 and fusion is V2-16. V2-01: **the corpus is certified.** `ground_truth.reviewed.json` (`2026-09-21.reviewed`) carries `human_verified` + reviewer **Диас** + `2026-09-21` on 10/10 cases, and `metrics.reviewed.json` is the first report in this project produced **without `--allow-drafts`**, `provisional: false`. Acceptance record in `backend/evaluation/research/ACCEPTANCE.md`; two new tests pin the gate (`test_the_reviewed_corpus_is_signed_and_scores_strictly`, and `test_certification_changes_no_measured_value`, which forbids a signature from ever moving a number). The owner's answer also settled the Aalto adjudication in the affirmative; it is recorded as a decision in that case's notes with the reasoning it overrides preserved. Draft7 applies the **owner's first human review of the corpus** — 62/220 known fields, 10/10 identities, two cases changed. Aalto's identity moves from the Finnish tietotekniikka page to the English-taught Computer Engineering major, because the requested scope is an international applicant and the Finnish route is not open to one in English; whether Computer Engineering satisfies a *computer science* request is left open for the reviewer, not asserted, on the same grounds draft2 refused Data Science. HKU gains `programme.faculty = "School of Computing and Data Science"` and its exact degree title, Bachelor of Engineering in Computer Science. Programme precision/recall are unchanged at 1/9 and 1/10 — the Aalto URL move neither gained nor lost a match against the frozen capture. Still 0/10 `human_verified`, because the schema requires a reviewer name and date and no AI may invent either. Draft6 resolves the Delft exact programme identity from the official tudelft.nl page — the last `unknown` of ten, carried since draft2 — taking programme identities to **10/10** at 61/219 known fields and 0/10 human signoffs. One field changes; no label, no frozen artifact and no production file is touched. Its two programme numbers *fall* (precision 1/8→1/9, recall 1/9→1/10) because a tenth answerable case and a ninth judgeable prediction enter the denominators against the same frozen capture: arithmetic, not a retrieval regression, and REVIEW_DRAFT6.md says so in those words. Draft5 is published in `a4cd5b3` (gpt-6-astra) — 61/219 known/total fields, 9 programme identities, 0 human signoffs, NTU qualification and conditional `english_evidence.*` minima plus the Toronto Kazakhstan credential, with separate report/worksheet/VERSIONS row and the replay test parametrised over `.draft5`. It was committed `wip:` because its gates had not finished; claude-opus-5 ran them on 2026-09-20 and they are green (§6), so draft5 is released. Its content is recovered gpt-6-astra work, not a second implementation. `3f7e467` publishes draft4 with exact Aalto CS identity/primary Finnish teaching language and Groningen NIS qualification equivalence/CS mathematics requirement: 56/215 known/total fields, 9 programme identities, 0 human signoffs. Separate metrics and complete human-review worksheet; 57 focused tests. `2f56a46` publishes lossless draft3 document projection (52/212 known/total fields), reversible manifest, separate report and review worksheet; 55 focused tests. `5403630` adds explicit offline award/document identity mapping and replay; `00e107f` keeps unknown policies unanswered, adds the human review worksheet and brings focused coverage to 51 tests. `7356d9e` published draft2: 46/206 known labels, 8/10 exact programme URLs, 0/10 human signoffs; separate replay report with programme precision/recall 1/8 and 27 benchmark tests. Frozen draft1/capture are unchanged. `d917259` integrated all 15 Markdown documents plus original manifest and navigation/task card; pushed. `5d2a3ed` write-ahead V2-01 baton; pushed. All 16 archive entries verified byte-for-byte after transfer; original untracked ZIP removed. 51f9512 pushed schema, offline scoring, bounded live capture, 10 draft cases, 14 tests and container isolation. `a243a46` pushed checkpointed HTTP/PDF counters, candidate ranks and evidence validation. `1187cd0` published direct claim mapping, compact baseline capture/metrics/report and human review queue. `d0a2fb4` fixes JSON type equality; 25 benchmark tests and both full CI matrices pass. Draft PR: https://github.com/wpalish/ashyq-apply/pull/14. Human certification remains outstanding.


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
