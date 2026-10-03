## Task
Owner task1: explicit benchmark search-provider selection. Agent: gpt-6-astra.

## What changed
- Workflow input auto/exa/exa_mcp/none; selection happens once per job.
- Historic auto precedence retained. Explicit exa without its key fails before capture.
- Logs, out/config.txt and all capture commands use the same selected provider.
- Application code, golden demo, production configuration and reference facts unchanged.

## Acceptance
- [x] YAML parses; both jobs use identical selection logic.
- [x] 20 offline selector scenarios pass, including missing-key/invalid-input failures; no secret output.
- [x] Normal push succeeded after owner refreshed workflow scope.
- [x] All8 exact-head CI checks passed on e40183efc50a581fa804c34c78bdd5b784f38992.
- [ ] Owner merges PR; workflow_dispatch input registers on main.
- [ ] Main benchmark120s/60reads with explicit exa; evidence recorded separately from PR41's300s diagnostics.

## Verification
Push run37107912115 and PR run37107916481:4/4 success each.
Push run logs: backend2873 passed on SQLite and PostgreSQL; SQLite coverage94.87% (floor92).
Ruff check/format and mypy324 passed. Frontend232 passed, typecheck/lint/build passed.
Browser79 passed plus6 auth tests. Security audit and containers passed.

## Contract
Manual workflow_dispatch adds search_provider choice; auto remains default. No application/API/migration change.

## Next step / limitations
Await owner squash merge under the explicit handoff instruction. UNIMATCH_EXA_API_KEY secret NAME exists; value not read and provider health not yet measured. Do not run auto/Serper for this task. After merge dispatch benchmark on main with explicit exa,120s/60reads. Do not infer complete search from these CI results. PR41 remains a separate draft and is not deployed by this workflow-only change.
