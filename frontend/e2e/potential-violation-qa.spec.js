import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

// Build 72.3: Deterministic UI regression tests. No provider, crawl, or AI calls.
const PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
const source='Seorang warga melaporkan dugaan pembagian uang kepada pemilih di lokasi kampanye.';
const findings=[
 {id:'101',campaign_id:'1',campaign_name:'QA Campaign',platform:'instagram',text_content:source,
  relevance_label:'RELEVANT',relevance_confidence:'HIGH',explanation:'Preliminary allegation in source content; requires independent verification.',
  location_signals:['Jakarta'],candidate_signals:[],potential_issues:[{category_id:7,category_name:'Politik Uang',evidence_quote:'pembagian uang kepada pemilih',explanation:'Preliminary signal only',signal_provenance:'LEGACY_MISSING_TYPE',requires_human_verification:true}],
  assessment_version:1,model_version:'mock-fixture',canonical_url:'https://example.org/source/101',can_review_flag:false},
 {id:'102',campaign_id:'1',campaign_name:'QA Campaign',platform:'x',text_content:'Diskusi kebijakan publik tanpa dugaan pelanggaran.',
  relevance_label:'RELEVANT',relevance_confidence:'HIGH',explanation:'Relevant policy discussion, no violation evidence.',
  location_signals:[],candidate_signals:[],potential_issues:[],assessment_version:1,model_version:'mock-fixture',can_review_flag:false},
 {id:'103',campaign_id:'1',campaign_name:'QA Campaign',platform:'instagram',text_content:'Komentar mengenai pemilihan dan debat kandidat.',
  relevance_label:'RELEVANT',relevance_confidence:'MEDIUM',explanation:'Topically relevant only.',
  location_signals:[],candidate_signals:[],potential_issues:[],assessment_version:1,model_version:'mock-fixture',can_review_flag:false},
];
const payload={findings,campaigns:[{id:'1',name:'QA Campaign'}],unassessed_count:0,
 assessment_counts:{PENDING:0,RELEVANT:3,IRRELEVANT:0,UNCERTAIN:0,OTHER:0},
 job_counts:{PENDING:0,PROCESSING:0,COMPLETED:3,FAILED:0},reconciliation:null,processing_status:'Stored QA data'};

async function setup(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill('admin@bawaslu.local');
 await page.getByLabel(/^password$/i).fill(PASSWORD);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
 let providerCalls=0;
 await page.route('**/api/functions/socialListening', async route=>{
  const body=route.request().postDataJSON();
  if(body.action==='campaignIntelligenceInbox'){
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload)});
  }else{
   providerCalls++;
   await route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({detail:'Paid action blocked by QA'})});
  }
 });
 await page.goto('/inbox');
 await expect(page.getByRole('heading',{name:'AI-screened intelligence findings'})).toBeVisible();
 return ()=>providerCalls;
}

test('historical review decisions render in the collapsed drawer on demand',async({page})=>{
 const withHistory={...payload,findings:findings.map((item,index)=>index===0?{...item,
  flag_review_status:'FLAG_DISMISSED',
  flag_review_history:[
   {decision:'FLAG_DISMISSED',assessment_version:2,reviewer_id:'officer-2',
    rationale:'Insufficient independent source evidence',reviewed_at:'2026-10-18T10:00:00'},
   {decision:'FURTHER_INVESTIGATION',assessment_version:1,reviewer_id:'officer-1',
    rationale:'Additional corroboration required',reviewed_at:'2026-10-17T10:00:00'}
  ]}:item)};
 await page.goto('/login');
 await page.getByLabel(/email/i).fill('admin@bawaslu.local');
 await page.getByLabel(/^password$/i).fill(PASSWORD);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
 let paidCalls=0;
 await page.route('**/api/functions/socialListening',async route=>{
  if(route.request().postDataJSON().action==='campaignIntelligenceInbox'){
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(withHistory)});
  }else{
   paidCalls++;
   await route.fulfill({status:400,contentType:'application/json',body:'{}'});
  }
 });
 await page.goto('/inbox');
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer.getByText('Review history (2 most recent)')).toBeVisible();
 await expect(drawer.getByText('Insufficient independent source evidence')).not.toBeVisible();
 await drawer.getByText('Review history (2 most recent)').click();
 await expect(drawer.getByText('Insufficient independent source evidence')).toBeVisible();
 await expect(drawer.getByText('Additional corroboration required')).toBeVisible();
 await expect(drawer.getByText('Assessment v2')).toBeVisible();
 await expect(drawer.locator('details[open] li').filter({hasText:'Assessment v1'})).toHaveCount(1);
 expect(paidCalls).toBe(0);
});

test('flag count and category filter stay consistent with the evidence list',async({page})=>{
 const paidCalls=await setup(page);
 await expect(page.getByText('Potential violations · signals only')).toBeVisible();
 await expect(page.getByText('Posts shown').locator('..')).toContainText('3');
 await expect(page.getByText('Potential violations · signals only').locator('..')).toContainText('1');
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await expect(page.getByText('Posts · 1 results')).toBeVisible();
 await expect(page.getByRole('button',{name:/View source and assessment/})).toHaveCount(1);
 await expect(page.getByText('Potential violations · signals only').locator('..')).toContainText('1');
 expect(paidCalls()).toBe(0);
});

test('non-flagged political discussion is not labeled a potential violation',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'All Relevant'}).click();
 await expect(page.getByRole('button',{name:/View source and assessment/})).toHaveCount(3);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await expect(page.getByText('Diskusi kebijakan publik tanpa dugaan pelanggaran.')).toHaveCount(0);
 expect(paidCalls()).toBe(0);
});

test('flag detail presents the configured category as preliminary evidence, not a verdict',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer).toBeVisible();
 await expect(drawer.getByText('Politik Uang')).toBeVisible();
 await expect(drawer.getByRole('note')).toContainText('Human verification required');
 await expect(drawer.getByRole('link',{name:/Open original source/})).toHaveAttribute('href','https://example.org/source/101');
 expect(paidCalls()).toBe(0);
});


test('legacy source-supported flag is disclosed without treating it as a verdict',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer.getByRole('note')).toContainText('Legacy AI signal (original type missing)');
 await expect(drawer.getByRole('note')).toContainText('Human verification required');
 expect(paidCalls()).toBe(0);
});


test('users without human validation authority see review guidance but no decision controls',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer.getByText('Human validation permission is required for review actions.')).toBeVisible();
 await expect(drawer.getByRole('button',{name:'Save human review'})).toHaveCount(0);
 await expect(drawer.getByRole('note')).toContainText('Human verification required');
 expect(paidCalls()).toBe(0);
});


test('review history absent for unreviewed evidence without paid calls',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer).toBeVisible();
 await expect(drawer.getByText('Review history (', {exact:false})).toHaveCount(0);
 expect(paidCalls()).toBe(0);
});
