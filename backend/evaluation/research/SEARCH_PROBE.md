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

---

# Ranking by page kind: +11 for one case, a lost case for another, not enabled

Measured 2026-09-21, twice, `--hop` on. `classify_url` scores a candidate by
what its URL says the page is.

| | Hop baseline | With page-kind ranking (two runs, identical) |
|---|---|---|
| Retrieval ceiling | **10/10** | **9/10** |
| Toronto | #19 | **#8** (+11) |
| KAIST | #30 | #28–30 |
| Warsaw | #1 | **lost** |
| everything else | — | unchanged |

**Not enabled.** `rank_candidates(..., rank_by_page_kind=False)` by default.
§12: a discovery change is good only if the benchmark improves, and the ceiling
falling is not an improvement however large the win elsewhere.

## Two things learned, both kept

**A URL can say reliably what a page is *not*, and not what it is.** A first
attempt also scored `/programmes/` and `/admissions/` as positive hints. It
promoted catalogue *index* pages over the specific programme page that was
asked for: Warsaw lost its place, NTU fell four, Groningen and Vienna two
each. Dropping the positive half and keeping only *research output*, *news*
and *vacancy* recognition left every other case exactly where it was and kept
Toronto's +11. The positive hints are gone from the code, with the reason
beside them.

**The Warsaw interaction is not understood, and is stated rather than
guessed.** Both of Warsaw's URLs classify as `UNKNOWN`, so the signal does not
touch them; something about reordering the other candidates costs it its
place. Two consecutive runs agree, so it is not the provider variance that
explains HKU's ±1. Worth understanding before the next attempt — the
`S1-INF` (bachelor) page was replaced at the top by `S2-INF`, the **master's**
programme, which the prefilter did not reject because that URL names no
recognisable degree level. That is a separate, real gap.

## The next attempt

Keep `classify_url` — it is a capability, not a failed experiment. Re-enable
the ranking signal only with a run that holds the ceiling at 10/10. The
likeliest route is to make it a *prefilter* concern rather than a ranking one:
a research-output page is not a weak candidate, it is the wrong kind of page,
and rejections are counted and explained where ranking adjustments are not.

---

# Re-baselined, with two corrections to what this file said before

Ten live runs later, the shipped configuration (hop on, page-kind ranking off,
Bologna cycle slugs on, `site:` prefix kept) measures **9/10** with one case at
rank 1. `baseline/search_probe.exa.hop.json` now holds that run.

**Correction 1: Toronto's +11 was not caused by the page-kind signal.** It was
credited to it here. With the signal explicitly disabled Toronto still comes
back at #8 in three consecutive runs, so the improvement is not attributable to
that change. The honest statement is that Toronto moved from 19 to 8 at some
point between runs and stayed there.

**Correction 2: the 10/10 is not currently reproducible, and the cause is
outside this repository.** Warsaw's `IN/S1-INF` is absent from the results our
generated queries produce, in every configuration tried — including the cycle
fix, which *actively rejects* the master's pages that had displaced it, and
including configurations that do not touch Warsaw's URLs at all. A direct
probe settles it: Exa returns that exact page at **rank 1** for
`University of Warsaw computer science first cycle programme S1-INF`, and not
at all for `site:uw.edu.pl "computer science" "bachelor"`. The page is in the
index; our query shape does not reach it.

So the ceiling is **9/10 today and was 10/10 a few runs ago with no code
change between them that explains the difference.** A benchmark against a live
third-party index measures that index too.

## Two more measured rejections

**Dropping the `site:` prefix** — arguably right, since the provider is already
told the domain through `includeDomains` and a keyword operator is noise to a
neural index — cost Aalto six places, three other cases one each, and took
cases-at-rank-1 from two to zero. Not shipped; `queries_for(site_prefix=...)`
keeps the switch so the next provider can be measured rather than argued about.

**Ranking by page kind** is covered above and stays off.

## What did ship from all of this

The **Bologna cycle slugs**, and they are a correctness fix rather than a
ranking one: Warsaw's catalogue writes the bachelor as `IN/S1-INF` and the
master as `IN/S2-INF`, and the degree reader saw neither, so a master's page
passed a bachelor prefilter. Eight such pages are now rejected per Warsaw run.
That is right whatever it does to a rank, and the full suite is green.

## For the next agent

Do not compare against a baseline older than a few runs. Re-measure the
baseline in the same session as the change, or the drift in the provider's
index will be attributed to the code.

---

# One query phrased like a person: ceiling back to 10/10, and Toronto pays for it

Measured 2026-09-21, twice, results all but identical. Committed as
`baseline/search_probe.exa.hop.json`.

| | Previous baseline | With a natural-language family |
|---|---|---|
| Retrieval ceiling | 9/10 | **10/10** |
| Correct page at rank 1 | 1 | **2** |
| Warsaw | not found | **found** |
| Vienna | #6 | #5 |
| KAIST | #30 | #26–30 |
| Delft | #2 | #3 |
| Aalto | #19 | #21 |
| **Toronto** | **#8** | **#19** |
| Queries per run | 50 | **60** |

Five of the six families were one shape — a `site:` operator with quoted
terms. That is keyword syntax, and against a neural index five variations of
one shape are one query asked five times. The new family states the request as
a sentence: institution, the degree in words *including its cycle wording*,
the field. Naming "first cycle" is what reaches the Bologna catalogues a slug
reader cannot see, and it is what brought Warsaw back.

**The cost is real and is not hidden.** Toronto drops eleven places, Aalto two,
Delft one, and a run costs 20% more queries because the sixth family now fits
inside the budget where a fifth used to. Shipped because the ceiling is the
metric that dominates: a page never retrieved can never be used, whereas a page
at #19 is reachable by a deeper fetch. If the fetch budget is ever tightened,
revisit this trade.

Note this is **not** the earlier rejected experiment. Dropping `site:` from
every family cost Aalto six places and took rank-1 cases from two to zero.
Adding *one* plain-language family alongside the operator ones is the narrow
version, and it measures better.

---

# Toronto diagnosed: it is the wrong campus, not the new query

Measured 2026-09-21 with per-candidate query provenance (§11), one targeted
run on Toronto alone.

The natural-language family was blamed for Toronto's #8 → #19. **It is not the
cause — that family is one of the two that *found* the correct page.** What
sits above it:

| # | Host | What it is |
|---|---|---|
| 1, 3 | `utm.utoronto.ca` | Mississauga campus |
| 7, 8, 9 | `utm.calendar`, `utsc.calendar`, `utsc.` | Mississauga and Scarborough |
| 4 | `future.utoronto.ca/data-computer-science` | a neighbouring field |
| 5 | `governingcouncil.utoronto.ca` | governance minutes |

The correct page, `future.utoronto.ca/program/computer-science` (St George),
sits at #18 with a single signal. Five of the seven candidates above it are
**other campuses of the same university**, which the prefilter correctly keeps
— they share a registrable domain — and which the ranking has no reason to
push down, because nothing in the pipeline knows a campus is a different
place to apply to.

This is the third time this session that a plausible attribution was wrong,
and the first time the evidence was available to catch it immediately.
Provenance earns its keep.

## What it does not tell us

Which campus was requested. The corpus's Toronto case is St George — its
identity notes say so and warn against transferring to UTM or UTSC — but the
*request* names only "University of Toronto". A request that names no campus
should not be answered with one campus's page, and the pipeline currently has
no way to express that.

That is V2-22 entity resolution, and §12 sanctions the data it needs:
university-specific knowledge is allowed when it is *verified registry
metadata*, not code. A campus list per institution in the registry is the
shape; inventing a "if host starts with utm, penalise" rule in the ranking is
the shape to avoid.

**No fix is shipped here.** The measurement exists, the cause is named, and
the fix needs data this repository does not yet hold.

---

# The registry already knew which host publishes programmes

Measured 2026-09-21, twice, results agreeing. The best single change of this
session, and it needed no new data: `institution_registry.json` records each
institution's homepage and seed URLs with a `seeds_verified_on` date, which is
exactly the *verified registry metadata* §12 sanctions for institution-specific
knowledge. Toronto's seeds name `future.utoronto.ca`; `utm.` and `utsc.` are
other campuses and are not named.

A candidate on a host the institution's own verified seeds name now scores
above one on a sibling host they never mention.

| Case | Before | After |
|---|---|---|
| **Toronto** | #19 | **#4** |
| **Warsaw** | #5 | **#1** |
| **HKU** | #6 | **#1** |
| **UBC** | #2 | **#1** |
| Groningen | #3 | #2 |
| Delft | #3 | #2 |
| Aalto | #21 | #17–20 |
| Vienna | #5 | #6 |
| KAIST | #26 | #26–30 |
| **Cases with the correct page first** | **2** | **4** |
| Retrieval ceiling | 10/10 | 10/10 |

Vienna's −1 is inside the provider's own variance. KAIST loses relative ground
because its correct page is on `cs.kaist.ac.kr`, which the seeds do not name —
honest and expected: a signal that rewards named hosts costs the pages that
are not on one. It is a **signal, never a rejection**, precisely so those pages
are not lost.

## Why this was not done three attempts earlier

It should have been. The previous entry concluded the campus fix "needs data
this repository does not yet hold" and put it to the owner. That was wrong: the
data was already committed, already verified, and already loaded by the
discovery code. The lesson is the plain one — **look for the data before
declaring it missing**, especially when the guide names the exact place it
would live.

The three rejected ranking experiments before it were all attempts to infer
from a URL what a verified record already stated.
