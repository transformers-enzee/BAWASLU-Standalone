# BAWASLU v168.4 — Complete lifecycle parity and acceptance integration

The campaign assessment operations view now reconciles all five supported ordinary queue states: PENDING, PROCESSING, COMPLETED, FAILED and SUPERSEDED_ASSESSED. The interrupted view subdivides PROCESSING into stale/nonstale and FAILED into quarantined/ordinary, and those partitions are recomposed before cross-checking. Previously only three state categories were actually compared.

Additional checks ensure that each module's state totals reconcile with its ordinary-job inventory. Non-atomic independent snapshot semantics remain explicit, and a mismatch generates a no-credit SNAPSHOT_AGGREGATE_DRIFT review rather than a claim of corruption.

The overview now prioritizes active PROCESSING over pending queue status when neither condition has an exception. End-to-end SQLite integration tests create all five job states, a stale interruption, confirmed quarantine marker, and an isolated neighboring campaign; they verify that ordinary legitimate partitioning does not cause false review alerts and that genuine inconsistency does.

No budget reservations, provider calls, live Supabase writes or officer-record changes.
