import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

/* Synthetic only — never contacts the paid provider, Supabase or external pages. */
const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}
const mocked={
 module:'OFFICER_DECISION_AI_INDEPENDENT_V3',version:'1.0',
 task:'RESEARCH',source_mode:'WEB_ONLY',perspective:'AUTO',
 report:{
  headline:'Synthetic official notice: officer review needed',
  answer:'A fictional official public notice was published [P-1]. This is not a violation finding.',
  key_takeaway:'Check original procedural records before public comment [P-1].',
  bawaslu_implication:'Confirm whether a BAWASLU supervisory duty is engaged.',
  relevance:'POSSIBLE',recommended_decision:'Authorize a preliminary record verification.',
  claims:[{claim:'A fictional notice was published [P-1].',source_ids:['P-1'],
    status:'PRIMARY_SOURCE_REPORTED',caveat:'Hearing is not a determination.'}],
  legal:[{issue:'Administrative supervision',institution:'BAWASLU',
     legal_reference:'Controlling official provision not verified',
     applicability:'Stage must be established',verification_needed:'Confirm legal version and election stage',
     source_ids:['P-1'],primary_legal_text_confirmed:false,officer_review_required:true}],
  options:[],
  actions:[{task:'Preserve the relevant dated correspondence',owner_role:'Legal records reviewer',
    evidence_needed:'Original nomination supervision record',
    deliverable:'Document provenance matrix',
    decision_gate:'Escalate after legal nexus is confirmed; otherwise close',
    source_ids:['P-1'],status:'PROPOSED_NOT_ASSIGNED'}],
  draft:'',limitations:['Synthetic test only'],
  quality:{attributed_claims:1,unsupported_claims:0,
    legal_applicability_officer_verified:false,actions_executed:false,
    human_approval_required:true,no_prior_assistant_context:true}
 },
 research_trail:{
  retrieved_at:'2026-11-24T02:00:00Z',web_status:'READ',
  search_queries:['Bahasa Indonesia official update','English latest official notice'],
  public_read_count:1,saved_count:0,
  sources:[{id:'P-1',kind:'OFFICIAL',
    title:'Synthetic official DKPP article',url:'https://dkpp.go.id/synthetic-test',
    published_at:'2026-11-24',updated_at:'',
    read_status:'READ',reason:'Article body retrieved'}]
 },
 audit:{read_only:true,no_prior_assistant_history_retrieved:true}
};
test('all previous assistants remain visible and independently reachable alongside AI-4',async({page})=>{
 const submissions=[];
 await page.route('**/api/officer-decision-ai/analyze',async route=>{
  submissions.push(route.request().postDataJSON());
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(mocked)});
 });
 await login(page);
 const nav=page.getByRole('navigation',{name:'BAWASLU workspace'});
 await expect(nav.locator('a[href="/management/ai-5"]')).toBeVisible();
 for(const href of ['/assistant','/ai-assistant','/ai-assistant-v2-new','/ai-4']){
  await expect(nav.locator('a[href="'+href+'"]')).toHaveCount(0);
 }
 await page.goto('/ai-assistant-v2-new');
 await expect(page.getByTestId('officer-v3-page')).toBeVisible();
 const choose=page.getByTestId('officer-v3-source-modes');
 await expect(choose.getByRole('button',{name:/Public web only/})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('textbox',{name:'Ask the new Officer Decision AI'}).fill('What changed this week?');
 await page.getByRole('button',{name:/Generate officer brief/}).click();
 await expect(page.getByTestId('officer-v3-result')).toBeVisible();
 expect(submissions).toHaveLength(1);
 expect(submissions[0]).toEqual({question:'What changed this week?',
   source_mode:'WEB_ONLY',task:'AUTO',perspective:'AUTO'});
 await expect(page.getByTestId('officer-v3-claims')).toContainText('fictional notice');
 await expect(page.getByTestId('officer-v3-actions')).toContainText('Document provenance matrix');
 const publicLink=page.getByTestId('officer-v3-claims').locator('a[href="https://dkpp.go.id/synthetic-test"]');
 await expect(publicLink.first()).toBeVisible();
 await page.getByTestId('officer-v3-research-trail').locator('summary').click();
 await expect(page.getByTestId('officer-v3-research-trail')).toContainText('Read page');
 await expect(page.getByTestId('officer-v3-research-trail')).toContainText('2026-11-24');
 await expect(page.getByTestId('officer-v3-research-trail')).toContainText('legal');
 await expect(page.getByTestId('officer-v3-work-products')).toContainText('Evidence matrix');
 await page.getByRole('button',{name:'Evidence matrix'}).click();
 await expect(page.getByLabel('Prepared review document')).toHaveValue(/EVIDENCE MATRIX/);
});
test('fresh independent module switches sources without importing old assistant context',async({page})=>{
 const payloads=[];
 await page.route('**/api/officer-decision-ai/analyze',async route=>{
  payloads.push(route.request().postDataJSON());
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(mocked)});
 });
 await login(page);await page.goto('/ai-assistant-v2-new');
 const group=page.getByTestId('officer-v3-source-modes');
 await group.getByRole('button',{name:/Web \+ SmartRadar/}).click();
 await page.getByRole('textbox',{name:'Ask the new Officer Decision AI'}).fill('Compare authorized evidence');
 await page.getByRole('button',{name:/Generate officer brief/}).click();
 expect(payloads[0].source_mode).toBe('WEB_AND_RECORDS');
 expect(Object.keys(payloads[0]).sort()).toEqual(['perspective','question','source_mode','task']);
 await group.getByRole('button',{name:/SmartRadar only/}).click();
 await page.getByRole('textbox',{name:'Ask the new Officer Decision AI'}).fill('What is saved?');
 await page.getByRole('button',{name:/Generate officer brief/}).click();
 expect(payloads[1].source_mode).toBe('RECORDS_ONLY');
 await page.getByRole('button',{name:'Clear and start fresh'}).click();
 await expect(page.getByTestId('officer-v3-result')).toHaveCount(0);
});

test('deep research renders complete Markdown report with tables and linked evidence',async({page})=>{
 const extended=JSON.parse(JSON.stringify(mocked));
 extended.research_depth='DEEP';
 extended.report.answer='## National overview\n\n**Synthetic evidence** [P-1]\n\n| Province | Reports |\n| --- | --- |\n| Province A | 12 |\n\n'+('A synthetic analytical paragraph.\n\n'.repeat(80))+'## Legislative review\n\nFinal report section.';
 extended.report.claims=Array.from({length:7},(_,i)=>({claim:'Synthetic finding '+(i+1),status:'PRIMARY_SOURCE_REPORTED',source_ids:['P-1'],caveat:''}));
 extended.research_trail.search_passes=[{objective:'National statistics',status:'DISCOVERED',discovered:3,read_count:1}];
 extended.report.numeric_series=[{title:'Synthetic provincial counts',election_type:'Pemilu',period:'2024',case_status:'Reports',unit:'reports',rows:[{label:'Province A',value:12,source_id:'P-1',source_quote:'Province A 12 reports'},{label:'Province B',value:8,source_id:'P-1',source_quote:'Province B 8 reports'}]}];
 await page.route('**/api/officer-decision-ai/analyze',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(extended)}));
 await login(page);await page.goto('/ai-assistant-v2-new');
 await page.getByRole('textbox',{name:'Ask the new Officer Decision AI'}).fill('What are the top 10 election violations by provinces, candidates, parties and laws?');
 await page.getByRole('button',{name:/Generate officer brief/}).click();
 const full=page.getByTestId('officer-v3-full-report');
 await expect(full.getByRole('heading',{name:'National overview'})).toBeVisible();
 await expect(full.getByRole('table')).toContainText('Province A');
 await expect(full.getByRole('link',{name:'P-1'})).toHaveAttribute('href','https://dkpp.go.id/synthetic-test');
 await expect(full).toContainText('Final report section.');
 await expect(page.getByTestId('officer-v3-numeric-series')).toContainText('Synthetic provincial counts');
 await page.getByTestId('officer-v3-claims').locator('summary').click();
 await expect(page.getByTestId('officer-v3-claims')).toContainText('Synthetic finding 7');
});
