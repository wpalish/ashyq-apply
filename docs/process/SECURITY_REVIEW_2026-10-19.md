# Security review — branch `claude/greeting-16wj2z`, commits since 2026-10-19 00:00 UTC

Reviewer: claude-opus-5 (worktree agent). Range: `84b2493d..5de8b6a3` (123 commits, 8be393a2 to
5de8b6a3), covering `backend/app`, `backend/scripts`, `backend/evaluation/research` (where the
search cap, the recorded-search builder and the Wikidata client live), `.github/workflows` and
`frontend/src`. Held-out material, `DISCOVERY_ANALYSIS_2026-10-17.md` and the scratchpad quarantine
directories were not opened. No search provider was called.

## Findings

| ID | Severity | Where | Status |
|----|----------|-------|--------|
| SR-01 | **High** | `backend/app/adapters/fetching.py` `_FractionalCrawlDelayParser.disallows` (was l.791-793) | **Fixed** |
| SR-02 | Medium | `backend/scripts/verify_evidence.py` `robots_override` / `check_with` | **Fixed** |
| SR-03 | Low | `.github/workflows/kb-refresh.yml` "Scope" step | **Fixed** |
| SR-04 | Low | `backend/app/adapters/fetching.py` `trust_env_proxy` (`_pinned_request(pin=False)`, `_send_to_any_address`) | **Fixed** |
| SR-05 | Low | `.github/workflows/benchmark-capture.yml` l.259-270, 747-756, 800-807, 829 | **Fixed** (pre-existing) |
| SR-06 | Low | `backend/evaluation/research/wikidata_domains.py` l.175, 232-256, 620 | **Fixed** (owner exception recorded) |
| SR-07 | Info | `backend/app/adapters/fetching.py` `Fetcher._invalid_url` | Noted |
| SR-08 | Info | `backend/app/domain/message_keys.py` `_compiled` | Noted |

### SR-01 (High, fixed): robots.txt wildcard rule is a ReDoS on the crawler's event loop

The new strict robots check compiled each rule to a regex, `".*".join(re.escape(part) ...)`. robots.txt is
served by the site being read, so it is attacker-controlled (SECURITY.md: "Every university URL is
attacker-controlled"). A rule such as `Disallow: /*a*a*a*a*a*a*a*a*b` becomes `.*a.*a…b`, which backtracks
polynomially in the URL length with the number of stars as the exponent. Measured before the fix: 6 stars on
a 60-character path took 1.2 s; 8 stars did not finish in 60 s. The match runs synchronously inside
`RobotsPolicy.allowed`, i.e. on the asyncio loop, so one hostile robots.txt freezes every case of the worker
(and the API process when a run executes there). It is reachable from the product: every live-mode read and
every source re-scan goes through `RobotsPolicy.allowed` with `respect_robots` on.

**Exploit:** a site in (or redirected to within) a run's discovery serves the robots.txt above. The next read
of any path on that host hangs the process indefinitely.

**Fix:** `robots_rule_matches(path, target)` matches the RFC 9309 glob without a regex: the first segment is a
prefix check, each following segment is found left-most with `str.find`, and a trailing `$` anchors the last
segment at the end. That is exact for `*`-only globs and linear in the number of segments. Tests:
`backend/tests/test_robots_wildcards.py` (RFC cases, 4,000 random rules against the old regex reading, and a
40-star rule on a 5,000-character path answered in under a second). The strict-direction semantics
(longest match, tie to Disallow) are unchanged.

### SR-02 (Medium, fixed): the KB robots override could read a non-official host

The owner's exception (AGENTS.md §6) covers "the specific KB evidence URLs". `robots_override` built the
fetcher's override set from every `robots_disallowed` row of the report that matches a draft row, official or
not, and `check_with` read the URL before looking at `official`. A draft or report row naming a non-official
host (an expert mistake, or an edited JSON file in a batch directory) would be read past its robots.txt, which
KB evidence can never be: the KB only cites official domains.

**Fix:** the override set is now only the official URLs among the targets (`is_official` against the draft's
case and seed id), and `check_with(..., official_only=True)` skips reading a non-official URL with a note.
Test: `test_robots_override_kb_never_reads_a_non_official_host` in `backend/tests/test_verify_evidence.py`.

The rest of the override checks out: the set is exact-match on each hop (`_redirect_policy`), every hop is
still network-policy checked and same-site checked, a redirect to an unlisted URL meets robots.txt again, the
URL gets one attempt, `Crawl-delay` is still honoured, and nothing under `backend/app` passes the argument
(the runner and the source scanner construct `Fetcher` without it).

### SR-03 (Low, fixed): `only` input could write extra lines into `GITHUB_OUTPUT`

`kb-refresh.yml` wrote `echo "only=$only" >> "$GITHUB_OUTPUT"` from a free-text `workflow_dispatch` input. An
input containing a newline (possible through the API) adds arbitrary step outputs, e.g. overriding `day`,
which names the queue file. Needs repository write access, hence Low. **Fix:** the step refuses anything but
`[a-z_, ]` before writing the output.

### SR-04 (Low, proposed): proxy mode gives up address pinning

With `Fetcher(trust_env_proxy=True)` the request is addressed by host name and the proxy resolves it again.
The network policy still resolves and checks the name locally first, but the address the proxy connects to is
not the address that was checked, so a DNS-rebinding host could make the proxy connect to an address the
policy would refuse (the proxy's own network). Reachability: only evaluation tooling (`verify_evidence.py
--trust-env-proxy`, `evaluation.research.live --trust-env-proxy`, `index_ceiling`); nothing under `app/`
sets it, and it reads only `HTTPS_PROXY` plus a CA bundle, with TLS verification forced on and
`trust_env=False`. **Proposal:** (a) make `ProxySettings.from_env` refuse when
`UNIMATCH_ENVIRONMENT=production`, so no deployment can turn it on through a code path added later;
(b) add one line to SECURITY.md "Known residual risks" that proxy mode trusts the proxy's resolver.

### SR-05 (Low, proposed, pre-existing): workflow inputs interpolated straight into shell

`benchmark-capture.yml` still expands `${{ inputs.case }}`, `${{ inputs.extra_args }}`,
`${{ inputs.base_args }}`, `${{ inputs.max_pages }}`, `${{ inputs.seconds_per_case }}` and
`${{ inputs.case_parallelism }}` inside `run:` scripts of jobs whose `env` holds the provider keys
(l.117-123, 538-541). A dispatcher can therefore run arbitrary shell with those secrets in the environment.
Only users with write access can dispatch, and they could edit the workflow anyway, so this is defence in
depth. The steps added in this range already do it right (the cap step, the recorded-store step and the
v2-store step pass inputs through `env:`, and `run_tag` is validated against `^[A-Za-z0-9_.-]+$`).
**Proposal:** move the remaining expansions into `env:` (`CASES`, `EXTRA_ARGS`, `BASE_ARGS`, ...), split
the flag strings with `read -r -a` like the recorded-store step, and validate `max_pages`, `seconds_per_case`
and `case_parallelism` with `^[0-9]+$`.

GitHub Actions note for the recorded path: the provider keys are blanked by writing `KEY=` to `GITHUB_ENV`.
That overrides job-level `env` for later steps, but a step-level `env:` naming a key would win; none does
today. The Python side does not depend on it: `search_provider=recorded` never reads a key and has no fallback
(`app/adapters/search/__init__.py`, `recorded.py`), and `Settings.validate_runtime` refuses `recorded` in
production and without a store file.

### SR-06 (Low, proposed): the Wikidata client is a network path outside `Fetcher`

`wikidata_domains.py` posts SPARQL to `https://query.wikidata.org/sparql` with its own `httpx.Client`. AGENTS.md
§6 says "no network outside [Fetcher] ... No other network path is exempt", and the only standing exceptions
are the search-provider seam and the KB robots override. The call itself is benign: fixed endpoint, no
redirects followed, no applicant data (catalogue names and countries only), held-out rows skipped before any
query is built, run by hand from evaluation tooling, nothing under `app/` imports it. Two small gaps:
the response body is not size-capped (`response.json()` on whatever arrives), and `_literal` escapes `\` and
`"` but not CR/LF, so a catalogue name with a newline yields an invalid query (an error, not an injection,
since the name never leaves a string literal otherwise). **Proposal:** record an owner exception for this tool
in AGENTS.md §6 (or route it through `check_url` plus a capped streamed read), escape `\n`/`\r` in `_literal`,
and cap the body. The P856 domains it writes are proposals: Wikidata is publicly editable, so a reviewer must
keep confirming them row by row before any reaches `official_domain`.

### SR-07 (Info): malformed-URL log line skips the PII guard

`Fetcher.get` now returns `UNPARSEABLE` before `find_pii` runs, and logs `invalid_url_reason`, which can echo
part of the URL from httpx's message (capped at 200 characters). These URLs come from page content, which
never carries applicant data (applicant fields are never added to URLs), so nothing leaks today. If URL
provenance ever widens, log only the reason class, not the message.

### SR-08 (Info): message-key templates are regex matched on served text

`annotate_result` full-matches 83 templates with lazy `.+?` groups against sentences that embed crawled names.
Measured on 300 repetitions of each template's separators: worst 14 ms (`question.satForAward`). No action;
if the templates grow multi-placeholder runs with repeated separators, cap the input length.

## Checked and found sound

- **Fetcher redirects / malformed URLs:** a `Location` that cannot be joined or requested ends the read as
  `HTTP_ERROR`; `page_link` drops unrequestable links; `strip_invisible_host` only removes `Cf` characters from
  the authority, and the cleaned URL still meets the network policy, the PII guard and the same-site rule.
- **Recorded search:** no HTTP client in the module, no inner provider, a miss is an empty answer; production
  refuses it at startup. The workflow selects it for both arms and blanks the keys.
- **Query cap / ledger:** `fcntl.flock` on a sidecar lock, atomic `replace` of the state file, malformed or
  mismatched ledgers refuse to open, the (N+1)th query is refused before the provider is asked. `--search-ledger`
  is an operator CLI path (the workflow passes `$PWD/out/search_ledger.json`), not user input.
- **KB loader:** `UNIMATCH_KNOWLEDGE_BASE_PATH` / `UNIMATCH_KNOWLEDGE_IMPORTED_PATH` are deployment settings
  only; no API field reaches them. KB mode builds the fetcher `offline` and the browser tier off.
- **New API fields:** `MessageRef` keys and params are attached on serve only, after the tenancy-checked
  queries (`owned_run`), and never stored. The frontend renders them as React text (no `dangerouslySetInnerHTML`
  anywhere in `frontend/src`), dictionary lookups are prefixed (`msg.`, `cost.`, `status.`) so no prototype key
  is reachable, and `SourceLink` still renders only `http(s)` as a link, with `rel="noopener noreferrer"`.
- **Secrets / PII:** added lines scanned for key, token, private-key, JWT, credentialed-proxy and phone/IIN
  shapes. Only synthetic test secrets (`SECRET = "synth…"`), `example.*` addresses and public institutional
  contact addresses and phone numbers inside saved university pages under `backend/tests/fixtures/` were found. Serper's error
  body excerpt masks the key before truncation and stays out of `str(exc)`.
