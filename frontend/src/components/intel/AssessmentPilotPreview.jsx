import { useEffect, useState } from 'react';
import { base44 } from '@/api/base44Client';

export default function AssessmentPilotPreview({ campaign }) {
 const [sampleSize,setSampleSize]=useState(40);
 const [plan,setPlan]=useState(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');

 useEffect(()=>{setPlan(null);setError('')},[campaign?.id]);

 async function load(size=sampleSize,anchor=null) {
  if(!campaign?.id||loading)return;
  setLoading(true);setError('');
  try {
   const res=await base44.functions.invoke('socialListening',{
    action:'campaignAssessmentPilotPreview',id:campaign.id,
    data:{sample_size:size,...(anchor?{anchor_id:anchor}:{})}
   });
   setPlan(res.data);
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

 const metrics=plan?[
  ['Completed',plan.counts.completed],
  ['Processing',plan.counts.processing],
  ['Queued',plan.counts.queued],
  ['Needs attention',plan.counts.failed],
  ['Not queued',plan.counts.not_queued],
 ]:[];
 return <details className="rounded-lg border border-slate-200 p-4" aria-label="AI assessment pilot">
  <summary className="cursor-pointer font-semibold text-sm">AI assessment pilot · 40–50 stored posts</summary>
  <div className="mt-3 space-y-3">
   <p className="text-xs text-slate-600">Review a read-only sample of stored Social Listening evidence before authorizing any paid AI assessment. This does not crawl, assess, or enqueue posts.</p>
   <div className="flex gap-3 flex-wrap items-end">
    <label className="text-xs font-medium">Sample size
     <select className="intel-input mt-1 block" value={sampleSize} onChange={e=>{setSampleSize(Number(e.target.value));setPlan(null)}}>
      <option value={40}>40 records</option><option value={50}>50 records</option>
     </select>
    </label>
    <button type="button" className="intel-ghost text-xs" disabled={loading} onClick={()=>load(sampleSize)}>{loading?'Preparing…':'Preview sample (free)'}</button>
    {plan&&<button type="button" className="intel-ghost text-xs" disabled={loading} onClick={()=>load(plan.requested,plan.sample_anchor_id)}>Refresh progress</button>}
   </div>
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
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
     <p className="font-semibold">Preview only. No AI provider called, no credits charged, and no paid batch job created.</p>
    </div>
    <div className="max-h-80 overflow-y-auto border rounded-lg">
     <table className="w-full text-left text-xs"><thead className="sticky top-0 bg-slate-100"><tr><th className="p-2">Post</th><th className="p-2">Platform</th><th className="p-2">Text sample</th><th className="p-2">Assessment</th></tr></thead><tbody>
      {plan.records.map(row=><tr key={row.id} className="border-t"><td className="p-2 whitespace-nowrap">#{row.id}{row.source_url&&<a className="block text-teal-700 underline" href={row.source_url} target="_blank" rel="noopener noreferrer">Source</a>}{row.assessment_state==='COMPLETED'&&<a className="block text-teal-700 underline" href={'/inbox?campaign_id='+encodeURIComponent(campaign.id)+'&result_id='+encodeURIComponent(row.id)}>Review in Inbox</a>}</td><td className="p-2">{row.platform}</td><td className="p-2 break-words max-w-[400px]">{row.text_excerpt||'Source text unavailable'}</td><td className="p-2 whitespace-nowrap">{row.assessment_state.replaceAll('_',' ')}{row.relevance_label&&<span className="block text-slate-500">{row.relevance_label}</span>}</td></tr>)}
     </tbody></table>
    </div>
    <p className="text-xs text-slate-500">Progress reflects stored assessments, not requests accepted for processing. The anchor keeps the same sample while this page remains open; a new preview creates a fresh sample. Human verification remains required for potential violation signals.</p>
   </section>}
  </div>
 </details>;
}
