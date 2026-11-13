# BAWASLU v151.4 — Legal reference eligibility in officer review

The existing evidence-coverage labels treated any uploaded PDF as a legal source. A cited report or general internal document could therefore result in LEGAL_REFERENCE_CITED_UNVERIFIED, even when no regulation, SOP or guidance page was provided.

Changes:
- Differentiate all cited PDF pages from legal-reference candidate pages classified REGULATION, SOP or GUIDANCE. Classification is only an eligibility hint, not confirmation of authenticity, authority, applicability or legal currentness.
- Return LEGAL_REFERENCE_NONLEGAL_PDF_ONLY when a legal question has PDF citations, but no cited page of an eligible document type.
- Request an authorized legal source in the read-only officer checklist when only nonlegal PDFs appear; do not use a nonlegal PDF as the citation target for an article-level matching step or as a basis for enforcement review.
- Keep the real cited PDF page count and show a bilingual officer warning when all cited PDF pages are nonlegal.
- Add six deterministic regression cases for reports, false article matches, guidance, mixed reports with unreviewed regulation, nonlegal enforcement citations and mixed eligible/ineligible documents.
- No actual authenticity validation, legal determination, database writes, migrations, paid AI, crawler or production promotion.

Staging branch architecture-v2-foundation-20261015; sequential build 151.4.
