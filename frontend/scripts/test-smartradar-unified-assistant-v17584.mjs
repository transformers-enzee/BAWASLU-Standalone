import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const page=read('../src/pages/IntelligenceAssistant.jsx');
const mode=read('../src/components/intel/AssistantModeControls.jsx');
const composer=read('../src/components/intel/AssistantComposerAttachments.jsx');
const citation=read('../src/components/intel/AssistantAttachmentCitation.jsx');
const evidence=read('../src/components/intel/AssistantWorkflowEvidence.jsx');
const feedback=read('../src/components/intel/AssistantResponseFeedback.jsx');
const controls=read('../src/components/intel/AssistantWorkflowControls.jsx');
const backend=read('../../backend/app/main.py');
const attachments=read('../../backend/app/assistant_attachments.py');
const modes=read('../../backend/app/assistant_mode.py');
const history=read('../../backend/app/assistant_history.py');
const grounding=read('../../backend/app/assistant_grounding.py');
const workflows=read('../../backend/app/assistant_workflows.py');
const schema=read('../../backend/migrations/20261123_assistant_chat_attachments.sql');
function has(file,strings){strings.forEach(s=>assert.ok(file.includes(s),'Missing contract '+s))}
has(mode,[
 'data-testid="smart-radar-assistant-active-mode"',
 'SmartRadar active analytical mode',
 'SmartRadar answer perspective',
 'MANAGEMENT','OPERATIONAL','AUTO','EXECUTIVE','RESEARCH',
 'leadership&&<option value="MANAGEMENT">',
]);
has(page,[
 'AssistantModeControls','AssistantComposerAttachments','AssistantResponseFeedback',
 'workspaceMode:workspace===\'MANAGEMENT\'?\'MANAGEMENT\':\'OPERATIONAL\',assistantMode,perspective',
 'conversationId:activeIdRef.current',
 'attachmentIds:selectedIds',
 'onProcessingChange={setAttachmentBusy}',
 'attachmentBusy||!question.trim()',
 'setAttachments([])',
]);
// The Operations route retains its historical name, but API requests must
// use the canonical analytical mode. Never regress to the rejected OPERATIONS payload.
assert.ok(page.includes("workspaceMode:workspace==='MANAGEMENT'?'MANAGEMENT':'OPERATIONAL'"));
assert.ok(modes.includes('if workspace=="OPERATIONS":workspace="OPERATIONAL"'), 'Backend must normalize the legacy Operations workspace name');
assert.ok(!page.includes('workspaceMode:workspace,assistantMode,perspective'));
has(controls,["['attachments','Conversation attachments'","'smartRadar','SmartRadar"]);
has(composer,[
 'data-testid="smart-radar-attachment-composer"',
 'Upload document','Add link','accept=".pdf,.docx,.txt"','multiple',
 'FormData','thread_id','/upload','/link',
 'Remove ','Ready · {item.sections} sections',
 'malware-scanned','Attachment processing',
]);
has(citation,[
 'Open authorized attachment citation','/api/assistant-attachments/',
 '/content?section=','Authorization:',"sourceId",'not independently verified',
]);
has(evidence,[
 'assistant-attachment-inline-citation-links',
 'AssistantAttachmentCitation',
 'USER_SUPPLIED_UNVERIFIED',
 'assistant-consulted-sources',
]);
has(feedback,[
 'smart-radar-response-feedback','HELPFUL','NEEDS_IMPROVEMENT',
 '/api/assistant-feedback',
 'Was this response useful?',
]);
has(backend,[
 'assistant_attachments_router','assistant_feedback_router',
 'mode_contract(body,p)','selected_attachment_evidence(',
 'conversationId','attachmentIds','mode_config=mode_config',
 'attached_source_ids','attachment_by_id',
]);
has(attachments,[
 'class AssistantChatAttachment(Base)',
 'MAX_ATTACHMENTS=8','MAX_BYTES=5*1024*1024',
 'def _clamav_scan(', 'ASSISTANT_CLAMAV_HOST',
 'def _decode_document(', 'PdfReader','Document(io.BytesIO(data))',
 'def attach_link(', 'fetch_public_source', 'parsed.scheme!="https"',
 'def read_attachment_section(', 'def remove_attachment(', 'derived_history_redacted',
 'def selected_attachment_evidence(', 'scope_json','USER_SUPPLIED_UNVERIFIED',
]);
has(modes,['def mode_contract(', 'def mode_directive(', 'view_intelligence',
 'National Leadership','MANAGEMENT','OPERATIONAL']);
has(history,['"attachment_ids":','"attached_source_ids":',
 '"assistant_mode":','"perspective":']);
has(grounding,['ATT-[a-f0-9]{32}-S[0-9]+']);
has(workflows,['CHAT_ATTACHMENT','USER_ATTACHED_UNVERIFIED_SOURCE']);
has(schema,['CREATE TABLE IF NOT EXISTS assistant_chat_attachments',
 'CREATE TABLE IF NOT EXISTS assistant_response_feedback',
 'REFERENCES assistant_threads(id) ON DELETE CASCADE']);
console.log('PASS v175.84 unified SmartRadar research/strategy/drafting modes, private attachments, citations and feedback');
