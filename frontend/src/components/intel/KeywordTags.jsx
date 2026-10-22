import { useState } from 'react';

export default function KeywordTags({label,items,onChange,required=false,placeholder='Type a keyword and press Enter'}){
 const [draft,setDraft]=useState('');
 const tags=Array.isArray(items)?items:[];
 function add(){
  const candidate=draft.trim();
  if(!candidate)return;
  if(candidate.length>120)return;
  if(tags.length>=30)return;
  if(!tags.some(x=>x.toLocaleLowerCase()===candidate.toLocaleLowerCase()))onChange([...tags,candidate]);
  setDraft('');
 }
 function remove(i){onChange(tags.filter((_,index)=>index!==i))}
 return <div className="text-sm">
  <label htmlFor={'tags-'+label.replace(/[^a-z]/gi,'-')} className="font-medium">{label}{required?' *':''}</label>
  <div className="mt-1 rounded-lg border border-slate-300 p-2 min-h-12 focus-within:ring-2 focus-within:ring-cyan-500">
   <div className="flex flex-wrap items-center gap-2">
    {tags.map((tag,i)=><span key={i} className="inline-flex max-w-full items-center gap-2 rounded-full bg-cyan-50 text-cyan-900 px-3 py-1 text-xs border border-cyan-200">
      <span className="break-all">{tag}</span>
      <button type="button" aria-label={'Remove '+tag+' from '+label} className="font-semibold" onClick={()=>remove(i)}>×</button>
    </span>)}
    <input id={'tags-'+label.replace(/[^a-z]/gi,'-')} className="min-w-32 flex-1 bg-transparent p-1 outline-none" aria-label={label} value={draft}
     maxLength={120} placeholder={tags.length?'Add another keyword':placeholder}
     onChange={e=>setDraft(e.target.value)}
     onKeyDown={e=>{if(e.key==='Enter'||e.key===','){e.preventDefault();add()}else if(e.key==='Backspace'&&!draft&&tags.length)remove(tags.length-1)}}/>
    <button type="button" className="intel-ghost" onClick={add} disabled={!draft.trim()||tags.length>=30}>Add</button>
   </div>
  </div>
  <p className="text-xs text-slate-500 mt-1">{tags.length}/30 keywords · Press Enter or Add · Click × to remove</p>
 </div>
}
