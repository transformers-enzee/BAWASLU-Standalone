# BAWASLU v149.6 — Officer AI Assistant and Development QA separation

Staging: architecture-v2-foundation-20261015; no production deployment.

- Normal users see answers, authorized evidence cards and concise source-verification warnings, not detailed AI evaluation metrics, scoring forms, review packets or question sampler.
- A collapsed **Development QA tools (administrators)** section retains all three review workflows for active National/Provincial Administrators with both view_intelligence and administration permission. Demo sessions never show QA tools.
- Administrator answer-level diagnostic blocks and packet exports appear only while the internal QA panel is expanded. The original QA computation remains unchanged.
- The simplified officer message still distinguishes contextual source cards from actual citations and notes unreviewed PDF / unverified legal currentness.
- No Supabase schema changes, database writes, crawling, paid model invocations, new navigation modules or user acceptance claims are introduced.
- This role gate is a presentation rule, not a new backend authorization boundary. Existing API permissions must be audited separately if QA endpoints require server-side admin restriction.
- Includes new static and browser checks. The real officer review, source approval and legal PDF currentness gates remain pending human acceptance.
