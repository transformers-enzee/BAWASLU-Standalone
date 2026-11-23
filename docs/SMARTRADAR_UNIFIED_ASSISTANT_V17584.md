# SmartRadar AI Research, Strategy & Productivity Assistant — v175.84

## Deployment safety

Development branch: architecture-v2-foundation-20261015. Existing v175.83 Render staging remains untouched until all of the following are true:

1. GitHub Docker build AND backend/frontend regression tests pass; GHCR digest and source SHA are recorded.
2. DBA confirms the attached migration creates **only new private chat and feedback tables** in the approved staging database; no production tables or case records modified. Apply backend/migrations/20261123_assistant_chat_attachments.sql to staging only after change approval. The prebuilt image runs with BAWASLU_STARTUP_READ_ONLY=1: it **will not create tables itself**.
3. An approved ClamAV-compatible INSTREAM malware scanner is reachable by the staging API. Configure ASSISTANT_CLAMAV_HOST and ASSISTANT_CLAMAV_PORT=3310. Uploads fail closed with HTTP 503 when the scanner is absent or inconclusive.
4. Manual UAT confirms documents, links, authenticated section opening and deletion with real, authorized staging officer accounts. Do NOT run paid OpenAI or SocialCrawl processing without an explicit budget.

## User workflow

One existing Intelligence Assistant appears in Operations at /assistant and Management at /management/assistant. The workspace sets the default analytical mode. Authorized national/provincial leadership may switch to Management mode; all authorized officers may use Operational mode. Auto, Executive, Operational and Research perspectives change emphasis without changing source permissions. Existing Research & Analysis versus Strategy & Drafting workflows remain available in the same conversation.

The composer has **Attach → Upload document** (multiple PDF/DOCX/TXT <=5 MB each) and **Attach → Add link** (public HTTPS only). Attachments are scoped to the thread and to the owner’s recorded jurisdiction. The app displays loading, failure and ready states, page/section counts, title, external link and retrieval timestamp. User-supplied attachment text never enters shared case records or the common legal reference library; it is only available through explicitly authorized, separate actions.

Files are MIME/signature/size validated, malware scanned before extraction, zip expansion limited, non-extractable/encrypted PDFs rejected with OCR guidance, and DOCX/TXT extracted with section labels. The original upload bytes are discarded. Only bounded extracted snippets, source digests, timestamps and metadata are retained in private chat tables. Social content from HTTPS links uses the existing public-source retrieval service with private-address, redirect, response-size and HTML controls; login-only pages are not bypassed. The final retrieved page is required to remain HTTPS.

The server re-verifies the currently authenticated user, thread ownership, and jurisdiction scope on each attachment selection, retrieval, citation opening, and deletion. A deleted attachment is deleted from its private table. The stored assistant replies derived from that attachment are replaced with a redaction message, and associated feedback is deleted. Thread deletion cascades to attachments and feedback. Shared case records are not affected.

Sources are labeled as saved snapshots, real public queries, unverified uploads/links, or simulated demo content; only consulted sources count in the research trail. Attachment citations use **[ATT-<opaque uuid>-S<section>]** and open through an authenticated API, never a public static file route. Citation opening checks permissions anew. Historical assistant answers are not primary evidence.

Feedback uses a saved assistant message and its owner’s thread ID. Ratings are Helpful or Needs improvement; an optional 600-character comment and response hash are retained without copying the original response into the feedback table.

## Access and legal safeguards

Management mode emphasizes decisions, affected institutions, change assessment, trade-offs, escalation conditions and leadership review. Operational mode starts with the next officer check, cited evidence, verification gaps, proposed reviewer office and deadlines/authorities requiring confirmation. The response perspective is separate from workflow, never bypassing authorization.

For both modes, source allegations remain allegations, verified events require independent source/authenticity checks, and legal claims require checking election type, jurisdiction, stage, and controlling official provisions. No private attachment is silently copied into the shared SmartRadar intelligence corpus. No AI reply approves sanctions, assignments, takedowns or external emails.

## Limitations to verify before rollout

- Mandatory ClamAV service must be provisioned; no insecure scanning bypass is enabled.
- The new staging-only schema must be migrated before running attachment endpoints because BAWASLU_STARTUP_READ_ONLY=1 intentionally prevents automatic schema writes.
- Existing conversation history stores only bounded user messages and citations. Privacy deletion redacts answers linked to deleted source IDs, but an officer should separately review any external exports or manual copies.
- Public HTML/social link retrieval is best effort; authenticated/private pages and non-HTML files may need upload or pasted excerpts. It does not create a SocialCrawl provider task.
- Full live document/links/feedback acceptance requires manual staging QA; source-level contracts alone are not a release acceptance signal.
- Document extracted sections are capped to 24,000 characters per source and eight sources per conversation. Not every page of large documents is guaranteed in the answer.
