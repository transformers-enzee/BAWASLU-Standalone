# v171.6: consolidated administrator processing preflight

Bulk staging improvement to cross-check historical-usage uncertainty, audit
availability, snapshot reliability, unknown exceptions, queue reconciliation,
and the legacy manual processing preflight before displaying an advisory
capacity figure.

The consolidated gate is **never authorization** to run AI. Its only positive
state is `PREFLIGHT_ONLY`. It returns zero displayable capacity whenever
a diagnostic safeguard or the original preflight is blocked. The original
capacity remains available as diagnostic data, clearly labelled as such.

No Supabase schema change, database write, automatic retry, quota reservation,
or paid provider call is introduced. Officer records remain unchanged.

Regression coverage: `backend/tests/test_assessment_review_gate_v1716.py`
and `frontend/scripts/test-assessment-review-gate-v1716.mjs`.
