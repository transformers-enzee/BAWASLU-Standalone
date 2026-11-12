import {useState} from 'react';
import {FileCheck2,UploadCloud,Download,ChevronDown} from 'lucide-react';
import {
 parseReviewCsv,aggregateAssistantReviews,aggregateSummaryJson
} from '@/lib/assistantReviewAggregation';

const title={
 citation_grounding:'Citation grounding',
 source_relevance:'Source relevance',
 legal_uncertainty:'Legal uncertainty',
 cross_module_consistency:'Cross-module consistency'
};
const asCount=value=>Number(value||0).toLocaleString('en-GB');

export default function AssistantReviewConsolidation(){
 const [open,setOpen]=useState(false);
 const [report,setReport]=useState(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');

 async function loadLocalFiles(event){
  const input=event.currentTarget;
  const files=Array.from(input.files||[]);
  setBusy(true);setError('');setReport(null);
  try{
   if(!files.length)return;
   if(files.length>100)throw Error('Choose at most 100 files per consolidation.');
   const packets=[],scores=[],problems=[];
   for(const file of files){
    if(file.size>2*1024*1024){
     problems.push(file.name+': file exceeds the 2 MB safety limit.');continue;
    }
    try{
     const content=await file.text();
     if(file.name.toLowerCase().endsWith('.json')){
      packets.push(JSON.parse(content));
     }else if(file.name.toLowerCase().endsWith('.csv')){
      scores.push(parseReviewCsv(content));
     }else{
      problems.push(file.name+': unsupported file type.');
     }
    }catch(e){problems.push(file.name+': '+(e.message||'Unrecognized format.'))}
   }
   const evaluation=aggregateAssistantReviews(packets,scores);
   setReport({...evaluation,errors:[...problems,...evaluation.errors]});
  }catch(e){setError(e?.message||'Could not read review documents.')}
  finally{setBusy(false);input.value=''}
 }
 function exportAggregate(){
  try{
   if(!report)return;
   const blob=new Blob([aggregateSummaryJson(report)],{
    type:'application/json;charset=utf-8'
   });
   const url=URL.createObjectURL(blob);
   const element=document.createElement('a');
   element.href=url;element.download='BAWASLU-human-review-aggregate-v1487.json';
   element.click();
   setTimeout(()=>URL.revokeObjectURL(url),10000);
  }catch(e){setError(e?.message||'Could not export report.')}
 }
 return <section data-testid="assistant-review-consolidation" className="rounded-xl border border-[#e7d7d8] bg-white">
  <button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)}
   className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left">
   <span className="flex items-center gap-2 text-sm font-semibold text-[#801b24]">
    <FileCheck2 size={17}/> Human answer-review consolidation
   </span>
   <ChevronDown size={16} className={open?'rotate-180 transition-transform':'transition-transform'}/>
  </button>
  {open&&<div className="border-t border-[#e8edf2] px-4 pb-4 pt-3 space-y-3">
   <p className="text-xs leading-5 text-[#65788b]">
    Combine exported AI Assistant evidence packets (.json) with separately scored officer sheets (.csv).
    All files stay in this browser session. Reviewers must inspect original sources;
    self-declared identities and file authenticity are not independently verified.
   </p>
   <label className="block rounded-lg border border-dashed border-[#bdc9d5] bg-[#f8fafc] p-3 text-xs text-[#486079]">
    <span className="mb-2 flex items-center gap-2 font-semibold"><UploadCloud size={16}/>
     Choose review packets and completed scoring sheets
    </span>
    <input data-testid="assistant-review-file-input" type="file" multiple
     accept=".json,.csv,application/json,text/csv"
     className="block w-full text-xs file:mr-3 file:rounded-md file:border-0 file:bg-[#801b24] file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white"
     disabled={busy} onChange={loadLocalFiles}/>
   </label>
   <p className="text-[11px] text-[#847252]">
    Each dimension needs ratings from two distinct reviewers. Disagreements require a separate,
    documented adjudicator. Missing scores are never counted as correct. No database upload or AI call occurs.
   </p>
   {busy&&<p role="status" className="text-sm text-[#52647a]">Validating local review files…</p>}
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {report&&<div data-testid="assistant-review-consolidation-result" className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
     <p className="text-xs font-semibold text-[#263749]">
      {asCount(report.packet_count)} evidence packets · {asCount(report.scoring_sheets_accepted)} scored sheets accepted
     </p>
     <button data-testid="assistant-review-summary-export" type="button"
      className="intel-ghost text-xs" onClick={exportAggregate}>
      <Download size={13}/> Export aggregate (.json)
     </button>
    </div>
    <div className="grid gap-2 sm:grid-cols-2">
     {report.dimension_stats.map(d=><div key={d.dimension} data-testid={'assistant-review-dimension-'+d.dimension}
       className="rounded-lg border border-[#e4eaf0] p-3">
      <p className="text-xs font-bold text-[#334960]">{title[d.dimension]||d.dimension}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
       <p className="text-lg font-bold tabular-nums text-[#801b24]">
        {d.score_1_support_rate_percent===null?'—':d.score_1_support_rate_percent+'%'}
       </p>
       <p className="text-[11px] text-[#65788b]">
        {asCount(d.consensus_supported)}/{asCount(d.consensus_scored)} supported
       </p>
      </div>
      <p className="mt-1 text-[11px] text-[#65788b]">
       {asCount(d.awaiting_review)} awaiting · {asCount(d.disagreement_unresolved)} unresolved ·
       {' '}{asCount(d.agreed_not_applicable)} N/A
      </p>
      <p className="mt-1 text-[11px] text-[#65788b]">
       Reviewer agreement: {d.reviewer_agreement_percent===null?'Not measured':
        d.reviewer_agreement_percent+'% ('+d.independent_agreements+'/'+d.independent_pairs+')'}
      </p>
     </div>)}
    </div>
    <p className="text-[11px] leading-5 text-[#8a6339]">
     Percentages represent only consensus/adjudicated human scores of 1 out of scores 0 or 1,
     not a verified AI accuracy rate. Denominators and disputed cases remain visible.
     This local report is not BAWASLU approval or independent confirmation of reviewer identity.
    </p>
    {!!report.cases.length&&<details className="rounded-lg border border-[#e4eaf0] p-3">
     <summary className="cursor-pointer text-xs font-semibold text-[#334960]">
      Per-packet review status ({report.cases.length} dimension rows)
     </summary>
     <div className="mt-2 max-h-56 overflow-y-auto space-y-1">
      {report.cases.slice(0,120).map(c=><p key={c.packet_id+':'+c.dimension}
       className="flex flex-wrap justify-between gap-2 text-[11px] text-[#52647a]">
       <span>{c.packet_id} · {title[c.dimension]}</span>
       <strong>{c.status.replaceAll('_',' ')}</strong>
      </p>)}
      {report.cases.length>120&&<p className="text-[11px]">Further results are included in the JSON summary.</p>}
     </div>
    </details>}
    {!!report.errors.length&&<div role="alert" data-testid="assistant-review-import-errors"
     className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-[#865e2d]">
     <p className="font-semibold">{report.errors.length} file(s) or records require correction.</p>
     {report.errors.slice(0,8).map((e,i)=><p key={i} className="mt-1 break-words">{e}</p>)}
     {report.errors.length>8&&<p>Additional problems are in the aggregate JSON.</p>}
    </div>}
   </div>}
  </div>}
 </section>;
}
