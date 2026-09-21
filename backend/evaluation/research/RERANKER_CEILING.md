# No reranker can help yet, and here is the proof

> **SUPERSEDED FOR THE NEW RETRIEVAL PATH, 2026-09-21.** Everything below is
> still true of the frozen capture and of the pipeline as it stands. It is no
> longer true of Phase 1's retrieval path: with a web-search generator the
> correct page reaches the candidate set in **9/10** cases and the current
> ranking puts it first in **2**, so a reranker now has **seven** cases of
> headroom where it had none. See [SEARCH_PROBE.md](SEARCH_PROBE.md). The
> conclusion here was right for the evidence it had, and the evidence changed.


Measured 2026-09-21 by claude-opus-5 against the certified corpus
`ground_truth.reviewed.json` (`2026-09-21.reviewed`, signed by Диас) and the
frozen `baseline/capture.json`. Reproduce with:

```sh
# From backend
python -m evaluation.research.ceiling --dataset evaluation/research/data/ground_truth.reviewed.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/ceiling.reviewed.json
```

| | |
|---|---|
| Cases scored | 10 |
| **Reranking ceiling** — cases where a correct page is anywhere in the candidate set | **1/10** |
| Cases the current ranking already puts first | 1 |
| **Headroom for any reranker** | **0** |
| Cases that retrieved no candidates at all | 3 |

## What this means

V2-14 asks for a comparison of rerankers: the current scorer against a
cross-encoder, against an optional Jev or LLM. That comparison cannot be run
usefully, because **there is nothing for a reranker to win.**

A reranker reorders the set retrieval produced. In this capture the correct
programme page is present in that set for exactly one case, NTU, and the
current ranking already has it at position 1. For the other nine the page is
absent, so no ordering function reaches it — not BM25, not a cross-encoder, not
Jev, not the most expensive model available.

**The 1/10 programme-page recall is entirely a retrieval failure.** The ranking
is already perfect on what it is given. Any money or latency spent on a
reranker today buys a measurable zero.

## Per case

| Case | Candidates retrieved | Correct page in the set |
|---|---|---|
| groningen | 4 | no |
| delft | 3 | no |
| aalto | 40 | no |
| vienna | 1 | no |
| warsaw | 0 | no |
| ubc | 0 | no |
| toronto | 1 | no |
| hku | 1 | no |
| **ntu** | 40 | **yes, position 1** |
| kaist | 0 | no |

Three cases retrieved nothing and three more retrieved a single URL. Two hit
the candidate cap of 40 and still missed. Those are two different failures —
*no candidates* and *wrong candidates* — and they want different fixes.

## What this licenses, and what it forbids

Licensed:

- Work on **retrieval**: a real search provider behind the V2-10 seam,
  university internal search (V2-15), discovery fusion (V2-16). Those are the
  only things that can raise the ceiling.
- Work on **scope and identity** (V2-17, V2-21). The corpus's other headline
  number is `wrong_scope_claim_rate` **5/5** against `primary_source_rate`
  **13/13**: what the pipeline reads is official and then applied to the wrong
  population, year or programme. That is orthogonal to retrieval and equally
  unfixed.

Not licensed, until this measurement changes:

- deploying or paying for a cross-encoder, Jev or an LLM reranker;
- tuning `SIGNAL_WEIGHTS` or the BM25 constants in
  `app/adapters/search/retrieval.py`. They are untuned on purpose, and tuning
  them against a ceiling of zero would be fitting noise.

Re-run this measurement after any retrieval change. The day the ceiling rises
above what the current ranking already gets, V2-14 becomes worth doing — and
this file is the before-number it will be judged against.
