# Offline institution directory

`python3 scripts/catalogue/build_directory.py` rebuilds the 500 identity records and the lightweight exact-name branding map from archived public inputs, reviewed identity overrides and completed image receipts. It makes no network requests. `python3 scripts/catalogue/verify_directory.py` verifies the count, unique identities, history/site references and all 500 chosen local image hashes against their receipts.

Public raw inputs are gzip snapshots in `inputs/` (deterministic gzip timestamps). The large source datasets are public university metadata, not applicant records. Individual history sources and image origins are exposed in the UI. Wikipedia-derived text retains article attribution/CC BY-SA; the 61 short editorial overrides cite institutional/public sources. Statistics are historical imports, not current admissions facts.

The 500 identity images comprise 492 official-site icons, two emblems and six institutional wordmarks. Some source icons are only 16 pixels wide. These are real identity assets, not a claim that 500 print-quality full logos have been licensed or that their current admissions requirements were checked. Images belong to their respective institutions. No generated replacement logos are used.

The collector scripts document this acquisition, but are not a refresh queue. Wikipedia metadata and later Wikimedia static acquisition each stopped on their first HTTP 429; do not rerun them or reconstruct missing response bodies. Completed receipts preserve successful image digests and the observed failures. The later official homepage, declared image and site-icon reads are separately recorded sources. Rebuilding from saved inputs does not retry any source.

The catalogue is available without invoking programme research. Explicitly checking selected programmes uses the existing research flow and its own authorization/provider boundaries. No applicant data is embedded in outbound university links.
