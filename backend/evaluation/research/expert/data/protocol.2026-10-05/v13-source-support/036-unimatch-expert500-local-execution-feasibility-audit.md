# Local execution / repeated workflow startup: source-only audit

Scope: public code and configuration only. No network, provider, Fetcher, model,
credential, label or source-corpus operation was performed. The timings supplied
below are parent-reported existing GH step observations, not a new measurement.

## Why one GH job per action

The frozen V12 parent constructs `actions: [item]` in `prepare_plan()`
(pilot1613–1635), then calls `workflow()` (1644–1665); the next action restores
previous independently hashed raw logs using `resume_run_id`. This is a transport
and provenance choice for interactive navigation, not a stock Fetcher requirement.
The workflow executes the normal controller CLI at benchmark-capture.yml579–594
and uploads original logs even on cancellation/failure at605–611. The frozen
report binds `dispatch.json`, `run.json`, run identity/head/conclusion and all
controller rows (report351–422,523–629). A local transport cannot silently produce
or substitute those GH identities.

## Recorded blocker versus current feasibility

benchmark-capture.yml7–9 describes an older agent container that had only a proxy
while Fetcher connected to checked, pinned IPs. This is an explicit historical
environment limitation. It does not establish that the present desktop's ordinary
network is unusable. The same workflow explicitly permits `self-hosted` at22–25.
No current connectivity or provider configuration was checked here.

There is no GH-only restriction in the inspected stock runtime:

- controller.run994–1024 constructs the stock Fetcher and configured provider and
  delegates to the strict executor; CLI1201–1211 accepts ordinary local file paths.
  Strict reads are cold (`use_cache=False`), robots remain enabled, and configured
  Exa identity must agree with the plan.
- live.capture_one246–295 supports the algorithm's strict budget; local CLI child
  wiring832–860 keeps exact source-time and finalization accounting. The strict
  fetch wrapper422–443 debits each read and disables cached responses.
- Fetcher499–525/854–866/932–951 owns pacing, robots, checked redirects and HTTP.
  network_policy108–144 validates URL/DNS addresses before connecting; the IP pin
  remains in fetching97–108 and554–579. These policies must remain unchanged.
- The public local venv config reports CPython3.12.13/macOS arm64; GH selects
  Python3.12 on ubuntu-latest. Thus identical source/provider policy does not mean
  identical OS/dependencies/site-observable execution environment.

Both fresh arms could use their existing stock local seams prospectively if the
owner verifies ordinary runtime feasibility, binds one declared environment for
both arms, and supplies a local receipt/report contract retaining every dispatch,
real raw hash/counter, immutable900s guard, algorithm120s/119s source deadline,
cold60/6 budgets, and durable shared provider/integrity STOP. The model process
must remain isolated from the repo/credentials/controller runtime. No IP, account,
provider, proxy or policy workaround is proposed.

## Minimal current-transport opportunity

The expert job already caches pip downloads (workflow450–455) but creates a fresh
venv and installs requirements-dev.txt on every action (456–457). The parent
reported original expert37339132790 steps: venv2s, pip16s; baseline37337773502:
venv4s, pip15s. Its reported53–55s total overhead also includes other job and
transport/poll work. Caching the installed venv could target roughly18s of that
expert setup sample; it cannot be claimed to remove the full53–55s.

A narrow prospective cache retains the same one-action job/runner/provider and
all existing restore/audit/STOP mechanics. Cache only the installed environment;
never pages, cold response cache, source outputs, plans, logs, settings or secrets.
Key and verify the exact resolved Python patch/ABI, OS/architecture/runner identity,
requirements hashes and setup/cache format. Do not restore a partially matching
venv or skip validity checks after a corrupt restore. requirements.txt/dev contain
several >= ranges, so an unchanged requirements hash alone does not attest an
identical resolved package set; retain the installed dependency manifest/fingerprint
and disclose it. A venv contains absolute interpreter/script paths and must match
the restore location/runtime.

Environment installation precedes the baseline capture_one active clock, while
expert900s absolute wall time includes dispatched-job setup/transport. Saving
setup adds no budget or reset. Preserve per-action fresh Fetcher/robots/provider
lifetime: a persistent worker sharing those objects would change behavior even
with cold page responses. Ordinary same-runner environment caching preserves the
current transport identities and requires fresh prospective workflow/source hashes,
CI/freeze and existing offline workflow/report provenance gates; no batching or
new STOP contract is necessary.

## Original public bytes inspected

- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/.github/workflows/benchmark-capture.yml` — SHA256 `3be119392da90baed37d4be72bc08878a37d2da29fcb6503049df9911abcff1d`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/evaluation/research/expert/controller.py` — SHA256 `88482a7aaed79080c8c58df9df762cbe8c0bf734fa3c01b43764af7ef20d4fb4`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/evaluation/research/live.py` — SHA256 `f3e67276795e8b338fbd13077b7557de82a087ad164beaa1c157c3dd9faf3326`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/app/adapters/fetching.py` — SHA256 `e197459b5947cabf272617aa730c3c0ed58cdd6952f84091ad50d5384244c895`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/app/adapters/network_policy.py` — SHA256 `221d53b18aac4c11388a589204817a29eb6e0c705f50724bda3b3e10e8c80f8f`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/app/adapters/search/__init__.py` — SHA256 `ce3ae88806c2d45fe5795775b8e3e0d20109f5165f2f6e29003ab09725b37ba6`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/requirements.txt` — SHA256 `4d98978db7324e2a4529fdae5a51130375fb6e5417b2324d42a5b04d69601267`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/requirements-dev.txt` — SHA256 `85814cfe94af7cf668284c455de6354d641b6b82480e3e3c435df507bc887a17`
- `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/.venv/pyvenv.cfg` — SHA256 `3f0e21cf1485027b25c9e4e3057e1767ae231cbf86f54b3e81b93076229b1808`
- `/tmp/unimatch-expert500-journal-pilot-v12.py` — SHA256 `1922e117436afdc001bef7cbf867e8b91db4062fd0b98cfce044c3b980a74b72`
- `/tmp/unimatch-expert500-journal-report-v12.py` — SHA256 `5a36256591fe4b76186a36448c4c6a3d0a8eeab989b427eb4031ebf00405a4fb`
