# BAWASLU v150.3 - Legal enforcement recommendation caution

## Problem
The AI Assistant's legal QA check could return PASS when an officer-reviewed legal PDF was cited and the article number matched, even if the answer advised an immediate arrest, penalty or other enforcement action. PASS evaluated reference metadata, not case facts, legal force or who is empowered to act.

## Implementation
- Flag a narrow set of assertive English and Indonesian enforcement/penalty directives with deterministic language patterns.
- Do not treat an unambiguous question, negative recommendation or quoted source as a positive enforcement instruction.
- When flagged, append a bilingual enforcement warning to the generated answer and mark legal_uncertainty as REVIEW_REQUIRED, regardless of review-status of cited documents.
- Display a concise warning on the normal officer view and preserve expanded diagnostics only in administrator Development QA.
- Do not infer that an absence of flagged words makes legal conclusions true. This is lexical triage only; real legal interpretation remains human-approved.

## Limitations
No automated finding of wrongdoing, legal or platform-policy enforcement, casework writes, social crawling or new model usage. Some indirect enforcement phrasing may not match the narrow language patterns. Citation presence still does not validate current legal applicability.

## QA
Five deterministic new tests cover assertive English directives, Indonesian sanctions, ordinary review procedures, negations/questions and absence of legal evidence. Existing CI and Render staging are separate release gates.
