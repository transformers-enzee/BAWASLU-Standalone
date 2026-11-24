import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

// Explicitly synthetic browser fixtures; live provider and actual Office/PDF
// file validity are checked separately at the authenticated API boundary.
const account='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(account);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}
const u='https://example.org/synthetic-source';
function answer(mode='GENERAL_RESEARCH',draft=false){
 const id='WEB-T3ST-1';
 return {assistant:'AI-5',turn_id:'a'.repeat(32),conversation_id:'test',
  mode,action_mode:'OPERATIONAL',source_mode:'WEB_ONLY',
  answer:{title:'Synthetic research',body:mode==='BAWASLU_ACTION'?
     'Your BAWASLU office should first verify the source [[WEB-T3ST-1]].':
     'This general research topic has multiple angles [[WEB-T3ST-1]].',
    draft:draft?'DRAFT MEMO\n\nEvidence should be reviewed [[WEB-T3ST-1]].':'',
    table:{title:'Comparison',columns:['Option','Trade-off'],
      rows:[['Verify','Officer time'],['Monitor','Missed developments']]},
    open_questions:['Which evidence would change the conclusion?'],
    source_ids:[id],human_review_required:true,actions_executed:false},
  research_trail:{public_status:'READ_SOURCES_AVAILABLE',
   searched_at:'2026-11-24T04:00:00Z',read_public_count:1,saved_count:0,
   attachment_count:0,attempts:[{phase:'public search',status:'FOUND',discovered:1}],
   sources:[{id,title:'Synthetic read publication',type:'PUBLIC_REPORT',
     read_status:'READ',basis:'LIVE_PUBLIC_LOOKUP',published_at:'2026-11-24',
     updated_at:'',url:u,reason:'Synthetic browser fixture'}],warnings:[]},
   synthesis_status:'COMPLETE',actions_executed:false};
}

test('AI-5 is additive: all earlier assistants are still visible',async({page})=>{
 await login(page);
 for(const route of ['/assistant','/ai-assistant','/ai-assistant-v2-new','/ai-4','/ai-5']){
  await expect(page.getByRole('navigation',{name:'Operational workspace'}).locator('a[href="'+route+'"]')).toBeVisible();
 }
 for(const route of ['/management/assistant','/management/ai-assistant',
                      '/management/ai-assistant-v2-new','/management/ai-4','/management/ai-5']){
  await expect(page.getByRole('navigation',{name:'Management workspace'}).locator('a[href="'+route+'"]')).toBeVisible();
 }
 await page.goto('/ai-5');
 await expect(page.getByTestId('ai5-page')).toContainText('AI-5 Assistant');
 await page.goto('/ai-4');
 await expect(page.getByTestId('ai4-page')).toBeVisible();
});

test('Open-ended multi-topic conversation changes direction and toggles BAWASLU mode',async({page})=>{
 const requests=[];
 await page.route('**/api/ai-5/chat',route=>{
  const body=route.request().postDataJSON();requests.push(body);
  return route.fulfill({status:200,contentType:'application/json',
   body:JSON.stringify(answer(body.mode))});
 });
 await login(page);await page.goto('/ai-5');
 await expect(page.getByTestId('ai5-modes').getByRole('button',{name:/General Research/})).toHaveAttribute('aria-pressed','true');
 await page.getByLabel('Ask AI-5').fill('Explain rainfall in one sentence.');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 await expect(page.getByTestId('ai5-answer').first()).toContainText('general research topic');
 await page.getByLabel('Ask AI-5').fill('Now challenge that from a completely different angle.');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 await page.getByTestId('ai5-use-bawaslu').click();
 await expect(page.getByTestId('ai5-action-options')).toBeVisible();
 await page.getByLabel('Ask AI-5').fill('How does this apply to my office?');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 await expect(page.getByTestId('ai5-answer').last()).toContainText('BAWASLU office');
 await page.getByTestId('ai5-modes').getByRole('button',{name:/General Research/}).click();
 await page.getByLabel('Ask AI-5').fill('Return to general research and change subject to astronomy.');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 expect(requests.map(x=>x.mode)).toEqual(['GENERAL_RESEARCH','GENERAL_RESEARCH',
    'BAWASLU_ACTION','GENERAL_RESEARCH']);
 expect(new Set(requests.map(x=>x.conversationId)).size).toBe(1);
 expect(requests.every(x=>x.sourceMode==='WEB_ONLY')).toBe(true);
});

test('Source mode is independent, attachments survive followups and can be removed',async({page})=>{
 const requests=[];
 await page.route('**/api/ai-5/upload',route=>route.fulfill({
  status:200,contentType:'application/json',
  body:JSON.stringify({attachment:{id:'a1',title:'analysis.txt',kind:'DOCUMENT',
    status:'READY',truncated:false,sections_count:1,url:''}})}));
 await page.route('**/api/ai-5/link',route=>route.fulfill({
  status:200,contentType:'application/json',
  body:JSON.stringify({attachment:{id:'l1',title:'Read official page',kind:'LINK',
    status:'READY',truncated:false,sections_count:1,url:u}})}));
 await page.route('**/api/ai-5/attachments/**',route=>route.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify({removed:true})}));
 await page.route('**/api/ai-5/chat',route=>{
  requests.push(route.request().postDataJSON());
  return route.fulfill({status:200,contentType:'application/json',
   body:JSON.stringify(answer('GENERAL_RESEARCH',true))});
 });
 await login(page);await page.goto('/ai-5');
 await page.locator('input[type="file"]').setInputFiles({
  name:'analysis.txt',mimeType:'text/plain',buffer:Buffer.from('Synthetic case description')});
 await expect(page.getByTestId('ai5-attachments')).toContainText('analysis.txt');
 await page.getByRole('button',{name:'Add link'}).click();
 await page.getByLabel('AI-5 public HTTPS URL').fill(u);
 await page.getByRole('button',{name:'Add',exact:true}).click();
 await expect(page.getByTestId('ai5-attachments')).toContainText('Read official page');
 await page.getByTestId('ai5-source-modes').getByRole('button',{name:/Web \+ SmartRadar/}).click();
 await page.getByLabel('Ask AI-5').fill('Compare the uploaded note against the attached link.');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 await page.getByTestId('ai5-modes').getByRole('button',{name:/Use for BAWASLU/}).click();
 await page.getByTestId('ai5-source-modes').getByRole('button',{name:/Web only/}).click();
 await page.getByLabel('Ask AI-5').fill('Now rewrite this as a short general summary.');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 expect(requests.map(x=>x.sourceMode)).toEqual(['WEB_SMARTRADAR','WEB_ONLY']);
 expect(new Set(requests.map(x=>x.conversationId)).size).toBe(1);
 await page.getByRole('button',{name:'Remove analysis.txt'}).click();
 await expect(page.getByTestId('ai5-attachments')).not.toContainText('analysis.txt');
});

test('PDF, Word and Excel buttons produce browser downloads; export requests select a turn',async({page})=>{
 const data=[];
 await page.route('**/api/ai-5/chat',route=>route.fulfill({status:200,
  contentType:'application/json',body:JSON.stringify(answer('GENERAL_RESEARCH',true))}));
 await page.route('**/api/ai-5/export/*',route=>{
  const ext=route.request().url().split('/').pop();
  data.push({ext,body:route.request().postDataJSON()});
  const bytes=Buffer.from(ext==='pdf'?'%PDF-1.4\n% Browser fixture':'PK Browser fixture file');
  return route.fulfill({status:200,body:bytes,headers:{
   'content-type':ext==='pdf'?'application/pdf':'application/octet-stream',
   'content-disposition':'attachment; filename="sample.'+ext+'"'}});
 });
 await login(page);await page.goto('/ai-5');
 await page.getByLabel('Ask AI-5').fill('Write a source-linked memo.');
 await page.getByRole('button',{name:'Ask AI-5'}).click();
 const panel=page.getByTestId('ai5-response');
 await expect(panel).toContainText('Editable deliverable');
 for(const label of ['PDF','Word','Excel']){
  const downloadPromise=page.waitForEvent('download');
  await panel.getByRole('button',{name:label,exact:true}).click();
  const item=await downloadPromise;
  await expect(item.suggestedFilename()).toMatch(/SmartRadar_AI5_.*\.(pdf|docx|xlsx)$/);
 }
 expect(data.map(x=>x.ext)).toEqual(['pdf','docx','xlsx']);
 expect(data.every(x=>x.body.turnId==='a'.repeat(32))).toBe(true);
 expect(data.every(x=>x.body.sourceMode==='WEB_ONLY')).toBe(true);
});

test('Management workspace opens AI-5 in General Research until BAWASLU is selected',async({page})=>{
 await login(page);await page.goto('/management/ai-5');
 await expect(page.getByTestId('ai5-page')).toBeVisible();
 await expect(page.getByTestId('ai5-modes').getByRole('button',{name:/General Research/})).toHaveAttribute('aria-pressed','true');
 await page.getByTestId('ai5-use-bawaslu').click();
 await expect(page.getByLabel('BAWASLU Action emphasis')).toHaveValue('MANAGEMENT');
});
