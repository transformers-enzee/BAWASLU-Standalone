import {useState} from 'react';
import {FilePenLine,ChevronDown,Download,UploadCloud} from 'lucide-react';
import {REVIEW_DIMENSIONS,validateReviewPacket} from '@/lib/assistantReviewAggregation';
import {blankOfficerScores,officerScoreCompletion,completedOfficerScoringCsv} from '@/lib/assistantReviewScoring';

const DISPLAY={
 citation_grounding:'Citation grounding',
 source_relevance:'Source relevance',
 legal_uncertainty:'Legal uncertainty',
 cross_module_consistency:'Cross-module consistency'
};
const safeSourceUrl=value=>{
 try{
  const url=new URL(String(value||''));
  return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password?url.href:'';
 }catch{return ''}
};

export default function AssistantHumanScoring(){
 const [open,setOpen]=useState(false);
 const [packet,setPacket]=useState(null);
 const [ratings,setRatings]=useState(blankOfficerScores);
 const [reviewerId,setReviewerId]=useState('');
 const [confirmed,setConfirmed]=useState(false);
 const [error,setError]=useState('');
 const [loading,setLoading]=useState(false);
 const progress=packet?officerScoreCompletion(packet,ratings,reviewerId):null;

 async function importPacket(event){
  const input=event.currentTarget;
  const file=input.files?.[0];
  setPacket(null);setRatings(blankOfficerScores());setConfirmed(false);setError('');
  if(!file)return;
  setLoading(true);
  try{
   if(!file.name.toLowerCase().endsWith('.json'))throw Error('Choose an original Assistant review packet (.json).');
   if(file.size>2*1024*1024)throw Error('Packet is above the 2 MB local file limit.');
   const next=JSON.parse(await file.text());
   validateReviewPacket(next);
   if(next.human_scorecard?.checks?.length!==4)throw Error('Missing four rating dimensions.');
   setPacket(next);
  }catch(e){setError(e?.message||'Packet could not be opened.')}
  finally{setLoading(false);input.value=''}
 }
 function setRow(id,key,value){
  setRatings(old=>({...old,[id]:{...old[id],[key]:value}}));
  setConfirmed(false);
 }
 function saveScoringSheet(){
  try{
   if(!confirmed)throw Error('Confirm that you personally reviewed the original evidence.');
   const csv=completedOfficerScoringCsv(packet,ratings,reviewerId,new Date().toISOString());
   const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
   const link=document.createElement('a');
   link.href=url;
   link.download='BAWASLU-officer-scoring-'+packet.packet_id+'.csv';
   link.click();
   setTimeout(()=>URL.revokeObjectURL(url),10000);
   setError('');
  }catch(e){setError(e?.message||'Could not prepare the scoring sheet.')}
 }
 return <section data-testid="assistant-human-scoring" className="rounded-xl border border-[#e7d7d8] bg-white">
  <button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)}
   className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left">
   <span className="flex items-center gap-2 text-sm font-semibold text-[#801b24]">
    <FilePenLine size={17}/> Prepare independent officer scoring sheet
   </span>
   <ChevronDown size={16} className={open?'rotate-180 transition-transform':'transition-transform'}/>
  </button>
  {open&&<div className="space-y-3 border-t border-[#e8edf2] px-4 pb-4 pt-3">
   <p className="text-xs leading-5 text-[#65788b]">
    Import an actual AI answer packet exported in this system, inspect its original source evidence,
    and enter your own scores. Everything stays in this browser session. Do not use synthetic
    examples as BAWASLU human acceptance. Importing a file does not authenticate its author.
   </p>
   <label className="block rounded-lg border border-dashed border-[#bdc9d5] bg-[#f8fafc] p-3 text-xs text-[#486079]">
    <span className="mb-2 flex items-center gap-2 font-semibold"><UploadCloud size={16}/> Open original Assistant evidence packet</span>
    <input type="file" accept=".json,application/json" data-testid="assistant-human-scoring-file"
     className="block w-full text-xs" disabled={loading} onChange={importPacket}/>
   </label>
   {loading&&<p role="status" className="text-xs">Inspecting local packet...</p>}
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {packet&&<div data-testid="assistant-human-scoring-workspace" className="space-y-3">
    <p className="text-xs text-[#805f25]">
     Packet {packet.packet_id}. The packet ID is not cryptographic proof. Independent source review
     and authenticated officer sign-off are still required for BAWASLU acceptance.
    </p>
    <details className="rounded-lg border border-[#e4eaf0] p-3">
     <summary className="cursor-pointer text-xs font-semibold">Show question, AI answer and source references</summary>
     <div className="mt-3 space-y-2 text-xs">
      <p><strong>Question:</strong> {packet.question}</p>
      <p className="whitespace-pre-wrap break-words"><strong>Answer:</strong> {String(packet.assistant_answer||'').slice(0,15000)}</p>
      {String(packet.assistant_answer||'').length>15000&&<p>Long answer preview abbreviated. Use the original secure packet for complete text.</p>}
      <p><strong>Cited IDs:</strong> {(packet.cited_source_ids||[]).join(', ')||'None'}</p>
      {(packet.evidence_snapshot?.exported_records||[]).map((r,i)=><div key={i} className="rounded-md bg-[#f8fafc] p-2">
       <p>{r.record_id||'Unidentified'} · {r.platform||r.record_type||'Source'}</p>
       <p className="whitespace-pre-wrap break-words">{String(r.source_excerpt||'').slice(0,600)}</p>
       {safeSourceUrl(r.source_url)&&<a className="text-[#801b24] underline" href={safeSourceUrl(r.source_url)}
        target="_blank" rel="noopener noreferrer">Inspect original source</a>}
      </div>)}
     </div>
    </details>
    <div className="space-y-1">
     <label htmlFor="assistant-officer-id" className="text-xs font-semibold">Your reviewer ID</label>
     <input id="assistant-officer-id" data-testid="assistant-reviewer-id" value={reviewerId}
      maxLength={80} placeholder="Authorized reviewer identifier"
      onChange={e=>{setReviewerId(e.target.value);setConfirmed(false)}}
      className="intel-input w-full max-w-sm"/>
     <p className="text-[11px] text-[#65788b]">The ID is self-declared here; official identity and authorization must be checked outside this local worksheet.</p>
    </div>
    <div className="grid gap-3 md:grid-cols-2">
     {REVIEW_DIMENSIONS.map(id=>{
      const row=ratings[id];
      return <div key={id} className="space-y-2 rounded-lg border border-[#e4eaf0] p-3">
       <label htmlFor={'assistant-score-'+id} className="block text-xs font-semibold">{DISPLAY[id]}</label>
       <select id={'assistant-score-'+id} data-testid={'assistant-score-'+id}
        className="w-full rounded-lg border border-[#d5e0e8] bg-white p-2 text-xs"
        value={row.score} onChange={e=>setRow(id,'score',e.target.value)}>
        <option value="">Choose your score</option>
        <option value="1">1 - Supported</option>
        <option value="0">0 - Unsupported / incorrect</option>
        <option value="N/A">N/A - Not applicable</option>
       </select>
       <input aria-label={DISPLAY[id]+' evidence reference'}
        data-testid={'assistant-evidence-'+id}
        className="intel-input w-full text-xs" maxLength={500}
        value={row.evidence_reference}
        onChange={e=>setRow(id,'evidence_reference',e.target.value)}
        placeholder={row.score==='N/A'?'Evidence optional for N/A':'Original evidence reference (required for 0/1)'}/>
       <textarea aria-label={DISPLAY[id]+' review note'} data-testid={'assistant-note-'+id}
        className="intel-input w-full min-h-20 text-xs" maxLength={1500}
        value={row.reviewer_note}
        onChange={e=>setRow(id,'reviewer_note',e.target.value)}
        placeholder="Explain your assessment (12+ characters)"/>
      </div>
     })}
    </div>
    <p data-testid="assistant-human-scoring-progress" className="text-xs font-semibold">
     {progress.completed}/{progress.total} dimension scores complete
    </p>
    {!!progress.errors.length&&<details className="text-xs text-[#996528]">
     <summary className="cursor-pointer">Remaining requirements ({progress.errors.length})</summary>
     <ul className="ml-5 mt-1 list-disc">{progress.errors.map((e,i)=><li key={i}>{e}</li>)}</ul>
    </details>}
    <label className="flex items-start gap-2 text-xs text-[#52647a]">
     <input type="checkbox" data-testid="assistant-scoring-confirm" checked={confirmed}
      onChange={e=>setConfirmed(e.target.checked)} className="mt-0.5"/>
     I personally inspected the original sources and completed these ratings independently.
     This declaration is not server-verified officer approval.
    </label>
    <button type="button" data-testid="assistant-human-scoring-export"
     className="intel-button text-xs" disabled={!progress.ready||!confirmed} onClick={saveScoringSheet}>
     <Download size={14}/> Export completed scoring CSV
    </button>
    <p className="text-[11px] leading-5 text-[#65788b]">
     Send this CSV and its original matching JSON packet only through approved secure channels.
     A second authorized reviewer must score independently; use Human answer-review consolidation
     to compare results. No records are saved to the database, and no AI credit is consumed.
    </p>
   </div>}
  </div>}
 </section>;
}
