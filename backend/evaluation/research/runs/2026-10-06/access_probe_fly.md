# Access probe from production (Fly, region ams), 2026-10-06

`scripts/probe_access.py` run on machine 8dd627ae93e508 by the owner's operator.
Production fetcher unchanged: own user agent, robots.txt honoured, no cache, no proxy.

Totals: ok=18, http_error=5, robots_disallowed=4, blocked=5 (32 URLs).

| Case | Result | Cause |
|---|---|---|
| delft, vienna, warsaw, ubc, kaist | all ok | — |
| groningen | 3/4 ok | `fse/.../apply-bsc/language` returns 404: stale gold URL |
| toronto | 1/5 ok | `future.utoronto.ca` returns 403 to production too; only `web.cs.toronto.edu` opens |
| aalto | 0/3 | robots.txt ReadTimeout, so RFC 9309 treats the site as disallowed |
| hku | 0/3 | `admissions.hku.hk` robots ConnectError; `www.admissions.hku.hk` does not resolve (stale host) |
| ntu | 0/3 | `www.ntu.edu.sg` does not resolve from the Fly machine (DNS) |

Decisions taken under delegation ("делай по своим рекомендациям"):
- Toronto and Aalto misses on these pages are ACCESS in production, not benchmark artefacts. No bypass.
  They leave the recall denominator of DoD target 3 until the sites open.
- NTU DNS failure needs a recheck (`nslookup www.ntu.edu.sg` on the machine) before it is called permanent.
- Stale gold URLs (Groningen language page, HKU www host) go to the owner as a gold correction; gold is not edited without a signature.
