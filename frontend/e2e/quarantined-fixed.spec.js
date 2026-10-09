import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const ADMIN_EMAIL='admin@bawaslu.local';
const ADMIN_PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
const ANALYST_EMAIL='qa.fixed.analyst@example.com';
const ANALYST_PASSWORD=['qa','fixed','analyst','local'].join('-');

async function loginToken(request,email,password){
  const r=await request.post('/api/auth/login',{data:{email,password}});
  expect(r.ok()).toBeTruthy();
  return (await r.json()).access_token;
}
async function registry(request,token,action,data={},id=null){
  return request.post('/api/functions/registry',{headers:{Authorization:'Bearer '+token},data:{action,data,id}});
}
async function intelligence(request,token,action,data={},id=null){
  return request.post('/api/functions/intelligence',{headers:{Authorization:'Bearer '+token},data:{action,data,id}});
}
async function ensureAnalyst(request){
  const reg=await request.post('/api/auth/register',{data:{email:ANALYST_EMAIL,password:ANALYST_PASSWORD,full_name:'QA Fixed Analyst'}});
  expect([200,409]).toContain(reg.status());
  const adminToken=await loginToken(request,ADMIN_EMAIL,ADMIN_PASSWORD);
  const list=await registry(request,adminToken,'users');
  const analyst=(await list.json()).users.find(x=>x.email===ANALYST_EMAIL);
  const assign=await registry(request,adminToken,'setUser',{
    access_role:'Provincial Analyst',geographic_scope:'Province',province:'Bali',regency_city:'',status:'Active',
    permissions:{view_intelligence:true,add_intelligence:true,edit_intelligence:true,review_ai_suggestions:true,human_validation:false,verify_evidence:false,manage_watchlist:false,upload_evidence:true,manage_users:false,administration:false}
  },analyst.id);
  expect(assign.ok()).toBeTruthy();
}
async function uiLogin(page,email,password){
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/^password$/i).fill(password);
  await page.getByRole('button',{name:/log in|masuk/i}).click();
  await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}

test.beforeEach(async({request})=>{await ensureAnalyst(request);});

test('fixed provincial analyst navigation selectors',async({page})=>{
  await uiLogin(page,ANALYST_EMAIL,ANALYST_PASSWORD);
  const nav=page.getByRole('navigation');
  await expect(nav.getByRole('link',{name:/intelligence inbox/i})).toBeVisible();
  await expect(nav.getByRole('link',{name:/intelligence assistant/i})).toBeVisible();
  await expect(nav.getByRole('link',{name:/add intelligence/i})).toBeVisible();
  await expect(nav.getByRole('link',{name:/data sources/i})).toHaveCount(0);
  await expect(nav.getByRole('link',{name:/validation/i})).toHaveCount(0);
  await expect(nav.getByRole('link',{name:/administration/i})).toHaveCount(0);
  for(const route of ['/sources','/validation','/administration']){
    await page.goto(route);
    await expect(page.getByRole('alert')).toContainText(/access denied/i);
  }
});

test('fixed Data Sources province selectors',async({page})=>{
  await uiLogin(page,ADMIN_EMAIL,ADMIN_PASSWORD);
  await page.goto('/sources');
  await page.getByRole('button',{name:/register source/i}).click();
  const form=page.locator('form');
  await form.getByLabel(/^name/i).fill('Playwright Fixed Source');
  await form.getByLabel(/source type/i).selectOption('OFFICIAL_SOURCE');
  await form.getByLabel(/source status/i).selectOption('Active');
  const selects=form.locator('select');
  await selects.nth(2).selectOption({label:'Bali'});
  await selects.nth(3).selectOption({label:'Kabupaten Bangli'});
  await form.getByLabel(/description/i).fill('Automated fixed-selector QA source');
  await form.getByRole('button',{name:/save source/i}).click();
  await expect(page.getByText('Playwright Fixed Source')).toBeVisible();
  await expect(page.getByText(/Kabupaten Bangli, Bali/)).toBeVisible();
});

test('fixed validation card selector uses exact intelligence code',async({page,request})=>{
  const adminToken=await loginToken(request,ADMIN_EMAIL,ADMIN_PASSWORD);
  const created=await intelligence(request,adminToken,'create',{
    title:'Playwright Fixed Validation Record',original_content:'Synthetic local QA evidence only.',
    source_type:'MANUAL_ENTRY',evidence_type:'OBSERVED',verification_status:'UNVERIFIED',
    review_status:'Pending Review',priority:'Medium',jurisdiction_type:'Unresolved'
  });
  const record=(await created.json()).item;
  const blocked=await intelligence(request,adminToken,'review',{decision:'Validated as Relevant Intelligence',review_notes:'QA'},record.id);
  expect(blocked.status()).toBe(400);
  const confirm=await intelligence(request,adminToken,'confirmJurisdiction',{jurisdiction_type:'Province',province:'Bali',regency_city:''},record.id);
  expect(confirm.ok()).toBeTruthy();

  await uiLogin(page,ADMIN_EMAIL,ADMIN_PASSWORD);
  await page.goto('/validation');
  const card=page.getByRole('article').filter({has:page.getByRole('link',{name:record.intelligence_id,exact:true})});
  await expect(card).toBeVisible();
  await card.getByRole('combobox').selectOption({label:'Validated as Relevant Intelligence'});
  await card.getByRole('button',{name:/record decision/i}).click();
  await expect(page.getByRole('status')).toContainText(/human validation decision saved/i);
});
