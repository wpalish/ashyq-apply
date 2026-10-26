# Returned by the provider, never read (ticket 05, 2026-10-18)

Ticket: [05](wayfinder/finish-algorithm/issues/05-returned-never-read.md). This is a read-only analysis of two
sets of traces:

- clean baseline 2 (`base2-{cohort,dev2,dev3,dev4}`): both arms run the defaults, 2 repetitions each, so 4
  repetitions per case;
- the RK-2 captures (`rk2-*`).

No heldout case was opened.

## Answer

**No.** No single rank rule built on query-family agreement reads the gold on two or more of unibo, ctu, tcd,
unsw and ubc without a predicted loss elsewhere. Ticket 06 is therefore closed as "no rule", and the five cases
go to the residue (ticket 16) with the causes listed at the end of the single-rule section.

## Method

- **Source.** Each case and repetition has a `x/<case>-<arm>/<ts>/<case>.raw.json`. From its `discovery_trace`
  this analysis uses:
  - `search_results`: the query family and the provider's rank;
  - `pages_read`: the URL and the verdict; an empty verdict means the page was confirmed;
  - `selected` and `lead_found_by`.

  The gold is the case's `programme_urls` plus the twins the trace recorded. Pages are matched to it with
  `same_programme_page`, the rule the scorecard's `gold_seen` uses.
- **Families agreeing.** In the rank table, this counts the families that returned *any* form of the gold,
  twins included. Retrieval cannot count that way: it counts agreement per URL. On unibo, ethz and warsaw each
  form of the gold (the English page and the local-language twin) comes from a single family.
- **Replay.** The traces do not record the `rank_candidates` scores, so the original order is rebuilt from what
  recovery did.
  - Recovery reads in ranked order and stops at the first confirmation, so the search reads are the start of the
    ranked order.
  - A candidate that was never read either ranked below the confirmed page or was dropped by the prefilter.
  - Unread candidates are ordered among themselves by their best provider rank.

  Each rule reorders that list per discovery pass, which is where `discover_candidates` counts families. The
  replay then walks the new list until it reaches a confirmation:
  - a page that was read keeps its recorded verdict;
  - an unread gold page is assumed to confirm;
  - an unread page that is not the gold is unknown (`?`), and that is a predicted **risk**. It may confirm a
    wrong page, or it may use up a read on a host with a deadline.

## Rank table (base2, 4 repetitions)

Each family column gives the provider's rank of the gold in that family. `—` means the family did not return it.

Cases are left out when neither the gold nor a twin appears in any `search_results` row: kaist, ntu, psaclay,
puc, and the 12 cases with no programme label.

The reads column shows the first eight reads of a repetition that missed the gold, or of repetition 1 when none
missed. Reads of the gold are in **bold**.

The worker A/B cases (toronto, kaist, tsinghua, kuleuven, ub, iitd, uio, uba, ctu) appear here only as rank rows.

| case | field_and_degree | programmes | natural_language | local_language | undergraduate | courses | families agreeing | gold confirmed (reps) | URLs read, in order (rep shown) |
|---|---|---|---|---|---|---|---|---|---|
| aalto (cohort) | 1 (3/4) | 4,5 | 1 (1/4) | — | 4 | — | 3 | 0/4 | off#1: none (BLOCKED) |
| delft (cohort) | 1 | — | — | 1 | — | — | 2 | 4/4 | off#1: bsc-molecular-science ×2 (subject mismatch); **bachelors/computer-science-and-engineering** (confirmed); 5 further reads after it |
| groningen (cohort) | 1 | — | 1 | 1 | — | — | 3 | 4/4 | off#1: **www.rug.nl/bachelors/computing-science?lang=en** (confirmed) |
| hku (cohort) | 1,3 | — | 1 (2/4) | — | — | — | 1–2 | 2/4 | off#1: www.cds.hku.hk/ (not a programme page); www.cs.hku.hk/ (confirmed) |
| toronto (cohort) | — | 3 | — | — | 2 (2/4) | — | 1–2 | 0/4 | off#1: www.utm.utoronto.ca/math-cs-stats/undergraduate-students/programs/… (confirmed) |
| ubc (cohort) | 6,7,8 | 1 | — | — | — | — | 2 | 0/4 | off#1: you.ubc.ca/programs/computer-science-vancouver-ba (confirmed) |
| vienna (cohort) | 1 | — | — | 1 | — | — | 2 | 4/4 | off#1: **aufnahmeverfahren.univie.ac.at/en/computer-science** (confirmed); informatik.univie.ac.at/…/bachelor-informatik-… (confirmed) |
| warsaw (cohort) | — | — | — | 2 | — | — | 1 | 4/4 | off#1: **informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF** (confirmed) |
| ethz (dev2) | 1 | — | — | 1 | — | — | 2 (one per form) | 4/4 | off#1: **ethz.ch/en/studies/bachelor/…/computer-science.html** (confirmed) |
| tcd (dev2) | 1 | 1 | 1 | — | — | — | 3 | 2/4 | on#1: a-z-of-ug-courses (subject mismatch); two short-course pages (not a programme page); courses/undergraduate/courses/computer-science-jh (confirmed) |
| uba (dev2) | — | — | — | 2 | — | — | 1 | 3/4 | on#2: exactas.uba.ar/ensenanza/carreras-de-grado/ciencias-de-la-computacion (not a programme page); deadline |
| uppsala (dev2) | 1,4 | — | — | 1 (3/4) | — | — | 1–2 | 3/4 | on#2: hto.blog.uu.se/2024/09/17/… (not a programme page) |
| auckland (dev3) | 1 | 1 | — | — | — | — | 2 | 4/4 | off#1: **…/find-a-study-option/computer-science** (confirmed); 7 sibling pages after it (subject mismatch) |
| chula (dev3) | 1 | — | — | 1 | — | — | 2 | 4/4 | off#1: programs/sandbox21-002, -001 (program catalog); **math.sc.chula.ac.th/program/undergraduate/computer-science** (confirmed) |
| iitd (dev3) | — | — | 8 (3/4) | — | — | — | 0–1 | 2/4 | off#2: eight cse/maths pages and course pages, none a programme page |
| imperial (dev3) | — | 4 (1/4) | — | — | — | — | 0–1 | 4/4 | off#1: mathematics-computer-science (subject mismatch); **undergraduate/2027/computing-beng** (confirmed); 6 further reads |
| kuleuven (dev3) | — | — | — | 2 | — | — | 1 | 0/4 | off#1: wms.cs.kuleuven.be ×2, admin.kuleuven.be dossier (not a programme page); onderwijsaanbod …/SC_51016742/… (confirmed) |
| ub (dev3) | — | 2 | 1 | — | — | 1 (1/4) | 2–3 | 0/4 | off#1: sira.ub.edu/static/fitxes/MatematiquesInformatica.html (not a programme page) |
| ucph (dev3) | 1 | — | — | 1 | — | — | 2 | 4/4 | off#1: **www.ku.dk/studies/bachelor/computer-science** (confirmed); 7 sibling pages (subject mismatch) |
| uio (dev3) | — | — | — | 1 | — | — | 1 | 3/4 | on#2: www.mn.uio.no/ifi/english/research/groups/itu (not a programme page) |
| um (dev3) | 1 | 1 | — | — | — | — | 2 | 4/4 | off#1: three postgraduate/PDF pages (not a programme page); **bachelor-of-computer-science-computer-system-and-network** (confirmed) |
| unsw (dev3) | 1,3 | 2 | — | — | — | — | 2 | 3/4 | on#1: …bachelor-of-science-in-computer-science-bengaluru (campus abroad); …bachelor-of-commerce-computer-science (confirmed); staff/beng-chong (subject mismatch) |
| ctu (dev4) | — | — | — | 5 | — | — | 1 | 2/4 | off#2: bilakniha stplan30021468 (other variant); intranet.fel …/pruchody (not a programme page); fel.cvut.cz/en/study-programs/eecs-… (not a programme page); bilakniha course, stplan and katedra pages ×5 |
| kit (dev4) | 1,3 | — | 1 | 1 | — | — | 3 | 4/4 | off#1: **www.sle.kit.edu/english/vorstudium/bachelor-informatics.php** (confirmed) |
| ktu (dev4) | 2 | — | 1,4 | 1 | — | — | 3 | 4/4 | off#1: a faculty PDF (not a programme page); **admissions.ktu.edu/programme/b-informatics** (confirmed) |
| rwth (dev4) | 1 | — | 1 (2/4) | 1 | — | — | 2–3 | 4/4 | off#1: three sc.informatik lehre/studium pages (not a programme page); **sc.informatik.rwth-aachen.de/en/studium/bachelor/informatik** (confirmed) |
| unibo (dev4) | 2 (2/4) | — | 2 | 1 | — | — | 2–3 | 0/4 | off#1: cs.unibo.it/~pellitta/…CVeng.pdf (not a programme page); corsi.unibo.it/1cycle/ComputerScienceEngineering (confirmed) |

### What the gold would have needed (the five cases the ticket names)

| case | gold: rank and families | read instead (confirmed) | what the gold needed |
|---|---|---|---|
| unibo | `laurea/informatica`: local_language 1 (4/4). Twin `1cycle/ComputerScience`: natural_language 2; also field_and_degree 2 in 2/4 | `1cycle/ComputerScienceEngineering` (field_and_degree 1, one family), confirmed in 3/4. In the 4th repetition `2024/8009` was rejected and recovery hit the deadline | The local_language rank-1 page read before the field_and_degree rank-1 page. Agreement helps only in the 2/4 repetitions where two families return the English twin |
| tcd | `courses/undergraduate/courses/computer-science`: rank 1 in all three first-pass families (4/4) | `computer-science-jh` (natural_language 2, programmes 4: two families), confirmed in both `on` repetitions | Three families ranked above two. A tie-break between one-family and multi-family pages does not separate them; ordering by family count does |
| unsw | `bachelor-of-computer-science`: field_and_degree 1 (3/4) or 3 (1/4); programmes 2 | on#1: `…-bengaluru` (field_and_degree 1, rejected: campus abroad), then `bachelor-of-commerce-computer-science` (natural_language 1, one family), confirmed | The two-family gold ahead of a one-family page. An agreement rule does that, but it first reads `your-future/what-is-computer-science` (field_and_degree 2, programmes 1), which nobody reads today, so its verdict is unknown |
| ubc | `computer-science-vancouver-bsc`: programmes 1, field_and_degree 6–8 (two families) | `computer-science-vancouver-ba` (field_and_degree 1, programmes 4: two families), confirmed 4/4 | A rule on the requested degree word (BSc rather than BA). Both pages come from two families, so **no family rule separates them** |
| ctu | `studijni-programy/bakalarske-studium/informatika`: local_language 5 only (4/4) | off#2 and on#1: department and course pages, e.g. `fel.cvut.cz/en/study-programs/eecs-…` (field_and_degree 1, programmes 3, undergraduate 1) and `bilakniha` pages. In the 2 repetitions that hit, the gold was the 3rd or 4th read | Not a rank rule. local_language rank 1 is the bachelor listing `programy-a-obory/bakalarske`, and every agreeing URL in pass 2 is a wrong page. This is worker B's case |

## One rule for all of them? Predicted effect per case

Four rules were replayed on all 4 repetitions of every case that has search results:

- **A** (the ticket's shape): a URL from ≥ 2 families, **or** at local_language rank 1, goes ahead of the rest.
  Order is kept within each group.
- **B**: a URL from ≥ 2 families goes ahead.
- **C**: the local_language rank-1 URL goes ahead.
- **D**: more families first (3 > 2 > 1), then today's order.

`x/4` counts repetitions. "Risk" means the first new read would be an unread page that is not the gold, so its
verdict is unknown.

| case | A (≥2 fam or ll#1) | B (≥2 fam) | C (ll#1) | D (family count) |
|---|---|---|---|---|
| unibo | **gain 4/4** | gain 1/4 | **gain 4/4** | gain 1/4 |
| tcd | unchanged (the gold and `-jh` both come from several families) | unchanged | unchanged | **gain 2/2 (`on` arm)** |
| unsw | unchanged; risk on#1 (`what-is-computer-science` read first) | as A | unchanged | as A |
| ubc | unchanged (miss) | unchanged | unchanged | unchanged |
| ctu | **risk 2/4**: in the 2 repetitions that hit, the listing `bakalarske` is read before the gold | unchanged | **risk 2/4** | unchanged |
| hku | gain 2/4; **risk 2/4** (`zh-hans` admissions page at ll#1, not a recorded twin) | gain 2/4; **risk 2/4** (`csai…/Regulation…` syllabus PDF, two families) | **risk 2/4** | as B |
| warsaw | **risk 3/4** (`/pl/programme?q=S1-INF` at ll#1, not a form of the gold) | risk 1/4 | **risk 3/4** | risk 1/4 |
| ethz | reordered, same page | **risk 4/4**: `inf.ethz.ch/studies/bachelor.html` (field_and_degree 2 + natural_language 1) goes ahead of the gold forms, which come from one family each. It is probably a wrong programme page | reordered, same page | **risk 4/4** (as B) |
| uba | **risk 1/4**: `df.uba.ar/~silvina/women/…` (two families) is read ahead of the gold. The host allows about two reads before its ~55–60 s deadline, which is how RK-2 failed | risk 1/4 | unchanged | risk 1/4 |
| uio | gain 1/4 | **risk 3/4** (a publications PDF from two families) | gain 1/4 | **risk 3/4** |
| chula | risk 1/4 | risk 4/4 (graduate applied-mathematics page, two families) | unchanged | risk 4/4 |
| ucph | reordered, same page | risk 3/4 (`studies/masters/computer-science`, two families) | reordered, same page | risk 3/4 |
| imperial | risk 1/4 (postgraduate-taught page, two families) | risk 1/4 | unchanged | risk 1/4 |
| delft, groningen, auckland, um, kit, ktu, rwth, vienna, uppsala | unchanged, or reordered with the same page confirmed | same | same | same |

Some of these risks are probably harmless. The prefilter drops `masters` and `graduate` slugs as
`wrong_degree_level`, and the confirm step rejects PDFs. Four cases are different: ethz (rules B and D), warsaw
(A and C), ctu (A and C) and uba (A, B and D). Each has either a page the confirm step could accept or an extra
read on a host that runs into its deadline.

**Verdict.**

- **C** is the only rule with a gain and no predicted wrong page on an English-language case. But it covers just
  **one** of the five cases (unibo), with risks on warsaw (3/4) and ctu (2/4).
- **D** is the only rule that covers two cases: tcd, and unibo in 1/4. It predicts a stable loss on ethz (4/4)
  and carries risks on hku, uio, ucph, chula and uba.
- The ticket's shape **A** covers unibo only. It carries C's risks plus uba's.
- **No single rule covers ≥ 2 of the five cases without a predicted loss.** Ticket 06 is not built.

Residue causes for ticket 16:

| case | why no rank rule fixes it |
|---|---|
| unibo | A one-family English sibling at field_and_degree 1 outranks the local_language rank-1 page. Rule C alone would fix it, at a risk to warsaw and ctu |
| tcd | The joint-honours sibling is confirmed first. Fixing it needs a family-count order, which loses ethz |
| unsw | In some repetitions the provider puts the Bengaluru page at field_and_degree 1; the one-family commerce page then confirms |
| ubc | BA against BSc, both from two families. This needs a degree-word rule, not a rank rule |
| ctu | The gold is only at local_language 5. Worker B's case |

## RK-2 post-mortem: what displaced the uba and unsw pages

1. **uba.** RK-2(c) moved each family's top result ahead of the ranked order. That made the second read
   `robotica.dc.uba.ar/en/members` (field_and_degree 1, on#2) or a PDF from `cms.dm.uba.ar` (on#1), not the gold
   at local_language 2. On this slow host recovery reaches its ~55–60 s deadline after two reads, so the gold was
   never read.
2. **unsw.** RK-2(c) read each family's top first. `…-bengaluru` (field_and_degree 1) was rejected, and then
   `bachelor-of-commerce-computer-science` (natural_language 1, a single family) was confirmed. That stopped
   recovery before the two-family gold (field_and_degree 3, programmes 2), which the off arm read second.
3. **The common cause.** Promoting a single family's top result spends a read before the gold. The confirm step
   accepts a sibling programme page, and a slow host has no spare reads. Any rule that moves a page ahead of
   today's confirmed page must survive both; D fails on ethz, and C fails on warsaw and ctu.
