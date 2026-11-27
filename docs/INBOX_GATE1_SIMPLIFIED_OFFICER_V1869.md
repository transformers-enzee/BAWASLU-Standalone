# BAWASLU v186.9 — Human Gate 1 simplified officer experience

## Primary change
The Human Gate 1 user-facing pilot on **Politik Uang / campaign 9** now has exactly two operator actions: **Review & Correct** and **Add Missing Evidence**. Technical audit, Gate 2 readiness and feedback panes remain accessible but are collapsed by default on this real-data QA pilot. The synthetic QA pilot retains its previous controls.

## Review & Correct
- Before editing, the UI shows up to three **heuristic quality hints from saved fields**. These are not fresh LLM judgments, confirmed inaccuracies or provider re-fetches. No API credits are used.
- Choose any source, AI-assessment, data quality, relevance or sentiment field through **one selector**. The original and current QA-only values appear side by side.
- For an ordinary correction, enter a new value and press **Save correction** or **Save & Next**. The UI fills its required audit explanation automatically as a **system-generated administrative note** expressly stating the field is not independently verified. Both the original provider value and canonical AI assessment remain unchanged. An optional section allows an officer to supply a rationale, reference link or source-confirmation claim.
- Missing values may be marked **Information unavailable** rather than fabricated.
- Identity, incident location, potential election issues, source URLs or source text are high-impact. These require a meaningful explanatory note and a separate authorized officer's approval before whole-record OFFICER_VERIFIED is permitted.
- **Correct another field** queues more edits but is never mandatory for a single correction. The final batch is audited append-only with optimistic revision matching and provenance.
- For routine content already correct, **Looks correct · Approve & Next** records an officer information-review decision. It never verifies a legal allegation, publishes to Command Centre or trains AI. **Hold for verification** is available; Exclude requires a specific reason.
- **Save & Next** moves to the next item in the currently loaded filtered review queue, when one is present. It does not silently submit another record.
- A reviewer's approval buttons appear only if the signed-in officer has the independent-review permission and did not author the latest high-impact edit. Backend rejects self-approval regardless of UI.
- Full revision and audit history remains under one collapsible detail control.

## Add Missing Evidence
- Officer supplies **source URL, text/description and platform**. Other details are optional.
- The system generates an administrative intake note if no additional explanation was entered.
- Manual intake remains an **unverified QA-only proposal** in the AuditEvent ledger, not a new Social Listening post and not eligible for direct publication.
- The original Social Listening API payloads are never rewritten, and no recrawl is executed.

## Governance limits
This release changes the officer UI and one read-only reviewer capability flag. It does not add a migration, amend shared Supabase data during deployment, enable automatic learning, or expose QA corrections to Command Centre.
The API continues enforcing campaign 9 name + DRAFT status, active officer grants, geographic scope, original-source digest, immutable AI assessment ID, source link isolation, revision conflicts, and independent high-impact review. All QA changes are append-only audit records.
A system-generated audit note is *not* evidence verification; source-confirmed status still requires a real supporting URL.

## Manual QA after deployment
1. Sign in using existing BAWASLU admin. Open /inbox?gate1=1&campaign_id=9&result_id=1909.
2. Verify only **Review & Correct** and **Add Missing Evidence** show as primary choices; technical pilot section is collapsed.
3. On a routine field such as Language, change value and select Save correction without additional required forms. Confirm original preserved and new value in QA-only history.
4. Select candidate_names, see high-impact rationale prompt and second-officer approval requirement. Use a fictional QA-only correction, not an allegation.
5. Click Add Missing Evidence: enter a safe test URL (example.invalid), description and platform; confirm unverified QA status without creating a Social Listening record.
6. Click Looks correct · Approve & Next only for a record the officer actually reviewed. Verify the next loaded evidence selected and no Command Centre publication.
7. Confirm feedback and Gate 2 readiness remain in collapsed advanced sections and campaign 9 remains publication-blocked.
