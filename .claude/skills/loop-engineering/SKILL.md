---
name: loop-engineering
description: Run iterative build-test-critique-fix cycles on a working system until it meets an explicit Definition of Done. Use when building an MVP end to end, hardening a system against known failure modes, or whenever tempted to declare something finished because it compiled.
---

# Loop engineering

Build in vertical slices, run each one for real, and fix the root cause of what
you find. The discipline is not the cycle — it is refusing to declare done on
evidence you have not gathered.

## The cycle

**1. Plan.** Choose one vertical slice with a checkable outcome. Not "the
backend" — "a research run produces results with sources attached".

**2. Build.** Finish it. No `TODO` in a path the slice depends on.

**3. Run.** Actually execute it. Lint, typecheck, unit and integration tests.
A compiling program is not a running one.

**4. Inspect.** Drive the UI. Screenshot the main states. Check the console, the
network, and the layout at every breakpoint you claim to support. Read the
output — do not skim it. The bug is usually visible in the numbers.

**5. Simulate.** Run the failure cases deliberately, not just the happy path.
Enumerate them up front; each one deserves a test.

**6. Critique.** Score the result against what the product *claims about
itself*, dimension by dimension, and name the weakest link.

**7. Fix.** Find the root cause. Do not change the expected value to make a
test pass — if a test fails, decide whether the code or the test is wrong, and
say which.

**8. Repeat** until the Definition of Done is met.

## Simulating failure

For any research or data product, the cases worth seeding:

- the subject qualifies cleanly
- a requirement is *nearly* met (the boundary, not the middle)
- a rule excludes the subject for a reason the marketing does not mention
- the source's own wording overstates what it provides
- two authoritative sources disagree
- the data is expired
- the data describes a different period than it appears to
- data is simply missing
- the source is unreachable
- the user rejects the result

Build a fixture corpus where each case is deliberately present. A demo where
everything works proves nothing.

## Reading test failures

A failing test is one of three things, and it is worth naming which:

1. **A product bug** — fix the code.
2. **A wrong assertion** — fix the test, and say so plainly.
3. **A design inconsistency the test exposed** — the most valuable kind. A
   screen that promised lead-time ordering and delivered fixed grouping is a
   defect in the product, not in the test that noticed.

Never take the third for the second.

## Running against reality

A system verified only against its own fixtures is verified against its own
assumptions. Run it once against the real world, early. Expect it to reveal
things fixtures cannot: mis-joined relative URLs, guards that false-positive on
ordinary data, heuristics that follow navigation furniture, metrics that report
100% when nothing substantive was verified.

Every one of those is invisible to a corpus you wrote yourself.

## Reporting

Keep a loop report. For each cycle record: what was built, what was run, the
defects found **with their root cause**, what was fixed, and what remains.

Distinguish "a wrong answer" from "a missing answer". A system that reports what
it could not determine is in a different category from one that guesses.

## Definition of done

Write it before starting, and check it literally. Typical bar:

- the application starts from the README's instructions alone
- the pipeline works end to end
- real adapters exist, not only mocks
- a demo mode runs with no external credentials
- results carry sources and verification dates
- unknowns are reported as unknown
- contradictions are shown to the user
- lint, typecheck, unit, integration and E2E all pass
- no critical console errors; the main screens are responsive
- documentation covers setup, architecture and limitations
- no open high-severity defects

"It compiled" is not on that list.
