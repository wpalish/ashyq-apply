## Summary
- Add auto/exa/exa_mcp/none workflow input; resolve once per job.
- Preserve historic auto secret precedence; explicit exa fails before capture without its key.
- Record the same selected provider in logs, out/config.txt and capture arguments.

## Validation
- YAML parses; identical selector blocks in both jobs.
- 20 offline shell scenarios passed: auto precedence, overrides, missing key and invalid input.
- No actual provider request, secret output, application code change or production setting change.
- Full cloud gates and registration on main remain pending.

## Blocker
Normal push of e40183e to task/benchmark-provider-choice was rejected because the local OAuth authorization lacks workflow scope. No alternate write path attempted. After owner grants scope, push this existing branch, create the PR, review CI, and wait for owner merge before dispatching the 120s/60-read benchmark. Do not select auto/Serper for this task.
