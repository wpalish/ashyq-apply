# G3 focused route repair1

External root-authored source repair; NOT_APPLIED / NOT_RUN.

The evidence metadata query projects three FK-bearing run_id inputs. Its implicit ResearchRun join is ambiguous before the preview source bundle and is converted into safe source_unreadable/saved_unreadable. Explicit ProgramResultRow anchor and ResearchRun ON preserve the complete selected columns, both aggregate outer joins, owner/selected filters, ordered results and all source/proof guards. The 38 grouped previous failures are a source-supported attribution, pending actual repaired execution.

Unexpected SQL failures now return write_unconfirmed503 after the identical rollback and exact own UUID reconciliation. Explicit expected-revision/CAS ActionError409 remains untouched. The native fresh strong parent fence serializes legitimate writers; arbitrary integrity/trigger errors cannot imply that someone else changed the case. Existing SQLite/PG trigger rollback, same/different UUID and actual-writer controls remain unchanged and must execute. No message or original SQL input is returned.

Exactly three literal changes, including removal of the unused import/exception binding, invert to the full exact original route. No domain/schema/native other test/config change.
