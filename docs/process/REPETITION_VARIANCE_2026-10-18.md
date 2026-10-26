# Repetition variance: which cases flip between identical repetitions, and why

Read-only analysis, 2026-10-18 (ticket [04](wayfinder/finish-algorithm/issues/04-repetition-variance.md)).
Captures: `scratchpad/runs/{base2,ap1c}-{cohort,dev2,dev3,dev4}/{sc.json,x/}`. The heldout split was not opened:
`heldout-final` and the nine heldout ids are excluded by name in every script, and only the four development
gold files were read. Scripts: `scratchpad/variance_tools/{collect,summarise,compact,seqdiff,false_signals}.py`,
all run with `python3 -I`.

## 0. Headline

- **Thirteen development cases flip across the eight repetitions. Only two are host-caused:** kuleuven (robots.txt
  reads on its subhosts time out in 6 of 8 reps) and unibo in one rep (7 read timeouts). toronto's page is
  host-blocked in every rep, so it is constant. Its wrong-versus-missed flip is ours.
- **The rest are ours.** Two causes:
  - **(b) provider rank:** hku, iitd, unsw. The gold URL's rank changes between reps even though the reads
    before the first query are identical.
  - **(c) order / stage clock.** The gold rank stays the same, but one of three things changes the result:
    - a different lead takes the slot (tcd, ctu, rwth, uba);
    - the 55 s discovery deadline lands before the gold read (uppsala, uio, uba);
    - the SO-1 slow-host rule fires on one latency spike (uct core).
- **The ticket's named "host" examples are not host flips:**
  - tcd's `7/40 failed` is the same 4 `http_error` + 3 `blocked` in all eight reps, both hit and wrong;
  - uba's `PARTIALLY_BLOCKED` is the same 1 `http_error` + 2 `robots_disallowed` in all eight reps;
  - uct's single timeout is in a rep that still answered.

  A constant failure count cannot explain a flip.
- **No (d) harness case.** Every case ends `complete`. The longest case took 110 s, under the 115 s kill, and
  no rep has a run error.
- **The ap1c repetitions are usable as defaults for discovery:**
  - `ap1c` was built at `d7cbf8f`, which differs from `base2`'s `593bd29` only in AP-1c (a flag-off change in
    `web_scholarships.py`);
  - `ap1c.on` adds `--nav-link-level-guard`, which acts only in the funding phase;
  - no label differs between `ap1c.on` and the other six reps except the flips listed below, which also happen
    in reps without the flag.
- **The dev2 "2/6" repetition (`base2.on#2`) is a slow repetition, not a blocked one:**
  - three cases lost their page in the same rep: tcd by order, uba and uppsala by the discovery deadline;
  - every one of their reads was served.

Column order in every table: `b.off1 b.off2 b.on1 b.on2 a.off1 a.off2 a.on1 a.on2` (b = base2, a = ap1c).
Each cell has three parts:
- the page outcome: **H**it, **W**rong, **M**issed, **R**elated, **u**nadjudicated;
- known core answered/known;
- reads and seconds.

## 1. cohort

| case | b.off1 | b.off2 | b.on1 | b.on2 | a.off1 | a.off2 | a.on1 | a.on2 | class | evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| hku | W 0/2 r18 38s | H 1/2 r17 33s | H 1/2 r17 34s | W 0/2 r18 42s | W 0/2 r18 36s | W 0/2 r18 38s | H 1/2 r17 41s | W 0/2 r18 35s | **(b) provider** | The first 9 reads are identical (`hku-off/20261018T181401Z` vs `…181600Z` `.log`); `robots_disallowed` 9 in every rep. Gold rank in `field_and_degree`: **1** in the three hit reps, **3** in the five wrong reps (wrong reps pick `www.cs.hku.hk/`). `programme.exists` and `scholarships.computing_data_science_entrance.exists` flip with the page. |
| toronto | W 0/2 r23 26s | W 0/2 r23 27s | M 0/2 r30 26s | M 0/2 r30 30s | M 0/2 r30 26s | M 0/2 r30 28s | M 0/2 r30 26s | M 0/2 r30 29s | page: **(a) host, constant**; W↔M flip: **(b/c)** | `future.utoronto.ca` returns `http_error` on every read in every rep, so the gold (`programmes` rank 3) is never readable. The two W reps read `www.utm.utoronto.ca/…/computer-science` after search #2. The six M reps read `www.cs.utoronto.ca/` instead and are refused on a cross-site redirect. The provider order differs at positions 3–6 (`toronto-off/20261018T181340Z` vs `toronto-on/20261018T181407Z`). |

Never flip (cohort): aalto (M), delft (H), groningen (H), kaist (M), ntu (H), ubc (R), vienna (H), warsaw (H).

## 2. dev2

| case | b.off1 | b.off2 | b.on1 | b.on2 | a.off1 | a.off2 | a.on1 | a.on2 | class | evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| tcd | H 2/4 r56 110s | H 2/4 r58 97s | W 2/4 r58 106s | W 2/4 r58 101s | H 2/4 r58 107s | W 2/4 r58 97s | H 2/4 r58 95s | H 2/4 r58 102s | **(c) order** | The gold is rank **1** in `field_and_degree`, `natural_language` and `programmes` in all 8 reps. Failures are constant: 4 `http_error` and 3 `blocked`. The fetch sequences diverge at step 18: the wrong reps read one more walker page (`/courses/short-courses`, t=33) before search. Their leads are then `computer-science-jh` [`natural_language`, `programmes`] instead of the gold [all three] (`tcd-off/20261018T181116Z` vs `tcd-on/20261018T181309Z`). Core answers are the same in every rep. |
| uba | H 0/2 r32 77s | H 0/2 r32 77s | H 0/2 r32 75s | M 0/2 r29 71s | H 0/2 r29 80s | H 0/2 r30 75s | H 0/2 r34 84s | H 0/2 r18 62s | **(c) stage clock + lead slot** | The gold is `local_language` rank **2** in all 8 reps. Failures are the same 1 `http_error` and 2 `robots_disallowed` in all 8. In `b.on2` the walker read one more page (t=33) and search #2 took 4 s instead of 2 s. The `field_and_degree` list was reordered, so its `~ezoppi` lead took the slot, and discovery stopped at `deadline/recovery` (55.8 s) with the gold `returned`, never read (`uba-on/20261018T181514Z` vs `…181631Z`). |
| uct | u 1/1 r34 99s | u 1/1 r36 64s | u 1/1 r38 69s | u 1/1 r35 63s | u 0/1 r15 42s | u 1/1 r36 58s | u 1/1 r36 65s | u 1/1 r36 61s | **(c) order (SO-1 slow-host rule)** | In `a.off1` the first `uct.ac.za/sitemap.xml` read took 11.6 s. `host_cost.slow` became true from that one sample (`first_read_rule`, `live_discovery.py` `HostCost.slow`), so the sitemap was capped and the walker skipped. The case ended at 15 reads and 42 s, and `ielts.overall` was lost. No read failed. `b.off1` had 1 `timeout` and 1 `blocked`, and still answered. |
| uppsala | H 2/4 r23 73s | H 2/4 r25 78s | H 2/4 r25 73s | M 1/4 r20 69s | H 2/4 r26 48s | H 2/4 r23 40s | H 2/4 r26 54s | H 2/4 r26 50s | **(c) stage clock** | No read fails in any rep. In the base2 reps `www.uu.se` sitemaps (`files-1`, `images-1`, `images-2`: 6.6–10.9 s each) take 36–42 s of discovery. In the ap1c reps the slow-host rule fires and the sitemap stage takes 7 s. In `b.on2` the sitemap stage took 42.4 s, and the gold (`field_and_degree` rank 4, the same list as `b.on1`) missed the second lead slot at the 55 s deadline (`deadline/recovery`). The `deadline` label is lost with the page (`uppsala-on/20261018T181348Z` vs `…181232Z`). |

Never flip (dev2): ethz (H), kaznu (u), khalifa (u), psaclay (H), tsinghua (M), tec (u).

## 3. dev3

| case | b.off1 | b.off2 | b.on1 | b.on2 | a.off1 | a.off2 | a.on1 | a.on2 | class | evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| iitd | H r32 60s | M r30 50s | M r30 53s | H r32 57s | H r32 57s | M r33 57s | H r32 54s | M r33 53s | **(b) provider** | The first 9 reads are identical. The gold is `natural_language` rank **8** in the hit reps and **absent** in `b.on1` and `a.off2` (`gold_seen: never`). In `b.off2` it is rank 8 too, but the `programmes` list differs: it has `~suban/CSL102`, `COL100` and `ms-program`, and 5 leads take the slots before the gold (`iitd-off/20261018T181808Z` vs `…182105Z`). No core labels. |
| kuleuven | W r32 75s | M r5 59s | M r5 58s | M r5 64s | W r38 101s | M r6 68s | M r6 68s | M r4 50s | **(a) host** | In 6 reps the robots.txt reads on `eng.`, `wms.cs.`, `set.` and `onderwijsaanbod.kuleuven.be` time out at 10.0 s, and every URL on those hosts becomes `robots_disallowed` (12–16 per rep). In the 2 W reps robots answers, `network_unavailable` occurs 2–3 times, and the case confirms `…/SC_51016742/diploma_omschrijving` (not the gold). It is never a hit (`kuleuven-off/20261018T181344Z` vs `…181707Z`). |
| uio | H r19 70s | H r22 67s | H r22 68s | M r18 64s | H r30 59s | H r30 56s | H r30 60s | H r38 72s | **(c) stage clock** | The gold is `local_language` rank **1** in all 8 reps, with no failures. In the base2 reps the `sitemap-www.mn.uio.no-0.xml` read is slow, and the sitemap stage takes 46–51 s. In the ap1c reps the same document comes back `too_large` in 1.3 s, and the sitemap stage takes 28 s. In `b.on2` the sitemap stage took 51.1 s, and the gold lead was cut at `deadline/recovery` (`uio-on/20261018T182050Z` vs `…181940Z`). |
| unsw | H 0/3 r21 98s | H 0/3 r21 100s | R 0/3 r23 106s | H 0/3 r21 99s | H 0/3 r20 110s | H 0/3 r22 107s | R 0/3 r24 110s | H 0/3 r19 93s | **(b) provider** | The first 7 reads are identical. In the R reps the gold is `field_and_degree` rank **3** (rank 1 in `b.*`/`a.on2`), and the `natural_language` lead `bachelor-of-commerce-computer-science` is confirmed first (`unsw-on/20261018T181257Z` vs `…181445Z`). `a.off*` also have rank 3 and still hit, so rank 3 is a coin flip, not a certain loss. Core is 0/3 in every rep. |

Never flip (dev3): auckland, chula, imperial, puc, ucph, um (H); ub (M); msu, ntutw, usp, utokyo (u).

## 4. dev4

| case | b.off1 | b.off2 | b.on1 | b.on2 | a.off1 | a.off2 | a.on1 | a.on2 | class | evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| ctu | H r24 49s | M r26 72s | M r26 75s | H r24 43s | M r26 74s | W r31 53s | H r25 48s | M r26 71s | **(c) order (lead slots)** | The gold is `local_language` rank **5** in 7 reps and rank 4 in 1. The reads diverge right after search #2, because the `field_and_degree`, `natural_language` and `programmes` lists reorder their non-gold URLs. The M reps spend their slots on `bilakniha`/`fel` leads and stop at `deadline/navigation` (≈71 s discovery) with the gold returned and never read. The W rep confirms `bk.fit.cvut.cz/en/obory/…` (`ctu-off/20261018T181112Z` vs `…181406Z`; `ctu-on/20261018T181449Z` vs `ctu-off/20261018T181652Z`). |
| rwth | H r56 105s | H r56 96s | H r51 91s | H r51 89s | M r57 101s | H r51 86s | H r57 98s | H r56 94s | **(c) order** | The gold is rank 1 in every family in all reps. In `a.off1` the reads diverge after the homepage: the only lead is `informatik…/bachelorstudiengaenge`, and its 8-page walk ends at `deadline/navigation` (56 s). The hit rep reads `sc.informatik…/bachelor/informatik` at t=25 (`rwth-off/20261018T181332Z` vs `…181832Z`). The SO-1 slow flag is also inconsistent: slow in 6 reps, not slow in 2. |
| unibo | R r25 38s | M r16 66s | R r19 34s | R r25 40s | R r25 40s | R r23 72s | R r25 37s | R r19 33s | **(a) host** (one rep) | `b.off2` has 7 `timeout` reads and 2 reads of 10 s or more, then `deadline/recovery`. Every other rep is R (it confirms `1cycle/ComputerScienceEngineering`, related, not gold), with 2 `unparseable` and no timeouts. |

Never flip (dev4): kit, ktu (H); boun, itu, taltech, vut (u).

## 5. Verdict per flaky case (for 01 Q3)

| case | verdict | leaves the denominator for | owner |
|---|---|---|---|
| kuleuven | **host** | every rep where the subhost robots.txt reads time out (6/8 here); the other 2 are a wrong page, which is ours | worker B (missed) |
| unibo | **host** for `b.off2` only | that rep; the other 7 are R (ours: gold returned, never read) | ticket 05 |
| toronto (page) | **host**, constant | every rep (the gold host 403s); the W↔M flip is ours | worker A |
| hku | **ours**: provider rank | — | ticket 06 (family agreement), worker A |
| iitd | **ours**: provider rank + lead slots | — | ticket 06, worker B |
| unsw | **ours**: provider rank | — | ticket 06 |
| tcd | **ours**: order (lead choice, gold is rank 1 everywhere) | — | worker A |
| ctu | **ours**: order (lead slots, gold returned and never read) | — | ticket 05, worker B |
| rwth | **ours**: order (single lead, walker eats the clock) | — | ticket 05 |
| uba | **ours**: stage clock + lead slot | — | worker B |
| uio | **ours**: stage clock (sitemap stage 46–51 s) | — | worker B; map fog "stage order on slow hosts" |
| uppsala | **ours**: stage clock (sitemap 36–42 s; SO-1 fires only sometimes) | — | map fog "stage order on slow hosts" (SO-1/SM-1 re-measure) |
| uct (core) | **ours**: SO-1 `first_read_rule` fires on one 11.6 s read | — | map fog "stage order on slow hosts" |

Under 01 Q3, the host rule removes only kuleuven (6 reps), unibo `b.off2`, and toronto's page. tcd and uba stay
in the denominator.

**Stage order on slow hosts is now specifiable.** The map's fog item can be ticketed. Three cases (uppsala, uio,
uct) flip because of how discovery spends its clock on a slow host:
- the 55 s discovery deadline is fixed;
- the SO-1 slow decision is made from the first two reads;
- the sitemap stage has no time cap of its own (uppsala and uio spend 36–51 s there when SO-1 does not fire).

rwth's inconsistent slow flag (6 slow, 2 not slow) shows the same rule.

## 6. Cost of a paired run in false signals

**Null model** (`false_signals.py`):
- method: take every split of the eight identical reps into "off" and "on" arms, and count the items the scorecard
  would call a stable gain or loss (all on reps hit and no off rep hits, or the reverse);
- page items are included alongside labels.

| set | 2 reps per arm: expected false stable signals / paired run | 4 reps per arm |
|---|---|---|
| cohort | 0.43 (hku page and 2 hku labels, 0.14 each) | 0 |
| dev2 | 0.14 (tcd page) | 0 |
| dev3 | 0.24 (iitd page 0.17, unsw page 0.07) | 0.03 (iitd page) |
| dev4 | 0.31 (ctu page 0.14, ctu `programme.exists` 0.17) | 0.03 (ctu `programme.exists`) |
| **all four sets** | **≈ 1.1 per cycle** (≈ 0.46 if only label rows count, as `changes` does) | **≈ 0.06** |

**History.** The development `sc.json` files carry 62 stable gains and losses in `changes`:
- 6 sit on an item that flips under identical defaults:
  - bundle5-dev2 `uct:ielts.overall`;
  - dl5-dev2 `uppsala:deadline`;
  - qb1b-cohort `hku:programme.exists`;
  - fx3-dev4, r1-dev4 and rk2-dev4 `rwth:programme.exists`.
- The three rwth "gains" come from three unrelated flags. That is what noise looks like: the flag was credited,
  and the item flips 1 in 8 under defaults.
- The other 56 are on items that never flip across today's eight reps. The comparison is a proxy, because the
  code changed across that history.

**Recommendation.**
1. **Keep 2 reps per arm for screening.** It is cheap, and the expected false signal is about one item per
   4-set cycle.
2. **Discount any stable gain or loss on the flaky list above.** If such an item is the only evidence for a
   flag, rerun 2 more reps per arm before the flag goes on by default.
3. **Run the acceptance baseline (17) with 4 reps,** as this baseline already did. Judge "worst repetition" only
   after the §5 host exclusions: the worst dev2 rep (2/6) is a slow rep, not a blocked one, and 4 reps put the
   false-signal rate near zero.
4. **The heldout acceptance protocol (2 arms × 2 reps) carries ≈ 0.3 false items per set at this noise level.**
   Owner decision 21 fixes that protocol, so read its per-target result with that margin.
