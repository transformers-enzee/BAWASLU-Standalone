# BAWASLU v150.6 - Categorical Legal Outcome Safeguards

## Identified gap
v150.5 checked source ID integrity, named articles and direct coercive instructions, but a model could still claim a candidate was guilty, an electoral violation was confirmed, or a penalty had already occurred without citing any article number or using an explicit enforcement instruction. Valid PDF IDs and officer-reviewed file metadata do not establish an official finding.

## Development
- Added conservative bilingual language-pattern detection for categorical statements of electoral wrongdoing, guilt/conviction and imposed legal consequences.
- Flag only assertive independent clauses, retaining the earlier clause segmentation. Negated, tentative, question-form and explicitly attributed quoted claims are not automatically treated as model-confirmed judgments.
- Mark the existing legal-uncertainty quality check REVIEW_REQUIRED when such a statement is present, including with a reviewed PDF and without any legal PDF.
- Add a concise bilingual source-verification caution in the normal officer answer UI; leave detailed scoring in Development QA.
- Retain citation filtering, publication-time semantics, human review, existing exact-PDF and article checks. No automatic modification of AI answer factual claims beyond appending a caution.
- Eight regression cases cover English and Indonesian assertions, hedges, reported speech, independent clauses, missing PDF authority and neutral procedure responses.

## Boundaries
Heuristics are incomplete: a match is not proof of incorrectness; lack of match is not proof of correctness. This does not adjudicate wrongdoing, verify legal effect, inspect real court records, create casework tasks or contact social media providers. No paid model usage, new database tables, Supabase migrations, additional crawls or production push.

Staging branch architecture-v2-foundation-20261015; next build 150.6. CI and exact Render release verification required.
