# BAWASLU v179.8 — AI-5 document visual-QA completion

Build v179.7 introduced broad-scope research and a PDF with headings and clickable source citations. Visual review of a representative seven-country, four-column PDF identified a large leading blank page caused by keeping the section heading together with the entire long table. The retained table heading no longer forces the full table onto the next page. Normal English word wrapping replaces CJK wrapping for prose/table text, reducing broken words.

This bulk follow-up also adds source-title/date hyperlinks throughout editable Word output (including tables), and readable source titles plus clickable links in the Excel Sources sheet. Tests now inspect Word package relationships, Excel cell hyperlinks, PDF source annotations, and long-comparison first-page content. No external actions or data mutations.

Original attachment caveat: the pilot provided text with two AI-5 answers, not raw provider queries, authenticated research trail, model evidence payload or PDF. Reconstructing those exact historical calls remains impossible from that text alone. Deterministic tests replay the original question wording and an unrelated question with mocked evidence. Final live UAT must compare authenticated staging chat and PDF after deployment.

Branch architecture-v2-foundation-20261015, Docker build 179.8. Expected staging image after verified GitHub Actions publication: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-179.8`. Production and Supabase records remain unchanged. Manual Render deployment only after user saves the image and replies Saved.
