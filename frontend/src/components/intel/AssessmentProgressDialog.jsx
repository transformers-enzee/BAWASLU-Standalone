import {useEffect, useState} from 'react';
import {base44} from '@/api/base44Client';

const FINISHED=['COMPLETED','FAILED','NEEDS_ATTENTION','NO_NEW_POSTS'];
const labels={COLLECTING:'Collecting SocialCrawl posts',ASSESSING:'AI assessment in progress',
 COMPLETED:'Assessment complete',NEEDS_ATTENTION:'Some posts need attention',
 FAILED:'Run failed',NO_NEW_POSTS:'No new posts captured'};
export default function AssessmentProgressDialog({title,run,onRefresh,onResume,onClose,loading=false,error='',showCost=false,onConfirm=null,preview=null}){
 const stage=run?.stage||(run?.status==='QUEUED'||run?.status==='RUNNING'?'COLLECTING':'ASSESSING');
 const count=Number(run?.total||0),done=Number(run?.completed||0);
 const percent=Number(run?.progress_percent||0);
 return <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/65 p-4" onMouseDown={e=>{if(e.target===e.currentTarget)onClose?.()}}>
  <section className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" role="dialog" aria-modal="true" aria-label="Activation and AI assessment progress">
   <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
    <div><h2 className="text-lg font-bold text-[#19324a]">{title||'Campaign activation'}</h2>
     <p className="mt-1 text-xs text-slate-500">{run?.run_id?'Run #'+run.run_id:'Provider and AI cost approval'}</p></div>
    <button type="button" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onClick={onClose} aria-label="Close progress popup">✕ Close</button>
   </header>
   <div className="space-y-5 overflow-y-auto p-5">
    {!run&&<div className="space-y-3">
     <p className="text-sm text-slate-700">Activate runs one paid SocialCrawl Discover collection (up to 100 posts). Once stored, each new post is queued for a full AI intelligence assessment, subject to the saved request budget. Only qualifying signals appear in Intelligence Inbox.</p>
     <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">SocialCrawl: up to {preview?.credit_cap||100} credits. Up to 100 separate GPT assessments may incur variable token charges. No repeated crawl or duplicate AI assessment is authorized automatically.</p>
     {preview&&<p className="text-xs text-slate-600">Keywords: {(preview.keywords_used||[]).join(', ')} · Platforms: {(preview.platforms||[]).join(', ')}</p>}
     {onConfirm&&<button type="button" className="rounded-lg bg-[#127b69] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50" disabled={loading||!preview} onClick={onConfirm}>{loading?'Activating…':'Confirm paid activation'}</button>}
    </div>}
    {run&&<>
     <div className="grid grid-cols-3 gap-2">
      {[
       ['1 · Collect',run.status==='FAILED'?'Failed':run.total?'Complete':'In progress'],
       ['2 · Save',run.total?'Complete':run.stage==='NO_NEW_POSTS'?'No posts':'Pending'],
       ['3 · AI assess',count?done+' / '+count:'Pending']
      ].map(([name,value])=><div key={name} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><p className="text-[11px] font-semibold text-slate-500">{name}</p><p className="mt-1 text-sm font-bold text-[#19324a]">{value}</p></div>)}
     </div>
     <div role="status" aria-live="polite" className="space-y-2">
      <p className="flex items-center justify-between gap-3 text-sm font-semibold"><span>{labels[stage]||stage}</span>{count>0&&<strong>{percent}%</strong>}</p>
      {count>0?<div className="h-3 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label="Full AI assessments completed" aria-valuemin={0} aria-valuemax={count} aria-valuenow={done}><div className="h-full rounded-full bg-emerald-500 transition-all duration-300" style={{width:percent+'%'}}/></div>:
       <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200"><div className="h-full w-1/3 animate-pulse rounded-full bg-emerald-500"/></div>}
      {stage==='COLLECTING'&&<p className="text-xs text-slate-500">SocialCrawl has not supplied an exact collection percentage. This indicator will update when the posts are saved.</p>}
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
     {run.budget&&<p className="text-xs text-slate-600">Remaining controlled AI request allowance: {run.budget.available||0}. The actual charge depends on provider token usage.</p>}
     {run.error&&<p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">{run.error}</p>}
     {run.status_reason&&<p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">{run.status_reason}</p>}
     {stage==='NEEDS_ATTENTION'&&<p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">Assessment is paused or requires review, not actively advancing. Failed and ambiguous paid requests are never retried automatically. Only never-sent queued work can resume, with your confirmation.</p>}
     <div className="flex flex-wrap gap-2">
      <button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold" disabled={loading} onClick={onRefresh}>Refresh status</button>
      {!!run.queued&&!run.processing&&onResume&&<button type="button" className="rounded-lg bg-[#127b69] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={loading} onClick={onResume}>Resume queued assessments</button>}
     </div>
     {stage==='COMPLETED'&&<p className="text-xs text-emerald-800">All eligible sources in this run have been fully assessed. Review relevant findings in Intelligence Inbox; not all captured posts become Inbox cases.</p>}
    </>}
    {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
    {loading&&<p role="status" className="text-xs text-slate-600">Checking saved progress…</p>}
   </div>
  </section>
 </div>;
}