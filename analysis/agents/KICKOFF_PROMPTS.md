# Kickoff prompts — paste as the first message of every session

Same text for both agents except the name. Keep it short: the rules live in `AGENTS.md`, the state lives in
`docs/process/HANDOFF.md`; the prompt only forces the agent to read them and report before acting.

---

## A. Standard start (repo already has AGENTS.md / HANDOFF.md)

```
You are <Claude Code | Codex>, one of two AI engineers on this repository. You work in relay with the other
one, never simultaneously; the previous session may have been cut off at any point. Your commit trailer is
`Agent: <claude-opus-5 | gpt-6-astra>`.

Do, in this order, and do not write code until step 4 is done:
1. `git fetch --all --prune` and run `python scripts/handoff_check.py`; paste its output.
2. Read AGENTS.md and docs/process/HANDOFF.md in full. Read analysis/AI_TASK_BRIEF.md §6 for the current task.
3. Reconcile the tree with HANDOFF §1–§5. List every discrepancy (uncommitted files, wip HEAD, red gates,
   steps already done). If HANDOFF §2 is `ready-for-review` by the other agent, review that work first.
4. Take the baton: update HANDOFF §1 and §11, commit `handoff: <you> takes the baton at [<task>]`, push.
5. Report to me in ≤ 10 lines: where the previous session stopped, your exact next sub-step, the files you
   will touch. Then proceed by AGENTS.md §2 (write-ahead in HANDOFF §5, commits ≤ 45 min, push after each).

Do not re-open decisions D1–D12. If something contradicts the brief, write it into HANDOFF §7 and ask me.
```

## B. First session ever (bootstrapping the workflow — whichever agent has tokens)

```
You are <Claude Code | Codex>. Before any feature work, install the relay workflow for two AI engineers:
1. Verify these files exist (I unpacked them): AGENTS.md and CLAUDE.md at the repo root,
   docs/process/HANDOFF.md, scripts/handoff_check.py, .github/PULL_REQUEST_TEMPLATE.md, and analysis/ with
   AI_TASK_BRIEF.md, SPEC_matching_v2.md, reference/ranking_v2.py. If any is missing, copy it from
   analysis/agents/ (templates) and tell me.
2. Run `python scripts/handoff_check.py` and paste the output.
3. Run the gates from AGENTS.md §5 on clean main and write the real numbers into HANDOFF §6.
4. Commit "docs: relay workflow for the two ai engineers, with a handoff file and a check script" with the
   trailer `Agent: <you>` and push to main (this one time main is allowed).
5. Then follow prompt A from step 4 onward, starting task [0.1] on branch task/0.1-profile-priorities.
```

## C. Recovery start (you know the previous session died mid-work)

```
The previous session (<other agent>) was cut off while working on [<task>]. Assume HANDOFF.md is behind
reality. Do prompt A steps 1–3, but additionally:
- `git diff` and `git diff --cached` every uncommitted file and decide: finished code, half-finished code,
  or junk. Record the verdict per file in HANDOFF §4.
- Run the full gates and paste counts.
- If the uncommitted work is coherent, commit it as `wip: [<task>] <what it is> (recovered from cut-off)`.
  If it is not, stash it with a message (`git stash push -m "cutoff-<task>-<date>"`) and note that in §4.
Only then take the baton and continue from the reconciled §5.
```

## D. Asking for a review (the relay is the review)

```
HANDOFF §2 says [<task>] is ready-for-review by <other agent>. Review it before anything else:
- read the PR body and compare the pasted gate output with what you get when you run the gates yourself;
- check the invariants list in .github/PULL_REQUEST_TEMPLATE.md, and numbers against
  analysis/reference/ranking_v2.py where applicable;
- write findings as PR comments (quote the line, state the invariant, propose the fix) and summarise in
  HANDOFF §7. Fix trivial issues yourself in commits marked `fix: review — …`; anything non-trivial → ask me.
```
