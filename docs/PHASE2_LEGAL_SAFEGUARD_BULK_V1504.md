# BAWASLU v150.4: Bulk legal attribution and conservative enforcement gate

Problem and implementation:
1. Sentence-wide negation or quoted text could suppress a later, independent penalty/enforcement directive. Split statements into bounded clauses (punctuation and but/namun/tetapi), so each clause is assessed separately. This is lexical triage, not legal intent detection.
2. The v150.2 sentence check tested legal articles *against nearby cited pages* when a citation was present but did not warn when a legal article statement had no PDF citation in the same sentence, even though the answer cited a PDF elsewhere. Mark such article statements as unattributed, show a user warning, and require human review. It is a review signal, not proof that a claim is false.
3. The legal readiness check could pass when an answer cited one officer-reviewed legal PDF and one unreviewed PDF. Mixed cited review status now forces REVIEW_REQUIRED, even when the reviewed PDF supports another article.
4. Preserve ordinary procedural advice, user questions and negated language; add dedicated regression cases to prevent false positive changes. The three new grounded warnings appear in the officer UI without exposing development scoring forms.

Limits: no production promotion, new DB calls, Supabase mutations, legal enforcement, provider calls, paid AI runs or crawls. Existing article checks are lexical and heuristic, and official legal currentness remains unverified. Reviewers still need to verify legal applicability, evidence, authorization, and real-world enforcement decisions.

Staging: architecture-v2-foundation-20261015; version 150.4; five CI jobs plus exact Render deployment gate.
