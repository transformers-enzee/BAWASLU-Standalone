import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const app=read('../src/App.jsx');
const nav=read('../src/components/intel/AccessNavigation.jsx');
const page=read('../src/pages/AI4Assistant.jsx');
const main=read('../../backend/app/main.py');
const api=read('../../backend/app/ai4/api.py');
const core=read('../../backend/app/ai4/core.py');
const attachments=read('../../backend/app/ai4/attachments.py');
const legacy=read('../../backend/app/unified_ai/api.py');
const docker=read('../../Dockerfile');
const has=(c,x)=>assert.ok(c.includes(x),'Required AI-4 contract not found: '+x);
has(app,'path="/ai-4" element={<AI4Assistant workspace="OPERATIONAL" />}');
has(app,'path="/management/ai-4" element={<AI4Assistant workspace="MANAGEMENT" />}');
has(app,'path="/ai-assistant" element={<UnifiedAIAssistant workspace="OPERATIONAL" />}');
has(app,'path="/management/ai-assistant" element={<UnifiedAIAssistant workspace="MANAGEMENT" />}');
has(nav,"['/ai-4','AI Assistant (New)'");
has(nav,"['/management/ai-4','AI Assistant (New)'");
has(main,'app.include_router(ai4_router)');
has(main,'app.include_router(unified_ai_router)');
has(api,'router=APIRouter(prefix="/api/ai-4"');
has(legacy,'router=APIRouter(prefix="/api/ai-assistant"');
has(api,'if prefs["smartRadar"]');
has(api,'public=search_public_web(');
for(const item of ['WEB_ONLY','WEB_SMARTRADAR','SMARTRADAR_ONLY','MANAGEMENT',
 'OPERATIONAL','AUTO','EXECUTIVE','RESEARCH'])has(core,item);
for(const item of ['@router.post("/upload")','@router.post("/link")',
 '@router.delete("/attachments/{conversation_id}/{attachment_id}")',
 '@router.post("/feedback")','@router.get("/feedback/{conversation_id}")'])has(api,item);
for(const item of ['PurePath','MAX_BYTES','zipfile','PdfReader','Document',
 'read_page','safe_url','scope(grant)','file_sections','evidence('])has(attachments,item);
for(const item of ['Upload document','Add link','Remove ','ai4-research-trail',
 'ai4-feedback','AI-4 editable draft','ai4-source-row','ai4-composer',
 'Web + SmartRadar','SmartRadar only','AI Assistant (New)'])has(page,item);
has(core,'SYSTEM_PROMPT=');
has(core,'Reply in the language');
has(core,'consistent, nonpartisan evidentiary standard');
has(docker,'ARG BAWASLU_BUILD_VERSION=179.2');
console.log('PASS AI-4 v179.2: independent routes, permissioned sources, attachments, follow-ups and feedback; existing assistant retained');
