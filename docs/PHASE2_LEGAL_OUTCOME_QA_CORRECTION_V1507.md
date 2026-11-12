# BAWASLU v150.7 QA Correction

The initial v150.6 CI suite identified a wrong test expectation for a neutral procedural answer: legal_uncertainty is NOT_APPLICABLE when no legal conclusion is being evaluated, not PASS. The test now respects the existing rubric.

The same release tightens the human-review flag for definite legal verdicts or enforcement directives when zero evidence records were retrieved; a categorical legal claim must still require human review even when no source card exists.

No database migration, Supabase write, social crawl or paid AI request. Sequential staged build v150.7; exact GitHub CI and Render deployment verification required.
