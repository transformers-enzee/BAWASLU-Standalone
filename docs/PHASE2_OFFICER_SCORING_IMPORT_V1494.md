# v149.4 - Human Review Scoring Import and Direct Answer Review

The scoring file picker accepts only BAWASLU_ASSISTANT_REVIEW_V1485 answer-evidence packets, not the v148.8 question plan, v148.7 human aggregate or chat-history export. The previous generic schema error lacked recovery instructions.

This release provides specific errors by file type and a Score this answer button beneath fresh Assistant responses, eliminating export-reimport for same-session reviewers. Independent reviewers may still use original exported JSON packets. The original packet fingerprint and required four-dimension validation remain unchanged.

No paid AI call, database write or review-score generation occurs on scoring button click. Authenticated officer approval and legal-currentness review remain separate human gates. CI, Playwright, security, build version and exact Render staging deployment are release acceptance conditions.
