# Security review — branch `claude/greeting-16wj2z`, commits since `5de8b6a3` (SEC-2)

Reviewer: claude-opus-5 (worktree agent). Range: `5de8b6a3..7d55695f` (116 commits, `a9cd2acb` to `7d55695f`).
It covers `backend/app`, `backend/scripts`, `backend/evaluation/research` (kb_build, core_drafts, wikidata,
identity-gate probe, read lists), `.github/workflows`, `frontend/src` and `frontend/e2e/kb-env`. The surfaces read
first are the ones NEXT_CYCLES_2026-10-22 lists under SEC-2: CAT-1, REL-1, WHY-1, E2E-KB, the `read_pages` lists,
NS-1b, LQ-2a, the fee shapes, the PDF decrypt path, `kb-refresh.yml`, `a15bf7d4` and `ci.yml`.

Held-out material, `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN`, `scratchpad/DEV5_BLIND` and
`DISCOVERY_ANALYSIS_2026-10-17.md` were not opened. The held-out check on the read lists compares domains in code
and prints counts only. No search provider was called. Nothing weakens `Fetcher`.

The severity scale is the one SECURITY_REVIEW_2026-10-19 used:

- **High**: attacker-controlled input stalls or breaks the product for every case.
- **Medium**: a real path that needs a precondition or is bounded.
- **Low**: defence in depth, or a path that needs repository write access or reviewed data.
- **Info**: noted, no action.

## Findings

| ID | Severity | Where | Status |
|----|----------|-------|--------|
| SR2-01 | **High** | `backend/app/adapters/page_classifier.py` `_HTML_LANG` (was l.289; used by `page_language` l.1539 and `is_host_root` l.314) | **Fixed** (`eca8f871`) |
| SR2-02 | **High** (pre-existing) | `backend/app/adapters/discovery/live_discovery.py` l.3594-3596 `_HTML_TAG`, `_LINK_TAG`, `_ATTRIBUTE` | **Fixed** (`a37138a1`) |
| SR2-03 | Medium | `.github/workflows/benchmark-capture.yml` `runner` input (l.22-25) and the RP-1 plan in `read_pages/README.self-hosted-2026-10-21.md` | **Mitigated in repo** (`fbbe8848`); the owner must act before registering a runner |
| SR2-04 | Low | `backend/app/adapters/search/intent.py` `_PHRASE_QUOTES` (l.407) | **Fixed** (`812e6de6`) |
| SR2-05 | Low | `backend/app/pipeline/runner.py` `_no_verified_programme_page` (l.1421-1444); `app/knowledge/__init__.py` `programme_route` | **Fixed** (`e9dd4472`, fixture `19cbea5b`) |
| SR2-06 | Low | `backend/evaluation/research/expert/core_drafts.py` `_number` (l.245); `app/knowledge/claims.py` `tuition_value` (l.538) | **Fixed** (`71c317bb`) |
| SR2-07 | Low | `frontend/e2e/kb-env/serve-api.sh` `rm -rf "$SCRATCH"` | **Fixed** (`06a67333`) |
| SR2-08 | Info | `frontend/e2e/kb-env/sitecustomize.py` `_ok` (l.22) | Noted |
| SR2-09 | Info | `backend/app/adapters/search/site_search.py` l.111-113; `evaluation/research/index_ceiling.py` l.541 | Noted (unreachable or eval only) |
| SR2-10 | Info | `backend/evaluation/research/wikidata_domains.py` `native_query` (l.695) | Noted |
| SR-07 | Info | `Fetcher._invalid_url` | Re-read: unchanged, still Info |
| SR-08 | Info | `app/domain/message_keys.py` | Re-read with the 18 new templates: worst 18 ms; still Info |

### SR2-01 (High, fixed): reading a page's `<html lang>` was quadratic on the event loop

`page_language` searched `<html[^>]*\blang\s*=\s*["']?([a-z]{2})` over the first 200,000 characters of a page.
`is_host_root` searched the same pattern over the whole page, up to `MAX_BYTES` (5 MB). The search restarts at every
`<html`. For each start, `[^>]*` runs to the next `>`, or to the end of the text, and then backtracks.

**Measured:** 40,000 unclosed `<html ` tags (200 kB) took **58 s**, and 20,000 `<html lang` took 31 s. All of it is
synchronous CPU time on the asyncio loop.

**Reach:**

- Before this range, LI-1 (`LOCALIZED_PAGE_IDENTITY`, on) already used the pattern.
- AW-2 (`78f70116`, `AWARD_SIGNALS_ALL_LANGUAGES` on by default) added a call from every page `classify_page` sees,
  at `page_classifier.py:1018`.
- ES-2 (`6aec5fc6`) added an unconditional call for every funding page, at `web_scholarships.py:610`.
- LQ-2 (flag off) added a call from the discovery walk.

Every live-mode read therefore reaches the pattern. One hostile university page freezes every case of the worker, and
of the API when a run executes there. That is the same impact as SR-01.

**Fix:** `html_lang_attr(html)` takes the earliest `<html` and the next `>` with `str.find`, and matches
`[^>]*\blang…` once from that tag's start, bounded by the `>`. If that fails, it continues after the `>`. A later
`<html` before the same `>` only sees a suffix of that text, so it cannot match where the first one did not. With no
`>` left, nothing after it can match either. The answer is the same as the old search's, the last `lang=` inside the
earliest matching tag. The regression test pins that against the old regex on 17 fixed cases and 4,000 random
markups. Each hostile input now finishes in under a second, including 2 MB for `is_host_root`.

Test: `backend/tests/test_html_lang_linear.py`.

### SR2-02 (High, pre-existing, fixed): the discovery tag and attribute scans were quadratic

The same class of bug is in three patterns of `live_discovery.py`. All three run on attacker-controlled page text:

| pattern | used by | measured |
|---|---|---|
| `_HTML_TAG = <html\b[^>]*>` | `english_alternate` l.3488 and `local_alternate` l.3530, both on the first 200,000 characters | 3.6 s at 200 kB of `<html ` |
| `_LINK_TAG = <link\b[^>]*>` | `findall` at l.3493, l.3535 and l.3569, on the same 200 kB head | 3.7 s at 200 kB of `<link ` |
| `_ATTRIBUTE` (name `[a-zA-Z_:][-\w:.]*` then `\s*=`) | every tag `_attributes` reads | **35 s for one 50,000-character attribute name**, quadratic: about 10 minutes at 200 kB |

`declared_alternates` runs from `DiscoveryTrace.note_read` (l.4212) on every identity read of the live walk. The
WF-17 trace is "recording only", but it is unconditional. NS-1b's hop pages are read on the same walk. A page
containing `<link aaaa…aaaa>` therefore stalls discovery for minutes. The code predates this range (`2feafa97` and
`a5e5512c`, 17-18 October). It is filed here because NS-1b and LQ-2 send more pages through the same walk.

**Fixed (`a37138a1`).** The applied fix is equivalent to the proposed patch below. It differs only in form:

- `_HTML_TAG` / `_LINK_TAG` are now `<html\b[^>]*+>?` and `<link\b[^>]*+>?`. A tag is consumed possessively up to
  its `>`, or to the end of the text when there is none, so the scan never restarts inside it. `_link_tags(head)` and
  `_html_tag(head)` drop a match that reached the end without `>`. This is exactly what the old `findall` / `search`
  returned, because with no `>` left no later start could match either.
- `_ATTRIBUTE` is the proposed pattern with the non-name-start head and the name made possessive (`*+`). A shorter
  name is followed by a name character, never `=`, so backtracking into it could never succeed.
- The three call sites' loop variable is `link_tag`, since `findall`'s `Any` no longer hid the reuse of `link` for
  `page_link(...)`.

`backend/tests/test_live_discovery_tag_scan.py` keeps the old patterns as the oracle and covers four things:

- **Hostile inputs**, each under 0.5 s. These are the review's three inputs, plus 150,000-character names that fit
  inside the 200,000-character head. The review's own `'<html lang="de"><link ' + "a" * 200_000 + ">"` is truncated
  before its `>`, so it never reaches `_attributes`. They run through `english_alternate`, `local_alternate` and
  `declared_alternates`, and through `_attributes` / `_link_tags` / `_html_tag` on 14 shapes.
- **Equivalence on generated input.** The groups, tags and dicts match the old patterns exactly on 60,000 generated
  realistic tags, 20,000 random markup strings and 1,000 multi-tag heads.
- **Equivalence on real pages.** The same holds on every tag (32,667) of the 189 HTML fixture and corpus pages.
- **The tests catch the bug.** With the old patterns patched back in, the hostile-timing tests fail.

| input | old | new |
|---|---|---|
| one 50,000-character attribute name | 28.1 s | 1.0 ms |
| 50,000 `:` | 24.8 s | 0.8 ms |
| 50,000-character name, `="`, 50,000 more, no closing quote | 76.6 s | 2.3 ms |
| 200 kB of `<link` / `<html` with no `>` | 3.8 s / 4.1 s | 0.5 ms / 0.3 ms |
| the review's three inputs and the 150 kB name, through all three functions | (above) | worst 2.8 ms |

`seed_demo.py` on a scratch DB (`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false`) prints output
byte-identical to the pre-fix code, apart from the random profile/run ids. Groningen is #1, and
`TestDemoRunIsByteIdentical` passes.

**Proposed patch (as filed).** Both replacements were checked against the old patterns on 20,000 and 50,000 random tags with
zero differences. Each now handles 200 kB in under 25 ms.

```python
# live_discovery.py, replacing l.3594-3596 and the five call sites
_TAG_OPEN = {name: re.compile(rf"<{name}\b", re.IGNORECASE) for name in ("html", "link")}
# Exactly the old _ATTRIBUTE's matches: a name starts only where a run of name
# characters starts (its non-name-start head skipped), so no start inside a run
# re-scans it.
_ATTRIBUTE = re.compile(
    r"""(?<![-\w:.])(?:(?![a-zA-Z_:])[-\w:.])*([a-zA-Z_:][-\w:.]*)\s*=\s*"""
    r"""(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)


def _tags(head: str, name: str, *, first: bool = False) -> list[str]:
    """What re.findall(rf"<{name}\b[^>]*>", head, re.I) returned, in linear time."""
    out: list[str] = []
    pos = 0
    while (found := _TAG_OPEN[name].search(head, pos)) is not None:
        close = head.find(">", found.end())
        if close < 0:
            break  # no ">" left: no later tag can close either
        out.append(head[found.start() : close + 1])
        if first:
            break
        pos = close + 1
    return out

# english_alternate / local_alternate:
#   tags = _tags(head, "html", first=True); tag = tags[0] if tags else None
#   lang = (_attributes(tag).get("lang") or "").strip().lower() if tag else ""
#   for link in _tags(head, "link"): ...
# declared_alternates: for link in _tags(head, "link"): ...
```

Test to add with it: the three functions on `"<html " * 40_000`, `"<link " * 40_000` and
`'<html lang="de"><link ' + "a" * 200_000 + ">"`, each under a second, plus the existing LI-1 and WF-17 tests
unchanged.

### SR2-03 (Medium, mitigated in repo; owner action before registration): a self-hosted runner on a public repository

RP-1 plans to register a self-hosted runner on the owner's computer. `benchmark-capture.yml` lets every job choose
its runner from a free-text input: `runs-on: ${{ inputs.runner || 'ubuntu-latest' }}`. That includes the jobs whose
environment holds the provider keys. The repository is **public**, confirmed through the GitHub API.

A registered runner executes whatever workflow file the dispatched ref contains, so a label does not protect it.

**Scenario.** Anyone who can push a branch and dispatch a workflow can run any command on the owner's machine. That
includes either AI agent, and agents read attacker-controlled pages. They push a branch whose workflow adds a step,
then run `gh workflow run benchmark-capture.yml --ref <branch> -f runner=self-hosted`. A pull request that changes a
`push`/`pull_request` workflow to `runs-on: self-hosted` reaches the same machine, unless the fork-approval setting
stops it. The production `Fetcher` refuses private addresses, but a modified workflow does not have to use it.

The precondition is not met today: no runner is registered. Hence Medium, not High.

**Done in the repository:**

- `backend/tests/test_workflow_runners.py` requires every job that a push, a pull request or a schedule starts to run
  on a GitHub-hosted image, or on a `runner` *choice* whose options are all hosted images (kb-refresh). No workflow
  here can pick the runner up by itself.
- The RP-1 README (item 5) and SECURITY.md "Known residual risks" now say what the owner must do before registering.
  The fork pull request setting must require approval for all outside collaborators. The runner must be `--ephemeral`
  (one job, then it unregisters) and started only for the dispatch, after `gh run list --status queued` shows nothing
  else waiting. It must run as a dedicated user or in a VM with no access to the owner's files, keys or LAN, and it
  must be removed when RP-1 is done.

This finding cannot be closed in code. Only the owner's runner setup closes it.

### SR2-04 (Low, fixed): an LQ-2 phrase could carry a quote the engine folds to `"`

`local_query_phrase` removed `"“”„«»` before quoting the phrase in `site:<d> "<phrase>"`. It did not remove `＂`
(fullwidth), `‟`, `〝〞〟` or `″‶`. The phrase is a link text from the institution's own site. A remaining quote that
the search engine normalises to `"` would close the phrase early and put the rest of the text outside it. Example:
`Informática＂ OR site:other.example ＂x`.

The impact is the scope of one query out of six, with no applicant data. Discovery still keeps only results on the
institution's site, and the rule is off (`LOCAL_QUERY_FROM_PAGE_EVIDENCE = False`). Hence Low.

**Fix:** the class now includes every double-quote form. Single quotes stay, so "Bachelor's" is unchanged. Test:
`test_lq2_no_double_quote_of_any_script_leaves_the_phrase` (13 marks) in `test_local_language_queries.py`.

The rest of LQ-2a checks out:

- The phrase comes only from a page whose `<html lang>` is a language of the institution's country.
- A phrase has at most 8 words and contains no digit, `@`, `http`, `www.` or personal title.
- It passes `_reject_applicant_data`, and so does the whole query text.
- The intent fields `local_phrase` and `native_name` are validated as applicant-free in `__post_init__`.
- `native_name` comes only from the reviewer-signed overlay (`importer.signed_native_names`, `review.decision ==
  "accept"`, 300-character cap). The overlay file does not exist today.

### SR2-05 (Low, fixed): REL-1 served an unchecked URL as "official page"

`kb_build.related_reason` takes `name` and `url` from the expert's related draft. Its `verified` field only records
whether a check passed, and the URL's host is not checked. The run then served the URL in
`"… the closest official route is {name} (official page: {url})"` and as `suggested_contact`. It did so whether or
not the host was an official domain, and whether or not the check passed: Melbourne's route is served with
`verified: false`.

`statement`, the expert note's first sentence, is stored in the KB but never served. The API and the frontend do
not read it. `name` and `url` are rendered as React text (`Ask: {suggested_contact}`), never as a link, so there is
no HTML or `javascript:` path into the UI.

**Fix:** `KnowledgeEntry.related_route` returns the reason only when its URL is http(s) on one of the entry's
`official_domains`. `programme_route` is `related_only` only when there is such a route; otherwise it is `unknown`
and the run asks the blocking "Which official page…" question. A `not_offered` entry keeps its statement but names
no page. All seven committed routes are on official hosts and unchanged; a test pins that. Tests: new cases in
`test_programme_route`, plus `test_a_route_on_a_non_official_host_is_never_called_an_official_page` and
`test_every_committed_related_route_is_on_an_official_page` (`test_knowledge_base.py`).

Not changed, and proposed for the owner: whether a route whose quote failed the check (`verified: false`) should
still be offered.

### SR2-06 (Low, fixed): `NaN` or `Infinity` from a draft could 500 the catalogue

`core_drafts._number` used `float()`, which accepts `"nan"`, `"inf"` and `"1e400"`. A single tuition amount, which
is not checked against the quote the way a range's bounds are, could therefore enter the KB as `NaN` (`json.dumps`
writes it). From there:

- `tuition_value` passed it into the CAT-1 card (`knowledge.tuition.amount`) and into the run's claims.
- Starlette's JSON encoder refuses `NaN`, so every catalogue page listing that university, and its results, would
  answer 500.

The input is reviewed KB data, hence Low.

**Fix:** `_number` returns `None` for a non-finite value. `tuition_value` reads only finite, non-negative figures,
and a range with `low < high`. A fee of 0 stays valid; the committed KB has one. The committed KB is unaffected.
Test: `backend/tests/test_kb_fee_figures.py`.

Range parsing otherwise checks out:

- `tuition_range` keeps a range only when `0 < low < high` and both bounds are printed in the verified quote.
- The runtime does no arithmetic on a fee beyond taking the upper bound.
- A per-credit rate is never multiplied out.

### SR2-07 (Low, fixed): the kb E2E harness would `rm -rf` any `E2E_KB_DIR`

`serve-api.sh` began with `rm -rf "$SCRATCH"`, where `SCRATCH` is the operator's `E2E_KB_DIR`.
`E2E_KB_DIR=backend/data` would delete the developer's database. A typo pointing at a home directory would delete
that. **Fix:** only a directory whose own name starts with `e2e-kb` is accepted (exit 64 before anything is
removed), and the command is `rm -rf --`. Test: `backend/tests/test_e2e_kb_harness.py`, which runs the script on
five refused names, including `..`.

### SR2-08 (Info): what the network guard does and does not fence

`sitecustomize.py` patches `socket.socket.connect`/`connect_ex` and `socket.getaddrinfo` in every Python process
that `serve-api.sh` starts, and the spec fails on any `BLOCKED` line. The fail-closed probe runs before anything
starts. The limits are below. None matters for kb mode today: no search provider is configured, the browser tier
is off and no native HTTP client is installed.

- A host name starting with `127.` (`127.0.0.1.nip.io`) passes `_ok` and is looked up in real DNS. The connect
  that follows is still checked, so only the DNS query leaks.
- UDP `sendto`, native resolvers (c-ares) and native HTTP clients bypass the Python socket API.
- The dead proxy `127.0.0.1:9` is allowed by the guard. A local process listening on port 9 would receive what was
  meant for the proxy.

The guard is not on any production path:

- `frontend/.dockerignore` excludes `e2e/` and, since `a15bf7d4`, `playwright.kb.config.ts`.
- The backend image excludes `data/`, `tests/` and `evaluation/`.
- `PYTHONPATH` is set only inside `serve-api.sh`.
- The scratch directory defaults to the ignored `backend/data/e2e-kb`.

### SR2-09 (Info): the same quadratic tag patterns where nothing reaches them

`site_search.py` (`_FORM`, `_ATTR`, `_SEARCH_INPUT`) has the SR2-01/02 shape: 1.6 s at 120 kB for `_FORM`, and
21 s for `_SEARCH_INPUT` at 140 kB, although the code only applies it to a 2,000-character tail. No module imports
`site_search`; `fusion.py` only names the string. `evaluation/research/index_ceiling.py:541` searches 20 kB, which
is under a second, and it is evaluation only. If either becomes reachable, use the `_tags` helper above.

### SR2-10 (Info): Wikidata item ids go into the next query unvalidated

`native_query` writes `wd:{item}` for ids that `_qid` cut from the previous response's URIs. The endpoint is fixed
and fetched over HTTPS, so only a compromised Wikidata could shape the second query, and the tool is run by hand.
Proposal: keep only `^Q\d+$`. The SR-06 points are in place:

- The owner's exception is recorded in AGENTS.md §6.
- The body is streamed under `MAX_RESPONSE_BYTES`.
- `_literal` escapes CR, LF and `'`.
- Redirects are off, and held-out rows leave before any query is built.

### SR-07 / SR-08 re-read

- **SR-07:** `Fetcher._invalid_url` is unchanged in this range, so the finding stays Info.
- **SR-08:** the catalogue now has 101 templates. I took each template's longest literal separator and repeated it
  300 times. The worst template, `question.programmeNotOffered`, took 18 ms.
- **`_split_reasons`:** it is quadratic in the number of `, ` pieces, but it runs only on the KB-built documents
  question. A 60-reason item took 18 ms. No action.

## Checked and found sound

- **CAT-1 (`GET /api/universities`):**
  - `verified` is a FastAPI `bool`. It filters only in kb mode; live and demo modes return `knowledge`/`kb_total`
    null as before.
  - `profile_id` still goes through `owned_profile`, so another tenant's case answers 404.
  - The `knowledge` block holds only KB facts: coverage counts, verification date, review label, and the first fee
    with its source URL, stale reasons and caveat. It carries no draft note, quote text, `statement` or unknown
    reason.
  - The catalogue renders it as text. `SourceLink` (`isSafeHref`, `rel="noopener noreferrer"`) remains the only
    link renderer for KB URLs.
- **WHY-1 (`kb_unknown`):**
  - Only `{question, kind, checked_on}` is served. `kind` is a `Literal`, and anything outside the vocabulary reads
    `unspecified`.
  - The frontend looks `question` up in a fixed `Record`. A key such as `constructor` maps to no tab, so the row is
    filtered out.
- **`read_pages` (CI-executed lists):**
  - All three committed `read_pages/*.json` lists (182 rows) and every `evidence_check.*.json` that parses as a list
    were checked. All are official for their `seed_id`.
  - No row is a held-out case or on a held-out case's domain. No KB-list row maps a held-out domain to a
    non-held-out seed id.
  - The job holds no secret, and its input arrives through `env`. The path must match `LIST_PATH` in both bash and
    Python, and `resolve_list` refuses anything that resolves outside the data directory.
  - `--robots-override-kb` is accepted only as the exact second word. It re-reads only the official, non-held-out
    URLs that robots.txt refused, once, through the same `kb_evidence_robots_override_urls` path as SR-02's fix.
  - `identity_gate` validates every word of its input, and its `--native-names` path is a fixed pattern.
  - The SR-05 fix (`ad8139b6`) is in place, and `test_no_workflow_expands_an_input_inside_a_run_script` covers all
    three workflows.
- **NS-1b hop reads:**
  - Hop links come from the homepage's `_harvest_links`. They are then filtered with
    `on_institution_site(url, domain)` without `trace.extra_domains`, so no DI-1 admissions domain is used, and with
    `_url_excluded` and the other-level checks.
  - At most `HOMEPAGE_HOP_READ_CAP = 5` links are read. They are read through the run's `Fetcher` (network policy,
    pinned address, every redirect hop re-validated), with no application retry, under the same `_spent()` budget.
  - The rule is off.
- **PDF decrypt:**
  - `open_reader` calls `decrypt("")` only. `NOT_DECRYPTED` returns None and an empty result; no password is
    guessed and no exception or message escapes.
  - Key derivation is constant-cost.
  - `read_pdf` keeps its page and time caps. `extraction.pdf_to_text` keeps its 40-page cap but has no time cap; that
    gap predates this range and is unchanged.
- **New dependencies:**
  - `cryptography==50.0.2` is pinned (installed 50.0.2), and `pip-audit -r backend/requirements.txt` runs in CI.
    Its transitive `cffi`/`pycparser` are unpinned, as all transitive dependencies are here.
  - `PyYAML==6.0.3` and `pytest-xdist==3.8.0` are dev-only. Tests use `yaml.safe_load` only.
- **`kb-refresh.yml`:** the SR-03 fix is in place (`^[a-z_,\ ]*$` before `GITHUB_OUTPUT`). Its `runner` input is a
  choice limited to `ubuntu-latest`.
- **`ci.yml`:**
  - The `e2e:kb` step runs in a job with no secrets.
  - The failure artifact holds the Playwright report and traces (synthetic applicant only) and `netguard.log`
    (process ids, the tail of each command line, blocked hosts). It holds no environment and no keys.
- **`a15bf7d4`:** the change only excludes the kb Playwright config from the web image's build context.
- **SH-1, ES-1 and ES-2 (scholarships):**
  - The sibling-host rule uses the public-suffix-aware `hosts_share_site` and drops mail redirectors. It is off.
  - The off-host counting line names the index URL and a count.
  - `html_lang` and `classifier_signal` are measurement fields that no branch reads. The `page_language` call behind
    them was SR2-01's reach.
- **Secrets / PII:** the added lines were scanned for key, token, private-key, JWT, credentialed-URL and phone/IIN
  shapes. Only synthetic test values, public institutional URLs in the KB and read lists, and
  `UNIMATCH_*_API_KEY: ${{ secrets.… }}` references (unchanged) were found.

## Verification

- Full backend suite, `pytest -q -p no:cacheprovider -o addopts="" -n 4 tests`: **7482 passed**. The baseline before
  this change was 7407 passed; the 75 new tests are the ones named above.
- `ruff check app tests evaluation scripts`, `ruff format --check app tests evaluation` and
  `mypy app tests evaluation` are clean.
- `seed_demo.py` was run against a scratch database because the runner changed. Groningen is #1, UBC is
  `OUT_OF_BUDGET`, and `TestDemoRunIsByteIdentical` passes.
- The frontend sources are untouched. Only `e2e/kb-env/serve-api.sh` changed, and
  `backend/tests/test_e2e_kb_harness.py` exercises it.
