# ASHYQ Apply research context for a blinded expert

You are helping diagnose an evidence-first university research pipeline. Your task is to recover an official route to a specific requested programme and its admissions evidence when the bounded baseline did not establish it. Record the actual observations and actions you use. Do not supply a retrospective story in place of tool logs.

The pipeline validates an applicant request, discovers university/programme candidates, opens official pages through `Fetcher`, extracts typed claims, and applies deterministic checks for provenance, exact programme identity, applicant population and academic year. Search provider results, titles and snippets are **discovery hints only**. An unknown requirement or intake remains UNKNOWN; silence is not evidence of absence. A cited number from the wrong campus, programme, population or year cannot answer the request.

This context was refreshed from the production app tree on `main@b672349`
on 2026-10-04. The run packet still names its precise app and evaluation
revisions; a different app tree requires a fresh code check. The public
catalogue contains 501 identities (500 imported seed identities plus one
additional curated institution). Catalogue hints are not admission evidence.

The programme discovery order in that app tree is:

1. Start with human-verified registry seeds, then inspect the university's sitemaps. Score URL paths by page category, requested field and degree. Keep at most three selected pages per category; a URL explicitly naming another degree is rejected.
2. If no programme page was selected, try public navigation. Read and classify up to eight programme candidates rather than trusting URL shape. Walk a catalogue if there is still room. Sitemap discovery stops after at most twelve documents/attempts and exits on oversized responses.
3. If a search provider is configured, build domain-restricted queries from institution, degree and field. Prefilter results, rank by lexical BM25 plus explicit signals, and keep the top ten search candidates before an additive navigation hop. Verified seed hosts are a positive ranking signal, not identity proof. The hop opens selected host roots through `Fetcher` and appends new links after the scored search list.
4. Discovery appends search candidates after the sitemap/walker pages, only while the three programme-page slots have room. `RECOVER_SEARCH_CANDIDATES` defaults on and checks search identities with bounded backfill. The older prune-only `CONFIRM_SEARCH_PROGRAMMES` switch defaults off. `SEARCH_BEFORE_NAVIGATION` also defaults off. A search candidate's position does not prove that the page was read or that any claim passed verification.

The six production `CORE_QUESTIONS` cover an English overall minimum, minimum
GPA, admission deadline, applicant cost, scholarship existence, and scholarship
international/citizenship eligibility. This audit also records Q0 exact
programme existence. Q2 asks broader secondary-qualification questions than
the production minimum-GPA completeness group; keep these measures separate.

The public audit applicant is from Kazakhstan, seeks a bachelor programme in
Computer Science for fall 2027, and has a KZ national secondary qualification.
No private applicant name, email, scores or documents are supplied. Neither
the applicant's nationality nor the requested year proves a page's published
scope. Preserve unknown programme, population, qualification and academic year.

## Budget and comparison mode

Strict expert runs have at most 60 cold `Fetcher.get` calls, six total Exa or
Exa MCP search attempts, and 120 seconds of active case time including model
selection. Robots/redirect checks and transport requests remain the production
Fetcher's responsibility; one get can issue multiple HTTP requests. The old
benchmark counts cache hits differently and is not an equal-budget comparator.
Use the opt-in strict evaluation harness, record its revision independently
of the unchanged production app revision, and stop the batch after provider429.

A catalogue packet's `independent_full_budget` mode gives the expert its own
fresh bounded run from public observations. It is an independent comparison,
not proof that recovery can fit into time already spent by the baseline. A
`baseline_intervention` must carry forward all previous reads, queries and
elapsed time. Never relabel or reset those counters on resume.

These are operating constraints, not instructions to prefer a known answer. The packet records the exact baseline commit and call/time caps; if that commit differs from the one described here, the run controller must refresh this context from code before starting. Never silently apply this dated sequence to a changed pipeline.

Your allowed action space is the site's public navigation, the configured public search-provider seam, official pages opened through the production `Fetcher`, and bounded browser/PDF fallbacks when the same safeguards apply. Respect robots.txt, egress, rate limits, privacy and provider budgets. Do not bypass access controls. If you need a tool unavailable to the pipeline, mark the action `outside_policy`; it may reveal a future capability but is not an immediately learnable rule.

Start from the packet's public baseline observation. Choose one next action,
save its controller-captured raw output, and continue within the packet's
comparison mode. Include failures. Record Q0-Q6 as found, not_published,
inaccessible or unresolved. Not finding an answer is unresolved; not_published
requires explicit official evidence of absence. Each found fact needs the
official URL, exact saved-source excerpt and block/heading/table or PDF page,
access date, programme, degree, intake/year and population. Proposals remain
unreviewed; structural validation does not replace semantic adjudication.
Miss causes are assigned by a separate evaluator only after submission, from
the same-day algorithm capture and observable logs. Do not guess its diagnosis.

You do not have access to the signed answer corpus. Do not request it, search for it, or infer that a page is correct only because its URL appeared in a benchmark report. The evaluator compares your submitted trace with sealed answers later.
