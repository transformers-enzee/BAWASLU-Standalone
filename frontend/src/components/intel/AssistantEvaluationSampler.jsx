import {useState} from 'react';
import {ClipboardList,ChevronDown,RefreshCw,FileDown} from 'lucide-react';

const LABELS={
 POTENTIAL_VIOLATION_SIGNAL:'Potential violation signal',
 PUBLIC_CONCERN:'Public concern',
 EMERGING_NARRATIVE:'Emerging narrative',
 GEOGRAPHIC_UNCERTAINTY:'Jurisdiction uncertainty',
 PLATFORM_POLICY_COMPARISON:'Platform policy check',
 CROSS_MODULE_COMPARISON:'Inbox / Social comparison',
 GENERAL_SOURCE_REVIEW:'General source review'
};

export default function AssistantEvaluationSampler({onPrepare,disabled=false}){
 const [open,setOpen]=useState(false);
 const [target,setTarget]=useState(24);
 const [loading,setLoading]=useState(false);
 const [data,setData]=useState(null);
 const [error,setError]=useState('');
 const [prepared,setPrepared]=useState('');
 async function preparePlan(){
  if(loading||disabled)return;
  setLoading(true);setError('');setData(null);setPrepared('');
  try{
   const token=window.__BAWASLU_DEMO_REPLICA__?'DEMO-SNAPSHOT':
    (window.localStorage.getItem('bawaslu_access_token')||'');
   if(!token)throw Error('Sign in to prepare a permission-scoped review sample.');
   const response=await fetch('/api/assistant-evaluation/questions?target='+target,{
    method:'GET',cache:'no-store',
    headers:{Authorization:'Bearer '+token}
   });
   const json=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(typeof json.detail==='string'?json.detail:
    'Saved source sampling is unavailable for this account.');
   if(json.framework!=='BAWASLU_ASSISTANT_EVALUATION_PLAN_V1488')
    throw Error('Unknown review sampling response.');
   setData(json);
  }catch(e){setError(e.message||'Could not prepare review questions.')}
  finally{setLoading(false)}
 }
 function choose(item){
  if(disabled)return;
  onPrepare(item.question);
  setPrepared(item.source_record_id);
 }
 function exportPlan(){
  if(!data)return;
  // Officer-initiated download, never an upload or a paid API call.
  const blob=new Blob([JSON.stringify({
   ...data,
   export_note:'Source URLs and record IDs are restricted review material. Share only with authorized officers.',
   file_exported_at:new Date().toISOString()
  },null,2)],{type:'application/json;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='BAWASLU-assistant-evaluation-questions-v1488.json';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
 }
 return <section data-testid="assistant-evaluation-sampler"
   className="rounded-xl border border-[#e7d7d8] bg-white">
   <button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)}
    className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left">
    <span className="flex items-center gap-2 text-sm font-semibold text-[#801b24]">
     <ClipboardList size={17}/> Prepare real-source Assistant evaluation questions
    </span>
    <ChevronDown size={16} className={open?'rotate-180 transition-transform':'transition-transform'}/>
   </button>
   {open&&<div className="border-t border-[#e8edf2] px-4 pb-4 pt-3 space-y-3">
    <p className="text-xs leading-5 text-[#65788b]">
     Prepare a diversity-oriented sample from relevant, saved Inbox posts you can access.
     This only reads cached, permission-scoped evidence. No AI answers are generated,
     no new posts are crawled and no model credits are consumed.
    </p>
    <div className="flex flex-wrap items-center gap-2">
     <label htmlFor="assistant-evaluation-target" className="text-xs font-semibold text-[#52647a]">
      Target questions
     </label>
     <select id="assistant-evaluation-target" value={target} onChange={e=>setTarget(Number(e.target.value))}
      disabled={loading||disabled}
      className="rounded-md border border-[#ccd7df] px-2 py-1.5 text-xs">
      {[20,24,30].map(n=><option key={n} value={n}>{n}</option>)}
     </select>
     <button type="button" data-testid="assistant-evaluation-generate"
      className="intel-button text-xs" disabled={loading||disabled} onClick={preparePlan}>
      <RefreshCw size={13}/>{loading?'Preparing…':'Prepare questions (no AI call)'}
     </button>
     {data&&<button type="button" data-testid="assistant-evaluation-export"
      className="intel-ghost text-xs" onClick={exportPlan}>
      <FileDown size={13}/> Export review plan (.json)
     </button>}
    </div>
    {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
    {data&&<div data-testid="assistant-evaluation-sampler-result" className="space-y-3">
     <p className="text-sm font-semibold text-[#263749]">
      {data.prepared_questions}/{data.target_questions} real-source questions prepared
      {data.shortfall>0&&<span className="ml-2 text-amber-800">
       · {data.shortfall} not available in this sample</span>}
     </p>
     <p className="text-[11px] leading-5 text-[#876532]">
      This is a bounded, non-random sample (up to 300 links per authorized campaign).
      Coverage is incomplete and source allegations remain unverified. A zero in a
      category does not prove there are no relevant posts elsewhere.
     </p>
     <div data-testid="assistant-evaluation-coverage"
      className="grid grid-cols-2 gap-2 md:grid-cols-3">
      {Object.entries(data.category_available_sources||{}).map(([key,count])=>
       <div key={key} className="rounded-md border border-[#e4eaf0] px-3 py-2">
        <p className="text-[11px] text-[#52647a]">{LABELS[key]||key}</p>
        <p className="font-bold text-sm">{data.category_selected_questions?.[key]||0}
         <span className="text-[11px] font-normal text-[#7b8d99]"> selected · {count} available</span>
        </p>
       </div>)}
     </div>
     {data.missing_categories?.length>0&&<p className="text-xs text-amber-800">
      Coverage gaps: {data.missing_categories.map(x=>LABELS[x]||x).join(', ')}.
     </p>}
     <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
      {(data.questions||[]).map(item=>
       <div key={item.source_record_id} className="rounded-lg border border-[#e3e9ee] bg-[#fafbfc] p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
         <p className="text-xs font-semibold">{item.question_number}. {LABELS[item.category]||item.category}
          <span className="ml-2 font-normal text-[#64748b]">
           {item.source_record_id} · {item.platform}
          </span>
         </p>
         <button type="button" data-testid="assistant-evaluation-use-question"
          onClick={()=>choose(item)} disabled={disabled||loading}
          className="intel-ghost text-xs">Use question (do not send)</button>
        </div>
        <p className="mt-1 text-[11px] text-[#52647a]">{item.question}</p>
        <a href={item.source_url} target="_blank" rel="noopener noreferrer"
         className="mt-1 inline-block text-[11px] text-[#801b24] underline">Open original source</a>
       </div>)}
     </div>
     {data.negative_control&&<div className="rounded-lg border border-dashed border-amber-300 p-3">
      <p className="text-xs font-semibold text-[#84642c]">Separate no-evidence control — excluded from real case counts</p>
      <p className="mt-1 text-[11px] text-[#64748b]">{data.negative_control.question}</p>
      <button type="button" data-testid="assistant-evaluation-use-control"
       className="intel-ghost mt-2 text-xs" disabled={disabled||loading}
       onClick={()=>choose(data.negative_control)}>Use control (do not send)</button>
     </div>}
     {prepared&&<p data-testid="assistant-evaluation-question-prepared"
      className="rounded-md bg-[#f3f8f5] p-2 text-xs text-[#146347]">
      {prepared} is loaded in the question field. Review it and press Send yourself
      to run an AI answer; that step may consume model credits.
     </p>}
     <p className="text-[11px] text-[#876532]">
      Officer-reviewed legal PDF evaluation and independently matched Inbox formal
      records are separate gaps. Prepared questions and automated checks do not
      constitute human answer-quality acceptance.
     </p>
    </div>}
   </div>}
 </section>;
}
