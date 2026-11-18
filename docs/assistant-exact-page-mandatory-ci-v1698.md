# v169.8 — enforce exact-source citation QA in the deployment gate

The Docker build now executes `test_assistant_source_guards_v1489.py` and `test_exact_pdf_page_grounding_v1500.py` alongside the established source-grounding regression suite. This specifically gates missing named social IDs, missing or withdrawn PDF pages, mixed-source page substitution, and page-level authorization on every Render staging deployment. No paid AI provider calls or live database changes.
