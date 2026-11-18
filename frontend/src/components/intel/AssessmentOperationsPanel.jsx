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
    <p className="text-xs text-slate-600">Assessment state: {String(data.lifecycle_status||'UNKNOWN').replaceAll('_',' ').toLowerCase()} · Checked {data.generated_at_utc?new Date(data.generated_at_utc).toLocaleString('en-GB'):'on request'}. Counts are independent readings, not an atomic snapshot.</p>
    <p className="text-xs text-slate-700">Worker: {remaining.worker_enabled?'Enabled':'Disabled'} · Automatic screening: {remaining.automatic_screening_enabled?'Enabled':'Disabled'} · Daily requests remaining: {fmt(remaining.daily_remaining)} · Lifetime requests remaining: {fmt(remaining.lifetime_remaining)}. These numbers do not authorize paid processing.</p>
    <p className="text-xs text-slate-600">Already-classified pending jobs excluded from AI eligibility: {fmt(remaining.pending_already_assessed_excluded_from_ai)}. These require queue-state review, not another provider call.</p>
    <p className="text-xs text-slate-600">Pending: {fmt(q.pending)} · Processing: {fmt(q.processing)} · Completed: {fmt(q.completed)} · Failed: {fmt(q.failed)} · Historical usage review: {fmt(done.completed_requiring_manual_history_review)} · Interrupted jobs quarantined: {fmt(recovery.already_quarantined_for_manual_review)}</p>
    {data.issues?.length>0?<div className="rounded-lg border border-amber-200 p-3"><h5 className="text-xs font-semibold text-amber-900">Needs review ({data.issues.length} categories)</h5><ul className="mt-2 space-y-2">{data.issues.map(issue=><li key={issue.code} className="text-xs text-slate-700"><strong>{issue.code.replaceAll('_',' ')}</strong> · {fmt(issue.count)} — {issue.next_step}</li>)}</ul></div>:<p className="text-xs text-emerald-700">No reconciliation warnings detected in this campaign.</p>}
    <p className="text-xs text-slate-500">Read-only. Classification and interrupted-job recovery require separate authorized actions and confirmation. No AI or crawl credits used.</p>
   </>}
  </div>}
 </section>;
}
