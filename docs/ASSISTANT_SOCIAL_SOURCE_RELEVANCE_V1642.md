# v164.2 — Operational Social Listening evidence selection

The Assistant previously selected Social Listening posts using substring checks against a combined original-text/author/campaign/topic/candidate field and then awarded up to 14 ranking points for publication recency. This could admit a post that matched only a shared campaign label or an incidental substring, and place a recent metadata-only match before a source explicitly discussing the officer's question.

v164.2 applies whole-word matching using already-authorized posts. The original post body receives 20 points per distinct matching query term, while topic and actor metadata receive three points each; campaign names do not create topic matches because the campaign is already scoping the retrieval. Publication recency adds at most three points and only when the question does not expressly include a year. Missing, irrelevant, or contentless posts remain excluded, identical source IDs across campaigns are deduplicated, and named SOCIAL IDs retain strict complete-selection rules.

Broad narrative/sentiment questions continue to obtain a bounded starting sample when the question has no literal topical hit. These are **not** population-level measurements. No new DB requests, additional AI calls, changes to stored posts, permissions, staging schema or administrator QA screens were introduced.

Automated regression covers direct versus metadata-only ranking, campaign-label false positives, substring false positives, source eligibility, actor signal matching, hyphenated geographic references, deduplication, broad analytic fallback, and strict named-source authorization. Live officer answer quality remains a separate acceptance check.
