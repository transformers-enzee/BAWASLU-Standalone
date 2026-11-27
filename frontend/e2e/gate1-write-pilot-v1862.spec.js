import fs from 'node:fs';
import {test, expect} from '@playwright/test';

// Real browser -> Vite -> FastAPI -> disposable PostgreSQL. No mocks.
// This suite MUST NOT run against Render/Supabase or ordinary Playwright DB.
const LOCAL_URL='http://127.0.0.1:5173';
const PASSWORD='Fictional-Gate1-CI-Only-1862!';
const url=process.env.PLAYWRIGHT_BASE_URL||'';
const enabled=process.env.BAWASLU_GATE1_ISOLATED_E2E==='YES'
  && url===LOCAL_URL && process.env.GATE1_CI_SEED_FILE;
test.skip(!enabled,'Only runs in the explicitly isolated localhost PostgreSQL CI workflow.');

function ids(){
  return JSON.parse(fs.readFileSync(process.env.GATE1_CI_SEED_FILE,'utf8'));
}

async function login(page,email){
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/^password$/i).fill(PASSWORD);
  await page.getByRole('button',{name:/log in|masuk/i}).click();
  await page.waitForURL(target=>!target.pathname.startsWith('/login'));
  const token=await page.evaluate(()=>localStorage.getItem('bawaslu_access_token'));
  expect(token?.length).toBeGreaterThan(20);
  return {Authorization:'Bearer '+token};
}

async function sourceSnapshot(request,headers,campaignId,sourceId){
  const response=await request.get(
    '/api/inbox/human-review/campaign/'+campaignId+'/source/'+sourceId,
    {headers},
  );
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function reason(page,description){
  await page.getByLabel('Review reason').fill(description);
}

test('real UI and HTTP: corrections, audit, restore, revalidation and no publication',async({page,request})=>{
  const idsData=ids();
  const outbound=[];
  const pageErrors=[];
  page.on('dialog',dialog=>dialog.accept());
  page.on('request',req=>{
    if(/api\.openai\.com|socialcrawl|api\.anthropic\.com/i.test(req.url()))outbound.push(req.url());
  });
  page.on('pageerror',err=>pageErrors.push(err.message));
  const headers=await login(page,'gate1-ci-admin@example.invalid');
  const route='/inbox?gate1=1&campaign_id='+idsData.campaign_id;
  await page.goto(route);
  await expect(page.getByTestId('gate1-qa-pilot-preflight')).toBeVisible();
  await page.getByTestId('gate1-check-pilot-readiness').click();
  await expect(page.getByTestId('gate1-pilot-readiness-report')).toContainText('ELIGIBLE FOR QA');
  await expect(page.getByTestId('gate1-pilot-readiness-report')).toContainText('Non-synthetic links: 0');

  const queue=page.getByRole('region',{name:'Human Review source queue'});
  // Only the ordinary synthetic post is in the queue, not WATCHLIST_ACCOUNT.
  await expect(queue.getByRole('button',{name:new RegExp('#'+idsData.source_id+'\\b')})).toHaveCount(1);
  await queue.getByRole('button',{name:new RegExp('#'+idsData.source_id+'\\b')}).click();

  const details=page.getByRole('region',{name:'Human Review evidence detail'});
  await expect(details).toContainText('Synthetic QA-only example');
  await expect(details).toContainText('Original AI relevance: IRRELEVANT');
  await expect(page.getByTestId('gate1-correction-workbench')).toBeVisible();
  await page.getByTestId('gate1-gate2-readiness').getByRole('button').click();
  await expect(page.getByTestId('gate1-gate2-packet')).toContainText('BLOCKED');
  await expect(page.getByTestId('gate1-gate2-packet')).toContainText('CURRENT_GATE1_INFORMATION_REVIEW_REQUIRED');

  const before=await sourceSnapshot(request,headers,idsData.campaign_id,idsData.source_id);
  expect(before.effective_relevance).toBe('IRRELEVANT');
  const stalePayload={
    field:'relevance',value:'UNCERTAIN',
    expected_revision:before.relevance_revision,
    expected_assessment_id:before.assessment_id,
    expected_source_digest:before.source_integrity_digest,
    reason:'Old browser tab must not override newer officer correction',
  };
  const api='/api/inbox/human-review/campaign/'+idsData.campaign_id+
    '/source/'+idsData.source_id+'/corrections';

  await reason(page,'Fictional post was actually relevant to the mock election forum.');
  await page.getByTestId('gate1-save-field-correction').click();
  await expect(details).toContainText('Effective relevance: RELEVANT');
  await expect(details).toContainText('Original AI relevance: IRRELEVANT');

  // Stale optimistic-lock revision must be rejected without creating a new row.
  const stale=await request.post(api,{headers,data:stalePayload});
  expect(stale.status()).toBe(409);

  await page.getByLabel('Correct field').selectOption('sentiment');
  await page.getByLabel('New value').selectOption('NEUTRAL');
  await reason(page,'Synthetic review determines the fictional discussion is neutral.');
  await page.getByTestId('gate1-save-field-correction').click();
  await expect(details).toContainText('Effective sentiment: NEUTRAL');
  await expect(details).toContainText('AI sentiment: NEGATIVE');

  await page.getByTestId('gate1-review-decision').selectOption('OFFICER_VERIFIED');
  await reason(page,'Verified the saved fictional information snapshot, not a legal allegation.');
  await page.getByTestId('gate1-save-review-decision').click();
  await expect(page.getByTestId('gate1-information-status')).toContainText('OFFICER_VERIFIED');
  await page.getByTestId('gate1-gate2-readiness').getByRole('button').click();
  await expect(page.getByTestId('gate1-gate2-packet')).toContainText('CANDIDATE_FOR_INSIGHT_DRAFT');
  await expect(page.getByTestId('gate1-gate2-packet')).toContainText('No Command Centre publication');

  // Admins may triage verified CURRENT corrections for offline evaluation only.
  // This is an append-only governance disposition, NOT a model-training action.
  await page.getByTestId('gate1-offline-feedback').getByRole('button',{name:/View correction feedback/}).click();
  const neutralFeedback=page.getByTestId('gate1-feedback-item').filter({hasText:'NEGATIVE → NEUTRAL'});
  await expect(neutralFeedback).toBeVisible();
  await neutralFeedback.getByTestId('gate1-feedback-triage').getByRole('combobox')
    .selectOption('ACCEPT_OFFLINE_EVALUATION');
  await page.getByLabel('Offline feedback triage reason')
    .last().fill('Fictional data was verified for offline evaluation only.');
  await neutralFeedback.getByRole('button',{name:/Record audited offline decision/}).click();
  await expect(page.getByText('Offline feedback triage saved. Model training remains disabled.')).toBeVisible();
  await page.getByTestId('gate1-offline-feedback').getByRole('button',{name:/View correction feedback/}).click();
  await expect(page.getByTestId('gate1-offline-feedback')).toContainText('ACCEPT_OFFLINE_EVALUATION');

  // New officer correction automatically invalidates the prior information QA decision.
  await page.getByLabel('New value').selectOption('POSITIVE');
  await reason(page,'A later fictional sentiment correction requires another review.');
  await page.getByTestId('gate1-save-field-correction').click();
  await expect(page.getByTestId('gate1-information-status')).toContainText('REVALIDATION_REQUIRED');
  await page.getByTestId('gate1-gate2-readiness').getByRole('button').click();
  await expect(page.getByTestId('gate1-gate2-packet')).toContainText('BLOCKED');
  await expect(page.getByTestId('gate1-gate2-packet')).toContainText('CURRENT_GATE1_INFORMATION_REVIEW_REQUIRED');
  await page.getByTestId('gate1-offline-feedback').getByRole('button',{name:/View correction feedback/}).click();
  const queueUrl='/api/inbox/human-review/campaign/'+idsData.campaign_id+
    '/source/'+idsData.source_id+'/feedback';
  const afterChange=await request.get(queueUrl,{headers});
  expect(afterChange.ok()).toBeTruthy();
  const feedbackAfter=await afterChange.json();
  const approvedButStale=feedbackAfter.items.find(x=>x.triage_decision==='ACCEPT_OFFLINE_EVALUATION');
  expect(approvedButStale).toBeDefined();
  expect(approvedButStale.offline_evaluation_candidate).toBe(false);
  expect(approvedButStale.training_triggered).toBe(false);

  await page.getByTestId('gate1-review-status-filter').selectOption('revalidation_required');
  await expect(queue.getByRole('button',{name:new RegExp('#'+idsData.source_id+'\\b')})).toBeVisible();
  await page.getByTestId('gate1-review-status-filter').selectOption('all');

  await reason(page,'Restore original fictional relevance, preserving all earlier versions.');
  await page.getByRole('button',{name:/View review & correction history/}).click();
  const firstVersion=page.getByText(/v1 · IRRELEVANT · OFFLINE_FICTIONAL_QA/).locator('..');
  await expect(firstVersion.getByRole('button',{name:/Restore/})).toBeVisible();
  await firstVersion.getByRole('button',{name:/Restore/}).click();
  await expect(details).toContainText('Effective relevance: IRRELEVANT');
  await page.getByRole('button',{name:/View review & correction history/}).click();
  await expect(page.getByTestId('gate1-audit-history')).toContainText('GATE1_FIELD_RESTORED');
  await expect(page.getByTestId('gate1-audit-history')).toContainText('v3 · IRRELEVANT');
  const after=await sourceSnapshot(request,headers,idsData.campaign_id,idsData.source_id);
  expect(after.original_ai_relevance).toBe('IRRELEVANT');
  expect(after.assessment_version).toBe(3);
  expect(after.information_review_status).toBe('REVALIDATION_REQUIRED');
  expect(after.original_source_preserved).toBe(true);
  expect(after.official_insight_approval_required).toBe(true);
  await page.getByTestId('gate1-feedback-queue').getByRole('button',{name:/View officer correction feedback queue/}).click();
  await expect(page.getByTestId('gate1-feedback-queue')).toContainText('ACCEPT_OFFLINE_EVALUATION');
  const governance=await request.get('/api/inbox/human-review/campaign/'+idsData.campaign_id+
    '/source/'+idsData.source_id+'/gate2-readiness',{headers});
  const readiness=await governance.json();
  expect(governance.ok()).toBeTruthy();
  expect(readiness.command_centre_published).toBe(false);
  expect(readiness.proposed_insight_created).toBe(false);
  expect(outbound).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test('read-only officer, operational campaign and watchlist evidence fail closed',async({page,request})=>{
  const data=ids();
  const headers=await login(page,'gate1-ci-viewer@example.invalid');
  await page.goto('/inbox?gate1=1&campaign_id='+data.campaign_id);
  const queue=page.getByRole('region',{name:'Human Review source queue'});
  await queue.getByRole('button',{name:new RegExp('#'+data.source_id+'\\b')}).click();
  await expect(page.getByRole('region',{name:'Human Review evidence detail'})).toContainText('Synthetic QA-only example');
  await expect(page.getByTestId('gate1-correction-workbench')).toHaveCount(0);
  await page.getByTestId('gate1-offline-feedback').getByRole('button',{name:/View correction feedback/}).click();
  await expect(page.getByTestId('gate1-offline-feedback')).not.toContainText('Record audited offline decision');
  await page.getByTestId('gate1-check-pilot-readiness').click();
  await expect(page.getByRole('alert')).toContainText('Administrator access is required');

  const snapshot=await sourceSnapshot(request,headers,data.campaign_id,data.source_id);
  const body={
    field:'relevance', value:'RELEVANT',
    expected_revision:snapshot.relevance_revision,
    expected_assessment_id:snapshot.assessment_id,
    expected_source_digest:snapshot.source_integrity_digest,
    reason:'Viewer cannot alter fictional sample evidence',
  };
  const pilotUrl='/api/inbox/human-review/campaign/'+data.campaign_id+
    '/source/'+data.source_id+'/corrections';
  expect((await request.post(pilotUrl,{headers,data:body})).status()).toBe(403);
  expect((await request.post(pilotUrl,{data:body})).status()).toBe(401);
  expect((await request.get(
    '/api/inbox/human-review/campaign/'+data.campaign_id+
    '/source/'+data.watchlist_source_id,{headers},
  )).status()).toBe(404);

  // Clear the viewer's test-only tab token before signing in as admin.
  await page.evaluate(()=>localStorage.removeItem('bawaslu_access_token'));
  // Even a national administrator cannot write to ordinary non-QA campaigns.
  const admin=await login(page,'gate1-ci-admin@example.invalid');
  const ordinary=await sourceSnapshot(
    request,admin,data.protected_campaign_id,data.protected_source_id,
  );
  const otherUrl='/api/inbox/human-review/campaign/'+data.protected_campaign_id+
    '/source/'+data.protected_source_id+'/corrections';
  expect((await request.post(otherUrl,{headers:admin,data:{
    field:'relevance',value:'IRRELEVANT',
    expected_revision:ordinary.relevance_revision,
    expected_assessment_id:ordinary.assessment_id,
    expected_source_digest:ordinary.source_integrity_digest,
    reason:'Protected operational campaign must reject test writes',
  }})).status()).toBe(403);
});
