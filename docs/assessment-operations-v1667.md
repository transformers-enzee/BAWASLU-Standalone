# v166.7 — Safe live operational status across campaign switching

The unified assessment operations view introduced in v166.6 combines several independent database queries. A single response is not a transactionally consistent point-in-time snapshot, especially while background jobs are running. The read-only response now includes a UTC generation timestamp, `snapshot_is_atomic=false`, and explicit `lifecycle_status` values: REVIEW_REQUIRED, AWAITING_PROCESSING, PROCESSING or NO_EXCEPTIONS. A pending queue is not presented as complete work.

The campaign dashboard panel resets upon campaign selection change, remounts with a campaign-specific component key and ignores late API responses from the previous campaign using both request tokens and campaign-ID guards. It displays the timestamp and non-atomicity note, and continues to fetch these heavier aggregates only when opened.

No AI providers, crawlers or database mutations are triggered. Existing campaign authorization is unchanged. Synthetic regression QA covers pending-only, unqueued, empty and frontend race protections.
