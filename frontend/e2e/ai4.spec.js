import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

// All HTTP replies below are explicit simulated fixtures, not live web results.
const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}
const url='https://bawaslu.go.id/synthetic-ai4-fixture';
function reply(workspace='OPERATIONAL',attachment=false){
 return {assistant:'AI-4',turn_id:'a'.repeat(32),workspace,perspective:'AUTO',source_mode:'WEB_ONLY',
  answer:{lead:'Your office should verify the latest original announcement before any action.',
   findings:[{text:'A synthetic official notice is available for checking.',source_ids:['WEB-1']},
             ...(attachment?[{text:'The uploaded case note requires corroboration.',source_ids:['FILE-ABC123-1']}]:[])],
   comparison:[{option:'Review original record',benefit:'Better provenance',
     tradeoff:'Review time',responsible_role:'BAWASLU reviewer',
     timeframe:'Proposed week one',source_ids:['WEB-1']}],
   next_steps:[{action:'Confirm jurisdiction and election stage',owner_role:'Legal reviewer',
     review_point:'Before official filing',source_ids:['WEB-1']}],
   uncertainties:['This is a synthetic controlled test.'],clarifying_question:'',
   draft:attachment?'DRAFT MEMO — evidence still needs verification.':'',
   review_required:true,actions_executed:false},
  source_trail:{public_status:'READ_SOURCES_AVAILABLE',searched_at:'2026-11-24T04:00:00Z',
   read_public_count:1,saved_count:0,attached_count:attachment?1:0,
   queries:['official announcement latest'],passes:[],warnings:[],
   sources:[{id:'WEB-1',title:'Synthetic official announcement',type:'PUBLIC_OFFICIAL',
    read_status:'READ',basis:'LIVE_PUBLIC_LOOKUP',published_at:'2026-11-24',
    url,updated_at:'',reason:'Simulated read result'},
    ...(attachment?[{id:'FILE-ABC123-1',title:'review.txt · section 1',type:'ATTACHMENT_TXT',
      read_status:'READ',basis:'OFFICER_UPLOADED_UNVERIFIED',section:'section 1',
      url:'',published_at:'',reason:'Officer-supplied test excerpt'}]:[])]},
  synthesis_status:'COMPLETE',human_review_required:true,actions_executed:false}
}
test('AI-4 and old AI Assistant remain separate navigation entries',async({page})=>{
 await login(page);
 const op=page.getByRole('navigation',{name:'Operational workspace'});
 const mgmt=page.getByRole('navigation',{name:'Management workspace'});
 for(const href of ['/assistant','/ai-assistant','/ai-assistant-v2-new','/ai-4']){
  await expect(op.locator('a[href="'+href+'"]')).toBeVisible();
 }
 for(const href of ['/management/assistant','/management/ai-assistant',
                    '/management/ai-assistant-v2-new','/management/ai-4']){
  await expect(mgmt.locator('a[href="'+href+'"]')).toBeVisible();
 }
 await page.goto('/ai-4');
 await expect(page.getByTestId('ai4-page')).toContainText('AI Assistant (New)');
 await page.goto('/ai-assistant');
 await expect(page.getByTestId('unified-ai-page')).toBeVisible();
});
test('AI-4 Web only presents source-linked officer guidance and expandable trace',async({page})=>{
 const calls=[];
 await page.route('**/api/ai-4/chat',route=>{
  calls.push(route.request().postDataJSON());
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply())});
 });
 await login(page);await page.goto('/ai-4');
 await expect(page.getByTestId('ai4-source-modes').getByRole('button',{name:/Web only/})).toHaveAttribute('aria-pressed','true');
 await page.getByLabel('Ask AI-4').fill('What changed in the latest official public announcement?');
 await page.getByRole('button',{name:'Ask AI-4'}).click();
 await expect(page.getByTestId('ai4-lead')).toContainText('Your office should verify');
 await expect(page.getByTestId('ai4-finding').first().getByRole('link')).toHaveAttribute('href',url);
 await page.getByTestId('ai4-research-trail').locator('summary').first().click();
 await expect(page.getByTestId('ai4-research-trail')).toContainText('2026-11-24');
 await expect(page.getByTestId('ai4-research-trail')).toContainText('Read');
 expect(calls[0].sourceMode).toBe('WEB_ONLY');
 expect(calls[0].conversationId).toMatch(/^[0-9a-f-]{36}$/);
});
test('AI-4 upload remains available during follow-up and can be removed',async({page})=>{
 const payloads=[];
 await page.route('**/api/ai-4/upload',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({attachment:{
   id:'attachment123',kind:'DOCUMENT',status:'READY',title:'review.txt',url:'',
   sections_count:1,truncated:false}})}));
 await page.route('**/api/ai-4/attachments/**',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({removed:true})}));
 await page.route('**/api/ai-4/chat',route=>{
  payloads.push(route.request().postDataJSON());
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply('OPERATIONAL',true))});
 });
 await login(page);await page.goto('/ai-4');
 await page.locator('input[type="file"]').setInputFiles({name:'review.txt',mimeType:'text/plain',
  buffer:Buffer.from('Synthetic review note to cite and verify.')});
 await expect(page.getByTestId('ai4-attachments')).toContainText('review.txt');
 await expect(page.getByTestId('ai4-attachments')).toContainText('READY');
 await page.getByLabel('Ask AI-4').fill('Review the uploaded file for evidence gaps.');
 await page.getByRole('button',{name:'Ask AI-4'}).click();
 await expect(page.getByTestId('ai4-finding').nth(1)).toContainText('uploaded case note');
 await page.getByRole('button',{name:'Shorten'}).click();
 await expect(page.getByLabel('Ask AI-4')).toHaveValue(/Shorten the previous draft/);
 await page.getByRole('button',{name:'Ask AI-4'}).click();
 expect(payloads[0].conversationId).toBe(payloads[1].conversationId);
 expect(payloads[1].previousDraft).toContain('DRAFT MEMO');
 await page.getByRole('button',{name:'Remove review.txt'}).click();
 await expect(page.getByTestId('ai4-attachments')).toHaveCount(0);
});
test('AI-4 reads a public link and records evaluation feedback',async({page})=>{
 await page.route('**/api/ai-4/link',route=>
  route.fulfill({status:200,contentType:'application/json',
    body:JSON.stringify({attachment:{id:'link123',title:'Official test page',
      kind:'LINK',status:'READY',url,sections_count:1,truncated:false}})}));
 await page.route('**/api/ai-4/chat',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply())}));
 let evaluated=null;
 await page.route('**/api/ai-4/feedback',route=>{
  evaluated=route.request().postDataJSON();
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({saved:true,count:1})});
 });
 await login(page);await page.goto('/ai-4');
 await page.getByRole('button',{name:'Add link'}).click();
 await page.getByLabel('Public HTTPS URL').fill(url);
 await page.getByRole('button',{name:'Add',exact:true}).click();
 await expect(page.getByTestId('ai4-attachments')).toContainText('Official test page');
 await page.getByLabel('Ask AI-4').fill('Assess this official publication');
 await page.getByRole('button',{name:'Ask AI-4'}).click();
 await page.getByTestId('ai4-feedback').locator('summary').click();
 await page.getByLabel('AI-4 Clarity').selectOption('4');
 await page.getByLabel('AI-4 Source quality').selectOption('3');
 await page.getByLabel('AI-4 Useful for Bawaslu work').selectOption('5');
 await page.getByRole('button',{name:'Save feedback'}).click();
 await expect(page.getByTestId('ai4-feedback')).toContainText('Evaluation saved');
 expect(evaluated.usefulness).toBe(5);
});
test('Management AI-4 remains independent with leadership emphasis',async({page})=>{
 await page.route('**/api/ai-4/chat',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply('MANAGEMENT'))}));
 await login(page);await page.goto('/management/ai-4');
 await expect(page.getByTestId('ai4-page')).toContainText('Management');
 await page.getByLabel('Ask AI-4').fill('What should leadership decide next?');
 await page.getByRole('button',{name:'Ask AI-4'}).click();
 await expect(page.getByTestId('ai4-response')).toContainText('Realistic options and trade-offs');
});
