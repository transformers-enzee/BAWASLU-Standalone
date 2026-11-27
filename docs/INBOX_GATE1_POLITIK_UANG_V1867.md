# BAWASLU v186.7 - Politik Uang (Campaign 9) Human Gate 1 officer-override pilot

## Scope, source verification (read-only)
- Existing shared operational Supabase campaign: ID **9**, name **Politik Uang**, status **DRAFT**.
- As verified on 2026-11-27, 128 ordinary campaign evidence records, 236 saved assessment versions, zero shared source links to other campaigns, zero already promoted sources.
- The user explicitly identified this campaign as test-only. Other campaigns and official BAWASLU views must not accept QA correction writes.
- Do not seed or modify the real source records. Do not run paid APIs, training, or automatic Command Centre publishing.

## Implementation
- Allowlist is strictly checked server-side for name, ID, DRAFT status, officer role, geography, existing campaign edit permission, and two explicit QA opt-in flags.
- Every write rechecks that the source is linked as ordinary evidence, not cross-linked to other campaigns, and not promoted to official intelligence.
- Relevance and sentiment overrides are **append-only AuditEvent records** with the original AI assessment ID, SHA256 source fingerprint, officer, reason, and revision. They appear as effective values **only in Human Gate 1 QA views**, not the canonical EvidenceAssessment or OfficerSentimentCorrection tables.
- Review decisions and offline feedback triage are separately audited. A stale source or changed AI assessment invalidates effective QA revision and the review requires revalidation.
- Only a specific active admin officer is allowed to correct; viewer remains read-only. Officers must provide a reason of at least 10 characters.
- Campaign 9 Gate 2 readiness is always **BLOCKED** by QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION, even if an officer marked the information verified. No legal finding approval and no insight publication.
- The previously built isolated QA sandbox and synthetic pilot remain independently scoped.

## Activation: AFTER the verified v186.7 image is deployed to bawaslu-standalone-staging
Set these variables **only** on the existing staging service. Do not change the production service, QA sandbox, or Supabase secrets:
```
BAWASLU_INBOX_GATE1_READ_ENABLED=true
BAWASLU_INBOX_GATE1_WRITE_ENABLED=true
BAWASLU_INBOX_GATE1_PILOT_MODE=staging
BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS=9
BAWASLU_INBOX_GATE1_REAL_QA_CAMPAIGN_ID=9
BAWASLU_INBOX_GATE1_REAL_QA_CONFIRM=POLITIK_UANG_AUDIT_ONLY
```
The real-campaign QA flag is intentionally **not** activated by deployment alone. Verify image and officer permissions before enabling.

## Officer acceptance — main BAWASLU administrator (no new QA login)
1. Open `https://bawaslu-standalone-staging.onrender.com/inbox?gate1=1&campaign_id=9` (hard refresh).
2. Choose Politik Uang and click **Check staging pilot readiness**. Confirm the QA real-evidence count, permissions and write eligibility.
3. Select source #1909 or another source with saved AI assessment; the officer-correction panel appears under Original evidence & assessment. Confirm original AI value and source link.
4. Change **Election relevance** to a *different* classification, write a reason of 10+ characters, click **Save audited field correction**.
5. Confirm the effective QA relevance changes and original AI relevance stays the same. Check historical revision, reviewer and rationale; switching review category shows the corrected classification.
6. Choose **OFFICER_VERIFIED** for information only with a reason, save; open feedback queue, inspect correction and triage. This does **not** verify allegations or train AI.
7. Click **Check insight-draft readiness**. Confirm blocker `QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION` and no Command Centre insight.
8. Try read-only officer login (if available), verify correction controls hidden; choose other real campaign, verify write controls remain disabled.

## Database safety: automatic and manual
Only run automated integration against disposable localhost PostgreSQL. The v186.7 workflow checks unchanged canonical assessment and Social Listening counts, append-only revision, stale edit rejection, feedback, reviewer security, cross-campaign source block and permanent Gate 2 publication block.
Before enabling writes on shared Supabase, use the main app's staging-only admin account and test a single assessment; never test officer data outside campaign 9.
