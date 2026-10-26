# Shahrin reference-assisted QA on architecture-v2

The live runner is `backend/app/smart_radar_qa_tuning.py`, not the older `main`-branch QA placeholder.

This change adds an **explicit checkbox on new prompt versions**. Existing versions including V9 are immutable and use their historical static examples. New versions saved with the checkbox carry a `[shahrin-ref-v1]` marker in their `change_note` and use the private SQL retrieval routine during paid assessments.

## Lifecycle

1. QA administrator creates a new version in the workbench, opting into Shahrin references.
2. The run action keeps the existing maximum three assessments per request, lifetime budget, opt-in click, no automatic retry, and failure recording.
3. Before registering each billable attempt, the runner retrieves up to three safe examples from `pilot_smart_radar.qa_shahrin_examples_for_post`. The existing protected exemplar cohort is cross-checked again.
4. The exact reference excerpts and human labels are supplied as *untrusted example data* for the specific target. The target human label, QA IDs, and provisional raw category never enter the model request.
5. Results are stored under the **new prompt version** with the reference revision, IDs and fingerprint in `result_json`. The usual prompt/source/model cache and validation remain unchanged.

## Existing database dependency

The private helper function and exemplar table are already present in the pilot Supabase schema. The backend's database connection must have permission to invoke the function; the browser cannot. No public or authenticated direct database grants should be added.

This code does NOT enable automatic paid assessment, make live classification claims, or trigger any AI calls on page load. It does not deploy officer-facing intelligence logic.

## Verification

From `backend/`:

```bash
python -m pytest -q tests/test_smart_radar_qa_references.py tests/test_smart_radar_qa_tuning.py
```

Also run your existing CI QA regression workflow. Enable one new reference-assisted version only for a controlled, human-initiated test, not for historic V9 rows. The standalone `main` branch PR #4 remains separate and should not be merged into this branch.