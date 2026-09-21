# Web search raises the retrieval ceiling from 1/10 to 9/10

> Two measurements live in this file. The first is the headline result and is
> committed as the baseline. The second, at the end, is a **negative** result:
> fusing the navigation hop as an equal generator made the benchmark worse and
> was therefore not shipped.

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

---

# Negative result: fusing the navigation hop as an equal generator makes things worse

Measured 2026-09-21, same corpus, same 50 queries, with
`--hop` enabled so each of the top three search results had its navigation
read and the resulting links fused in through V2-16.

| | Search only | With the hop fused as an equal |
|---|---|---|
| Retrieval ceiling | **9/10** | **8/10** |
| Correct page at rank 1 | 2 | 2 (but different cases) |
| NTU | **#1** | #12 |
| UBC | #2 | #16 |
| Groningen | #3 | #11 |
| HKU | #5 | #11 |
| Aalto | #19 | **lost entirely** |

The hop contributed 16–30 candidates per case. Each one starts again at rank 1
on its own entry page, and `GENERATOR_WEIGHTS` gives `catalogue_walker` and
`web_search` the same trust, so a navigation link ranked first on some page
outscored a search result ranked tenth or twentieth. Correct pages were pushed
down and, for Aalto, out of the top 25 altogether.

Per §12 — *a discovery change is good only if the benchmark improves* — **this
is not shipped.** `discover_candidates` takes a `fetch` callable that defaults
to `None`, so the hop is off unless a caller asks for it, and the probe needs
`--hop` to turn it on. The committed baseline in `search_probe.exa.json` is the
search-only run.

## What the result actually says

The hop is not wrong; it was *used* wrongly. Search ranking here is measured
and good — 9/10 reachable, and the misses are ranking problems, not coverage
problems. The hop exists for the one case search cannot see at all. Those are
different jobs:

- **Coverage** adds pages nothing else found. It must never displace a page a
  ranked generator already placed well.
- **Ranking** decides order among pages already found, and fusion by rank is
  the right tool there only when both inputs are genuinely ranked.

A navigation list is not ranked in the sense RRF assumes: link order on a page
is layout, not relevance. Treating it as a ranking was the error.

KAIST also stayed unreachable with the hop on, for a separate reason: its top
search results are `pure.kaist.ac.kr` research profiles, so the hop opened
those rather than `cs.kaist.ac.kr/` — the page whose navigation *does* contain
the answer (proved in V2-16b, rank 3). Choosing entry points by search rank
alone picks the wrong door.

## What to try next, in order

1. **Append, do not interleave.** Hop-only candidates after the search list,
   keeping agreement where both generators found a page. Re-measure; the
   ceiling should rise to 10/10 without any case moving down.
2. **Choose entry points by kind, not by rank.** A department or faculty root
   is worth opening; a research-profile page is not. `page_classifier` already
   distinguishes them and the retrieval path does not consult it.
3. Only then consider giving the hop a weight in fusion, and only if a
   measurement asks for it.

---

# Resolved: coverage must be additive, and the ceiling reaches 10/10

Measured 2026-09-21, same corpus, 50 queries, `--hop` enabled, after three
failed attempts. Committed as `baseline/search_probe.exa.hop.json`.

| | Search only | Hop as an equal | **Hop as additive coverage** |
|---|---|---|---|
| Retrieval ceiling | 9/10 | 8/10 | **10/10** |
| KAIST | not found | not found | **#30** |
| Cases moved down by the hop | — | 6 | **0** |

## The three failures, because each taught something

**1. Fused as an equal generator → 8/10.** Recorded above. A navigation list is
layout, not relevance.

**2. Appended, entry points chosen by search rank → 9/10, hop contributes
nothing visible.** KAIST's top results are `pure.kaist.ac.kr` research
profiles, a graphics lab and the sociology department. `cs.kaist.ac.kr` — whose
navigation demonstrably holds the answer — sat sixth among candidate hosts and
was never opened. Search rank says which host search liked; it does not say
which host runs degrees. Entry points are now scored: a host naming the
requested field wins, an admissions host next, and a lab or publication
repository is not opened at all.

**3. Appended *inside* the same budget → still nothing.** This one was
invisible for three runs. Search returned exactly `top_k` candidates, the hop
appended after them, and the final truncation cut every appended row off again.
**"Never displace" and "must add" cannot both hold inside one fixed budget.**
The search list is now truncated first and coverage extends it, so the hop
competes for nothing.

## The one case that looks worse, and why it is not

HKU reads 5 → 6 in every hop run. Its record shows `hop_candidates: 0` and
`hop_entry_points: 0` — the hop fetched nothing and contributed nothing, so
HKU's list is search-only and mechanically identical to the baseline. The
difference is Exa's own run-to-run variation.

Worth stating as a method rule: **this provider is not deterministic, so a
single run cannot detect a one-position change.** Compare ceilings and
large moves; treat ±1 as noise unless two runs agree.

## Still open

- KAIST is reachable at #30, which is *reachable*, not *good*. The ranking work
  (entity resolution for wrong-campus misses, consulting `page_classifier`) is
  unchanged and is what would move it up.
- HKU opened no entry point at all. Worth a look: either every candidate host
  scored below zero, or the fetches failed.
- None of this touches `wrong_scope_claim_rate` 5/5.
