# BAWASLU — Real Officer Acceptance Runbook (v148.0)

**Environment:** Staging only, `architecture-v2-foundation-20261015`.  
**Scope:** Operational proof of a genuine source-linked officer assignment, original source inspection, independent report approval and an auditable trail.  
**Do not claim legal compliance or client sign-off from this workflow alone.**

## Observed readiness baseline (12 November 2026)

Read-only Supabase query: **0 case assignments, 0 case reports, 0 case transitions, 0 officer-reviewed PDFs.** There is no existing real case to inspect or approve. The application can be accepted in automated tests, but real client acceptance remains unproven.

## New existing-casework functionality

- `POST /api/casework/cases/{id}/source-review` adds a source-access review event by the **current assigned receiving officer, after accepting** an assignment. Requires authenticated `add_intelligence` permission and existing case visibility. No schema additions.
- Three review outcomes: `SOURCE_CHECKED`, `NEEDS_INFORMATION`, `SOURCE_UNAVAILABLE`; all require a factual officer note of at least 20 characters.
- `SOURCE_CHECKED` is refused unless the officer confirms opening a stored original HTTP(S) source URL. It is **not** verification that the allegation is true or a statutory violation.
- `GET /api/casework/cases/{id}` now includes `workflow_trace` with **five auditable process checkpoints**, rendered inside Intelligence Inbox casework. Older report versions remain audit history. The checklist is explicitly not client acceptance or legal review.
- Source-review events retain source type, source ID, campaign ID, original URL, officer identity and notes. There is no automatic case creation, platform takedown, approval, AI billing, legal judgment or external action.

## Detailed manual QA — an authorized human must perform these actions

1. Sign into BAWASLU staging as an authorized **national officer** with permission to create casework. Open **Command Centre**, select a finding with a real saved post, then choose **Officer casework follow-up → Start source-linked officer review**. Alternatively open a relevant saved post in **Intelligence Inbox** and choose **Assign / Transfer**.
2. Verify the displayed **source ID, campaign, original URL and source excerpt** match the actual post. Do not proceed if provenance is missing or unrelated. Set the responsible department. Choose the provincial team *only if a qualified officer has separately verified the incident province*; otherwise route nationally. Save the assignment **once** and note the case ID.
3. Sign in as the actual receiving officer. From **Intelligence Inbox → Assigned to me / Incoming handoffs**, open the case and click **Accept & start review**. The audit checklist should advance from 1/5 to 2/5.
4. In **Original source access review**, open the **original post**, confirm its date, author, context, screenshots and links, and record a factual note (20+ characters). Choose **Original opened and context reviewed** only if it was truly opened, and tick the confirmation checkbox. Otherwise use **More information required** or **Original unavailable**. A genuine source check advances the trace to 3/5; the other outcomes do not.
5. Open the **Report** tab, create a *manual* source-grounded draft, explain which claims remain unverified in findings/verification notes, save and **Submit for approval**. The current report submission advances the trace to 4/5. No paid AI model is required.
6. Sign in as a **different authorized reviewer** with `human_validation` permission and access to the case. In **Intelligence Inbox → Reports to approve**, inspect the original source, officer review and latest report, then **Approve** only if genuinely appropriate. The author should not be able to approve their own submission. After a genuine independent approval the procedural trace reaches **5/5**.
7. Reopen the case and inspect **Activity history**: `CREATED`, `ACKNOWLEDGED`, `SOURCE_REVIEW_RECORDED`, `REPORT_SUBMITTED`, and `REPORT_APPROVED`; check distinct officer IDs. Verify the source/campaign IDs and that the current report is approved. No law, element or deadline has been certified by the software.
8. As an unrelated provincial analyst or Viewer, verify that unauthorized source review or case access is denied, and that an old/superseded report cannot be approved. If the evidence becomes inaccessible, record `SOURCE_UNAVAILABLE`; the source-check checkpoint should return to incomplete.

**Capture for sign-off:** case ID, source ID, campaign ID, receiving jurisdiction/department, source-review officer/date, report ID, independent reviewer/date, and screenshot of the five-step procedural trace. Do not paste private tokens or identifiable client evidence into public issue trackers.

## Automated QA vs. client acceptance

- Automated SQLite tests exercise full case creation → receiving acknowledgment → human source check → latest report submission → separate reviewer approval; negative, role-based and rerouting cases are also tested. Automated tests run with simulated evidence and cannot establish a real user's review.
- Client acceptance remains **PENDING** until authorized officers perform the steps above on genuine evidence. The PDF corpus also remains unapproved; legal currentness is a separate competent legal review.
- Keep real-case manual QA in **staging**, not production. Avoid using any real report to assert electoral-law wrongdoing without independent verification.
