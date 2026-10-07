import { Link } from 'react-router-dom';

const asList=value=>Array.isArray(value)?value:[];
const listLabel=value=>Array.isArray(value)?value.join(', '):(typeof value==='string'&&value.trim()?value:'—');

export default function DuplicatePanel({item,comparison,related=[],match=null,busy,onDecision,canDecide=false}){
 const safeRelated=asList(related);
 const sources=safeRelated.filter(x=>x&&item&&(x.merged_into===item.id||item.merged_into===x.id));
 const basis=asList(match?.basis);
 const score=Number(match?.score);
 const scoreLabel=Number.isFinite(score)?Math.round(score*100):null;
 if(!item)return null;
 return <>
  {item.duplicate_of&&<section className="intel-card border-[#ebd6a8] bg-[#fffaf0] p-5 space-y-3 text-sm">
   <h2 className="font-semibold">Potential Duplicate</h2>
   <p>Original records and evidence are retained separately. A human reviewer must decide whether to merge or keep them separate.</p>
   {match&&<div className="rounded-lg border border-[#ead7a7] bg-white/70 p-3">
    <p className="font-semibold">Similarity: {scoreLabel===null?'Available for review':scoreLabel+'%'}</p>
    {basis.length>0&&<p className="text-xs text-[#65798a] mt-1">Why flagged: {basis.join(' · ')}</p>}
   </div>}
   <details>
    <summary className="cursor-pointer text-[#126d91] font-semibold">View Comparison</summary>
    <div className="grid md:grid-cols-2 gap-4 mt-3">{[item,comparison].filter(Boolean).map(x=><div key={x.id||x.intelligence_id} className="border rounded-lg p-3 space-y-2 break-words">
     <Link className="text-[#126d91] underline" to={`/intelligence/${x.id}`}>{x.intelligence_id||'Record'} · {x.title||'Untitled'}</Link>
     <p>Source: {x.source_name||x.author||'Not recorded'}</p>
     <p>URL: {x.source_url||'Not recorded'}</p>
     <p>Published: {x.publication_datetime||x.publication_date||'Not recorded'}</p>
     <p>Entity: {listLabel(x.related_entities)}</p>
     <p>Topics: {listLabel(x.related_topics)}</p>
     <p className="whitespace-pre-wrap">Original text: {x.original_content||'No text entered'}</p>
    </div>)}</div>
   </details>
   {item.duplicate_resolution&&item.duplicate_resolution!=='Pending'?<p>Decision: {item.duplicate_resolution}</p>:canDecide?<div className="flex flex-wrap gap-2"><button disabled={busy} onClick={()=>onDecision?.('Merge')} className="intel-button">Merge</button><button disabled={busy} onClick={()=>onDecision?.('Keep Separate')} className="intel-ghost">Keep Separate</button></div>:<p>Awaiting an authorized human reviewer.</p>}
  </section>}
  {sources.length>0&&<section className="intel-card p-5"><h2 className="font-semibold mb-2">Preserved source records</h2>{sources.map(x=><Link key={x.id||x.intelligence_id} to={`/intelligence/${x.id}`} className="block text-sm text-[#126d91] py-2 underline">{x.intelligence_id||'Record'} · {x.title||'Untitled'} · {x.source_url||'No URL'} · Original content and evidence</Link>)}</section>}
 </>;
}
