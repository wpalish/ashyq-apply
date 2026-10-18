# Production site-identity gate: in the design, in the benchmark

Type: grilling
Status: resolved
Blocked by: 01, 12
Map: ../map.md · HITL — scope and a measurement choice.

## Question

For a university outside the registry, production (`CatalogueDiscoveryAdapter._identify_site` →
`_probe_site`) starts discovery only when the homepage's `<title>`/`<h1>` contains the normalized English seed
name (≥ 8 chars) or an acronym equal to the host label plus the word university/college/institute. Offline,
that rule fails 8 of 15 conclusive development homepages — Chinese, Japanese, Norwegian, Danish and Swedish
titles, "IIT Delhi", and a seed name with a suffix ("Trinity College Dublin, The University of Dublin")
([Production site-identity gate on development homepages](12-identity-gate-offline.md)). The benchmark never
exercises the gate (`live.dev2_entry` hands discovery a verified homepage).

❓ **Q1** - **The gate is part of this design.** A rule set that finds the programme page but is never
reached in production does not meet the destination (Q2 of
[Confirm the destination](01-destination.md)).

➡️ Yes.

---

❓ **Q2** - **Redesign shape (recommended, for the loop to build):** identity is established when *any* of
(i) the seed's `official_site` host equals the probed host after redirects; (ii) the page's `<html lang>`
names the country's language and the title contains the *native-script* name from the seed row's aliases (the
importer keeps only the English name and a parenthesised suffix today); (iii) the English name appears in an
English alternate (`hreflang="en"`) of the homepage, read once; (iv) today's rule. Every branch records which
one fired as the `site_identity` proof.

➡️ Yes — with (i) first, because 353 of 500 seed rows carry a domain and the redirect target is the cheapest
proof.

---

❓ **Q3** - **The benchmark gets a second arm** (`--through-identity-gate`) that builds the entry from the seed
row and runs `_identify_site`, so every paired run also reports "identity established: n/N".

➡️ Yes.

---

❓ **Q4** - **The 147 seed rows without a domain** (Melbourne, Seoul National, Tokyo, Sorbonne …) stay on the
one-query provider fallback that already exists (`"name" "country" official university website`, outside the
six-query budget); this map does not redesign it.

➡️ Yes.

## Answer

2026-10-18, the owner (Диас): **yes** via 02-Q3 — the recommended answers stand as written.

Accepted: Q1, Q2, Q3, Q4 — each recommended answer (➡️) above is the decision.
