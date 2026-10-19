# G-07 gold knockout on replay — the guess list (2026-10-19)

Generalisation ticket 07, replay plan 2026-10-19 §3 (cycle 1 deliverable). Development cases only: cohort, dev2, dev3,
dev4. No dev5 or heldout material was opened; no search provider was called (everything below is read from the four
replay artifacts and the signed development corpora).

## Runs

`expert_paired`, `search_provider=recorded`, pipeline `219d6a73` (before CH-1 `98028238` and UA-1 `169660ec`).
On arm = `--knockout-gold <dataset>`: every labelled gold URL of the case, its trivial spellings and any page that
redirects onto it or declares it as an `hreflang` alternate are answered with a synthetic 404 (`GoldKnockout` in
`evaluation/research/live.py`). Off arm = the same replay without the knockout.

| set | run | scored on | cases with a gold page |
|---|---|---|---|
| cohort | 39241545248 | `ground_truth.reviewed11.json` | 10 |
| dev2 | 39241550005 | `dev2.draft3.json` | 10 |
| dev3 | 39241555623 | `dev3.draft3.json` | 14 |
| dev4 | 39241559928 | `dev4.draft3.json` | 5 |

Sources: the scorecard JSONs (`programme_pages`, `readable.wrong_programme_pages`), and per capture
`capture.json` (telemetry `knockout_gold_urls` / `knockout_refused`) and `<case>.raw.json`
(`canary.institutions[0].discovery_trace`: `errors`, `stage_order`, `pages_read`, `lead_found_by`, `search_results`,
`walker`, `unresolved`; claims' `page_title` and `matched_because`). `knockout_leaked_hits` is 0 on every on column
(page recall 0 on all four sets).

## 1. Guess rate per set

**Guess rate = wrong programme pages confirmed with the gold hidden ÷ cases that have a gold page**, per on repetition.
The second column restricts the numerator to the cases whose gold the knockout actually refused (`knockout_refused > 0`).
That is the plan's `knockout_guess_cases_wrong ÷ knockout_cases_gold_refused`. The third column counts only the guesses
the knockout created, leaving out cases already wrong in the off arm.

| set | on#1 | on#2 | wrong among gold-refused (on#1, on#2) | new under knockout (not wrong off) | off arm wrong |
|---|---|---|---|---|---|
| cohort | **2/10** (toronto, ntu) | **2/10** | 2/8, 2/8 | 1/10 (ntu) | 1, 1 (toronto) |
| dev2 | **4/10** (psaclay, tcd, uct, khalifa) | **4/10** | 3/7, 3/7 (uct's gold is never read, so not refused) | 3/10 (psaclay, tcd, khalifa) | 1, 1 (uct) |
| dev3 | **2/14** (kuleuven, uio) | **1/14** (uio) | 1/8, 1/8 (kuleuven's gold is never reached) | 1/14 (uio) | 1, 0 (kuleuven, host-flaky) |
| dev4 | **2/5** (ctu, rwth) | **2/5** | 2/5, 2/5 | 2/5 (ctu, rwth) | 0, 0 |
| all | 10/39 | 9/39 | 8/28, 8/28 | 7/39 | 3, 2 |

The knockout is deterministic on replay: every case reads the same in both on repetitions except kuleuven, which is
host-flaky in the A/A too. The abstentions are the other gold-refused cases, which end `missed` or `related`:
cohort 6, dev2 4, dev3 7, dev4 3.

## 2. Every wrong confirm

The capture records no `h1`. `PageClassification.heading` arrived with CH-1, after these runs. The `page subject`
the trace quotes is the classifier's identity, which is the page's first `h1` when it has one, otherwise the title
before the site suffix. Below it is marked "subject (≈ h1)" and is the best available proxy. The CH-1 column is
`head_identity_rejects` at `98028238`, applied to the recorded title and that proxy with `requested_level=bachelor`,
`fields=['computer science']`. The page body was not re-read.

| set | case | confirmed URL (on, both reps unless noted) | confirm path (trace) | title / h1 (recorded) | would refuse it | gold / right page in the results? |
|---|---|---|---|---|---|---|
| cohort | toronto | `www.utm.utoronto.ca/math-cs-stats/undergraduate-students/programs/computer-science` — **same page off** | identity recovery (QB-1 pass 1): `natural_language` lead, "checked 7, confirmed 1"; robots `http_error`, 4 sitemap probes 403, both navigation fallbacks unreachable | not recorded (no claim carries the title) | **UA-1** (zero ok entry reads). CH-1 cannot be judged without the head; the URL carries `undergraduate`, so rule 2 passes | gold `future.utoronto.ca/program/computer-science` returned by `programmes` (refused, host 403 anyway); `artsci`/`utm.calendar` `Bachelor-of-Computer-Science` returned by `field_and_degree`, unresolved (host down) |
| cohort | ntu | `…/undergraduate-programme/bachelor-of-computing-in-computer-science-with-second-major-in-business`, `…-(international-trading)`, `…/bachelor-of-computing-(hons)-in-computer-science-with-a-second-major-in-sustainability` | confirm stage on registry-seed/sitemap leads (`seeds, sitemaps, confirm`); search never ran ("all 3 programme-page slots were already filled") | title "Bachelor of Computing in Computer Science with Second Major in Business \| NTU Singapore"; subject (≈ h1) the same; `matched_because`: "covers every requested subject word" | **none.** CH-1 passes: level, subject and URL slug are all in the head | gold refused (1 read); no search. The off arm confirms the same two second-major pages beside the gold. Related "Mathematical and Computer Sciences" and "Data Science and AI … Sustainability" were read and refused as related (R2) |
| dev2 | psaclay | `universite-paris-saclay.fr/formation/licence/informatique/l2-informatique` | identity recovery (QB-1 pass 1): `local_language` lead, "checked 4, confirmed 1"; hreflang English alternate read | title "L2 Informatique \| Université Paris-Saclay"; subject (≈ h1) "L2 Informatique"; `matched_because`: "a narrower name for the same subject" | **none.** CH-1 passes: `licence` slug, subject in head | gold `formation/licence/informatique` returned by `local_language` (refused; its English twin refused too, `knockout_refused` 2). Siblings `l3-informatique` and `licence-double-diplome/…` were returned, not read. The confirmed page is a path child of the unresolved gold lead |
| dev2 | tcd | `tcd.ie/courses/undergraduate/courses/computer-science-jh/` | identity recovery (QB-1 pass 1): `natural_language` + `programmes` lead, "checked 2, confirmed 1"; sitemaps 404, navigation fallback | title "Computer Science (JH) - Courses \| Trinity College Dublin"; subject (≈ h1) "Computer Science (JH)"; "covers every requested subject word" | **none.** CH-1 passes: `undergraduate` slug, subject in head; R2 reads "(JH)" as filler | gold returned by all three families (refused); `scss/courses/undergraduate/computer-science/` (the school's page for the same degree) was returned by `field_and_degree` + `programmes`, never read |
| dev2 | uct | `sit.uct.ac.za/department-computer-science` — **same page off** | identity recovery **listing acceptance** ("named by its full degree title on a listing page": "B.Sc (Hons) in Computer Science"), "checked 3, confirmed 1"; QB-1 then skips pass 2 | title "Department of Computer Science \| School of Information Technology"; h1 not recorded | **CH-1 unit word** ("department", in the title's first part) | gold `sit.uct.ac.za/bsc-degrees` returned by `field_and_degree` + `programmes`, never read (`knockout_refused` 0). BBusSc/BCom CS pages were read and refused as related (R2, correct) |
| dev2 | khalifa | (a) `ku.ac.ae/zmu` and (b) `ku.ac.ae/department/department-of-computer-science` | (a) **catalogue walker** (link "BSc in Computer Science program", score 12, `program_detail`) before search. (b) identity recovery **listing acceptance** ("named by its full degree title on a listing page"), "checked 3, confirmed 1" | (a) title and subject (≈ h1) "BSc in Computer Science at ZMU - Khalifa University". (b) title "Computer Science - Khalifa University", h1 not recorded | (a) **none.** CH-1 passes: "BSc" and the subject are in the head. (b) **CH-1 no level in head, slug or label**, or the unit word if the h1 reads "Department of …" | gold `program/bsc-in-computer-science` returned by `natural_language` + `programmes` (refused); `program/bsc-in-computer-engineering` returned, not read. **The case stays wrong under CH-1 because (a) survives** |
| dev3 | kuleuven | `kuleuven.be/programmes/opleidingen/bachelor-informatica` (on#1 only) — **same page off#1** | identity recovery (QB-1 pass 1): `local_language` lead, "checked 3, confirmed 1"; sitemaps 401/404, navigation fallback. In on#2 the same leads are unresolved and nothing is confirmed | title and subject (≈ h1) "Bachelor in de informatica — KU Leuven opleidingsaanbod" | **none.** CH-1 passes: `bachelor` slug and level and subject in head | gold (`onderwijsaanbod.` catalogue entry) never returned (`knockout_refused` 0). Not a knockout guess: possibly an undeclared twin of the gold (replay plan §2) |
| dev3 | uio | `uio.no/studier/program/informatikk-ledelse` | identity recovery (QB-1 pass 1): `local_language` lead, "checked 2, confirmed 1" | title "Informatikk: digital økonomi og ledelse (bachelor) – Universitetet i Oslo"; subject (≈ h1) "Informatikk: digital økonomi og ledelse"; "names the requested field … or one of its aliases" | **none.** CH-1 passes: "(bachelor)" and the subject head "Informatikk" are in the title | gold `informatikk-programmering` returned by `local_language` (refused). Same-family siblings `inf-design`, `matematikk-informatikk`, `maskinlering-kunstig-intelligens`, `informatikk-robotikk` and `mn.uio.no/ifi/studier/programmer/` (listing) were returned, not read |
| dev4 | ctu | `fit.cvut.cz/en/applicants/admissions-procedure/bachelor-study-program` | identity recovery (QB-1 pass 1): `natural_language` lead, "checked 4, confirmed 1" | title "Bachelor study program - FIT CTU"; subject (≈ h1) "Bachelor's degree programme Informatics"; "names the requested field … or one of its aliases" | **none if the h1 carries "Informatics"** (the subject suggests it does). CH-1 no subject in head if the subject came from body context. h1 not recorded, so undecided | gold `…/bakalarske-studium/informatika` returned by `local_language` (refused). Faculty listing `studium/programy-a-obory/bakalarske` returned, not read |
| dev4 | rwth | `informatik.rwth-aachen.de/…/bewerbungsinfos/~npqh/bachelor-informatik?lidx=1` (English alternate of the German page, which was refused on subject) | identity recovery (QB-1 pass 1): `local_language` lead, then hreflang English alternate, "checked 4, confirmed 1" | title "Bachelor Computer Science \| Faculty of Computer Science \| RWTH Aachen University \| EN"; subject (≈ h1) "Application for the B.Sc. Computer Science Course of Study"; "shares ['computer', 'science']" | **none.** CH-1 passes: "Bachelor" and the subject in the title's first part, `bachelor` slug; "Faculty" is in the title's site suffix, not the head | gold (3 forms incl. `sc.informatik…/en/studium/bachelor/informatik`) returned by every family (refused; German twin refused too, `knockout_refused` 2). `informatik-b-sc-` on `www.rwth-aachen.de` is the gold itself |

## 3. Conclusion

**CH-1's spec covers the unit-page shape, not the knockout's guesses.** Of the 10 distinct wrong pages, CH-1
refuses 2: uct's department page (unit word) and khalifa's department page (no level). Only uct changes at the case
level, because khalifa stays wrong on its walker-confirmed `zmu` page. UA-1 refuses toronto. Both uct and toronto are
already wrong in the off arm. Of the 7 guesses the knockout created (ntu, psaclay, tcd, khalifa, uio, ctu, rwth), CH-1
moves at most one case (ctu, and only if its h1 lacks the subject) and UA-1 moves none. Projected on-arm wrong counts
with CH-1 + UA-1: cohort 2 → 1, dev2 4 → 3, dev3 2/1 → 2/1, dev4 2 → 2 (or 1). That assumes recovery confirms
nothing new after a refusal, which is a floor, not a forecast.

§4 run 7's bar ("`knockout_guess_cases_wrong` → 0, or down on ≥ 2 sets") is therefore not expected to pass on CH-1
alone. Read 7a–d with that expectation. If it fails, that is a finding about CH-1's coverage, not a reason to widen
CH-1.

Every knockout guess has a head that names the requested level and subject, plus a qualifier that makes it something
else. Identity recovery reads the first lead whose head fits and stops (QB-1 skips pass 2). No planned rule
(CH-1, UA-1, CL-2) covers these shapes. Candidate tickets, generic only:

1. **Combination qualifier in the head = related programme** (ntu "… with Second Major in Business", tcd
   "Computer Science (JH)"). R2 already makes "<related field> and <field>" related. Extend its shapes to
   combination markers: joint honours / JH, second major, double/dual degree, "with <another field>". The table must
   be dictionary-grade across `languages.json`, with no word taken from these pages. 2 cases, 2 sets.
2. **A head that names a part or a process of a programme is not the programme page** (psaclay "L2 Informatique",
   a year of a licence; rwth "Application for the B.Sc. …"; ctu "admissions procedure / Bachelor study program").
   Stage markers (L1–L3, year n, first/second year) and process nouns (application, admission, how to apply, and
   their dictionary equivalents) in the head make the page a sub-page. When the page's URL is a path child of
   another programme lead, prefer the parent; psaclay's confirmed page sits under the unresolved gold. 3 cases,
   2 sets.
3. **A subtitle that names a related field makes a specialisation** (uio "Informatikk: digital økonomi og
   ledelse"). R2 tests only the subject head before `:`. Apply its related-field words
   (`_RELATED_FIELD_WORDS`, ontology `related_not_equivalent`) to the subtitle as well. Caution: uio's gold is itself
   "Informatikk: programmering og systemarkitektur", so the rule must refuse only related-field subtitles and never
   subtitles in general. 1 case; it needs a second set before build.
4. **Delivery-site qualifier** (khalifa "BSc in Computer Science at <partner institution>", confirmed by the
   catalogue walker, which CH-1's listing-acceptance hook does not touch). A head of the form "<programme> at
   <named place or institution that is not the requested one>" is a delivery variant. It is a CG-1 extension, and
   toronto's satellite campus is the same family on the host side. 1 case; it needs a second set before build.

Not ticketed: kuleuven is no knockout guess (gold never reached, same page off). It stays with the twin check in
replay plan §2.
