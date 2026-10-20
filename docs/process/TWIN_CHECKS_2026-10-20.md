# Twin and label hand-checks (TW-1), 2026-10-20

This is a research note for owner questions Q1 (uct), Q2 (kuleuven) and Q3 (tcd) from NEXT_CYCLES_2026-10-19 §8,
following ticket TW-1 in NEXT_CYCLES_2026-10-20 §6.

- **No gold file is edited.** `dev2.draft3.json` and `dev3.draft3.json` stay as they are. The snippets in §4 are
  proposals for `dev2.draft4.json` and `dev3.draft4.json`. The main session applies them only after the owner signs,
  and only after CI `verify_evidence` has found the quotes, as ticket 10 did.
- All three cases are development cases (dev2: uct, tcd; dev3: kuleuven).

## 1. How the pages were read

| item | value |
|---|---|
| reader | the production `app.adapters.fetching.Fetcher`: robots.txt read first and honoured, Crawl-delay honoured, our own `USER_AGENT` (contact field `tw-1 hand-check`), `use_cache=False`, no override of any kind |
| route | direct first. The container was refused: `www.tcd.ie` robots.txt `ConnectError`, which counts as a full disallow under RFC 9309. Then `trust_env_proxy=True` (the agent sandbox's HTTPS_PROXY, TLS verified against its CA bundle), which is the documented opt-in for agent-run checks |
| when | 2026-10-20, 00:57–01:00 UTC |
| quote check | every quote below was run through `verify_evidence`'s own matching (`readable_text`, then `quote_in`) on the saved pages: **10/10 found**. This is a stand-in. CI `mode=verify_evidence` remains the check that counts |
| not opened | no heldout file, capture, log or label; no other worker's scratchpad; no paid search |

| URL | outcome | final URL | `rel=canonical` | hreflang | sha256 (16) |
|---|---|---|---|---|---|
| `https://www.tcd.ie/courses/undergraduate/courses/computer-science/` (tcd gold) | 200 | same | `/courses/undergraduate/courses/computer-science/` (self) | none | `26ac662224697c46` |
| `https://www.tcd.ie/scss/courses/undergraduate/computer-science/` | 200 | same | **none** | none | `8e721dfc113b36aa` |
| `https://scss.tcd.ie/undergraduate/computer-science/` (the gold page's only link to the School) | **404** | `https://www.tcd.ie/scss/undergraduate/computer-science/` | — | — | — |
| `https://sit.uct.ac.za/bsc-degrees` (uct gold) | 200 | same | self | none | `4b9d215be0c6fff8` |
| `https://sit.uct.ac.za/ba-informatics` (uct related) | 200 | same | self | none | `f22076d0174b628b` |
| `https://uct.ac.za/students/study-uct-degrees-diplomas-science/science-undergraduate` (the expert's faculty page) | 200 | same | self | none | `eaa96654488a5a14` |
| `https://www.kuleuven.be/programmes/opleidingen/bachelor-informatica` | **not read**: robots.txt unreachable (`ConnectError` / `ConnectTimeout`), 3 attempts over 3 min | — | — | — | — |
| `https://onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742.htm` (kuleuven gold) | **not read**: same | — | — | — | — |

The agent proxy's status endpoint shows the cause for both kuleuven hosts: `ws_closed_mid_exchange`, "tunnel closed
(code 1006) after 7s". The host drops the sandbox's egress. KNOWLEDGE_BASE.md already lists KU Leuven among the hosts
that reset the container, and REPETITION_VARIANCE_2026-10-18 records the same robots timeouts on the CI runner in 6 of
8 repetitions.

## 2. Findings per case

### Q1 — uct (dev2): `sit.uct.ac.za/bsc-degrees` vs `ba-informatics`

**Relation:** the gold is the BSc (Computer Science major) page. `ba-informatics` is a different degree from the same
School, in a different faculty. Keep the label as it is.

- **The head looks like a listing, but the body is not one.** The title is "BSc degrees | School of Information
  Technology" and the h1 is "BSc degrees". The main content, however, describes exactly one programme, the BSc with a
  Computer Science major:
  - "A BSc degree in Computer Science includes a sequence of courses that constitute a complete undergraduate training
    in Computer Science";
  - the key courses (MAM1004, CSC1015, CSC1016, CSC2001, CSC2002, CSC3002, CSC3003);
  - an AI major note;
  - the entry rule: "Core requirements include admission to a BSc degree and at least 70% for NSC Mathematics (or
    equivalent)";
  - a contact line: "For queries about a BSc in Computer Science, contact …".

  No other BSc major is described on the page.
- **There is no CS entry page below it.** The School's navigation (Our degrees → undergraduates) lists `bsc-degrees`,
  `bcom-degrees`, `our-degrees-undergraduates/bbussc-degrees` and `ba-informatics`. `bsc-degrees` has no child page.
  The other entries in its menu are:
  - BCom IS & CS, a Commerce degree;
  - BBusSc CS, a Commerce degree, already labelled related;
  - Honours, Masters and PhD.

  The expert's faculty page (`uct.ac.za/…/science-undergraduate`) lists "Computer Science" as plain text among 20+
  "Bachelor of Science" majors. It does not link to a CS page and quotes no SB001 plan code. So it is one tier more
  general than the gold, not a better gold.
- **`ba-informatics` is a BA/BSocSc degree in the Humanities faculty, run by the same School of IT.** The page says
  "Information Systems or Computer Science can be taken as a major along with another Humanities subject as part of a
  general BA/BSocSc degree", with co-majors in African Languages, Economics, Psychology and others. It is a different
  degree from the BSc, so the ticket-10 label `related` is right. It has the same shape as UBC's BA.
- **Why the run misses.** The page is labelled correctly. CH-1 refuses a listing-shaped head ("… degrees") by design,
  and MISS_STAGES §1.1 row 9 already records that no generic rule should accept that head. uct stays `related`, which
  is correct, on the current pipeline. This is a reach/residue question, not a label question.

**Recommendation for Q1:** keep the gold, with no change to `programme_urls` or `related_programme_urls`. The only
proposed edit is a `review.notes` sentence that records this check (§4.1). The ticket's bar of "uct hit or related" is
met as `related`.

### Q2 — kuleuven (dev3): `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` vs `onderwijsaanbod…/SC_51016742`

**Relation:** the evidence points to the same programme presented on two official pages. The twin is **not declared**:
there is no redirect and no hreflang between the two pages. Canonical and the programme code are unverified, because
neither host answers this container.

The available evidence comes from existing dev3 records, not from today's read:

1. **No redirect onto the gold and no hreflang declaration of it.** In the gold-knockout run (GOLD_KNOCKOUT_2026-10-19
   §2, dev3 kuleuven) the www page was confirmed in the knockout arm (on#1). That arm's `GoldKnockout.screen`
   (`evaluation/research/live.py`) replaces with a synthetic 404:
   - any read whose final URL is a gold form;
   - any page whose `declared_alternates` (`<link rel=alternate hreflang>` on `kuleuven.be`) includes a gold form.

   The page passed that screen, so on that run it neither redirected to `SC_51016742` nor declared it as an hreflang
   alternate. The normal arm agrees: the page was scored `wrong`, not `hit`. WF-17 (`returned_matching_gold`) would
   have counted a declared twin.
2. **The gold declares nothing either.** The 2026-10-18 hand-fetch of the gold, kept as
   `backend/tests/fixtures/localized_identity/kuleuven.html` ("title, html lang, hreflang alternates … kept"), has:
   - no hreflang alternate;
   - no link to `www.kuleuven.be/programmes/…`.

   Its only `www.kuleuven.be` links are footer links (inschrijvingen, levenslang leren, disclaimer, jobsite). The trim
   did not promise to keep `rel=canonical`, so the gold's canonical is **unknown**.
3. **Same programme by content.**
   - The confirmed head was "Bachelor in de informatica — KU Leuven opleidingsaanbod" (GOLD_KNOCKOUT), with level and
     subject in the head and slug.
   - The gold's title is "Bachelor in de informatica (Leuven) - Studieprogramma", with the gold quote "Bachelor in de
     informatica (Leuven) (Bachelor of Science, 180 sp.)".
   - `www.kuleuven.be/programmes/opleidingen/*` is the university's prospective-student programme page
     ("opleidingsaanbod"). `onderwijsaanbod.kuleuven.be/opleidingen/n/SC_*` is the official study-programme catalogue
     ("Studieprogramma"). This is the same two-page shape as tcd.
   - **One open point is the campus.** The gold is the Leuven programme. If the www page also covers a Kulak (Kortrijk)
     first-year track, it is still the same degree, but its scope is wider than the gold's. It would then remain a twin
     of the degree under the tcd convention below, but the owner should know.

**Recommendation for Q2:** sign the page as a twin **conditionally**. The main session adds the www page to
`programme_urls` (§4.2) only after one CI read confirms all of the following:

- (a) `final_url` equals the requested URL (no redirect);
- (b) the readable text names "Bachelor in de informatica" with Leuven, and with 180 studiepunten or Bachelor of
  Science;
- (c) the excerpt in §4.2 is found by `verify_evidence`.

Until then, keep the `wrong`. The read list is committed with this note as
`backend/evaluation/research/expert/data/read_pages/tw1-kuleuven-2026-10-20.json` (seed_id `kuleuven`, an official
case domain; dev3 only). To run it:

```bash
gh workflow run benchmark-capture.yml --ref claude/greeting-16wj2z -f mode=read_pages \
    -f extra_args=evaluation/research/expert/data/read_pages/tw1-kuleuven-2026-10-20.json
```

`read_pages` returns readable text and `final_url`, not the raw head, so it cannot settle `rel=canonical`. Canonical
does not decide the question either way: the scorer treats a declared twin, not a canonical, as the same page. If the
owner wants canonical too, the next CI read that keeps raw HTML (a dev3 capture from a repetition where the host
answers) shows it.

If the read fails again (the host is flaky on CI too), the owner can still sign on evidence 1–3. The risk is low,
because the only alternative reading is "a KU Leuven page about the same named degree".

### Q3 — tcd (dev2): `www.tcd.ie/scss/courses/undergraduate/computer-science/` vs the gold

**Relation:** the same programme, verified by the same CAO course code and the same awards. The twin is not declared:
there is no canonical, hreflang or redirect between the two pages. The School's page links to the gold as its apply
page.

| fact | gold `tcd.ie/courses/undergraduate/courses/computer-science/` | School `tcd.ie/scss/courses/undergraduate/computer-science/` |
|---|---|---|
| title / h1 | "Computer Science - Courses \| Trinity College Dublin" / "Computer Science" | "Computer Science - School of Computer Science and Statistics \| Trinity College Dublin" / "Computer Science" |
| course code | "CAO Code TR033" | "Course Code: TR033" |
| award | "B.A. (Moderatorship) Honours Bachelor Degree (NFQ Level 8)" / optional M.C.S. (NFQ 9) | "BA (Mod) Computer Science – 4 years / Master in Computer Science (MCS) – 5 years"; "Duration: 4 Years (BA Mod) or 5 Years (MCS)" |
| canonical | self | none |
| hreflang | none | none |
| link between them | links to `scss.tcd.ie/undergraduate/computer-science/`, which redirects to `www.tcd.ie/scss/undergraduate/computer-science/` and returns **404**; there is no link to the School's course page | "Apply for Computer Science" → `https://www.tcd.ie/courses/undergraduate/courses/computer-science/` (the gold) |

Both pages carry one course code (TR033) and one award pair, and the School's page sends applicants to the gold. It is
the School's presentation of the gold programme, not a sibling. A sibling would be `computer-science-jh` (Joint
Honours), which is a different CAO entry.

**A record discrepancy for the owner:**
- GOLD_KNOCKOUT_2026-10-19 (dev2 tcd row) records that the knockout arm **confirmed `computer-science-jh`**, and that
  the School's page was "returned … never read".
- NEXT_CYCLES_2026-10-19 Q3 says the knockout run "confirms `tcd.ie/scss/courses/undergraduate/computer-science`".

The likeliest reading is that the later pipeline (CQ-1 refuses the "(JH)" head) moved the knockout confirmation from JH
to the School's page. This note did not open the day-end captures to check. The twin label helps only for runs that
return the School's page. A run that returns `computer-science-jh` stays wrong, which is correct, because JH is a
different programme.

**Recommendation for Q3:** sign the page as a twin. Add the School's page to `programme_urls`, with a
`programme_evidence` quote (§4.3).

## 3. What the new drafts change when scoring (expected; the main session re-scores)

| case | today (draft3) | with draft4 as proposed | notes |
|---|---|---|---|
| uct | related | related (unchanged) | label confirmed |
| kuleuven | wrong in readable reps | hit in readable reps that return the www page (only if Q2's condition is met) | unreadable reps stay missed |
| tcd, knockout arm | wrong (School's page; if NEXT_CYCLES_10-19 is right) | hit on the re-scored day-end artifacts; knockout dev2 1 → 0 | normal arm unchanged: the gold is the hit |

**Caveat for future knockout runs.** `GoldKnockout.from_dataset` refuses every URL in `programme_urls`. If
`dev2.draft4.json` (or dev3) is passed as `--knockout-gold`, the School's page (and the www kuleuven page) are knocked
out too, and the arm measures a different, harder thing. To compare with the 2026-10-19 knockout numbers, keep
`--knockout-gold` on draft3 and score with draft4, or record the change in the ledger.

## 4. Draft4 snippets (proposals only; not applied)

The main session applies these after the owner signs. The steps are:
1. copy draft3 to draft4;
2. bump `version` / `dataset_version`;
3. apply the field changes;
4. run CI `mode=verify_evidence` on the new quotes.

### 4.1 `dev2.draft4.json` — uct (notes only)

```json
{
  "id": "uct",
  "programme_urls": ["https://sit.uct.ac.za/bsc-degrees"],
  "related_programme_urls": [
    "https://sit.uct.ac.za/ba-informatics",
    "https://sit.uct.ac.za/bachelor-business-science-specialising-computer-science"
  ],
  "review": {
    "notes": "<draft3 notes unchanged> TW-1 (2026-10-20, docs/process/TWIN_CHECKS_2026-10-20.md): bsc-degrees re-read with the production Fetcher; its head is a listing ('BSc degrees') but its body describes only the BSc with a Computer Science major ('Core requirements include admission to a BSc degree and at least 70% for NSC Mathematics (or equivalent)'); no CS page below it; ba-informatics is the Humanities BA/BSocSc of the same School (related). Label kept. Q1 signed <date> by <owner>."
  }
}
```

### 4.2 `dev3.draft4.json` — kuleuven (conditional on the CI read in §2 Q2)

```json
{
  "id": "kuleuven",
  "programme_urls": [
    "https://onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742.htm",
    "https://www.kuleuven.be/programmes/opleidingen/bachelor-informatica"
  ],
  "programme_evidence": [
    "<draft3 SC_51016742.htm evidence unchanged>",
    {
      "url": "https://www.kuleuven.be/programmes/opleidingen/bachelor-informatica",
      "excerpt": "<quote taken from the read_pages text: the line naming 'Bachelor in de informatica' with campus Leuven and its credits/degree>",
      "scope": {
        "university": "KU Leuven",
        "programme": "Bachelor in de informatica",
        "degree": "bachelor",
        "field": null, "intake": null, "population": null, "qualification": null, "academic_year": null
      },
      "accessed_on": "<date of the CI read>",
      "source_type": "official",
      "excerpt_truncated": false
    }
  ],
  "review": {
    "notes": "<draft3 notes unchanged> TW-1 (2026-10-20): www.kuleuven.be/programmes/opleidingen/bachelor-informatica is KU Leuven's programme page for the same degree as the onderwijsaanbod catalogue entry; no redirect and no hreflang between them (knockout screen passed it; gold fixture declares none); signed as a twin of the gold <date> by <owner>."
  }
}
```

The excerpt is left blank on purpose. No quote is written from a page this worker could not read.

### 4.3 `dev2.draft4.json` — tcd

```json
{
  "id": "tcd",
  "programme_urls": [
    "https://www.tcd.ie/courses/undergraduate/courses/computer-science/",
    "https://www.tcd.ie/scss/courses/undergraduate/computer-science/"
  ],
  "programme_evidence": [
    "<draft3 courses/computer-science evidence unchanged>",
    {
      "url": "https://www.tcd.ie/scss/courses/undergraduate/computer-science/",
      "excerpt": "Course Code: TR033",
      "scope": {
        "university": "Trinity College Dublin",
        "programme": "BA (Mod) Computer Science – 4 years / Master in Computer Science (MCS) – 5 years",
        "degree": "bachelor",
        "field": null, "intake": null, "population": null, "qualification": null, "academic_year": null
      },
      "accessed_on": "2026-10-20",
      "source_type": "official",
      "excerpt_truncated": false
    }
  ],
  "review": {
    "notes": "<draft3 notes unchanged> TW-1 (2026-10-20, docs/process/TWIN_CHECKS_2026-10-20.md): the School of Computer Science and Statistics page carries the same CAO code (TR033) and the same awards (BA (Mod) / optional MCS) as the gold and links to it as 'Apply for Computer Science'; no canonical/hreflang/redirect between them; signed as a twin of the gold <date> by <owner>."
  }
}
```

Alternative excerpts (all found by `quote_in` on the saved page):
- "BA (Mod) Computer Science – 4 years / Master in Computer Science (MCS) – 5 years";
- "Duration: 4 Years (BA Mod) or 5 Years (MCS)";
- "Trinity Computer Science students can study for an Honours Bachelor's degree (BA (Mod) Computer Science) over four
  years".

## 5. What the owner signs

| # | question | recommendation | effect |
|---|---|---|---|
| Q1 | uct: keep `sit.uct.ac.za/bsc-degrees` as the gold, with `ba-informatics` and BBusSc as related? | **yes, keep** (no label change; notes line only) | uct stays `related`; the miss is CH-1's listing-head refusal (residue), not the label |
| Q2 | kuleuven: add `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` to the gold as an undeclared twin, once one CI `read_pages` run confirms it is the Leuven "Bachelor in de informatica" with no redirect? | **yes, conditionally** | the readable reps go from wrong to hit; normal-mode wrong pages fall to 0 |
| Q3 | tcd: add `www.tcd.ie/scss/courses/undergraduate/computer-science/` (TR033) to the gold as a twin? | **yes** | the knockout guess becomes a hit on re-score (dev2 1 → 0); the normal arm is unchanged |
