# v163.4 - Authorized pilot review handoff

The existing owner-scoped, bounded pilot queue now has a read-only handoff endpoint. It computes deterministic operational buckets for awaiting review, under review, blocked, stale/recheck required, ineligible, follow-up required and evidence-checked no-action proposed. The export returns only saved thread IDs, reply positions, reviewer IDs, review versions and timestamps, bucket/status and attestation-current indicators. No answer text, question text, source excerpts, URLs, new model calls or database writes.

The handoff covers at most 40 recent owned threads and 120 saved replies; it is not a comprehensive historical census or representative accuracy evaluation. An evidence-checked FOLLOWUP_REQUIRED record is NOT considered an accurate response or a corrected issue. Stale fingerprints override prior evidence checked status. Live evidence source authorization remains necessary at actual audit. Export and queue require active reviewer permissions; formal legal signoff and BAWASLU acceptance remain separate.

Automated regressions verify ownership, no writes, stale overriding follow-up, ineligible records, and no inferred verdict.
