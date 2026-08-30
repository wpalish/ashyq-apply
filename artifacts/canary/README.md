# Canary raw output

The bytes behind every live-discovery number this repository states.

`HEAD.txt` names the commit the runs were executed at. `run1`, `run2` and
`run3` are three separate executions of `scripts/canary_discovery.py` against
the ten-institution registry; `holdout` is one execution against the frozen
six-institution holdout set.

`artifacts/release-evidence.json` records each file's path *and* its sha256, so
three runs cannot be confused with one file counted three times — the previous
artifact recorded only basenames, and all three rows were identical.

**What three runs establish, and what they do not.** The fetcher caches for 24
hours, so consecutive runs read mostly the same stored responses. These runs
therefore measure the *pipeline's* repeatability, not the network's: they show
that the same inputs give the same answer, and they do not show what a different
day's fetch would give. The digests being different while the numbers agree is
the whole of the claim.

`../canary-baseline-5679fb3/` holds the same four executions at the commit
before the extraction fixes, kept so the before-and-after is checkable rather
than asserted.
