# v167.0 — No-credit queue reconciliation

Live Supabase evidence on 18 November 2026: campaign 4 has 70 PENDING jobs already holding latest RELEVANT/IRRELEVANT/UNCERTAIN classifications; campaign 2 has 29 genuinely unassessed PENDING jobs. Existing worker screening skips many already-assessed records, but their PENDING job states misrepresent processing demand.

An authorized read-only campaignAssessmentSupersededPreview action and an explicitly confirmed campaignAssessmentSupersededApply action now permit a bounded, idempotent transition of fully classified PENDING jobs to SUPERSEDED_ASSESSED. This is deliberately distinct from AI COMPLETED; it does not fabricate usage records, modify classifications or initiate provider calls. Race-safe updates revalidate the latest classification, campaign, state and watchlist exclusion. Audit/readiness counts track superseded jobs separately.

Deployment itself does not perform live reconciliation; human editor confirmation is separately required. Automated regression QA checks version precedence, no-cost operation, bounded repeat calls, campaign boundaries and truthful state counts.
