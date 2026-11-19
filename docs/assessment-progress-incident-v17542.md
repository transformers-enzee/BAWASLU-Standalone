# v175.42 — Assessment progress and worker readiness incident

## What was observed
- UI: “Assess all”, 334 queued, 0 processing/completed, no verified throughput, status refresh errors
- Render: PostgreSQL GroupingError in read-only `campaign_completion_audit`, triggered by `assessment_operations_overview`
- The shared-database staging image has `BAWASLU_STARTUP_READ_ONLY=1`. This skips automatic startup work **including the optional AI screening worker**; it is not proof that a previously queued provider request is safe to replay.

## Fix
Aggregate the latest model-version histogram by the actual SQL column `model_version`, rather than repeating parametrized `coalesce(nullif(...))` expressions as both SELECT and GROUP BY. Merge empty and null values into the existing UNSPECIFIED bucket in Python. The query is read-only and does not spend AI credits.

## Deployment and operations gate
- Build and validate version v175.42; do not enable workers or trigger model requests automatically.
- Refresh **status only** after an approved staging deployment.
- Independently examine queue states, last update timestamps, background-worker readiness and provider usage before any assessment replay.
- Because staging shares the main Supabase project, do not enable the worker or process 334 queued posts without explicit credit/budget approval and a carefully reviewed isolation plan.
- Do not treat queued or active status as completed, or infer model charges from a progress bar.
