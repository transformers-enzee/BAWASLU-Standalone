# BAWASLU · ZocialEye and AI Assistant QA checkpoint — 19 November 2026

**Scope:** Existing BAWASLU campaign (ID 1), ZocialEye offline import `offline-xlsx-20261119-batch-%`, Assess All run #36.

## Verified database state
- Imported and campaign-linked: 434 unique ZocialEye source records; all have stored source text and canonical URLs.
- Completed GPT assessment jobs: 100; pending: 334; processing: 0; failed: 0.
- Model used in completed assessment rows: `gpt-4o-mini`.
- Completed assessment labels: 38 RELEVANT, 45 IRRELEVANT, 17 UNCERTAIN.
- Per-campaign AI reservation rows: 100 on 2026-11-19 (UTC), 144 total lifetime at inspection.
- The 334 pending jobs were not executed through this QA audit.

## Relevance explanation contradictions requiring review
A conservative read-only SQL review found **3 high-confidence IRRELEVANT posts with explanations denying electoral references despite explicit electoral references in the post itself**:
- Source 874 refers to *pilpres* and a vice-presidential candidate; explanation says it does not discuss elections or candidates.
- Source 883 mentions *capres* and Gibran; explanation says it does not discuss relevant electoral topics.
- Source 913 mentions winning *pilpres*; explanation denies election-related issues.

These are **QA flags, not automatic relevance corrections**. Political history, candidate mentions and electoral vocabulary do not themselves prove current-campaign scope or violations.

A broader lexical screen found 13 IRRELEVANT posts mentioning election terms, but does **not** establish 13 incorrect classifications.

## Implemented on isolated development branch
- Guarded import-specific CLI: `backend/scripts/resume_zocialeye_assessment.py`. Default is dry-run; actual assessment requires explicit `--execute --acknowledge-metered`, existing backend OpenAI credentials, DB access, and budget. Targets only pending jobs in run #36, does not requeue failed jobs or override classifications.
- Read-only contradiction flagger: `backend/app/assessment_qa_flags.py`.
- Five regression cases: `backend/tests/test_assessment_qa_flags.py`.
- More precise source-grounded screening prompt in `backend/app/auto_relevance.py`; explicitly separates election mention, campaign scope, historical relevance, and violation allegations.
- Separate GitHub Actions workflow: `.github/workflows/isolated-bulk-qa.yml` (CI status not confirmed).

## Automated QA performed
- Direct Supabase audit of imported posts, saved classifications, pending jobs and quota: successful.
- Five local deterministic relevance-flag tests: 5/5 passed.
- Backend integration tests, authenticated paid AI resume and live Assistant answer generation: **not executed** in this checkpoint.
- Source PDF library: one active 12-page sample simulation, unreviewed and not semantically indexed; 23 stored text chunks spanning all 12 pages. This is not a validated legal corpus.

## Deployment and safety
- No new Render deployments initiated by this checkpoint.
- `BAWASLU-Standalone` auto-deploy was verified **off** as of the latest service inspection.
- The isolated branch is not Render's deployment branch.
- Do not mark 334 pending jobs complete, bypass model budgets, promote Inbox cases, or change officer decisions based on heuristic QA.
- When credentials and a supported runner are available, perform an authorized dry-run and resume with the existing budget reservation worker; verify every committed result after each controlled batch.

## AI Assistant acceptance work still required
1. Live questions in Executive/Deep/Investigation depth and each supported language.
2. Full subquestion coverage without unsupported additions.
3. PDF page citations checked against exact indexed passages.
4. Separation of platform moderation vs election-law procedure.
5. Social Listening / Inbox source segregation, sample denominators and duplicates.
6. Report/PDF output consistency with generated answer, source citations and layout.

No claim of end-to-end Assistant acceptance is warranted until these tests run against the real authenticated application.
