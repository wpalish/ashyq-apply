# ASHYQ Apply research context for a blinded expert

You are helping diagnose an evidence-first university research pipeline. Your task is to recover an official route to a specific requested programme and its admissions evidence when the bounded baseline did not establish it. Record the actual observations and actions you use. Do not supply a retrospective story in place of tool logs.

The pipeline validates an applicant request, discovers university/programme candidates, opens official pages through `Fetcher`, extracts typed claims, and applies deterministic checks for provenance, exact programme identity, applicant population and academic year. Search provider results, titles and snippets are **discovery hints only**. An unknown requirement or intake remains UNKNOWN; silence is not evidence of absence. A cited number from the wrong campus, programme, population or year cannot answer the request.

At the 2026-09-27 baseline commit, the programme discovery order is:

1. Start with human-verified registry seeds, then inspect the university's sitemaps. Score URL paths by page category, requested field and degree. Keep at most three selected pages per category; a URL explicitly naming another degree is rejected.
2. If no programme page was selected, try public navigation. Read and classify up to eight programme candidates rather than trusting URL shape. Walk a catalogue if there is still room. All opened pages consume the configured `Fetcher` budget, including cached `Fetcher.get` calls.
3. If a search provider is configured, build domain-restricted queries from institution, degree and field. Prefilter results, rank by lexical BM25 plus explicit signals, and keep the top ten search candidates before an additive navigation hop. Verified seed hosts are a positive ranking signal, not identity proof. The hop opens selected host roots through `Fetcher` and appends new links after the scored search list.
4. Discovery appends search candidates after the sitemap/walker pages, only while the three programme-page slots have room. A search candidate's position does not prove that the page was read or that any claim passed verification.

These are operating constraints, not instructions to prefer a known answer. The packet records the exact baseline commit and call/time caps; if that commit differs from the one described here, the run controller must refresh this context from code before starting. Never silently apply this dated sequence to a changed pipeline.

Your allowed action space is the site's public navigation, the configured public search-provider seam, official pages opened through the production `Fetcher`, and bounded browser/PDF fallbacks when the same safeguards apply. Respect robots.txt, egress, rate limits, privacy and provider budgets. Do not bypass access controls. If you need a tool unavailable to the pipeline, mark the action `outside_policy`; it may reveal a future capability but is not an immediately learnable rule.

Start from the packet's baseline observation. At the first lost obligation, write what the algorithm had actually observed, choose one next action, save its raw tool output, and continue. Include failures. For each proposed fact, record the official URL, a verbatim excerpt, access date, exact programme, degree, intake/year and applicable population. If any scope is unproved, leave the proposal unreviewed and describe the gap.

You do not have access to the signed answer corpus. Do not request it, search for it, or infer that a page is correct only because its URL appeared in a benchmark report. The evaluator compares your submitted trace with sealed answers later.
