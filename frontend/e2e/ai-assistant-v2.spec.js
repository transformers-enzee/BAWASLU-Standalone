import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

// Controlled simulated fixtures: NO live provider, SocialCrawl, case mutation,
// or assertion that Bryan/Grace have performed an actual user review.
const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}
const NEW='https://bawaslu.go.id/notice/revised';
const OLD='https://bawaslu.go.id/notice/older';
function source(id,kind,url,when,status='READ'){
 return {id,type:kind,url,title:id==='WEB-1'?'Simulated newest official correction':'Simulated earlier official notice',
  read_status:status,basis:'LIVE_PUBLIC_LOOKUP',published_at:when,updated_at:'',location_verified:false,
  duplicate_of:'',excerpt:'Synthetic official notice text; not a real publication',
  reliability:'OFFICIAL_PUBLICATION_UNVERIFIED',reason:'Page content was read in this controlled fixture'};
}
function reply(workspace='OPERATIONAL',draft=false){
 return {assistant_version:'UNIFIED_AI_V1',workspace,workflow:draft?'DRAFTING':'RESEARCH',
  source_mode:'WEB_ONLY',perspective:'AUTO',
  answer:{lead:'Controlled example: the newer official notice supersedes the earlier notice.',
    first_step:'Verify the latest original notice before proceeding.',
    attention:'WATCH',confidence:'MODERATE',
    what_changed:'The newer simulated source carries a revised date.',
    why_it_matters:'Dates affect what the officer should verify.',
    geographic_implications:'No verified incident location.',
    institutional_implications:'BAWASLU jurisdiction requires review.',
    recommendation:'Use the newer substantiated notice provisionally and check authority.',
    findings:[{claim:'The simulated newer notice supersedes the older document.',
      source_ids:['WEB-1'],uncertainty:'No actual official case or source was queried.'}],
    options:[{title:'Verify first',benefit:'Correct date',tradeoff:'Officer time',reason:'Lower risk',source_ids:['WEB-1']}],
    plan:[{task:'Check revised announcement',owner_role:'Authorised legal reviewer',
      milestone:'Proposed day 1',review_point:'Officer sign-off',evidence_needed:'Original notice',
      decision_gate:'Escalate only with valid jurisdiction',source_ids:['WEB-1'],state:'DRAFT_NOT_ASSIGNED_OR_APPROVED'}],
    legal_checks:['Verify controlling legal rule and deadline.'],
    watch_next:['Possible further official correction.'],
    uncertainties:['No national trend can be inferred.'],
    draft:draft?'SIMULATED DRAFT MEMO\n\nThis content requires officer review [WEB-1].':'',
  },
  sources:[source('WEB-1','PUBLIC_OFFICIAL',NEW,'2026-11-24'),
           source('WEB-2','PUBLIC_OFFICIAL',OLD,'2026-11-20')],
  source_consultation:[
   {key:'publicWeb',label:'Public web and official sources',selected:true,status:'READ_SOURCES_AVAILABLE',
     read_count:2,snippet_count:0,inaccessible_count:0,basis:'LIVE_PUBLIC_LOOKUP'},
   {key:'smartRadar',label:'SmartRadar records',selected:false,status:'NOT_SELECTED',basis:'NOT_SELECTED',count:0},
   {key:'legalReferences',label:'Reference library',selected:false,status:'NOT_SELECTED',basis:'NOT_SELECTED',count:0}
  ],
  public_research:{status:'READ_SOURCES_AVAILABLE',read_count:2,as_of:'2026-11-24T03:00:00Z',
   date_window:{start:'2026-11-11',end:'2026-11-24'},
   attempts:[{phase:'discovery',status:'DISCOVERED',discovered:2},
             {phase:'newest updates/corrections',status:'DISCOVERED',discovered:1}],
   queries:['perubahan pengumuman terbaru','newest official correction']},
  warnings:['SIMULATED_FIXTURE; no actual public search performed.'],
  review_policy:'DRAFT_ONLY_AUTHORISED_OFFICER_REVIEW'}
}
test('Web only first: Operational response uses newest readable official page and no saved source',async({page})=>{
 const payloads=[];
 await page.route('**/api/ai-assistant/chat',route=>{
  payloads.push(route.request().postDataJSON());
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply())});
 });
 await login(page);await page.goto('/ai-assistant');
 await expect(page.getByTestId('unified-ai-page')).toBeVisible();
 const modes=page.getByTestId('unified-source-modes');
 await expect(modes.getByRole('button',{name:/Web only/})).toHaveAttribute('aria-pressed','true');
 await page.getByLabel('Ask AI Assistant').fill('What changed in official guidance in the past 2 weeks?');
 await page.getByRole('button',{name:'Ask AI'}).click();
 await expect(page.getByTestId('unified-ai-answer')).toContainText('Verify the latest original notice');
 await expect(page.getByTestId('unified-finding')).toContainText('WEB-1');
 await expect(page.getByTestId('unified-finding').getByRole('link')).toHaveAttribute('href',NEW);
 await page.getByTestId('unified-research-trail').locator('summary').first().click();
 await expect(page.getByTestId('unified-research-trail')).toContainText('2026-11-24');
 await expect(page.getByTestId('unified-research-trail')).toContainText('Read · original page opened');
 expect(payloads).toHaveLength(1);
 expect(payloads[0].sourceMode).toBe('WEB_ONLY');
 expect(payloads[0].workspace).toBe('OPERATIONAL');
 expect(JSON.stringify(payloads[0])).not.toContain('SOCIAL-740');
});
test('Management mode leads with executive conclusion, attention and conditional plan',async({page})=>{
 await page.route('**/api/ai-assistant/chat',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply('MANAGEMENT'))}));
 await login(page);await page.goto('/management');
 await expect(page.getByTestId('executive-brief')).toBeVisible();
 await page.goto('/management/ai-assistant');
 await expect(page.getByTestId('unified-ai-page')).toContainText('Management intelligence');
 await page.getByLabel('Ask AI Assistant').fill('What decision needs leadership review?');
 await page.getByRole('button',{name:'Ask AI'}).click();
 await expect(page.getByTestId('unified-ai-answer')).toContainText('Executive conclusion');
 await expect(page.getByTestId('unified-ai-answer')).toContainText('Attention: WATCH');
 await expect(page.getByTestId('unified-action')).toContainText('Authorised legal reviewer');
});
test('Can switch source modes, edit a memo and continue drafting without sending',async({page})=>{
 const payloads=[];
 await page.route('**/api/ai-assistant/chat',route=>{
  payloads.push(route.request().postDataJSON());
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reply('OPERATIONAL',true))});
 });
 await login(page);await page.goto('/ai-assistant');
 const modes=page.getByTestId('unified-source-modes');
 await modes.getByRole('button',{name:/Web \+ SmartRadar/}).click();
 await page.getByLabel('Assistant workflow').selectOption('DRAFTING');
 await page.getByLabel('Ask AI Assistant').fill('Draft a redacted leadership memo.');
 await page.getByRole('button',{name:'Ask AI'}).click();
 await expect(page.getByTestId('unified-ai-draft')).toBeVisible();
 await page.getByTestId('unified-ai-draft').fill('Revised draft by reviewer. Not approved.');
 await page.getByRole('button',{name:'Shorten',exact:true}).click();
 await expect(page.getByLabel('Ask AI Assistant')).toContainText('Shorten the draft');
 await page.getByRole('button',{name:'Ask AI'}).click();
 expect(payloads[0].sourceMode).toBe('WEB_SMARTRADAR');
 expect(payloads[1].previousDraft).toBe('Revised draft by reviewer. Not approved.');
 expect(payloads[1].workflow).toBe('DRAFTING');
 await modes.getByRole('button',{name:/SmartRadar only/}).click();
 await expect(page.getByTestId('unified-ai-answer')).toHaveCount(0);
});
test('Controlled SOCIAL-740/SOCIAL-1160 walkthrough is explicitly unverified and private',async({page})=>{
 await login(page);await page.goto('/ai-assistant');
 await page.getByText('Controlled officer walkthrough', {exact:false}).click();
 await page.getByRole('button',{name:/Prepare controlled review question/}).click();
 await expect(page.getByTestId('unified-source-modes').getByRole('button',{name:/SmartRadar only/}))
  .toHaveAttribute('aria-pressed','true');
 await expect(page.getByLabel('Ask AI Assistant')).toHaveValue(/SOCIAL-740 and SOCIAL-1160/);
 await expect(page.getByText('These IDs do not establish a violation',{exact:false})).toBeVisible();
});
