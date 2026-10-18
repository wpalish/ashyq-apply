# Prototype: the discovery plan v3 for an unseen site, one page to react to

Type: prototype
Status: claimed
Blocked by: 03, 05, 06, 07, 18, 19, 20
Map: ../map.md · HITL — a rough, concrete artefact the owner reacts to; it is not the design until the owner says so.

## Question

How should programme-page discovery *behave* on a local-language site with an English twin and an opaque or
slow host, stage by stage, inside 6 queries / 60 reads / 120 s? The research tickets settle the facts; the
identity, identity-gate, model and query-language decisions settle the policy; this prototype turns them into
one page — a stage table (trigger, reads, seconds, stop condition, precision guard, motivating development
case) and the list of flags the loop would build, in paired-run order — so the owner can say "this, not
that" before anything is coded.

Sketch to start from (to be rewritten once the blocking tickets are answered):

| # | stage | trigger | guard | motivating case |
|---|---|---|---|---|
| 0 | site identity (production) | seed row | redirect/host proof first, native title via `<html lang>`, English homepage alternate | tsinghua, uio, ucph, uppsala, iitd, tcd |
| 1 | robots + first sitemap document; English homepage alternate read once when the homepage is not English; a homepage section link followed on its local label, two hops ([Local catalogue entry](20-local-catalogue-entry.md)) | always | one read; two hops inside `MAX_FALLBACK_PAGES` | uio, puc, kuleuven, utokyo |
| 2 | sitemap `keep()` with evidence-sum ([Sitemap keep rule](18-keep-rule-evidence-sum.md)), SM-1 child priority; the catalogue host's own sitemap, ≤ 3 documents (ticket 20) | sitemaps declared, or a catalogue host linked | cap on evidence-only picks; the same `keep()` | uba, um, vienna, psaclay-fr, puc |
| 3 | search by 33 s **regardless of unconfirmed slots** (defect fix); families 3 + 3 with a local-language family replacing `admissions` when the site language is known | nothing confirmed | same confirm predicate | uio, puc, uba, kuleuven |
| 4 | confirm ≤ 8 with the LX-1 lexicon generalised per language (local degree words for bachelor *and* master — `PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md` §3 Change 1) and the [Subject match](19-subject-title-shapes.md) title shapes; follow a declared twin in either direction and record it | candidates | classifier, campus guard, related-programme outcome | iitd, puc, uio, kuleuven, ucph |
| 5 | walker / navigation with link-text identity on opaque hosts (fog — only if specified by then) | no confirmation | | kaist, tsinghua, ntutw |
| 6 | stop when confirmed; report `unavailable` on access classes; persist the trace at the checkpoint | always | | ubc, imperial, aalto |

## Answer

(open — the owner's reactions and the agreed stage table are recorded here; the artefact itself is linked,
not pasted)
