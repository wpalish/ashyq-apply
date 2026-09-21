# Web search raises the retrieval ceiling from 1/10 to 9/10

Measured 2026-09-21 by claude-opus-5 against the certified corpus
`ground_truth.reviewed.json` (`2026-09-21.reviewed`, signed by Диас), using the
Phase 1 retrieval path — `DiscoveryIntent` → bounded queries → Exa → prefilter
→ BM25 and deterministic signals. **50 queries** for the whole run.

```sh
# From backend, with the key in the environment and never in a file
UNIMATCH_EXA_API_KEY=... python -m evaluation.research.search_probe --dataset evaluation/research/data/ground_truth.reviewed.json --out evaluation/research/baseline/search_probe.exa.json --live
```

| | Before (frozen capture) | With web search |
|---|---|---|
| Correct page anywhere in the candidate set | **1/10** | **9/10** |
| Correct page at rank 1 | 1 | 2 |
| Cases that retrieved nothing at all | 3 | **0** |
| Headroom for a reranker | **0** | **7** |

## What changed, and what did not

**Retrieval was the bottleneck, and web search removes most of it.** Every case
now produces candidates; the three that previously retrieved nothing — Warsaw,
UBC, KAIST — now retrieve twenty-five each, and Warsaw's correct page comes
back first. This is the single largest movement any change in this project has
produced, and it is measured rather than asserted.

**Ranking is now the bottleneck, which it was not before.** V2-14 showed a
reranker had zero headroom because the right page was almost never in the set.
It is in the set nine times out of ten now, and our ranking puts it first
twice. Seven cases have the answer in hand and show something else at the top:

| Case | Correct page at | Current top candidate |
|---|---|---|
| warsaw | **1** | the correct page |
| ntu | **1** | the correct page |
| delft | 2 | the right programme's page (a different URL) |
| ubc | 2 | the Okanagan campus, not Vancouver |
| groningen | 3 | a course-catalogue entry |
| vienna | 5 | a faculty degree-programmes index |
| hku | 5 | a school prospectus page |
| aalto | 19 | **a research publication** |
| toronto | 19 | the Mississauga campus, not St George |
| kaist | not found | a research-organisation profile |

Two failure shapes, and they are different problems:

1. **Wrong campus or wrong faculty.** UBC Okanagan for UBC Vancouver, Toronto
   Mississauga for St George. These are the *same university* by registrable
   domain, so the prefilter correctly keeps them; they are the wrong *entity*.
   That is V2-22 (entity resolution) and V2-17's university dimension needs to
   be finer than "same domain".
2. **Not a programme page at all.** Aalto's top result is a research
   publication and KAIST's is an organisation profile. Both would be rejected
   by a page classifier the retrieval path does not yet consult, and the
   ontology's `related_not_equivalent` terms are not being used to push them
   down.

**KAIST is the one case still unreachable.** Its correct page is
`cs.kaist.ac.kr/content?menu=188` — a query-string-addressed CMS page with no
words in its URL, which is the hardest possible shape for both lexical ranking
and a neural index. Worth its own look; not worth a per-university hack, which
§12 forbids.

## What this licenses

- **V2-14 becomes worth doing.** A reranker now has seven cases of headroom
  where it had none. Re-read `RERANKER_CEILING.md`: its conclusion was correct
  for the frozen capture and is now superseded for the retrieval path.
- **Tuning is now legitimate**, where it was forbidden. `SIGNAL_WEIGHTS` and
  the BM25 constants in `app/adapters/search/retrieval.py` can be tuned against
  this probe, because there is finally a signal to tune towards.
- **V2-22 and a stricter university dimension** move up: two of seven misses
  are wrong-campus, and no amount of ranking fixes an entity error.

## What it does not license

This probe measures **retrieval only**. Nothing is wired into the pipeline,
no claim was extracted, and the corpus's other headline failure —
`wrong_scope_claim_rate` 5/5 — is untouched by any of this. Per §12 a
discovery change is good only if the benchmark improves; this is the evidence
that wiring it in is worth doing, not evidence that the product got better.

Fetch budget and cost are within bounds: 50 queries, 5 per case, no case over
the 25-result cap, no provider failures.
