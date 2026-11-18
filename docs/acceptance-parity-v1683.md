# v168.3 — Operational cross-aggregate parity and safe preview instructions

The on-demand status overview now compares already-fetched worker, completion audit, interrupted-job and superseded counts, without running additional database queries. Disagreements surface a SNAPSHOT_AGGREGATE_DRIFT history-review warning. As counts originate from independent reads, one mismatch is not conclusive database corruption; refresh and investigate persistent divergence.

The resolution checklist now includes the exact dry-run payload for campaignAssessmentJobReconcile. That endpoint can write jobs if called without `dry_run:true`; showing only its name as a read-only preview was misleading. No automatic preview or database write occurs. Existing campaign authorization and explicit paid-AI approval remain unchanged.

Synthetic regression covers aggregate parity, mismatching snapshots, fail-closed acceptance, dry-run argument disclosure and zero additional DB reads.
