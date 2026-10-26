# Worker C (in flight): core answers on found pages — groningen, ntu, warsaw, ethz, uppsala, tcd

Type: task
Status: claimed
Blocked by: —
Map: ../map.md · AFK task, **already in progress** (2026-10-18). Registered for the frontier and for 16.

## Goal

Target 4 on cohort/dev2: groningen 3/5 (nl scholarship on a client-rendered list — A1), ntu 1/5 (Nanyang
binding alias — ticket 02 Q1; SAT prose — B1; gpa prose — 02 Q7), warsaw 0/2 (award on `bpm.uw.edu.pl` + PDF —
A6), ethz 0/2 (static HTML has no award link — A1), uppsala 2/4 (TOEFL section score — B3; deadline — 02 Q5;
Anders Wall award one query away — SQ-1), tcd 2/4 (E3 award on the index page — AP-1; tuition — FE-2b landed).
Cause codes from `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` §2.

## Bar

As ticket 11, plus: **no new wrong claim is the hard line** — `claim_precision` 1.00 today and target 1 is met;
an evidence rule that trades one right answer for one wrong is rejected on the spot. Labels whose fix is a corpus
line (02) are not coded around. Residue classes: groningen nl, ethz **client-rendered / no link**; warsaw **other
host + PDF**.

## Files the worker holds

`backend/app/adapters/{web_requirements,web_scholarships,extraction,structured_extraction}.py`, `document_ir`,
their tests. Shared with worker D by landing order (one PR at a time); ticket 08's future flags (ET-1, LE-1) wait
for C and D to finish.

## Done when

As ticket 11; every label either stably hit or named in 16 with its class.
