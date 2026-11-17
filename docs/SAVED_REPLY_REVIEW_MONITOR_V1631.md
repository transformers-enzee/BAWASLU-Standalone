# v163.1 Review monitoring and audit-event integrity

The existing owner-only saved-reply review listing reports bounded effective progress states, stale historical replies and *current* evidence-checked completion counts. An edited, missing or ineligible saved reply returns an effective RECHECK_SAVED_REPLY state and is excluded from current completions; original audit events remain preserved. Owner-scoped threads are loaded once per request to reduce database calls. The reviewer interface shows these counts and a read-only event timeline.

The update path captures the prior state before SQLAlchemy executes the versioned update, so append-only history records the actual transition rather than the newly synchronized state. No model generation, source excerpts, legal signoff, client acceptance, or new tables are introduced.
