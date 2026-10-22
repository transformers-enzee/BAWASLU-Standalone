import { useEffect, useState } from 'react';
import { base44 } from '@/api/base44Client';

export default function AssessmentPilotPreview({ campaign }) {
 const [sampleSize,setSampleSize]=useState(10);
 const [plan,setPlan]=useState(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [costAcknowledged,setCostAcknowledged]=useState(false);
 const [starting,setStarting]=useState(false);
 const [notice,setNotice]=useState('');

 useEffect(()=>{setPlan(null);setError('');setCostAcknowledged(false);setNotice('')},[campaign?.id]);

 async function load(size=sampleSize,anchor=null) {
  if(!campaign?.id||loading)return;
  setLoading(true);setError('');
  try {
   const res=await base44.functions.invoke('socialListening',{
    action:'campaignAssessmentPilotPreview',id:campaign.id,
    data:{sample_size:size,...(anchor?{anchor_id:anchor}:{})}
   });
   setPlan(res.data);
   setCostAcknowledged(false);
  }catch(e){setError(e.response?.data?.detail||e.message||'Unable to preview pilot records')}
  finally{setLoading(false)}
 }

 useEffect(()=>{
  if(!campaign?.id||!plan||!(plan.counts?.queued||plan.counts?.processing))return;
  let active=true;
  const timer=window.setInterval(async()=>{
   try {
    const res=await base44.functions.invoke('socialListening',{
     action:'campaignAssessmentPilotPreview',id:campaign.id,
     data:{sample_size:plan.requested,anchor_id:plan.sample_anchor_id}
    });
    if(active)setPlan(res.data);
   }catch(e){if(active)setError('Progress refresh unavailable; refresh manually.')}
  },12000);
  return()=>{active=false;window.clearInterval(timer)}
 },[campaign?.id,plan?.requested,plan?.sample_anchor_id,plan?.counts?.queued,plan?.counts?.processing]);

 async function start(resume=false) {
  if(!plan||starting||!costAcknowledged)return;
  const queued=resume?plan.counts.queued:plan.counts.not_queued;
  if(!queued)return;
  const confirmed=window.confirm('Approve up to '+queued+' billable AI requests for the '+plan.requested+' selected posts? SocialCrawl credits: 0. AI token charges vary. Failed or uncertain requests will not retry automatically.');
  if(!confirmed)return;
  setStarting(true);setError('');setNotice('');
  try {
   const r=await base44.functions.invoke('socialListening',{
    action:'campaignAssessmentPilotStart',id:campaign.id,
    data:{sample_size:plan.requested,anchor_id:plan.sample_anchor_id,
     expected_result_ids:plan.records.map(row=>row.id),
     confirm_ai_cost:true,resume}
   });
   setNotice('Approved '+r.data.queued+' selected AI assessment requests. Monitoring stored progress; no automatic retries for failed calls.');
   const latest=await base44.functions.invoke('socialListening',{
    action:'campaignAssessmentPilotPreview',id:campaign.id,
    data:{sample_size:plan.requested,anchor_id:plan.sample_anchor_id}
   });
   setPlan(latest.data);setCostAcknowledged(false);
  }catch(e){setError(e.response?.data?.detail||e.message||'Could not start paid AI batch')}
  finally{setStarting(false)}
 }
 const readiness=plan?.readiness||{};
 const blocked=!plan?.has_campaign_description||!readiness.ai_provider_configured||
   !readiness.database_supports_reservations||!readiness.per_request_worker_enabled||
   (readiness.request_budget_remaining||0)<(plan?.counts?.not_queued||0);
 const metrics=plan?[
  ['Completed',plan.counts.completed],
  ['Processing',plan.counts.processing],
  ['Queued',plan.counts.queued],
  ['Needs attention',plan.counts.failed],
  ['Not queued',plan.counts.not_queued],
 ]:[];
 return <details className="rounded-lg border border-slate-200 p-4" aria-label="AI assessment pilot">
  <summary className="cursor-pointer font-semibold text-sm">AI assessment pilot · 10 new or 40–50 stored posts</summary>
  <div className="mt-3 space-y-3">
   <p className="text-xs text-slate-600">Sample preview is free. After checking the campaign objective, gate questions, and selected sources, you can authorize a paid AI assessment of these exact posts. No SocialCrawl credits are used.</p>
   <div className="flex gap-3 flex-wrap items-end">
    <label className="text-xs font-medium">Sample size
     <select className="intel-input mt-1 block" value={sampleSize} onChange={e=>{setSampleSize(Number(e.target.value));setPlan(null)}}>
      <option value={10}>10 unassessed posts only</option><option value={40}>40 records (mixed progress)</option><option value={50}>50 records (mixed progress)</option>
     </select>
    </label>
    <button type="button" className="intel-ghost text-xs" disabled={loading} onClick={()=>load(sampleSize)}>{loading?'Preparing…':'Preview sample (free)'}</button>
    {plan&&<button type="button" className="intel-ghost text-xs" disabled={loading} onClick={()=>load(plan.requested,plan.sample_anchor_id)}>Refresh progress</button>}
   </div>
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {notice&&<p role="status" className="text-xs font-semibold text-teal-700">{notice}</p>}
   {plan&&<section className="space-y-3" aria-label="Assessment pilot progress">
    <p className="text-xs font-semibold">{plan.total} of {plan.requested} records selected · {plan.sampling_method}</p>
    <div className="flex items-center justify-between text-xs"><span>Stored AI assessments completed</span><strong>{plan.progress_percent}%</strong></div>
    <div role="progressbar" aria-label="Pilot assessment completion" aria-valuemin={0} aria-valuemax={100} aria-valuenow={plan.progress_percent} className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
     <div className="h-full bg-teal-600" style={{width:plan.progress_percent+'%'}}/>
    </div>
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">{metrics.map(([label,n])=><div key={label} className="rounded-lg border p-2 text-xs"><strong className="block text-base">{n}</strong>{label}</div>)}</div>
    <div className="rounded-lg bg-slate-50 p-3 space-y-1 text-xs">
     <p>Campaign objective: <strong>{plan.has_campaign_description?'Provided':'Missing'}</strong> · Main keywords: {plan.main_keyword_count} · Subkeywords: {plan.secondary_keyword_count} · Active admin gate questions: {plan.active_admin_gates}</p>
     {(plan.warnings||[]).map((warning,i)=><p key={i} className="font-medium text-amber-800">{warning}</p>)}
     <p>{plan.cost_note}</p>
     <p className="font-semibold">This preview never charges or starts jobs. Only the separately confirmed Start/Resume action initiates billable AI requests.</p>
     <p>AI provider: {readiness.ai_provider_configured?'Configured':'Not configured'} · Request budget remaining: {readiness.request_budget_remaining||0} · Protected reservations: {readiness.database_supports_reservations?'Ready':'Unavailable'}</p>
    </div>
    <div className="border-t pt-3 space-y-2 text-xs" aria-label="Paid AI batch approval">
     <strong className="block text-sm">Batch AI assessment · explicit cost approval</strong>
     <p>Up to <strong>{plan.counts.not_queued}</strong> new paid AI requests; token charges vary by post length and model. SocialCrawl credits: <strong>0</strong>. Previously assessed posts are not billed again.</p>
     {!plan.has_campaign_description&&<p className="font-medium text-amber-800">Blocked: edit this campaign to add its objective/description before paying for assessments.</p>}
     {!readiness.ai_provider_configured&&<p className="font-medium text-amber-800">Blocked: AI provider key not configured in the server environment.</p>}
     {!readiness.per_request_worker_enabled&&<p className="font-medium text-amber-800">Blocked: the controlled AI worker request limit is disabled.</p>}
     {!readiness.database_supports_reservations&&<p className="font-medium text-amber-800">Blocked: protected database budget reservations unavailable.</p>}
     {(readiness.request_budget_remaining||0)<plan.counts.not_queued&&<p className="font-medium text-amber-800">Blocked: request budget has fewer remaining requests than the selected batch.</p>}
     <label className="flex items-start gap-2"><input type="checkbox" checked={costAcknowledged} onChange={e=>setCostAcknowledged(e.target.checked)}/><span>I authorize variable, billable AI token charges for only these selected posts and understand that preliminary AI conclusions require human verification.</span></label>
     <div className="flex flex-wrap gap-2">
      <button type="button" className="intel-button text-xs" disabled={!costAcknowledged||blocked||starting||loading||plan.counts.not_queued===0||plan.counts.queued>0||plan.counts.processing>0||plan.counts.failed>0} onClick={()=>start(false)}>{starting?'Starting…':'Start batch AI assessment ('+plan.counts.not_queued+')'}</button>
      {plan.counts.queued>0&&plan.counts.processing===0&&<button type="button" className="intel-ghost text-xs" disabled={starting||loading||!costAcknowledged||!plan.has_campaign_description||!readiness.ai_provider_configured||!readiness.per_request_worker_enabled||!readiness.database_supports_reservations||(readiness.request_budget_remaining||0)<plan.counts.queued} onClick={()=>start(true)}>Resume queued batch ({plan.counts.queued})</button>}
     </div>
    </div>
    <div className="max-h-80 overflow-y-auto border rounded-lg">
     <table className="w-full text-left text-xs"><thead className="sticky top-0 bg-slate-100"><tr><th className="p-2">Post</th><th className="p-2">Platform</th><th className="p-2">Text sample</th><th className="p-2">Assessment</th></tr></thead><tbody>
      {plan.records.map(row=><tr key={row.id} className="border-t"><td className="p-2 whitespace-nowrap">#{row.id}{row.source_url&&<a className="block text-teal-700 underline" href={row.source_url} target="_blank" rel="noopener noreferrer">Source</a>}{row.assessment_state==='COMPLETED'&&<a className="block text-teal-700 underline" href={'/inbox?campaign_id='+encodeURIComponent(campaign.id)+'&result_id='+encodeURIComponent(row.id)}>Review in Inbox</a>}</td><td className="p-2">{row.platform}</td><td className="p-2 break-words max-w-[400px]">{row.text_excerpt||'Source text unavailable'}</td><td className="p-2 whitespace-nowrap">{row.assessment_state.replaceAll('_',' ')}{row.relevance_label&&<span className="block text-slate-500">{row.relevance_label}</span>}</td></tr>)}
     </tbody></table>
    </div>
    <p className="text-xs text-slate-500">Progress reflects actual saved assessments, not merely accepted requests. Pending job records persist if the worker is interrupted; restart only queued work through explicit confirmation. Ambiguous or failed paid calls are never retried automatically. Human review is required for potential violation signals.</p>
   </section>}
  </div>
 </details>;
}
