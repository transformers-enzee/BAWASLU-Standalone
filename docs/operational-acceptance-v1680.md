# v168.0 — Assessment operational acceptance preflight

A read-only campaign operational acceptance decision now collects existing assessment exception flags, pending eligible work, quota capacity and provider configuration. The status separates HOLD_FOR_HISTORY_REVIEW, HOLD_FOR_QUEUE_RECONCILIATION, NO_ELIGIBLE_WORK, CONFIGURATION_OR_BUDGET_BLOCKED and ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL.

Manual batch prerequisites are evaluated independently from disabled automatic-worker settings. The capacity estimate is explicitly not cost approval, and no provider requests, reservations, queue updates or credits are issued. A stale unknown-provider call or historical provenance gap takes priority over ordinary pending work. All status decisions use existing campaign-scoped aggregates, without extra database reads. The campaign dashboard presents the result on demand.

Synthetic QA verifies review precedence, missing work, worker-disabled manual eligibility, budget/provider blockers, 20-request manual cap and no-cost invariants. Existing authorization remains unchanged.
