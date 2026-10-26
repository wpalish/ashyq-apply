# Production site-identity gate on development homepages

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5, offline, on homepages fetched with plain curl.

## Question

In the product, a university outside the 19-entry registry reaches discovery only if
`CatalogueDiscoveryAdapter._identify_site` establishes its site (`backend/app/catalogue/discovery.py`
L101–190). Applied to the development universities' real homepages, how often does that rule pass, and why
does it fail? Does the benchmark measure it?

## Answer

Rule (`_probe_site`, L135–190): fetch `https://{host}/`; require `page.ok` and no off-site redirect; take
`<title>` + all `<h1>`, normalize; pass when the normalized seed name (`canonical_name(row["name"])`, ≥ 8
chars) is a substring, **or** a 3–7-character acronym equals the host label (`www.` stripped) and appears as
a whole word together with "university/college/institute". Aliases known to the row: the seed name itself and
a parenthesised suffix of it (`importer.py` L196–200) — no native-script name, no short form.

Offline result (`scratchpad/wf_tools/identity_gate.py`; homepages in `scratchpad/pd_pages/` and
`scratchpad/wf_pages/`, fetched 2026-10-18):

| verdict | cases | title seen |
|---|---|---|
| PASS (7) | psaclay, uba, puc, ethz (`ETH Zürich - Homepage`), usp, khalifa, um | English/Latin name present |
| **FAIL, conclusive (8)** | tsinghua (`清华大学`), ntutw (`國立臺灣大學`), utokyo (`東京大学`), uio (`Forsiden - Universitetet i Oslo`), ucph (`Københavns Universitet`), uppsala (`Uppsala universitet`), iitd (`Home Page : IIT Delhi`), tcd (`Trinity College Dublin` vs seed `Trinity College Dublin, The University of Dublin`) | native-language or short name; the seed name is the long English form |
| FAIL, inconclusive (4) | msu (3.9 KB shell), ub (`Just a moment...`, Cloudflare), chula (960 B), tec (885 B) | the saved copy is a redirect/JS/challenge shell, not the page the Fetcher would see |
| not fetched | kaznu (no connection from this sandbox) | — |

So **8 of 15 conclusive development homepages fail the gate**: in production these universities return
"Official website identity not established" and never run discovery, whatever the discovery rules do. The
heldout countries (Czechia, Germany, Turkey, Estonia, Italy, Lithuania, Kazakhstan) publish homepages with
native titles as a rule, so the gate is the first wall an unseen university meets there — a public-facts
inference, not a heldout observation.

Three cheap signals the rule ignores, all present in the fetched pages: (i) the probed host equals the seed
row's `official_site` host after redirects (identity by the owner's own catalogue row); (ii) `<html lang>`
plus a native name — not available in the row today; (iii) a homepage `hreflang="en"` alternate whose title
carries the English name (uio, ucph, uppsala, tsinghua, utokyo all publish an English homepage).

**The benchmark bypasses the gate.** `evaluation/research/live.py` `dev2_entry` (L150–165) builds
`{"name","country","city","homepage"}` directly from the seed row and `DEV2_DOMAINS`, "the exact shape
`_identify_site` returns", so every dev2/dev3 number measures discovery *after* an identity the product may
never establish. There is no arm that runs `_identify_site`. Decision: [Production site-identity gate: in the
design, in the benchmark](05-identity-gate-in-design.md).

### Sources

- `backend/app/catalogue/discovery.py` L43–190; `backend/app/catalogue/importer.py` L144–205;
  `backend/evaluation/research/live.py` L76–165.
- Script: `scratchpad/wf_tools/identity_gate.py`; pages: `scratchpad/pd_pages/{tsinghua,msu,ntutw,uio,psaclay,kudk,ub,uba,uc,chula,tec}.html`,
  `scratchpad/wf_pages/{utokyo,ethz,usp,khalifa,iitd,um,uppsala,tcd}_home.html`.
