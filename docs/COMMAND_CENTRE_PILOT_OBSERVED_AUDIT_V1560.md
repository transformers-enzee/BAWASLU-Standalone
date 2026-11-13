# v156.0 Bounded, authorization-scoped observed casework stages

The unsigned officer acceptance worksheet now distinguishes stages observed in actual existing casework audit events from those not observed. Only visible active cases whose saved Inbox source also passes current eligibility are queried. One bounded SQL window retrieves at most 200 transitions per visible case, and another fetches its latest report. The existing _acceptance_trace logic determines source-link, receiving officer acknowledgement, original-source review, report submission and independent approval observations.

A stage's 'completed' flag remains false, because evidence observed in casework does not constitute formal client acceptance or independent pilot signoff. Source unavailable or case not visible means no case-specific audit observations are disclosed. Truncation is indicated. Bilingual UI retains human verification caveats. No schema migration, new cases, approvals, AI calls or paid crawl.
