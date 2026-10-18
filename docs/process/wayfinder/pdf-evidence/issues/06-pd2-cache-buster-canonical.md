# PD-2 `CACHE_BUSTER_CANONICAL`: a numeric cache-buster is dropped before the PII guard sees the link

Type: task
Status: open
Blocked by: 01 (Q5), (previous map 13 and 14 landed — the queue sites are in files workers C and D hold)
Map: ../map.md · AFK task behind one flag; one paired run. The guard itself is not touched (AGENTS §6).

## Goal

um's «Fee Structure, UG, International — Updated 22 Oct 2025.pdf» is refused in 4/4 base2 repetitions because its link
carries `?_t=1761184801` and `fetching._QUERY_DIGITS = \b\d{9,}\b` reads nine digits as a possible passport or card
number («refused_privacy»); ucph's study regulation `…erhvervska.pdf?177667006` is refused the same way. Both are
official same-domain PDFs with a server-side cache-buster. The fix is **canonicalisation at the queue**, not a softer
guard: before a discovered link is queued, drop a query parameter whose name is a known cache-buster (`_t`, `t`, `ts`,
`v`, `ver`, `version`, `rev`, `timestamp`, `cache`, `cb`, `nocache`) or whose entire query is a bare number, **when the
value is purely numeric** and the link is on the institution's own registrable domain; everything else — a digit
sequence in the path, in a named parameter not on the list, or beside letters — still reaches the guard unchanged and
is still refused.

## Flag and loop id

`CACHE_BUSTER_CANONICAL = False` in a **new** `app/adapters/url_canonical.py` (`canonical_link(url) -> str`), harness
`--cache-buster-canonical`, loop id **PD-2**. Hook: one call where links are turned into queue targets in the three
stages (≤ 2 lines each, after C and D land). `fetching.find_pii` / `assert_no_pii` / `_QUERY_DIGITS` are **not**
edited; a test asserts the module's source has no diff in those names.

## Bar

One paired run per set. No new wrong claim; no stable loss; reads not above the off arm by more than 1 per case
(the previously refused PDF is now one read — refused requests were already counted on the wire). Expected gain on
today's labels: **0** (um tuition and ucph gpa/deadline are `unknown` or on HTML) — the rule earns its place by
turning two `refused_privacy` outcomes into readable pages and by being required before 08's fee-schedule work has
anything to read. If it adds a read with no label and no page-outcome change on any set, it is rejected (01-Q5 of the
previous map: no "for later").

## Done when

- Offline tests: `…/fee.pdf?_t=1761184801` → `…/fee.pdf`; `…/x.pdf?177667006` → `…/x.pdf`; `…/apply?id=123456789`
  unchanged and still refused by `find_pii`; `…/doc.pdf?_t=abc123456789` unchanged (not purely numeric); a link on
  another registrable domain unchanged; flag off → byte-identical.
- Paired run recorded; default-on or rejected; HANDOFF §8 line; a one-line note in `fetching.py`'s guard comment
  pointing at the canonicaliser (comment only).

## Evidence

`fetching.py` L862–876 (`_QUERY_DIGITS`, `find_pii`); base2 dev3 um page outcomes `fetch-failed · refused_privacy`
×4 and the ucph log line «refusing <PDF>: looks like long digit sequence in a query parameter» (`scratchpad/pdfmap/
captures_pdf.json`).
