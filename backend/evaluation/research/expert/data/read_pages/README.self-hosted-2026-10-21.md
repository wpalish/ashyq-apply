# Read list for the owner's computer: `self-hosted-2026-10-21.json` (RP-1)

This list covers the knowledge-base cells that neither the agent container nor the GitHub runner can read. The
ticket is RP-1 in `docs/process/NEXT_CYCLES_2026-10-21.md`.

The list has **105 rows on 28 universities**. Each row is one target page. All rows are on official domains, and none
is for a held-out case. `read_pages.parse_rows`, `read_pages.is_official` and `read_pages.heldout` accept every row, and
`tests/test_read_pages.py::test_the_committed_list_resolves_and_parses` checks the list.

## What is in it

1. **The access-class unknown cells: 63 cells on 21 universities.** These are the cells of
   `app/knowledge/kb_cs_bachelor.json` with `unknown[].kind == "access"`. The ticket text says 57 cells on 22
   universities. The committed KB has 63 cells on 21 universities, and that is what this list covers. Each cell has
   at least one row, except Adelaide's `deadline` (see the note at the end of this section).
2. **The 25 "blocked from this vantage point" rows of `docs/process/KB_REFRESH_2026-10-19.md`.** They point to 15
   distinct URLs (ANU, FU Berlin, KAIST ×2, KU Leuven ×2, NTU Taiwan, SNU ×3, HKU ×2, UTokyo, Chicago, Zhejiang).
3. **The two access programme pages.**
   - UCL: `…/courses/computer-science-bsc`, plus the `-2026` degree page.
   - Alberta: the `calendar.ualberta.ca` programme entry, plus the `www.ualberta.ca` BSc page.
4. **The "quote failed CI" cells, where the host is blocked.** Only Monash's three `english` cells qualify (the English
   page is listed). Birmingham's `tuition` is on the course page that is listed for `gpa`. The other unverified quotes
   (MIT, CMU, BU and others) are on readable hosts and need a re-quote, not a new vantage point.

**Not listed: Adelaide (`qs2027-079`) `deadline`.** Its answer page is on `ask.adelaideuni.edu.au`, and that host's
robots.txt disallows our user agent. A robots refusal is final from every vantage point.

Each row has the fields `seed_id`, `url` and `topic` (the question it mainly answers: `programme`, `english`, `gpa`,
`deadline`, `tuition` or `scholarship`). It also has `cells`, the KB cells it should answer, and `source`, where the
URL was recorded. `read_pages.py` ignores the extra fields.

| source | rows |
|---|---|
| `blocked-2026-10-20` (the earlier list; round 8's CI run read it and these rows failed) | 45 |
| `draft` (the `kb_drafts.2026-10-19` notes or the KB unknown reason name the page) | 24 |
| `web-search-2026-10-21` (search result URLs, used to fill gaps; not opened) | 19 |
| `kb-refresh-2026-10-19` (the refresh queue) | 15 |
| `kb-programme` (the KB entry's programme reason) | 2 |

| topic | rows |
|---|---|
| english | 23 |
| deadline | 19 |
| scholarship | 18 |
| tuition | 17 |
| gpa | 16 |
| programme | 12 |

## Rows and expected yield per university

The yield is the best case: it assumes the owner's connection gets past the block. There are three outcomes:

- **fact**: the page states the value.
- **not published**: the page settles the cell as `not_published`. Most `gpa` cells are like this, because the
  pages give A-level/IB or country-specific offers but no GPA minimum.
- **still unknown**: the block does not depend on where the request comes from.

| university | seed_id | rows | access cells | expected: fact / not published / still unknown | why it was blocked |
|---|---|---|---|---|---|
| Oxford | qs2027-004 | 5 | 4 | 3 / 1 (gpa) / 0 | Cloudflare challenge, 403 |
| UCL | qs2027-009 | 8 | 5 + programme | 4 / 1 (gpa) / 0; programme page: fact | Cloudflare 403 (runner too) |
| NUS | qs2027-010 | 3 | 1 | 1 / 0 / 0 | Incapsula empty body |
| HKU | qs2027-011 | 7 | 3 (+2 refresh) | 2 / 1 (gpa) / 0 | container: TLS chain incomplete; runner: robots.txt ConnectError |
| CUHK | qs2027-018 | 4 | 3 | 3 / 0 / 0 | same as HKU (`admission.cuhk.edu.hk`) |
| Melbourne | qs2027-023 | 8 | 5 | 4 / 1 (gpa) / 0 | Cloudflare/Incapsula 403 (runner too) |
| Monash | qs2027-031 | 7 | 4 (+3 quote) | 3 / 1 (gpa) / 0; English re-quoted | Cloudflare 403 (runner too) |
| Edinburgh | qs2027-035 | 1 | 1 | 0 / 0 / 1 | fee table rendered client-side |
| King's College London | qs2027-037 | 2 | 1 | 0 / 0 / 1 | fee block rendered client-side |
| Queensland | qs2027-041 | 1 | 1 | 0 / 0 / 1 | interactive entry-score selector |
| Columbia | qs2027-043 | 3 | 3 | 2 / 1 (gpa) / 0 | CloudFront 403 (runner too) |
| Michigan | qs2027-051 | 5 | 5 | 4 / 1 (gpa) / 0 | Cloudflare 403 (runner too) |
| CityUHK | qs2027-052 | 7 | 4 | 3 / 1 (gpa) / 0 | Incapsula empty body |
| NYU | qs2027-058 | 5 | 4 | 3 / 1 (gpa) / 0 | 403 (container), 405 (runner) |
| KAIST | qs2027-065 | 4 | 3 (+3 refresh) | 2 / 1 (gpa) / 0 | same as HKU (`admission.kaist.ac.kr`) |
| Birmingham | qs2027-069 | 1 | 1 | 0 / 0 / 1 | country selector rendered client-side |
| Adelaide | qs2027-079 | 0 | 1 | 0 / 0 / 1 | robots.txt disallow (final) |
| Durham | qs2027-085 | 7 | 5 | 4 / 1 (gpa) / 0 | CloudFront 403 (runner too) |
| Penn State | qs2027-092 | 4 | 1 | 1 / 0 / 0 | `tuition.psu.edu` 403 |
| Osaka | qs2027-095 | 2 | 3 | 0 / 0 / 3 | guideline PDF over the 5 MB fetch cap; the other PDF's text layer is garbled |
| Alberta | qs2027-096 | 10 | 5 + programme | 5 / 0 / 0; programme page: fact | CloudFront 403 (runner too); the calendar host asks for a 120 s Crawl-delay, which is over the 30 s the script waits, so those 3 rows stay `crawl_delay` from anywhere |
| refresh-only: ANU, FU Berlin, KU Leuven, NTU Taiwan, SNU, UTokyo, Chicago, Zhejiang | | 11 | (21 refresh rows) | re-verified or `quote_gone` | robots unreachable, timeout, HTTP 405 |

**Best-case total for the 63 access cells: 44 fact, 11 not published, 8 still unknown.**

The real yield depends on how each block reacts to a residential IP:

- **Blocks keyed on the IP's reputation** (CloudFront "Request blocked", most Cloudflare/Incapsula walls) should pass
  from the owner's computer.
- **A JavaScript challenge** that requires a browser will not pass from any IP.
- **The three hosts with an incomplete TLS chain** (`admission(s).*` at HKU, CUHK and KAIST) will fail on any vantage
  point if the cause really is the chain, because `httpx` does not fetch missing intermediates. The runner reported
  `ConnectError` on their robots.txt, so the cause is not settled.

The first run answers these questions per host, in `index.tsv`.

## How to run it on the owner's computer

`benchmark-capture.yml` already takes a `runner` input: `runs-on: ${{ inputs.runner || 'ubuntu-latest' }}`. The
`read_pages` job uses it too, so no workflow change is needed:

```bash
gh workflow run benchmark-capture.yml --ref claude/greeting-16wj2z \
    -f mode=read_pages -f runner=self-hosted \
    -f extra_args=evaluation/research/expert/data/read_pages/self-hosted-2026-10-21.json
```

What the owner needs before the run:

1. **A registered self-hosted runner that shows Idle.** Register it in the repository settings: Actions → Runners → New
   self-hosted runner. It must run on Linux or macOS, or Linux under WSL (HANDOFF names the planned label
   `ashyq-home`). Native Windows will not work, because the job's steps are bash and call `.venv/bin/python`.
   `runner=self-hosted` matches any self-hosted runner; pass a custom label (`-f runner=ashyq-home`) to pin one
   machine.
2. **Python 3.12 for `actions/setup-python`.** On a self-hosted runner it is downloaded into the runner's tool cache on
   the first run, so the machine needs internet access to GitHub and PyPI.
3. **The owner's decision on 01-Q4.** The sites see the owner's home IP. Every read is still the production
   `Fetcher`: our user agent, robots.txt honoured, Crawl-delay waited out up to 30 s, one request per URL, no cache.
4. **The ref to dispatch must contain this list.** Push the branch first.
5. **No fork pull requests on the self-hosted runner.** The workflow is `workflow_dispatch` only, but keep the
   repository setting that requires approval for fork pull requests.

`--robots-override-kb` (the owner's KB exception, AGENTS.md §6) may be appended to `extra_args`. It only re-reads URLs
whose robots.txt refused them, which on this list are the robots-unreachable hosts. Leave it off on the first run, so
that `index.tsv` shows which refusals come from robots.txt and which come from the network.

## After the run

1. Download the artifact `read-pages-<run id>` and draft from `pages.jsonl` as round 8 did
   (`kb_drafts.2026-10-19/topup_round8/README.md`).
2. Run the evidence check for the new drafts **on the same runner**: `mode=verify_evidence -f runner=self-hosted`.
   The GitHub runner cannot read these hosts, so a check from it would report every new quote as unreachable.
3. Re-stamp the refresh rows with `kb_build --refresh` against that report.
