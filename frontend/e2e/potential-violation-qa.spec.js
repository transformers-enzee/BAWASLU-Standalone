import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

// Build 72.3: Deterministic UI regression tests. No provider, crawl, or AI calls.
const PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
const source='SIMULASI / FIKTIF: Seorang warga mengaku melihat pembagian uang kepada pemilih di lokasi kampanye. Belum ada bukti independen; perlu diverifikasi.';
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
 await expect(drawer.getByLabel('Potential issue evidence')).toContainText('Politik Uang');
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

test('authorized officer can save a review and see the updated status without reloading',async({page})=>{
 const reviewable={...payload,findings:findings.map((item,index)=>index===0?{...item,can_review_flag:true}:item)};
 await page.goto('/login');
 await page.getByLabel(/email/i).fill('admin@bawaslu.local');
 await page.getByLabel(/^password$/i).fill(PASSWORD);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
 let reviewCalls=0,unexpectedCalls=0;
 await page.route('**/api/functions/socialListening',async route=>{
  const request=route.request().postDataJSON();
  if(request.action==='campaignIntelligenceInbox'){
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reviewable)});
  }else if(request.action==='campaignFlagReview'){
   reviewCalls++;
   expect(request.id).toBe('1');
   expect(request.data.result_id).toBe('101');
   expect(request.data.assessment_version).toBe(1);
   expect(request.data.decision).toBe('FURTHER_INVESTIGATION');
   expect(request.data.rationale).toContain('Further source verification');
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({saved:true,decision:request.data.decision,review_id:'77',paid_provider_called:false})});
  }else{
   unexpectedCalls++;
   await route.fulfill({status:400,contentType:'application/json',body:'{}'});
  }
 });
 await page.goto('/inbox');
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await drawer.locator('#flag-review-decision').selectOption('FURTHER_INVESTIGATION');
 await drawer.getByLabel(/Reason for decision/).fill('Further source verification is required.');
 page.once('dialog',dialog=>dialog.accept());
 await drawer.getByRole('button',{name:'Save human review'}).click();
 await expect(drawer.getByText('Current status:').locator('..')).toContainText('FURTHER_INVESTIGATION');
 await expect(drawer.getByRole('status')).toContainText('Human review decision saved');
 expect(reviewCalls).toBe(1);
 expect(unexpectedCalls).toBe(0);
});

test('location and candidate filters compose with potential violation selection',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByLabel('Jurisdiction').selectOption('province');
 await page.getByLabel('Select location').selectOption('DKI Jakarta');
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await expect(page.getByText('Posts · 1 results')).toBeVisible();
 await page.getByLabel('Select candidate').selectOption({index:0});
 await page.getByLabel('Jurisdiction').selectOption('national');
 await expect(page.getByText('Posts · 1 results')).toBeVisible();
 expect(paidCalls()).toBe(0);
});




test('candidate filter retains posts with no extracted candidate',async({page})=>{
 const paidCalls=await setup(page);
 const selector=page.getByLabel('Select candidate');
 await expect(selector.locator('option[value="__no_candidate__"]')).toHaveCount(1);
 await selector.selectOption('__no_candidate__');
 await expect(page.getByText('Posts · 3 results')).toBeVisible();
 await selector.selectOption('');
 await expect(page.getByText('Posts · 3 results')).toBeVisible();
 expect(paidCalls()).toBe(0);
});


test('nationwide jurisdiction retains unlocated posts and province narrows only supported signals',async({page})=>{
 const paidCalls=await setup(page);
 const jurisdiction=page.getByLabel('Jurisdiction');
 await expect(jurisdiction).toHaveValue('national');
 await expect(page.getByText('Posts · 3 results')).toBeVisible();
 await jurisdiction.selectOption('unresolved');
 await expect(page.getByText('Posts · 2 results')).toBeVisible();
 await jurisdiction.selectOption('province');
 await page.getByLabel('Select location').selectOption('DKI Jakarta');
 await expect(page.getByText('Posts · 1 results')).toBeVisible();
 expect(paidCalls()).toBe(0);
});


test('Inbox shows two primary views while jurisdiction and candidate remain filters',async({page})=>{
 const paidCalls=await setup(page);
 const filters=page.getByRole('region',{name:'Find and filter intelligence'});
 await expect(page.getByRole('button',{name:'All Relevant',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Potential Violation',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Location',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Candidate',exact:true})).toHaveCount(0);
 await expect(page.getByLabel('Jurisdiction')).toBeVisible();
 await expect(page.getByLabel('Select candidate')).toBeVisible();
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await expect(page.getByText('Posts · 1 results')).toBeVisible();
 expect(paidCalls()).toBe(0);
});


test('authorized officer sees manual flag form for relevant evidence without AI flags',async({page})=>{
 const manual={...payload,issue_categories:[{id:7,name:'Politik Uang'}],findings:findings.map((x,i)=>i===1?{...x,can_review_flag:true,is_flagged:false}:x)};
 await page.goto('/login');
 await page.getByLabel(/email/i).fill('admin@bawaslu.local');
 await page.getByLabel(/^password$/i).fill(PASSWORD);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
 let flags=0;
 await page.route('**/api/functions/socialListening',async route=>{
  const req=route.request().postDataJSON();
  if(req.action==='campaignIntelligenceInbox')return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(manual)});
  if(req.action==='campaignManualFlag'){
   flags++;
   expect(req.data.result_id).toBe('102');
   expect(String(req.data.category_id)).toBe('7');
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({saved:true,decision:'FURTHER_INVESTIGATION',paid_provider_called:false})});
  }
  throw new Error('Unexpected provider request: '+req.action);
 });
 await page.goto('/inbox');
 await page.getByRole('button',{name:/View source and assessment/}).nth(1).click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer.getByText('Flag this relevant post manually')).toBeVisible();
 await expect(drawer.getByRole('button',{name:'Save human review'})).toHaveCount(0);
 await drawer.locator('#manual-issue-category').selectOption('7');
 await drawer.locator('#manual-flag-rationale').fill('Requires additional source verification');
 page.once('dialog',dialog=>dialog.accept());
 await drawer.getByRole('button',{name:'Flag for investigation'}).click();
 await expect(drawer.getByText(/Human-origin preliminary flag saved/)).toBeVisible();
 expect(flags).toBe(1);
});

test('Potential issue category filters evidence and shows quotes without paid calls',async({page})=>{
 const paidCalls=await setup(page);
 const issue=page.getByLabel('Potential issue category');
 await issue.selectOption('Politik Uang');
 await expect(page.getByText('Posts · 1 results')).toBeVisible();
 await page.getByRole('button',{name:/View source and assessment/}).click();
 await expect(page.getByRole('dialog',{name:'Finding details'}).getByLabel('Potential issue evidence')).toContainText('pembagian uang kepada pemilih');
 expect(paidCalls()).toBe(0);
});

test('flagged inbox post shows preliminary review state without implying a verdict',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 await expect(page.getByRole('button',{name:/View source and assessment/})).toContainText('Awaiting human review');
 expect(paidCalls()).toBe(0);
});

test('synthetic preliminary vote-buying claim is visibly identified as a QA fixture',async({page})=>{
 const paidCalls=await setup(page);
 await page.getByRole('button',{name:'Potential Violation',exact:true}).click();
 const post=page.getByRole('button',{name:/View source and assessment/}).first();
 await expect(post).toContainText('Synthetic QA example');
 await post.click();
 const drawer=page.getByRole('dialog',{name:'Finding details'});
 await expect(drawer.getByRole('note',{name:''}).filter({hasText:'Synthetic QA example'})).toContainText('not a real social-media post');
 await expect(drawer.getByLabel('Potential issue evidence')).toContainText('pembagian uang kepada pemilih');
 await expect(drawer).toContainText('Human verification required');
 expect(paidCalls()).toBe(0);
});
