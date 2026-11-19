import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

// Runs against isolated localhost SQLite + Vite only. Never point this harness
// at staging or production. The component's read-only provider is mocked;
// no campaign data, provider credits, or database rows are involved.
test.beforeEach(async ({page},info)=>{
 if(process.env.PLAYWRIGHT_BASE_URL||!config.webServer){
  info.skip(true,'Requires isolated local web server');
 }
 await page.goto('/login');
 await page.evaluate(async ()=>{
  const React=await import('/node_modules/.vite/deps/react.js');
  const ReactDOM=await import('/node_modules/.vite/deps/react-dom_client.js');
  const {default:Panel}=await import('/src/components/intel/AssessmentOperationsPanel.jsx');
  const {base44}=await import('/src/api/base44Client.js');
  document.body.innerHTML='<main id="assessment-test-root"></main>';
  window.__assessmentCalls=[];
  window.__assessmentResolvers=[];
  base44.functions.invoke=async (_name,payload)=>{
    window.__assessmentCalls.push(payload);
    return await new Promise((resolve,reject)=>{
      window.__assessmentResolvers.push({resolve,reject,id:payload.id});
    });
  };
  const createRoot=ReactDOM.createRoot||ReactDOM.default?.createRoot;
  if(!createRoot)throw Error('ReactDOM client root export unavailable');
  window.__assessmentRoot=createRoot(document.querySelector('#assessment-test-root'));
  window.__renderAssessment=(campaignId)=>window.__assessmentRoot.render(
    (React.createElement||React.default?.createElement)(Panel,{campaignId}));
 });
});
const snapshot=(cid,kind='PENDING_WORK')=>({
 generated_at_utc:'2026-11-18T08:30:00Z',
 worker_readiness:{
  queue_counts:{pending:1,processing:0,completed:0,failed:0,
   claimable_pending_with_text:1},
  daily_remaining:0,lifetime_remaining:0,
  pending_already_assessed_excluded_from_ai:0
 },
 assessment_link_coverage:{pending_monitoring_without_job:0},
 completion_audit:{completed_jobs:0,verified_usage_backed_completed_jobs:0},
 interrupted_recovery:{stale_processing_jobs:0,
  already_quarantined_for_manual_review:0},
 operational_acceptance:{status:'NO_ELIGIBLE_WORK',
  manual_request_capacity_if_separately_approved:0},
 snapshot_consistency:{all_consistent:true},
 queue_triage:{
  status:kind,ordinary_job_total:1,bucket_total:1,
  buckets_partition_all_jobs:true,stale_threshold_minutes:10,
  buckets:[{code:kind==='HOLD_FOR_HISTORY_REVIEW'?'STALE_PROCESSING':'PENDING',
   count:1,priority:kind==='HOLD_FOR_HISTORY_REVIEW'?'URGENT_HISTORY_REVIEW':'QUEUE_REVIEW',
   next_step:'Read-only guidance for campaign '+cid}],
  pending_breakdown:{pending_total:1,eligible_with_text:1,
   missing_source_or_text:0,already_assessed:0,attempt_limit_exhausted:0,
   breakdown_total:1,breakdown_reconciled:true}
 },
 campaign_id:String(cid)
});
const mount=async(page,id)=>{
 await page.evaluate(id=>window.__renderAssessment(id),id);
 await page.getByRole('button',{name:'View status'}).click();
};
const respond=async(page,id,data)=>{
 await page.evaluate(({id,data})=>{
  const n=window.__assessmentResolvers.findIndex(x=>String(x.id)===String(id));
  if(n<0)throw Error('No pending mock response for campaign '+id);
  window.__assessmentResolvers.splice(n,1)[0].resolve({data});
 },{id,data});
};
test('read-only triage renders review priorities and no billable action',async({page})=>{
 await mount(page,101);
 await respond(page,101,snapshot(101,'HOLD_FOR_HISTORY_REVIEW'));
 await expect(page.getByTestId('assessment-triage-status')).toContainText('HOLD FOR HISTORY REVIEW');
 await expect(page.getByTestId('queue-bucket-STALE_PROCESSING')).toContainText('History review');
 await expect(page.getByTestId('assessment-pending-breakdown')).toContainText('Eligible with text');
 const calls=await page.evaluate(()=>window.__assessmentCalls);
 expect(calls).toHaveLength(1);
 expect(calls[0]).toMatchObject({id:'101',action:'campaignAssessmentOperationsOverview',data:{}});
});
test('switching campaigns ignores the previous campaign late response',async({page})=>{
 await mount(page,101);
 await page.evaluate(()=>window.__renderAssessment(202));
 await expect(page.getByRole('button',{name:'View status'})).toBeVisible();
 await respond(page,101,snapshot(101));
 await expect(page.getByTestId('assessment-queue-triage')).toHaveCount(0);
 await page.getByRole('button',{name:'View status'}).click();
 await respond(page,202,snapshot(202));
 await expect(page.getByTestId('assessment-triage-categories')).toContainText('campaign 202');
 await expect(page.getByTestId('assessment-triage-categories')).not.toContainText('campaign 101');
});
test('closing an in-flight status invalidates cached response and opening reloads',async({page})=>{
 await mount(page,301);
 await page.getByRole('button',{name:'Hide details'}).click();
 await respond(page,301,snapshot(301));
 await page.getByRole('button',{name:'View status'}).click();
 const calls=await page.evaluate(()=>window.__assessmentCalls.map(x=>x.id));
 expect(calls).toEqual(['301','301']);
 await respond(page,301,snapshot(301));
 await expect(page.getByTestId('assessment-queue-triage')).toContainText('Ordinary jobs');
});
test('failed refresh discards potentially stale numbers and offers retry',async({page})=>{
 await mount(page,401);
 await respond(page,401,snapshot(401));
 await page.getByRole('button',{name:'Refresh status'}).click();
 await expect(page.getByText(/previous results may be out of date/)).toBeVisible();
 await page.evaluate(()=>{
  window.__assessmentResolvers.shift().reject(new Error('Synthetic read failure'));
 });
 await expect(page.getByRole('alert')).toContainText('Synthetic read failure');
 await expect(page.getByTestId('assessment-triage-categories')).toHaveCount(0);
 await page.getByRole('button',{name:'Refresh status'}).click();
 await respond(page,401,snapshot(401));
 await expect(page.getByTestId('assessment-triage-categories')).toBeVisible();
});
test('inconsistent snapshot reports warning rather than treating totals as reliable',async({page})=>{
 await mount(page,501);
 const data=snapshot(501);
 data.snapshot_consistency.all_consistent=false;
 await respond(page,501,data);
 await expect(page.getByRole('alert')).toContainText('do not reconcile');
});

test('verified classification lineage stays informational and never dispatches provider work',async({page})=>{
 await mount(page,601);
 const data=snapshot(601);
 data.queue_triage.status='NO_ACTIVE_WORK';
 data.queue_triage.ordinary_job_total=2;
 data.queue_triage.bucket_total=2;
 data.queue_triage.buckets=[{code:'COMPLETED',count:2,priority:'COMPLETED_NOT_VERIFIED',
  next_step:'Verify recorded classification usage'}];
 data.queue_triage.pending_breakdown={pending_total:0,eligible_with_text:0,
  missing_source_or_text:0,already_assessed:0,attempt_limit_exhausted:0,
  breakdown_total:0,breakdown_reconciled:true};
 data.queue_triage.completion_provenance={completed_jobs:2,usage_backed_completed:2,
  requires_historical_usage_review:0,latest_classification_review:0};
 data.queue_triage.completion_snapshot_reconciled=true;
 await respond(page,601,data);
 const result=page.getByTestId('assessment-completion-provenance');
 await expect(result).toContainText('Usage-backed: 2');
 await expect(result).toContainText('Historical usage gaps: 0');
 await expect(result).not.toContainText('History review required');
 expect(await page.evaluate(()=>window.__assessmentCalls.map(x=>x.action)))
  .toEqual(['campaignAssessmentOperationsOverview']);
});
test('missing classification lineage and audit snapshot drift demand manual review only',async({page})=>{
 await mount(page,602);
 const data=snapshot(602);
 data.queue_triage.status='RECHECK_INDEPENDENT_SNAPSHOTS';
 data.queue_triage.completion_provenance={completed_jobs:3,usage_backed_completed:1,
  requires_historical_usage_review:2,latest_classification_review:1};
 data.queue_triage.completion_snapshot_reconciled=false;
 await respond(page,602,data);
 const panel=page.getByTestId('assessment-completion-provenance');
 await expect(panel).toContainText('Historical usage gaps: 2');
 await expect(panel).toContainText('Latest classification needs review: 1');
 await expect(panel).toContainText('History review required');
 await expect(panel.getByRole('alert')).toContainText('Completion counts differ');
 await expect(page.getByText(/Queue counts were read independently/)).toBeVisible();
 expect(await page.evaluate(()=>window.__assessmentCalls.map(x=>x.action)))
  .toEqual(['campaignAssessmentOperationsOverview']);
});

test('usage integrity flags are visible and never trigger provider operations',async({page})=>{
 await mount(page,703);
 const data=snapshot(703);
 data.queue_triage.status='HOLD_FOR_HISTORY_REVIEW';
 data.queue_triage.provider_usage_integrity={status:'REVIEW_REQUIRED',usage_rows:5,
  usage_flags:{campaign_id_mismatch:1,provider_usage_not_reported:2,
   negative_token_counts:1,provider_model_missing:1},
  lifecycle_flags:{noncompleted_jobs_with_classification_usage:1,
   assessments_with_duplicate_classification_usage:1}};
 await respond(page,703,data);
 const section=page.getByTestId('assessment-provider-usage-integrity');
 await expect(section).toContainText('Provider history review required');
 await expect(section).toContainText('Campaign mismatches: 1');
 await expect(section).toContainText('Assessments with duplicate classification usage: 1');
 await expect(section).toContainText('counts may overlap');
 expect(await page.evaluate(()=>window.__assessmentCalls.map(x=>x.action)))
  .toEqual(['campaignAssessmentOperationsOverview']);
});
test('older read-only API omitting integrity diagnostics warns explicitly',async({page})=>{
 await mount(page,704);
 await respond(page,704,snapshot(704));
 await expect(page.getByTestId('assessment-provider-usage-integrity'))
  .toContainText('Usage integrity detail unavailable');
});
test('completed KPI uses completed before usage-backed counts',async({page})=>{
 await mount(page,705);
 const data=snapshot(705);
 data.completion_audit={completed_jobs:9,verified_usage_backed_completed_jobs:4};
 await respond(page,705,data);
 const card=page.getByText('Completed / usage-backed').locator('..');
 await expect(card).toContainText('9 / 4');
});

test('consolidated gate blocks capacity when snapshot audit is unavailable',async({page})=>{
 await mount(page,1717);
 const data=snapshot(1717);
 data.exception_review={
  next_review_step:'REFRESH_SNAPSHOT',snapshot_reconciled:false,
  usage_audit_available:true,completion_audit_available:true,
  queue_exceptions_clear:true,missing_audits:[],groups:[],
  manual_approval_review_gate:{
   status:'BLOCKED',blockers:['SNAPSHOT_AUDIT_UNAVAILABLE'],
   displayable_capacity_if_all_checks_clear:0}
 };
 data.operational_acceptance.manual_request_capacity_if_separately_approved=12;
 await respond(page,1717,data);
 await expect(page.getByTestId('manual-approval-review-gate')).toContainText('Blocked');
 await expect(page.getByTestId('manual-approval-review-gate')).toContainText('capacity after all diagnostic checks: 0');
 await expect(page.getByTestId('manual-approval-blockers')).toContainText('SNAPSHOT AUDIT UNAVAILABLE');
 expect(await page.evaluate(()=>window.__assessmentCalls.map(x=>x.action)))
  .toEqual(['campaignAssessmentOperationsOverview']);
});
test('older API without consolidated gate prominently fails closed',async({page})=>{
 await mount(page,1718);
 const data=snapshot(1718);
 data.operational_acceptance.manual_request_capacity_if_separately_approved=8;
 data.exception_review={
  next_review_step:'VERIFY_HISTORICAL_USAGE_INDEPENDENTLY',
  snapshot_reconciled:true,usage_audit_available:true,
  completion_audit_available:true,queue_exceptions_clear:true,
  missing_audits:[],groups:[]};
 await respond(page,1718,data);
 await expect(page.getByTestId('manual-approval-gate-unavailable')).toContainText('Do not rely on the legacy capacity');
 await expect(page.getByTestId('manual-approval-review-gate')).toHaveCount(0);
 expect(await page.evaluate(()=>window.__assessmentCalls.map(x=>x.action)))
  .toEqual(['campaignAssessmentOperationsOverview']);
});
