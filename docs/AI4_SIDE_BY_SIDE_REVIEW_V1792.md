# SmartRadar AI-4 — side-by-side evaluation build (v179.2)

## Scope and routes

AI-4 is a **new assistant**, not a rewrite or retirement of the existing one.

| Workspace | New AI-4 | Existing assistant |
|---|---|---|
| Operations | /ai-4 — AI Assistant (New) | /ai-assistant — AI Assistant |
| Management (authorised leadership) | /management/ai-4 — AI Assistant (New) | /management/ai-assistant — AI Assistant |

The previously available BAWASLU Intelligence Assistant and other
historical direct URLs remain unchanged. No conversation, attachment,
case, approval, assignment or intelligence record is migrated.

AI-4 has a separate frontend and server API. It reuses the active
authentication, view-intelligence authorization, geographic access
grant and authorised source selectors, not historical prompts or
conversations. The server enforces Management-only role restrictions.

## Interaction and research

Management answers prioritise leadership implications, decisions,
monitoring and trade-offs. Operational answers prioritise evidence,
verification gaps, responsible reviewer roles and practical next steps.
Optional perspectives are Auto, Executive, Operational and Research.
Responses lead with the substantive answer in the question language,
cite individual findings and avoid repeating observations.

| Source mode | Public research | Saved BAWASLU data | Officer-added attachments |
|---|---|---|---|
| Web only | Yes | Never | Explicitly supplied only |
| Web + SmartRadar | Yes, first | Authorized scope only | Yes |
| SmartRadar only | No | Authorized scope only | Yes |

Web only does not retrieve saved internal records, including after a
failed public search. The assistant must disclose unavailability and
never silently substitute saved records. Switching source modes after
conversation work starts requires a new conversation.

The approved OpenAI Responses web-search integration discovers
attributed public URLs; the safe page reader then opens original
HTTPS pages before treating their content as evidence. Current and
recent queries run a second search for updates, corrections and
superseded announcements. Research Trail displays search status,
source URL, title, dates, READ, SNIPPET_ONLY or INACCESSIBLE
and uncertainty. Public news cannot be used as a representative
social-media trend without comparable coverage data.

## Upload document and Add link

New endpoints support PDF, DOCX, UTF-8 TXT and publicly reachable HTTPS
links. Structural safety checks include extension/signature,
5 MB limit, encrypted PDF rejection, 45-page limit, DOCX ZIP
expansion/entry limits, macro and embedded executable rejection,
UTF-8 validation, bounded excerpts and HTTPS SSRF protections.

At most eight attachments and 75,000 extracted characters are allowed
per conversation. Source citations identify file names and pages,
paragraphs, tables or sections. Uploaded document bytes are discarded
after extraction. The bounded extracted text remains only in
a user/jurisdiction-scoped memory cache in the current application
process, for up to 12 hours. Removed attachments cannot be used in
subsequent turns. Files and link excerpts ARE sent to the configured
AI synthesis provider for answering, but never added automatically
to SmartRadar's shared knowledge or web-search query.

**Pilot limitation:** attachment/feedback storage is process-local,
not durable. Restart or multiple server workers can lose attachments.
Production requires persistent encrypted storage, explicit retention
controls, and approved malware scanning; structural checks do not
prove files malware-free.

## Drafting and feedback

Follow-up questions can turn research into strategies, options,
action plans, memos and email drafts. Drafts remain editable,
and only authorised staff may file, approve, assign or send.

Per-response feedback captures 1–5 ratings for clarity, source quality
and usefulness, with optional redacted notes. Feedback is stored in
the same temporary owner-scoped session and available via the feedback
GET endpoint. It does not survive server restarts and must not be
mistaken for permanent user acceptance evidence.

## Human review checklist

1. Verify both original and new assistant navigation links work
   independently, including Management and Operational routes.
2. Test a current public question in Web only; confirm that saved
   retrieval is disabled and citations link to actually READ pages.
3. Check a superseded public announcement against a newer correction.
4. Use mixed mode to verify public findings and authorised saved
   observations remain separate and scope restrictions hold.
5. Upload PDF, DOCX and TXT; check source names and page/section
   references. Remove a file, then ask a follow-up and verify it
   can no longer be cited.
6. Add a safe public HTTPS link, and reject inaccessible/private URLs.
7. Convert research into an action plan and leadership memo; request
   a shorter version or email while preserving factual caveats.
8. Compare Management strategic and Operational practical answers.
9. Capture clarity/source/usefulness feedback and whether the answer
   assisted the BAWASLU user's decision or next action.

| Reviewer | Office level | Current sources read? | Permissions passed? | File follow-up passed? | Useful/actionable? |
|---|---|---|---|---|---|
| BAWASLU operational reviewer | TBD | Pending | Pending | Pending | Pending |
| BAWASLU management reviewer | TBD | Pending | Pending | Pending | Pending |

Automated tests use simulated sources and cannot establish the
success of real paid live web research. Authenticated staging search
and human evaluation are required before deciding whether to retire
any existing assistant.

## Release boundaries

This is the AI-4 v179.2 development release. It does not deploy,
retire or replace historical services, migrate conversations or
perform external institutional actions. Staging promotion requires
the verified image to be selected in Render's image-based service.
