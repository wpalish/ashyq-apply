# 5. Extraction is measured against hand-verified truth, frozen first

Date: 2026-08-30
Status: Accepted

## Context

Decision-grade extraction completeness sat at 5.6% against twenty-five
questions, and nothing in the repository could say why. The canary counts the
claims the extractor produced. It cannot count the ones it should have produced,
because nobody had written down what the pages say.

"51 claims, 5.6% complete" is equally consistent with an extractor that is
nearly right and one that is nearly useless. With no denominator, every change
looks like progress if the only measure is how much the machine emitted — and
the fastest way to raise the number is to emit more, which is the opposite of
what an applicant needs. A false deadline is worse than a missing one.

Two findings from the first four audited programmes show what the missing
denominator was hiding. Toronto's canary row read *nine claims, 0.00
completeness*: the facts were being found and thrown away by a domain
comparison. And Groningen's English requirement — a plain HTML table on the
university's own page — was read by nothing at all, because extraction worked
on flattened text where the column headers are gone. Neither was visible in a
completeness average.

## Decision

A person reads the institution's page and records the answer, with the evidence
the product itself demands: the official URL, the excerpt that carries it, when
it was read, how specific the page is, and the claim's status.

**Three verdicts, and the third is what makes the other two mean anything.**

| verdict | meaning | a miss is | a claim is |
|---|---|---|---|
| `answered` | the institution publishes it | a recall failure | correct |
| `absent` | it does not, *checked* rather than assumed | nothing | a precision failure |
| `not_checked` | nobody has audited this pair yet | excluded | excluded |

`absent` is a positive finding and is recorded with the reason. It is a claim
about the **institution**, not about one page: four entries in the first audit
said "no fee on the programme page, the university publishes it elsewhere, not
audited yet" and were recorded as absences. The pipeline read that other page,
found the fee, and the evaluator scored a correct extraction as a false positive
— tuition precision fell to 0.50 entirely because the benchmark was wrong. A
test now rejects any `absent` whose own note admits the audit is unfinished.

`not_checked` is counted in neither numerator nor denominator and reported as
coverage on every run. A benchmark that hides its own gaps produces a number
that looks like a measurement.

**The selection is frozen before the thing it measures is touched.** Ten
institutions × two disciplines, chosen by a written rule rather than by taste,
and carrying a sha256 over the (institution, discipline) pairs. Adding audited
answers is free; changing *which* programmes are in the set fails a test until
it is re-frozen in a visible commit. A benchmark assembled after seeing the
results measures the assembler.

**Gold values are written the way the page states them.** The comparator
flattens produced values to their leaves and compares by token containment, so
a fee recorded as "EUR 2694" matches a claim carrying
`{'amount': 2694.0, 'currency': 'EUR'}`, and a deadline recorded as "January 15"
matches `2027-01-15`. Writing gold truth in the extractor's data structures
would make the benchmark measure agreement with the implementation. "6.5" still
fails against 7.0, which is the comparison that has to stay sharp.

**Missed and unreachable are separated.** For every answer the pipeline does not
produce, the evaluator fetches the page the gold claim cites and asks whether
the extractor can read it there. "The English requirement is missed" and "the
English requirement is on a page we never fetch" need completely different work,
and the first cycle produced one of each.

**The evaluator is given the pipeline's own entry points.** It first handed the
adapters a programme URL and nothing else, while the real pipeline also receives
an admissions, costs and scholarships page from discovery — so it measured
*less* than the pipeline and would have credited it with reach failures it does
not have. `--canary-run DIR` reproduces those entry points from a canary report,
which keeps discovery's output out of the gold truth, where it does not belong.

## Consequences

- Building the set is slow, by nature: it is a person reading pages. Coverage
  starts small and is stated on every run rather than smoothed over.
- The gold set is a maintenance burden — institutions edit their pages, and an
  answer recorded today can be wrong next year. `accessed_at` on every claim is
  what makes that detectable rather than silent.
- It cannot be a test. It needs the network, it is slow, and a drop is a finding
  to investigate rather than a build to fail. `tests/test_gold_dataset.py` tests
  the *dataset* — that every audited answer can be re-checked, that no answer
  comes from an aggregator, that the selection has not moved.
- Precision and recall replace completeness as the number to steer by.
  Completeness stays as the product threshold, because it is what an applicant
  experiences, but it cannot direct engineering work on its own.

## What it found immediately

Against four audited programmes: **precision 1.00, recall 0.46**. The extractor
has not once claimed something a page does not say, across every question where
the institution publishes nothing. It misses about half of what they do say, and
the misses are not scattered — required school subjects is missed on all four,
in three different shapes (a sentence, a list of IB courses, Ontario course
codes).
