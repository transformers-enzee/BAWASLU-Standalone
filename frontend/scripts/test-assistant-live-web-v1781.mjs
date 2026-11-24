import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const v2=read('../src/pages/AIAssistantV2.jsx');
const legacy=read('../src/pages/IntelligenceAssistant.jsx');
const controls=read('../src/components/intel/AssistantWorkflowControls.jsx');
const trail=read('../src/components/intel/AssistantWorkflowEvidence.jsx');
const api=read('../../backend/app/ai_assistant_v2.py');
const web=read('../../backend/app/assistant_orchestration.py');
const parser=read('../../backend/app/assistant_live_web.py');
const main=read('../../backend/app/main.py');
for(const x of ['WEB_ONLY','WEB_SMARTRADAR','SMARTRADAR_ONLY',
                'ai-assistant-v2-source-modes','sourceMode','ai-assistant-v2-web-page-status',
                'ai-assistant-v2-search-audit','Published:','Snippet only','Inaccessible',
                'CitedText', "read_status==='READ'"])
 assert.ok(v2.includes(x),'v2 missing '+x);
for(const x of ['assistant-source-modes','setSourceMode','WEB_ONLY','WEB_SMARTRADAR','SMARTRADAR_ONLY'])
 assert.ok(controls.includes(x),'legacy mode controls missing '+x);
assert.ok(legacy.includes("useState('WEB_ONLY')"));
assert.ok(legacy.includes('sourceMode,researchIntent:'));
assert.ok(trail.includes('assistant-public-pages-audit'));
assert.ok(api.includes('records=[]')&&api.includes('verify_public_pages(found)'));
assert.ok(api.includes('source_mode'));
assert.ok(api.indexOf('consulted_web=None')<api.indexOf('records,internal_warnings=gather('));
assert.ok(api.includes('if selected["smartRadar"] or selected["legalReferences"]'));
assert.ok(api.includes('readable_pages=sorted('));
assert.ok(web.includes('"tool_choice":"required"'));
assert.ok(web.includes('"include":["web_search_call.action.sources"]'));
assert.ok(web.includes('search_plan(question,utc_date)'));
for(const x of ['SNIPPET_ONLY','INACCESSIBLE','_global_dns','get_extra_info("server_addr")',
                'follow_redirects=False','MAX_DOWNLOAD','freshness_check_requested'])
 assert.ok(parser.includes(x),'safe web reading missing '+x);
assert.ok(main.includes('research=verify_public_pages(research) if research else None'));
console.log('PASS v178.1 live web source modes, strict read status, newest dates, clickable citations and source isolation');
