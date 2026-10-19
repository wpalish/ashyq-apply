# Which hosts refuse datacenter IPs but open to the owner's computer — the access ledger by vantage point

Type: research
Status: open
Blocked by: 01-Q4
Map: ../map.md · AFK — one self-hosted `verify_evidence` (07's `--from-kb`) run on the owner's computer, read beside
the GitHub and Fly results. Zero credits; the production fetcher unchanged.

## Question

From GitHub runners, 51 of the KB's 312 evidence URLs answer HTTP 403 (28 hosts, mostly US/UK admissions and
financial-aid hosts: `undergraduate.study.cam.ac.uk` 5, `admission.brown.edu` 4, `sfs.mit.edu`, `finaid.cornell.edu`,
`college.harvard.edu`, `apply.jhu.edu`, `admissions.berkeley.edu` 3 each…) and 21 are robots-refused on 10 hosts
(`www.bu.edu` 6, Northwestern 5, `bulletins.nyu.edu`, `admission.princeton.edu`, `www.cis.upenn.edu` 2 each…). From
Fly (ams) the 2026-10-06 probe opened 18 of 32 cohort gold URLs. Which of the refusals are *about the IP* (a 403 that
turns into a 200 from a person's computer with the same user agent) and which are about *us* (robots.txt names our
agent or all agents; a WAF that blocks on the user agent, which stays 403 at home)? The first class the self-hosted
runner can keep current; the second stays "unavailable" wherever we run.

## Test

1. The 75 refused URLs (+ the 14 Fly refusals) listed with their GitHub outcome; the same list run by 07's
   `verify_evidence --from-kb --only <those cases>` on `runner: self-hosted` (the owner's computer; `FETCH_CONTACT`
   set; no cache). Robots refusals are expected to stay refused — robots.txt is per user agent, and no run anywhere
   changes the agent string or ignores a disallow.
2. Table host × {GitHub, Fly (where probed), home}: `ok` / `403` / `robots` / `timeout`; per KB question the number
   of facts that only the home run can keep verified; per host a one-word class: `ip_block`, `ua_or_waf_block`,
   `robots`, `dead_host`.
3. A note on what the product's own production IP (Fly) sees, from `access_probe_fly.md`, and whether the KB mode
   (which fetches nothing at request time) is the only honest way to serve those universities — it is, until a
   site changes its policy; say so.

## Deliverable

`docs/process/ACCESS_LEDGER_BY_VANTAGE_2026-10-xx.md` with the table and the classes; the `ip_block` hosts become the
self-hosted part of 07's schedule; the rest are recorded as stale-honestly in the KB queue.

## Files the worker holds

The new doc only; the run is 07's workflow with the `runner` input. Read-only: the CI reports, `access_probe_fly.md`,
`scripts/probe_access.py`.

## Evidence

The CI reports' outcome counts (312: 237 ok, 51 403, 13 robots_disallowed, 8 robots_crawl_delay, 1 each unparseable /
too_large / timeout); `runs/2026-10-06/access_probe_fly.md`; `fetching.py` (`USER_AGENT`, `MAX_CRAWL_DELAY_SECONDS` 10).

## Done when

The ledger is committed; 07's schedule names which cases run on which runner; no host was read with any other agent
string or around any refusal.
