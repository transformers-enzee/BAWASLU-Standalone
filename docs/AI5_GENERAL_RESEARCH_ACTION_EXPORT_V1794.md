# SmartRadar AI-5 — v179.4 independent evaluation

## Scope and entry points

AI-5 is a separate fifth assistant. No previous assistant, historical route, prompt,
conversation, case, or stored decision has been removed or migrated.

| Workspace | AI-5 | Existing versions (unchanged) |
|---|---|---|
| Operational | /ai-5 | /assistant, /ai-assistant, /ai-assistant-v2-new, /ai-4 |
| Management (authorised leadership) | /management/ai-5 | /management/assistant, /management/ai-assistant, /management/ai-assistant-v2-new, /management/ai-4 |

The sidebar exposes all five versions. AI-5 uses its own /api/ai-5
router, engine, general web research and export service. Existing
authentication, access grants and permission-scoped source readers
are reused as infrastructure.

## Conversation and source controls

General Research is the default, including from Management workspace.
Users can ask about any subject without a task picker, change direction
and question findings. Use for BAWASLU switches to BAWASLU Action in
the same conversation. Operational emphasizes evidence and next steps;
authorised Management emphasizes implications, choices and decisions.
Switch back to General Research anytime.

Web only, Web + SmartRadar, SmartRadar only are independently selected.
Web only never invokes saved SmartRadar retrieval. Previous assistant
summaries based on saved records are stripped from Web-only prompts.
SmartRadar only cannot reuse public-search findings as provenance.
Explicitly supplied attachments remain available in all three modes.
Management Action checks leadership roles server-side.

The assistant uses flexible Markdown answers, optional comparison
tables, and editable drafts. The server retains recent conversation
turns in permission-bound temporary storage. Revision, reformatting,
or application of prior findings reuses allowed material without
unnecessary fresh public search. New factual questions may trigger
live search, with a second check for newer updates on recent stories.

## Evidence

Live public lookup uses approved OpenAI Responses web search, followed
by a safe bounded public HTTPS reader. The source audit distinguishes
READ, SNIPPET_ONLY and INACCESSIBLE. Inline citations are validated
against actually available source IDs. Saved social observations are
not official findings. For legal use, review the official instrument,
version, jurisdiction and authority before issuing a determination.

## Attachments

Upload PDF, DOCX or UTF-8 TXT (5 MB per file) and add safe public
HTTPS links. Existing extraction safeguards check formats and sizes,
PDF page limits, DOCX archive expansion and unsafe URLs. UI shows
processing, attachment titles and removal controls. Extracted file
text is sent to the answer model only when answering; not included
in the external web-search prompt. Removed attachments cannot support
new answers; exports based on removed files are blocked.

Pilot conversations and attachment excerpts are held for up to
12 hours in process-local memory. Restarts, multi-worker routing and
capacity limits can end a conversation. For production, implement
encrypted durable per-user storage, security-reviewed malware scanning
and formal retention/recovery controls.

## Real file exports

The authenticated endpoint POST /api/ai-5/export/{file_type}
generates actual bytes, never placeholder download labels:

- PDF: ReportLab; response, tables, caveats and provenance appendix.
- Word: editable python-docx; document and structured table.
- Excel: openpyxl; Analysis, Sources and Context and caveats tabs,
  source provenance and literal (formula-protected) cell contents.

The officer downloads the generated response in the browser.
Each export verifies current auth, source mode and whether any
supporting attachments have been removed. A failed export cannot
delete the original answer or draft. No action automatically files,
approves, sends or assigns official work.

## Acceptance review

| Case | Evaluation |
|---|---|
| Quick unrelated question | Direct short answer without BAWASLU boilerplate |
| Complex unrelated research | Useful depth, cited sources, tables if helpful |
| Challenge and new direction | Maintains allowed context, handles topic pivot |
| Use for BAWASLU then switch back | One conversation, role-correct Management/Operational emphasis |
| Web only after mixed source | No saved sources or internal model-derived content |
| Uploaded PDF/DOCX/TXT and HTTPS link | Processing, original section references, follow-up, removal |
| Rewrite or change audience | Previously cited findings and caveats survive |
| PDF/Word/Excel export | Valid binary files, editable Word, structured workbook |
| Export failure | Answer and draft remain available |
| Legacy regression | All four older assistant versions remain accessible |

These tests use synthetic fixtures. Live staging search quality,
authenticated document download and real BAWASLU-user feedback
remain acceptance tasks, not claims of sign-off.

## Release boundary

This is a new evaluation candidate, not an assistant retirement or
conversation migration. Staging promotion is separate from code
publication; production is unchanged unless separately approved.
