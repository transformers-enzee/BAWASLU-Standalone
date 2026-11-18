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
