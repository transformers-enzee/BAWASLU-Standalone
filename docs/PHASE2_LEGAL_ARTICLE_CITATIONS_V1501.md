# BAWASLU v150.1 — Legal article citation triage

## Why
The existing Assistant verifies that source IDs are selected and authorized, but a real PDF citation can still accompany a fabricated or misremembered article number. An officer-reviewed PDF also does not prove current legal force or correct interpretation.

## Scope
- Detect explicit **Pasal N** and **Article N** in the original generated answer.
- Compare article numbers against only the **actually cited PDF page excerpts**. Uncited PDF pages and social source cards cannot satisfy this check.
- When the cited excerpts lack the named article, append a bilingual legal-source caution and mark the already existing legal-uncertainty diagnostic REVIEW_REQUIRED.
- Expose the warning in the ordinary officer view without showing development QA scoring controls.
- Never claim that a successful text match establishes the article's applicability, currentness, or semantic support.
- Preserve the authorized source audit, original answer, separate legal and platform policy checks, and officer approval requirements.

## Exclusions
No additional AI model calls, database writes or migrations, new crawler jobs, automatic legal decisions or bulk evaluations. This check is deliberately lexical and cannot evaluate legal reasoning. It is a reason to inspect an official source, not proof that the model is substantively incorrect.

## QA
Five new backend cases cover fabricated article numbers, text-present but unverified legal passages, missing citations, unreviewed PDFs and uncited unrelated pages. Use all existing CI checks, staging-only deployment and sequential build v150.1.
