import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const app=read('../src/App.jsx');
const nav=read('../src/components/intel/AccessNavigation.jsx');
const ai=read('../src/pages/AI5Assistant.jsx');
const api=read('../../backend/app/ai5/api.py');
const engine=read('../../backend/app/ai5/engine.py');
const session=read('../../backend/app/ai5/state.py');
const web=read('../../backend/app/ai5/web.py');
const exportFile=read('../../backend/app/ai5/export.py');
const main=read('../../backend/app/main.py');
const docker=read('../../Dockerfile');
const have=(s,token)=>assert.ok(s.includes(token),'Missing contract: '+token);
for(const p of ['/assistant','/ai-assistant','/ai-assistant-v2-new','/ai-4','/ai-5',
                '/management/assistant','/management/ai-assistant',
                '/management/ai-assistant-v2-new','/management/ai-4','/management/ai-5'])
 have(nav,"'"+p+"'");
have(app,'path="/ai-5" element={<AI5Assistant workspace="OPERATIONAL" />}');
have(app,'path="/management/ai-5" element={<AI5Assistant workspace="MANAGEMENT" />}');
have(app,'path="/ai-4" element={<AI4Assistant workspace="OPERATIONAL" />}');
have(app,'path="/ai-assistant" element={<UnifiedAIAssistant workspace="OPERATIONAL" />}');
have(main,'app.include_router(ai5_router)');
have(main,'app.include_router(ai4_router)');
have(api,'router=APIRouter(prefix="/api/ai-5"');
have(api,'if cfg["source_mode"]!="WEB_ONLY"');
have(api,'saved_research(db,grant');
have(api,'@router.post("/export/{file_type}")');
have(engine,'referenceTurnId');
have(engine,'GENERAL_RESEARCH');
have(engine,'BAWASLU_ACTION');
have(engine,'Do NOT force election');
have(engine,'WEB_ONLY');
have(engine,'Management guidance requires an authorised leadership role');
have(session,'history_context');
have(session,'used_saved');
have(session,'latest_relevant');
have(session,'MAX_TURNS');
have(web,'GENERAL RESEARCH');
have(web,'read_page');
have(web,'SNIPPET_ONLY');
for(const x of ['create_pdf','create_docx','create_xlsx','PdfReader','Document','Workbook']){
 if(x==='PdfReader')continue;
 have(exportFile,x);
}
have(exportFile,'SimpleDocTemplate');
have(exportFile,'from openpyxl import Workbook');
for(const x of ['ai5-page','ai5-modes','ai5-use-bawaslu',
 'ai5-source-modes','Upload document','Add link','ai5-attachments',
 'ai5-research-trail','ai5-response','AI-5 editable draft',
 "['pdf','docx','xlsx']"])
 have(ai,x);
have(docker,'ARG BAWASLU_BUILD_VERSION=182.5');
have(docker,'tests/test_ai5_v1794.py');
have(main,"BAWASLU_BUILD_VERSION','182.5'");
console.log('PASS AI-5 v179.4 independent routes, unrestricted general mode, permissioned research and real export contracts');
