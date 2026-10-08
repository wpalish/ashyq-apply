# Owned preview preparation — saved-only review

B final static ACCEPT binds guarded helper f753a15fbc65e43329682895e7462330038500fa3fc97e450771dbfa710fbad2. Helper runtime is NOT_RUN at this checkpoint; source/cleanup outcome needs actual execution.

Old preview_recovery.py was rejected before execution: no STOP guard, snapshot not bound to applied source, resume could mutate an existing DB, cleanup did not wait. The guarded replacement is a distinct file; no old source is overwritten. Second saved review required hash-bound summary.source equality and failure-safe per-child cleanup/group observation; both corrected before use.

Current helper requires two actual passed own core/full records, passed13-stage full and hash-bound summary/source map, applied HEAD and16 current source pins, STOP, a fresh allowlisted20-result DEMO clone, none provider/authfalse/noWorker, and held shared runner lock. Cleanup tries all owned groups, records errors, verifies STOP/ports before normal unlock. Original seed bytes are checked unchanged. No primary database/runtime/real applicant/production write is permitted by this plan.

Queue race between free-check and native lock acquisition is fail-closed: approved runner acquires its own lock or returns2 without running. It never bypasses locking or kills another checkout. Original complete native console logs are saved separately; first doctor lock refusal was not a check failure or provider/model refusal. Copied helper/provenance files are not tests or experiments.
