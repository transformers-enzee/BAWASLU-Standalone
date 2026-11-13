# BAWASLU v151.0 — Officer next-step guidance for AI legal triage

The AI Assistant already identifies source and legal uncertainty, but its warnings do not guide officers through a coherent evidence-check sequence. This batch adds a read-only, bilingual officer review checklist generated from the deterministic source audit. The list is displayed collapsed beneath the existing source-caution message; the user can expand it without entering QA development forms.

Steps are produced only for relevant conditions: inspect cited social post context, recheck missing/omitted citations, match article references to cited PDF pages, request review of unreviewed PDFs, locate accessible legal references where absent, verify claimed verdicts against official records and confirm statutory authority before enforcement.

Every step's source_ids list is derived only from the displayed citations already selected within the officer's permission scope. Uncited, excess, invented, or inaccessible records are not reintroduced. Each step is marked NOT_STARTED, officer_action_only=true; the audit explicitly marks legal_action_ready=false. No backend mutation endpoint, workflow approval or casework record is triggered by the checklist.

Six deterministic regression scenarios cover mixed references, unreviewed documents, article mismatches, citation overflow, no-evidence directives and neutral procedural statements. Existing QA and Render release gates remain required. No paid model calls, social crawls, Supabase writes or legal adjudication.
