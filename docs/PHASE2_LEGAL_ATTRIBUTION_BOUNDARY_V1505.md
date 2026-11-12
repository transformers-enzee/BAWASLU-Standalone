# BAWASLU v150.5: Bulk QA follow-up and attribution boundary corrections

Why this patch exists: CI on v150.4 found three regressions. A named legal article with a valid standalone citation immediately after the sentence was incorrectly flagged as unattributed (two existing tests); splitting reported speech on commas also erased the quote attribution.

Fixes:
- Treat a following sentence/line consisting exclusively of authorized PDF citation tokens as a continuation of the immediately preceding article-level sentence. Do not borrow citations from unrelated narrative text, unselected DOC IDs or social source cards.
- Only split enforcement checks on independent statement boundaries (sentence breaks, but/namun/tetapi and semicolons), not ordinary commas inside "According to reports, ...". A separate positive instruction after "but" is still flagged.
- Avoid a contradictory client warning: a PDF claim that is merely unattributed gets the specific attribution warning, not the separate "article was not found" warning unless that mismatch actually occurs.
- Add five regression scenarios covering the above boundaries. The original v150.4 safeguards and casework rules remain unchanged.

No paid AI, social crawl, Supabase mutation, production deployment, legal determination, officer scoring or auto-enforcement. Version 150.5; staging only; full CI and Render verification required.
