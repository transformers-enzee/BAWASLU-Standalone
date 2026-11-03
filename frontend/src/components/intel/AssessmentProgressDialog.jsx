import {useEffect, useState} from 'react';
import {base44} from '@/api/base44Client';

const FINISHED=['COMPLETED','FAILED','NEEDS_ATTENTION','NO_NEW_POSTS'];
const since=value=>{if(!value)return 'No successful AI activity recorded';const d=new Date(value);if(Number.isNaN(d.getTime()))return 'Unknown';const m=Math.max(0,Math.round((Date.now()-d.getTime())/60000));return m<1?'Less than a minute ago':m+' minute(s) ago'};
const labels={COLLECTING:'Collecting SocialCrawl posts',ASSESSING:'AI assessment in progress',
 COMPLETED:'Assessment complete',NEEDS_ATTENTION:'Paused — action required',
 FAILED:'Run failed',NO_NEW_POSTS:'No new posts captured'};
export default function AssessmentProgressDialog({title,run,onRefresh,onResume,onClose,loading=false,previewLoading=false,error='',showCost=false,onConfirm=null,preview=null}){
 const stage=run?.stage||(run?.status==='QUEUED'||run?.status==='RUNNING'?'COLLECTING':'ASSESSING');
 const count=Number(run?.total||0),done=Number(run?.completed||0);
 // Collection percentage is unknown until results are saved.
 const collecting=stage==='COLLECTING';
 const verifiedPercent=count>0?Math.max(0,Math.min(100,Math.round(done/count*100))):null;
 const statusUnavailable=Boolean(error&&run);
 return <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/65 p-4" onMouseDown={e=>{if(e.target===e.currentTarget)onClose?.()}}>
  <section className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" role="dialog" aria-modal="true" aria-label="Activation and AI assessment progress">
   <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
    <div><h2 className="text-lg font-bold text-[#19324a]">{title||'Campaign activation'}</h2>
     <p className="mt-1 text-xs text-slate-500">{run?.run_id?'Run #'+run.run_id:'Confirm activation'}</p></div>
    <button type="button" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onClick={onClose} aria-label="Close progress popup">✕ Close</button>
   </header>
   <div className="space-y-5 overflow-y-auto p-5">
    {!run&&<div className="space-y-3">
     <p className="text-sm text-slate-700">Activate this campaign to collect posts and assess the saved results?</p>
     {preview&&<p className="text-xs text-slate-600">Keywords: {(preview.keywords_used||[]).join(', ')} · Platforms: {(preview.platforms||[]).join(', ')}</p>}
     {previewLoading&&<p role="status" className="text-xs text-slate-500">Checking campaign readiness…</p>}
     <div className="flex flex-wrap gap-2">
      <button type="button" className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold" disabled={loading} onClick={onClose}>Cancel</button>
      {onConfirm&&<button type="button" className="rounded-lg bg-[#a52a2f] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50" disabled={loading||previewLoading||!preview} onClick={onConfirm}>Activate</button>}
     </div>
     {loading&&<p role="status" className="text-xs text-slate-500">Submitting activation request…</p>}
    </div>}
    {run&&<>
     {collecting&&<div role="status" aria-live="polite" className="space-y-3">
       <p className="text-sm font-semibold text-[#19324a]">Collecting SocialCrawl posts</p>
       <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label="Collecting SocialCrawl posts; exact progress unavailable" aria-valuetext="Collecting; percentage unavailable"><div className="h-full w-1/3 animate-pulse rounded-full bg-emerald-500"/></div>
     </div>}
     {!collecting&&<>
     <div className="grid grid-cols-3 gap-2">
      {[
       ['1 · Collect',run.status==='FAILED'?'Failed':run.total?'Complete':'In progress'],
       ['2 · Save',run.total?'Complete':run.stage==='NO_NEW_POSTS'?'No posts':'Pending'],
       ['3 · AI assess',count?done+' / '+count:'Pending']
      ].map(([name,value])=><div key={name} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><p className="text-[11px] font-semibold text-slate-500">{name}</p><p className="mt-1 text-sm font-bold text-[#19324a]">{value}</p></div>)}
     </div>
     <div role="status" aria-live="polite" className="space-y-2">
      <p className="flex items-center justify-between gap-3 text-sm font-semibold"><span>{labels[stage]||stage}</span></p>
      {!collecting&&verifiedPercent!==null&&!statusUnavailable?<div className="h-3 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label="Full AI assessments completed" aria-valuemin={0} aria-valuemax={count} aria-valuenow={done}><div className="h-full rounded-full bg-emerald-500 transition-all duration-300" style={{width:verifiedPercent+'%'}}/></div>:
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label={statusUnavailable?'Latest progress unavailable':collecting?'Collection progress unknown':'Assessment totals pending'} aria-valuetext={statusUnavailable?'Status unavailable':collecting?'Waiting for SocialCrawl':'Waiting for saved totals'}><div className="h-full w-1/3 animate-pulse rounded-full bg-emerald-500"/></div>}
       {collecting&&<p className="text-xs text-slate-500">SocialCrawl does not supply an exact collection percentage. This animation means waiting, not 15% completion. Counts update after provider results are saved.</p>}
       {statusUnavailable&&<p role="alert" className="text-xs text-amber-800">Current progress cannot be verified. Collection may still be running.</p>}
     </div>
     <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
      {[
       ['Saved posts',run.posts_saved||0],
       ['Full AI assessed',run.completed||0],
       ['Queued',run.queued||0],
       ['Processing',run.processing||0],
       ['Needs review',run.failed||0],
       ['Unable to queue',run.blocked||0],
       ...(run.stalled?[['Stalled worker',run.stalled]]:[])
      ].map(([key,value])=><div key={key} className="rounded-lg border border-slate-200 p-3"><strong className="block text-lg text-[#19324a]">{value}</strong>{key}</div>)}
     </div>
     <div className="rounded-lg border border-[#dce5ed] bg-[#f7fafb] px-4 py-3 text-xs text-[#29445d]" aria-label="Live assessment diagnostics">
       <p><strong>Actual throughput:</strong> {Number(run.completed_per_minute||0).toFixed(2)} completed posts/min (last 10 minutes)</p>
       <p className="mt-1"><strong>Last successful assessment:</strong> {since(run.last_activity_at)}</p>
       <p className="mt-1"><strong>Estimated completion:</strong> {run.eta_seconds!=null&&stage==='ASSESSING'?Math.ceil(run.eta_seconds/60)+' min':'Paused or insufficient live activity — no reliable estimate'}</p>
       <p className="mt-1"><strong>Worker status:</strong> {run.stalled?'Stalled — review required':run.processing?'Processing':run.queued?'Queued / awaiting worker':'Idle'}</p>
     </div>
     {run.budget&&<p className="text-xs text-slate-600">Remaining controlled AI request allowance: {run.budget.available||0}. The actual charge depends on provider token usage.</p>}
     </>}
     {run.error&&<p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">{run.error}</p>}
     {run.status_reason&&<p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">{run.status_reason}</p>}
     {stage==='NEEDS_ATTENTION'&&<p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">Assessment is paused or requires review, not actively advancing. Failed and ambiguous paid requests are never retried automatically. Only never-sent queued work can resume, with your confirmation.</p>}
     <div className="flex flex-wrap gap-2">
      <button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold" disabled={loading} onClick={onRefresh}>Refresh status</button>
      {!!run.queued&&!run.processing&&onResume&&<button type="button" className="rounded-lg bg-[#a52a2f] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={loading} onClick={onResume}>Resume queued assessments</button>}
     </div>
     {stage==='COMPLETED'&&<p className="text-xs text-emerald-800">All eligible sources in this run have been fully assessed. Review relevant findings in Intelligence Inbox; not all captured posts become Inbox cases.</p>}
    </>}
    {error&&<p role="alert" className="text-sm text-red-700">Status request failed: {error}. Collection may still be running; use Refresh status to retry.</p>}
    {loading&&<p role="status" className="text-xs text-slate-600">Checking saved progress…</p>}
   </div>
  </section>
 </div>;
}