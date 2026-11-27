# BAWASLU v186.8 — Full data validation, correction and enrichment at Gate 1

## Audience and scope
This release extends **Politik Uang / campaign ID 9** controlled QA only. The existing officer account and 128 source links remain in the shared Supabase database. All changes are appended to the existing `audit_events` table; no `social_listening_results`, `evidence_assessments`, `officer_sentiment_corrections`, Command Centre, or publication records are rewritten. Changes in the QA workbench do **not** become operational information outside Gate 1.

## Workbench categories
- **Source data:** platform, content type, author identity, handle, post date, original source URL, text, language, transcript, translation, country, province, city, location basis, incident date, likes, comments, shares and views.
- **AI assessment:** candidate and party mentions, organizations, topics, public concerns, narratives, possible issue categories, explanations and geographic context. Relevance and sentiment continue through the existing v186.7 field selector.
- **Data quality:** completeness, provider-fetch status, missing fields, discrepancies, duplicate-reference, verification gaps, and officer notes.
- **Missing-source intake:** create a *separate unverified QA evidence proposal* when API providers omit a source. Requires a source/supporting URL; does not create a new Social Listening record. No binary files are uploaded in this batch.

Each batch of up to 15 corrections captures field, previous and proposed values, correction mode, verification level, supporting URL, field-specific reason, overall reason, officer identity, timestamp, immutable saved-source SHA256 digest, expected assessment ID and optimistic revision. Verification levels distinguish UNVERIFIED, OFFICER_SUPPLIED, and SOURCE_CONFIRMED, with supporting URL mandatory for source confirmation.

## Independent review
High-impact identity, geography and possible-violation edits require another authorized administrator. The same officer who wrote the latest batch cannot approve it. Gate 1 OFFICER_VERIFIED is disallowed while its secondary review is pending or rejected. Review status becomes stale on subsequent edits, even if the saved evidence is unchanged. Gate 2 is always BLOCKED on campaign 9 by QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION.

## What is explicitly NOT done
- Does not amend provider records, raw payloads, AI assessment rows or other campaigns' metrics.
- Does not call paid AI, social-provider APIs, recrawl an external URL, train models, publish insights, or export manual proposals.
- Does not upload image/document binaries. Source and supporting URLs plus plain text are supported.
- Does not roll out full-field review to operational campaigns. A separate downstream effective-information integration and official authorization process will be required for that.

## Activation and QA
No new Render environment variables are needed beyond the v186.7 Campaign 9 setup. Release remains opt-in for Campaign 9 with the existing `BAWASLU_INBOX_GATE1_REAL_QA_CAMPAIGN_ID=9` and companion flags.

After GitHub CI passes and the user updates the Render image:
1. Open `/inbox?gate1=1&campaign_id=9&result_id=1909` with the existing main admin.
2. In the new Full data validation & enrichment panel, inspect source/AI/quality field tabs and compare original with effective values.
3. Add a safe text or metadata change with a field reason. Add a second field. Save both as one audited batch.
4. Confirm original provider and AI labels unchanged, effective QA fields visible, revision history readable.
5. Try a sensitive field such as country or candidate names: secondary reviewer required, same officer cannot self-approve.
6. Test Missing-source intake with fictional text and example.invalid links. Confirm UNVERIFIED status, no Social Listening insertion, and no Command Centre publication.
7. Confirm a different campaign stays read-only and Gate 2 always stays blocked.
Automated checks use only disposable local PostgreSQL 17 and intentionally avoid any shared Supabase writes.
