import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const main=read('../../backend/app/main.py');
const app=read('../src/App.jsx');
const page=read('../src/pages/UnifiedAIAssistant.jsx');
const nav=read('../src/components/intel/AccessNavigation.jsx');
const home=read('../src/pages/ManagementHome.jsx');
const api=read('../../backend/app/unified_ai/api.py');
const contract=read('../../backend/app/unified_ai/contract.py');
const web=read('../../backend/app/unified_ai/web.py');
const saved=read('../../backend/app/unified_ai/saved.py');
const ai=read('../../backend/app/unified_ai/answer.py');
const docker=read('../../Dockerfile');
function has(s,x,label){assert.ok(s.includes(x),label||x)}
has(main,'app.include_router(unified_ai_router)','Unified backend enabled');
assert.ok(!main.includes('app.include_router(ai_assistant_v2_router)'),'Retired handler must not serve primary URL');
has(api,'@router.post("/chat")','Dedicated authenticated endpoint');
has(api,'if not has(grant,"view_intelligence")','Access enforcement');
has(api,'if cfg["sources"]["smartRadar"] or cfg["sources"]["legalReferences"]','Strict source option');
has(api,'public=public_research(question,cfg,key,model,base)','Fresh public research');
has(api,'saved_research(db,grant,','Authorized data access');
assert.ok(api.indexOf('public=public_research(')<api.indexOf('saved,warnings=saved_research('));
has(contract,'LEADERS=frozenset','Leadership gate');
has(contract,'BAWASLU kabupaten/kota','Office role level');
for(const p of ['AUTO','EXECUTIVE','OPERATIONAL','RESEARCH'])has(contract,p);
for(const p of ['WEB_ONLY','WEB_SMARTRADAR','SMARTRADAR_ONLY'])has(contract,p);
for(const p of ['RESEARCH','STRATEGY','DRAFTING'])has(contract,p);
has(web,'"tool_choice":"required"','OpenAI approved web search');
has(web,'"include":["web_search_call.action.sources"]','Attributable result URLs');
has(web,'read_page','Open original pages');
has(web,'SNIPPET_ONLY','Never upgrade snippet to evidence');
has(web,'freshness','Newer corrections for recent stories');
has(web,'sni_hostname','Pinned IP / verified TLS');
has(saved,'list_intelligence(db,grant)','Officer-scoped formal retrieval');
has(saved,'campaign_action(db,grant','Officer-scoped social retrieval');
has(saved,'simulasi','Reject sample law as authority');
has(ai,'eligible(s,config.get("window"))','Date window source eligibility');
has(ai,'SAVED_SOCIAL','Allegation class');
has(ai,'READ_OFFICIAL_PUBLICATION_NOT_OFFICER_AUTHENTICATED','Official read not officer adjudication');
has(ai,'owner_role','Action plan owner roles');
has(ai,'"store":False','No provider persistence');
has(app,'path="/ai-assistant" element={<UnifiedAIAssistant workspace="OPERATIONAL" />} />');
has(app,'path="/management/ai-assistant" element={<UnifiedAIAssistant workspace="MANAGEMENT" />} />');
assert.ok(nav.includes("'AI-5 Assistant'"),'One visible AI-5 entry required');
assert.ok(!nav.includes("AI-4 · AI Assistant"),'Legacy assistants hidden from officer navigation');
for(const route of ['/assistant','/ai-assistant-v2-new','/ai-4',
                    '/management/assistant','/management/ai-assistant-v2-new','/management/ai-4'])
 has(app,'path="'+route+'"','Legacy bookmarks must still resolve: '+route);
has(home,'/management/ai-5','Management research now opens AI-5');
for(const feature of ['unified-ai-page','unified-research-trail','unified-finding',
  'unified-action','unified-ai-draft','WEB_ONLY','WEB_SMARTRADAR','SMARTRADAR_ONLY',
  'Controlled officer walkthrough','SOCIAL-740','SOCIAL-1160','Copy','Turn into email'])
 has(page,feature,'Missing rebuilt experience: '+feature);
const version=main.match(/BAWASLU_BUILD_VERSION','([0-9]+\.[0-9]+)'/)?.[1];
assert.ok(version && Number(version)>=179.1,'Unified AI minimum version is 179.1');
has(docker,'ARG BAWASLU_BUILD_VERSION='+version);
console.log('PASS v179.1 rebuilt AI Assistant routes, isolated web research, structured source-linked decisions and review-only drafts');
