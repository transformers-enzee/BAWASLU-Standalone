# BAWASLU v183.10 — Intelligence Inbox Human Review Centre

Release scope: **officer review navigation and discoverability**; no new database tables, paid calls, or new authority to approve legal findings.

## Existing actions reused
- Original social post and provenance stay visible, including a source URL when known.
- Saved AI relevance, topic, sentiment, candidate cues, and jurisdiction suggestions remain preliminary until independently checked.
- Existing audited actions are unchanged: sentiment override, officer topic/public-concern assessment version, province and Kabupaten/Kota jurisdiction review, preliminary violation-flag confirmation/dismissal/further investigation.
- Authorization and campaign scope checks remain server-side. UI prompts cannot expand an officer's permissions or turn an allegation into a legal verdict.

## New officer journey
1. Intelligence Inbox post list now shows a clear **Review AI Assessment** action on each saved post.
2. A simple **Awaiting officer review** toggle filters the **currently loaded deduplicated** items to posts with preliminary/pending flags, including further-investigation status. This is **not** a full-corpus count.
3. Review entry opens the larger **Human Review Centre** drawer. The review checklist links to six relevant existing sections: source evidence, AI suggestions, sentiment, incident geography, topics/public concerns, and preliminary violation flag decisions.
4. Officers save each review decision individually using the existing controls. Saved responses preserve the original AI assessment and audit history. There is no misleading one-click global approval.
5. **Full details** returns to the complete technical source assessment display. Officers without a specific review permission can inspect accessible data but cannot save prohibited decisions.

## Manual QA on staging
- Open Intelligence Inbox, select a campaign, and use **Awaiting officer review**. Verify the count refers to loaded posts, not all eligible posts.
- Click **Review AI Assessment** on an existing safe staging source. Verify the guided drawer, six jump controls and original source remain visible.
- Verify all six links navigate to their sections, including the human review actions.
- Use a staging test record only (not an active case) to submit a supported classification correction with rationale and verify the saved version and post refresh.
- Check role restriction: read-only officer cannot save protected flags, and a second officer without campaign access cannot open or review the record.
- Verify previously saved flag decisions remain visible after refresh, the audit history remains intact and no paid AI call occurs from review navigation.
- Verify switching to Full details, closing/reopening drawer, filters, pagination, and mobile layout.

## Known limitations
This release does **not** implement a single transactional approval for all ten assessment groups, full training-label curation, formal institutional adjudication or automatic downstream recomputation for every corrected variable. Existing supported officer corrections and saving remain independent. The full Human Review v2 data workflow remains a later implementation stage.

## Build requirements
The staging branch must pass full backend regression, frontend build and the new `frontend/scripts/test-inbox-human-review-v18310.mjs` gate before the immutable staging Docker image is handed off. Do not auto-deploy to Render.
