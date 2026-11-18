import {useEffect,useRef,useState} from 'react';
import {base44} from '@/api/base44Client';

const fmt=n=>Number(n||0).toLocaleString();
export default function AssessmentOperationsPanel({campaignId}){
 const [open,setOpen]=useState(false);
 const [busy,setBusy]=useState(false);
 const [data,setData]=useState(null);
 const [error,setError]=useState('');
 const requestToken=useRef(0);
 const activeCampaign=useRef(String(campaignId||''));
 activeCampaign.current=String(campaignId||'');
 useEffect(()=>{
  setOpen(false);setData(null);setError('');setBusy(false);
  return ()=>{requestToken.current+=1;};
 },[campaignId]);
 async function load(){
  if(!campaignId||busy)return;
  const requestedCampaign=String(campaignId);
  const token=++requestToken.current;
  const stillCurrent=()=>token===requestToken.current&&activeCampaign.current===requestedCampaign;
  setBusy(true);setError('');
  try{
   const r=await base44.functions.invoke('socialListening',{
    action:'campaignAssessmentOperationsOverview',id:requestedCampaign,data:{}});
   if(stillCurrent())setData(r.data||null);
  }catch(e){
   if(stillCurrent()){
    setError(e.response?.data?.detail||e.message||'Could not load assessment operations');
    setData(null);
   }
  }finally{if(stillCurrent())setBusy(false)}
 }
 const q=data?.worker_readiness?.queue_counts||{};
 const c=data?.assessment_link_coverage||{};
 const done=data?.completion_audit||{};
 const recovery=data?.interrupted_recovery||{};
 const remaining=data?.worker_readiness||{};
 return <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3" aria-label="Assessment operations status">
  <div className="flex flex-wrap items-center justify-between gap-3">
   <div><h4 className="font-semibold text-slate-800">Assessment operations</h4>
    <p className="text-xs text-slate-500">Read-only queue, completion and budget diagnostics. No provider calls.</p></div>
   <div className="flex flex-wrap gap-2">
    {open&&<button type="button" className="intel-ghost text-xs" onClick={load} disabled={busy}>{busy?'Checking…':'Refresh status'}</button>}
    <button type="button" className="intel-ghost text-xs" aria-expanded={open} onClick={()=>{if(!open&&!data)void load();setOpen(!open);}}>{open?'Hide details':'View status'}</button>
   </div>
  </div>
  {open&&<div className="space-y-3">
   {busy&&!data&&<p role="status" className="text-xs text-slate-500">Checking saved assessment records…</p>}
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {data&&<>
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 text-sm">
     {[
      ['Queued, claimable',q.claimable_pending_with_text],
      ['Unqueued evidence',c.pending_monitoring_without_job],
      ['Completed / usage backed',fmt(done.verified_usage_backed_completed_jobs)+' / '+fmt(done.completed_jobs)],
      ['Stale processing',recovery.stale_processing_jobs],
     ].map(([label,value])=><div key={label} className="rounded-lg bg-slate-50 border border-slate-200 p-3"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold text-lg tabular-nums">{typeof value==='number'?fmt(value):value}</p></div>)}
    </div>
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs space-y-1">
     <p className="font-semibold text-slate-800">Operational acceptance: {String(data.operational_acceptance?.status||'UNKNOWN').replaceAll('_',' ')}</p>
     <p>Eligible unassessed jobs: {fmt(data.operational_acceptance?.eligible_unassessed_jobs)} · Manual batch capacity only after separate approval: {fmt(data.operational_acceptance?.manual_request_capacity_if_separately_approved)}</p>
     <p>Historical review: {(data.operational_acceptance?.historical_review_codes||[]).join(', ')||'None'} · Queue reconciliation: {(data.operational_acceptance?.queue_reconciliation_codes||[]).join(', ')||'None'}</p>
     <p>Manual configuration blockers: {(data.operational_acceptance?.manual_configuration_blockers||[]).join(', ')||'None'}. This preflight never authorizes AI charges.</p>
    </div>
    {data.operational_acceptance?.resolution_plan?.length>0&&<div className="rounded-lg border border-amber-200 p-3 space-y-2 text-xs">
      <h5 className="font-semibold text-slate-900">Resolution checklist · {data.operational_acceptance.outstanding_resolution_categories} active categories</h5>
      <p className="text-slate-600">Review history first, then reconcile eligible queue records. Clear status only after refreshing the read-only audit.</p>
      <ol className="space-y-2 list-decimal ml-4">
       {data.operational_acceptance.resolution_plan.map(item=><li key={item.code}>
        <strong>{item.code.replaceAll('_',' ')}</strong> ({fmt(item.affected_count)}; {item.group.toLowerCase()})
        <p>Next: {item.investigation_or_action}</p>
        <p className="text-slate-600">Clear when: {item.clearance_criterion}</p>
        {item.existing_read_only_preview_action&&<p className="text-slate-500">Available read-only preview: {item.existing_read_only_preview_action}</p>}
       </li>)}
      </ol>
      <p className="text-slate-500">Guidance only; access checks and explicit confirmation apply to any subsequent write action. No remediation is run here.</p>
    </div>}
    <p className="text-xs text-slate-600">Assessment state: {String(data.lifecycle_status||'UNKNOWN').replaceAll('_',' ').toLowerCase()} · Checked {data.generated_at_utc?new Date(data.generated_at_utc).toLocaleString('en-GB'):'on request'}. Counts are independent readings, not an atomic snapshot.</p>
    <p className="text-xs text-slate-700">Worker: {remaining.worker_enabled?'Enabled':'Disabled'} · Automatic screening: {remaining.automatic_screening_enabled?'Enabled':'Disabled'} · Daily requests remaining: {fmt(remaining.daily_remaining)} · Lifetime requests remaining: {fmt(remaining.lifetime_remaining)}. These numbers do not authorize paid processing.</p>
    <p className="text-xs text-slate-600">Superseded (not AI-completed): {fmt(q.superseded_assessed)} · Superseded with changed/missing classification requiring review: {fmt(data.already_assessed_queue_reconciliation?.superseded_without_current_classification)}.</p>
    <p className="text-xs text-slate-600">Already-classified pending jobs excluded from AI eligibility: {fmt(remaining.pending_already_assessed_excluded_from_ai)}. These require queue-state review, not another provider call.</p>
    <p className="text-xs text-slate-600">Classification-usage lifecycle conflicts: {fmt((done.classification_usage_lifecycle_quality?.noncompleted_jobs_with_classification_usage||0)+(done.classification_usage_lifecycle_quality?.assessments_with_duplicate_classification_usage||0))} (non-completed jobs or duplicate usage records).</p>
    <p className="text-xs text-slate-600">Relevance-completed jobs with only sentiment usage: {fmt(done.completed_sentiment_usage_without_classification_usage)}. Sentiment usage is not classification proof.</p>
    <p className="text-xs text-slate-600">Completed jobs requiring latest-classification review: {fmt((done.latest_completion_classification_review?.completed_missing_latest_assessment||0)+(done.latest_completion_classification_review?.completed_latest_unclassified_or_invalid||0))}. Historical AI usage is preserved separately.</p>
    <p className="text-xs text-slate-600">Pending: {fmt(q.pending)} · Processing: {fmt(q.processing)} · Completed: {fmt(q.completed)} · Failed: {fmt(q.failed)} · Historical usage review: {fmt(done.completed_requiring_manual_history_review)} · Interrupted jobs quarantined: {fmt(recovery.already_quarantined_for_manual_review)}</p>
    {data.issues?.length>0?<div className="rounded-lg border border-amber-200 p-3"><h5 className="text-xs font-semibold text-amber-900">Needs review ({data.issues.length} categories)</h5><ul className="mt-2 space-y-2">{data.issues.map(issue=><li key={issue.code} className="text-xs text-slate-700"><strong>{issue.code.replaceAll('_',' ')}</strong> · {fmt(issue.count)} — {issue.next_step}</li>)}</ul></div>:<p className="text-xs text-emerald-700">No reconciliation warnings detected in this campaign.</p>}
    <p className="text-xs text-slate-500">Read-only. Classification and interrupted-job recovery require separate authorized actions and confirmation. No AI or crawl credits used.</p>
   </>}
  </div>}
 </section>;
}
