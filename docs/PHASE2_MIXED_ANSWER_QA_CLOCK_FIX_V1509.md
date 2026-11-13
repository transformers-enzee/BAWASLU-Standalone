# BAWASLU v150.9: Rolling QA fixture clock correction for v150.8 release

The v150.8 mixed social/PDF legal safeguard tests passed, but one unrelated management-report integration test failed. Root cause: dataset() creates real-time case assignments, while the monitoring opt-in test passed a frozen 2026-11-12 NOW to the reporting query. After the CI runner crossed into 2026-11-13 UTC, fresh fixtures were later than that frozen end time, so the production query correctly returned zero assignments and the test incorrectly expected two.

The test now uses the current UTC clock for its live-created casework fixture. Tests deliberately validating a fixed publication window still use their frozen NOW/START timestamps. No production management-reporting changes, new database actions, paid AI calls or social crawls. Release remains staging-only with sequential build v150.9.

The v150.8 functionality remains: a twelve-unique-source citation cap enforced in both visible text and metadata; independent-clause legal certainty checks; and review-reason reconciliation for mixed social/PDF evidence.
