# G2 recovery final-v1 design peer close-out

2026-10-12 · **READ ONLY / DESIGN ONLY / NOT APPLIED / NOT RUN**

Reviewed sealed `G2_RECOVERY_DESIGN_FINAL_V1.md` SHA-256 `beeb82cf7b2ffacb0c62f6dfab87919b6eb3e10e369b7a09f4cd7bb0544e8f2d`, seal `6e0d2cfa6e5da814a8aa47b606635bb125405cd1b1c44e7a273f59444ba474b8`, and authoritative root reconciliation `G2_RECOVERY_WRITE_AHEAD_RECONCILED_V1.json` SHA-256 `8847adcc9cae7cd87ab3d91d72b94f59cfae86dc64e24d84340d2c5ca98d97bf`. The earlier mutable 5da0… draft has an exact preserved copy. The first fde0… draft bytes were not retained; no equivalence to them is asserted.

**Disposition:** Prior F1 is closed as an authoritative design constraint: all meaningful unsaved draft **or** pending state guards voluntary screen, case, hash and unload changes even when a session journal write succeeded. Security owner transition still immediately unmounts private state. The final document also distinguishes a failed initial journal write (`not_sent`, no PUT) from a failed later write after dispatch (outcome remains uncertain), and forbids automatic replacement/deletion of a malformed or foreign envelope. Exact UUID/body reconciliation, one bounded history GET, current owner/case/draft compare-clear, public pre-auth legal and authenticated App legal remain specified.

The inherited draft paragraph about allowing navigation after successful persistence and its 12-path table remain visible as history; the final file explicitly makes the root resolutions and 15-path allowlist authoritative. The source packet must follow those final sections. The design seal is not application integration, fresh frontend gate or browser persistence proof.
