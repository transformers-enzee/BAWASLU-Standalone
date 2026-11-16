# BAWASLU v159.3 — National Administrator acceptance review

The dedicated Acceptance Review page is linked inside Administration (not the main Intelligence navigation) and available at /administration/acceptance-review. Frontend access is limited to active nationwide National Administrators with administration and view_intelligence permissions; the v159.2 backend independently rechecks permissions. Demo replica mode never exposes the link or live API operations.

UI supports submitting bounded opaque evidence-reference IDs, refreshing recent submissions, independent review or revision request with explicit confirmation, status counts, and on-demand append-only audit history. A submitter cannot review their own submission. Status REVIEWED explicitly means "Evidence reviewed — not formal approval". API requests use the signed-in user's bearer token, same-origin host and no-store responses.

The UI is a governance tool, not part of ordinary officer casework, nor a BAWASLU-approved client or legal signoff. Real multi-administrator review and formal external acceptance are still pending, and no test records are created automatically by deployment.
