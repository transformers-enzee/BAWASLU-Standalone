# v158.7 — Independent acceptance readiness inventory

An **administrator-only**, read-only endpoint `GET /api/assistant-evaluation/acceptance-readiness?target=24` summarizes the count and coverage of the existing authorized source-linked Assistant review questions, includes the missing-source negative-control readiness flag, and provides counts from the developer-labeled synthetic legal-signal benchmark. It excludes post text, questions, source URLs, identities, casework and answer content.

It explicitly lists outstanding human actions: real model answer evaluation, independent legal-reference document version/currentness signoff, election-type applicability confirmation, missing-source negative-control review, and formal BAWASLU client acceptance. When the sample is too small, it adds a shortfall blocker instead of making up evidence.

The outcome is **preparation only**: no human ratings or legal determination can be inferred from synthetic passing tests. The endpoint uses existing permission-scoped Inbox access and no-store response headers, creates no database writes and consumes no AI credits. Formal signoff requires independently retained evidence outside this diagnostic endpoint.
