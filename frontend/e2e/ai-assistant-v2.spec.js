import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

// The examples are synthetic. No model, web, SocialCrawl or production calls.
const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}
const demoAnswer={
 workflow:'RESEARCH',perspective:'AUTO',research_status:'SOURCED',
 answer:{summary:'A synthetic saved report discusses a qualification-document question. No violation is established.',
  findings:[{claim:'The fictional record contains a disputed claim.',source_ids:['SOCIAL-12'],
     evidence_class:'REPORTED_ALLEGATION_NOT_VERIFIED',
     support:'SOURCE_LINKED_REQUIRES_REVIEW',uncertainty:'Original document is missing.'}],
  options:[],plan:[],draft:'',
  uncertainties:['Incident province not established.']},
 sources:[{id:'SOCIAL-12',title:'Simulated source — qualification document',type:'SOCIAL_LISTENING',
   date:'',location:'',location_verified:false,duplicate_of:''}],
 consulted_sources:[
  {key:'smartRadar',label:'Saved SmartRadar/BAWASLU intelligence',status:'CONSULTED',
   basis:'FIXED_SAVED_SNAPSHOT',selected_count:1,cited_source_ids:['SOCIAL-12']},
  {key:'publicWeb',label:'Public web/social research',status:'SELECTED_NOT_CONSULTED',
   basis:'NOT_CONSULTED',selected_count:0},
  {key:'legalReferences',label:'Authorized legal/reference library',status:'SELECTED_NOT_CONSULTED',
   basis:'NOT_CONSULTED',selected_count:0},
 ],
 warnings:['Simulated fixture: no public research was performed.'],
 draft_policy:'STAFF_REVIEW_ONLY_NO_SENDING_OR_APPROVAL'
};
const draftAnswer={...demoAnswer,workflow:'DRAFTING',
 answer:{...demoAnswer.answer,draft:'DRAFT MEMORANDUM\n\nTo: Leadership\nSubject: Synthetic education-record review\n\nThis is a preliminary, unverified example. [SOCIAL-12]'}};

test('new AI Assistant appears below the existing assistant and keeps research provenance',async({page})=>{
 await page.route('**/api/ai-assistant/chat',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(demoAnswer)}));
 await login(page);
 const old=page.locator('nav a[href="/assistant"]').first();
 const next=page.locator('nav a[href="/ai-assistant"]').first();
 await expect(old).toBeVisible();
 await expect(next).toBeVisible();
 await expect(next).toHaveText('AI Assistant');
 await page.goto('/ai-assistant');
 // This synthetic fixture contains saved evidence, so explicitly enable mixed mode.
 await page.getByRole('button',{name:/Web \+ SmartRadar/}).click();
 await expect(page.getByTestId('ai-assistant-v2-page')).toBeVisible();
 await page.getByRole('textbox',{name:'Ask AI Assistant'}).fill('Compare synthetic cases.');
 await page.getByRole('button',{name:'Ask AI'}).click();
 await expect(page.getByTestId('ai-assistant-v2-findings')).toContainText('fictional record');
 await page.getByTestId('ai-assistant-v2-research-trail').locator('summary').click();
 await expect(page.getByTestId('ai-assistant-v2-research-trail')).toContainText('Saved snapshot');
 await expect(page.getByTestId('ai-assistant-v2-research-trail')).toContainText('Selected · no source returned');
 await expect(page.getByTestId('ai-assistant-v2-research-trail')).toContainText('not established');
});

test('draft workflow supports edit, follow-up and review-only delivery',async({page})=>{
 const payloads=[];
 await page.route('**/api/ai-assistant/chat',async route=>{
  payloads.push(route.request().postDataJSON());
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(draftAnswer)});
 });
 await login(page);await page.goto('/ai-assistant');
 await page.getByRole('button',{name:/Draft & revise/}).click();
 await page.getByRole('textbox',{name:'Ask AI Assistant'}).fill('Draft an illustrative memo.');
 await page.getByRole('button',{name:'Ask AI'}).click();
 await expect(page.getByTestId('ai-assistant-v2-draft')).toBeVisible();
 await expect(page.getByText('For authorised staff review only.',{exact:false})).toBeVisible();
 const editor=page.getByLabel('Editable AI draft');
 await editor.fill('Revised by officer; still draft.');
 await page.getByRole('button',{name:'Shorten',exact:true}).click();
 await expect(page.getByRole('textbox',{name:'Ask AI Assistant'})).toHaveValue('Shorten the preceding draft while preserving all source caveats and citations.');
 await page.getByRole('button',{name:'Ask AI'}).click();
 expect(payloads.length).toBe(2);
 expect(payloads[1].previousDraft).toBe('Revised by officer; still draft.');
 expect(payloads[1].workflow).toBe('DRAFTING');
 expect(payloads[1].sourceMode).toBe('WEB_ONLY');
 expect(payloads[1].sources.smartRadar).toBe(false);
 expect(payloads[1].sources.publicWeb).toBe(true);
 expect(payloads[1].sources.legalReferences).toBe(false);
});

test('Web only, mixed and saved-only modes produce exact authorized source flags',async({page})=>{
 const payloads=[];
 await page.route('**/api/ai-assistant/chat',async route=>{
  payloads.push(route.request().postDataJSON());
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(demoAnswer)});
 });
 await login(page);await page.goto('/ai-assistant');
 await expect(page.getByRole('button',{name:/Web only/})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('textbox',{name:'Ask AI Assistant'}).fill('What happened recently?');
 await page.getByRole('button',{name:'Ask AI'}).click();
 expect(payloads[0].sourceMode).toBe('WEB_ONLY');
 expect(payloads[0].sources).toEqual({smartRadar:false,publicWeb:true,legalReferences:false});
 await page.getByRole('button',{name:/Web \+ SmartRadar/}).click();
 await page.getByRole('textbox',{name:'Ask AI Assistant'}).fill('Compare authorized records and public pages');
 await page.getByRole('button',{name:'Ask AI'}).click();
 expect(payloads[1].sourceMode).toBe('WEB_SMARTRADAR');
 expect(payloads[1].sources).toEqual({smartRadar:true,publicWeb:true,legalReferences:true});
 await page.getByRole('button',{name:/SmartRadar only/}).click();
 await page.getByRole('textbox',{name:'Ask AI Assistant'}).fill('Summarize local records');
 await page.getByRole('button',{name:'Ask AI'}).click();
 expect(payloads[2].sourceMode).toBe('SMARTRADAR_ONLY');
 expect(payloads[2].sources).toEqual({smartRadar:true,publicWeb:false,legalReferences:true});
});
