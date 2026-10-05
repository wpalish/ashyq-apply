# Attribution correction for the original runtime audit

The original audit uses "Owner design preference" / "owner-preferred" for the
persistent per-case worker. This direction was selected prospectively by the
root engineer, not specified by the owner. The owner's actual fixed method is
60 reads/6 queries, default model effort, a 900s expert guard and a 120s algorithm
budget. The original note is preserved unchanged; this correction supersedes
only that attribution. No runtime adapter or tests were implemented or executed.
