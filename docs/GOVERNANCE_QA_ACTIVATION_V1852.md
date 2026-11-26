# BAWASLU v185.2 — Administrator-only read QA isolation

- Latest staging baseline v185.1, Render staging only; no changes to Supabase schema or officer/source records.
- `BAWASLU_GOVERNANCE_QA_READ_ENABLED=true` activates admin QA campaign listing and scoped Gate 1/Gate 2 summaries. Every QA endpoint checks both `administration` and `view_intelligence` and geography scope.
- The normal Inbox and Command Centre remain controlled by `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED`, which can stay false.
- The general governance review-queue route remains closed to ordinary officers when the general integration flag is false; in QA-only mode it is restricted to administrators.
- Writes remain gated by `BAWASLU_GOVERNANCE_WRITES_ENABLED`, pilot mode and campaign allowlist; keep these off.
- The Gate 1 QA selection now samples each present category (unassessed / uncertain / excluded / relevant / unexpected) fairly from the 120 most recent authorized ordinary campaign evidence links. Counts are still strictly scoped sample counts, not population totals.
- Before user-facing manual QA, deploy to staging, activate only the QA read flag, verify admin, non-admin and out-of-scope behaviors using the actual authenticated app, and confirm no paid AI calls or record mutations.
