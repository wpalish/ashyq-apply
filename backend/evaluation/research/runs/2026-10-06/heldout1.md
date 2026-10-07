# Heldout check 1 (run 37554279823, 2026-10-07)

Cases: nu metu sabanci charles masaryk tum tartu polimi vilnius; all rules at
their defaults on `claude/greeting-16wj2z` (RL-1 on). Labels are not needed:
DoD target 6 compares core coverage (core questions any prediction answers).
The job hit its time limit during the last repetition (masaryk rows read
CAPTURE_IN_PROGRESS); every case has two complete "on" repetitions.

| case | programme page | core | note |
|---|---|---|---|
| charles | no | 0/6 | wall-clock budget exhausted in discovery |
| metu | no | 0/6 | wall-clock budget exhausted, 0 queries sent |
| nu | no | 0/6 | wall-clock budget exhausted |
| masaryk | no | 0/6 | cut by the job time limit |
| polimi | no | 0/6 | |
| vilnius | no | 0/6 | |
| sabanci | no | 1-2/6 | deadline (and GPA once) |
| tartu | yes | 0/6 | |
| tum | yes | 0/6 | programme and language only |

Core coverage: heldout 5/216 = 2.3%; cohort (rl1 on) 12/60 = 20%.
**Target 6 not met** (gap about 18 pp, limit 15 pp). The dominant failure is
discovery (7/9 without a programme page), not extraction. Per the DoD, rules
are not tuned on these cases; the finding goes to the owner.
