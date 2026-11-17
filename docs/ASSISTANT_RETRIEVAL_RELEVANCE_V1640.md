# v164.0 — Operational Assistant evidence relevance and scope

Formal Inbox retrieval selection now matches whole topical words, not arbitrary substrings of combined source and workflow-status text. Title and original content receive stronger matching weight than geography, actor/source metadata and human-approved triage fields. Officer review status and verification status remain separate filters; their text cannot alone make a record relevant to the question. Date windows, high-priority ranking, ownership and jurisdiction authorization remain unchanged. No additional database retrievals occur.

The existing Assistant prompt now explicitly distinguishes selected-source counts from all campaign data, incident prevalence and independent witnesses. It instructs the model to cite material source records and propose specific checks when evidence is missing, instead of asserting unsupported legal or social-media policy findings.

This work makes no model calls in the ranking step, no DB changes, no new QA screens and no additional provider requests. Regression tests target false-positive substrings, status-only matches, prioritization versus recency, valid date/review filters and scoped answer limitations.
