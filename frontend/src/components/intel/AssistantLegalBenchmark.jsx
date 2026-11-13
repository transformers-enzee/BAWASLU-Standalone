import {useState} from 'react';
import {ClipboardCheck,ChevronDown,Download,Play} from 'lucide-react';

export default function AssistantLegalBenchmark({disabled=false}){
 const [open,setOpen]=useState(false);
 const [running,setRunning]=useState(false);
 const [result,setResult]=useState(null);
 const [error,setError]=useState('');
 async function run(){
  if(disabled||running)return;
  setRunning(true);setError('');setResult(null);
  try{
   if(window.__BAWASLU_DEMO_REPLICA__)throw Error('Synthetic legal QA is unavailable in demo mode.');
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token)throw Error('Sign in with an authorized administrator account.');
   const res=await fetch('/api/assistant-evaluation/legal-benchmark',{
    method:'GET',cache:'no-store',headers:{Authorization:'Bearer '+token}});
   const value=await res.json().catch(()=>({}));
   if(!res.ok)throw Error(typeof value.detail==='string'?value.detail:'Legal QA is not available.');
   if(value.schema!=='BAWASLU_SYNTHETIC_LEGAL_SIGNAL_BENCHMARK_V1530')
    throw Error('Unexpected legal QA data version.');
   setResult(value);
  }catch(e){setError(e.message||'Could not run synthetic QA.')}
  finally{setRunning(false)}
 }
 function download(){
  if(!result)return;
  const contents=JSON.stringify(result,null,2);
  const blob=new Blob([contents],{type:'application/json;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;
  a.download='BAWASLU-legal-synthetic-benchmark-v1530.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
 }
 return <section data-testid="assistant-legal-benchmark" className="rounded-xl border border-[#e1e7ec] bg-white">
  <button type="button" onClick={()=>setOpen(v=>!v)} aria-expanded={open}
   className="flex w-full items-center justify-between gap-2 p-3 text-left">
   <span className="flex items-center gap-2 text-sm font-semibold text-[#801b24]">
    <ClipboardCheck size={17}/> Synthetic legal-answer signal QA (no AI calls)
   </span><ChevronDown size={16} className={open?'rotate-180':''}/>
  </button>
  {open&&<div className="border-t border-[#e1e7ec] p-3 space-y-3">
   <p className="text-xs text-[#65788b]">Tests fixed developer-labeled examples covering citations, legal scope, document review,
    article attribution, polarity, dates and quantities. These examples are not real BAWASLU cases
    or officer-approved legal references. Scores are signal-check agreement only, never real AI accuracy.</p>
   <div className="flex gap-2 flex-wrap">
    <button type="button" data-testid="assistant-legal-benchmark-run" onClick={run}
     disabled={disabled||running} className="intel-button text-xs">
     <Play size={13}/>{running?'Checking…':'Run offline synthetic benchmark'}
    </button>
    {result&&<button type="button" className="intel-ghost text-xs"
     data-testid="assistant-legal-benchmark-export" onClick={download}>
     <Download size={13}/>Export results (.json)</button>}
   </div>
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {result&&<div data-testid="assistant-legal-benchmark-results" className="space-y-3">
    <p className="text-sm font-semibold">{result.case_checks_matched}/{result.number_of_cases} synthetic cases matched;
     {' '}{result.matched_signal_assertions}/{result.labeled_signal_assertions} labeled signal checks matched</p>
    <p className="text-xs">Synthetic signal precision: {result.synthetic_signal_precision===null?'N/A':(100*result.synthetic_signal_precision).toFixed(1)+'%'}
     {' '}· Synthetic signal recall: {result.synthetic_signal_recall===null?'N/A':(100*result.synthetic_signal_recall).toFixed(1)+'%'}</p>
    <p className="text-xs text-amber-800">Human gold answers: 0. Real model answers: 0.
     Human answer-quality acceptance is still pending. No model credit, crawling or database writes.</p>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
     {Object.entries(result.category_counts||{}).map(([name,count])=><div key={name} className="rounded border border-[#e1e7ec] p-2 text-xs">
      <p className="font-semibold">{name.replaceAll('_',' ')}</p><p>{count} synthetic cases</p>
     </div>)}
    </div>
    {(result.cases||[]).some(x=>!x.case_matched)&&<details data-testid="assistant-legal-benchmark-failures" className="text-xs">
     <summary className="cursor-pointer font-semibold">Review mismatched synthetic cases ({result.case_checks_failed})</summary>
     <ul className="mt-2 space-y-2">{result.cases.filter(x=>!x.case_matched).map(x=>
      <li key={x.id} className="border rounded p-2">{x.id} · {x.category}
       <p>Expected signals: {x.expected_issue_present.join(', ')||'none'}.</p>
       <p>Unexpected if present: {x.expected_issue_absent.join(', ')||'none'}.</p>
       <p>Observed: {x.observed_issue_codes.join(', ')||'none'}.</p>
      </li>)}</ul>
    </details>}
   </div>}
  </div>}
 </section>;
}
