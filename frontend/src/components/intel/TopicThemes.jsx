import {useState} from 'react';
import {ExternalLink,X} from 'lucide-react';
const COLORS=['#137e70','#4d9caf','#e2ad56','#8d7cba','#db7d77','#7f9f62','#b07d9d','#7b939c'];
const SENTIMENT={Negative:'#d95a60',Neutral:'#e4ad41',Positive:'#20a074',Unclassified:'#dbe3e9'};
const safeUrl=s=>/^https:\/\//i.test(s||'')?s:null;
export default function TopicThemes({data}){
 const [selected,setSelected]=useState(null);
 const rows=(data?.categories||[]).filter(r=>Number(r.count)>0);
 const total=Number(data?.total_mentions||0),categorized=Number(data?.categorized_mentions||0);
 let offset=0;
 const gradient=rows.map((r,i)=>{
  const from=offset;offset+=total?100*Number(r.count)/total:0;
  return (r.name==='Not categorized'?'#d3dde2':COLORS[i%COLORS.length])+' '+from+'% '+offset+'%';
 }).join(',');
 const active=rows.find(r=>r.name===selected);
 return <section aria-label="Topics and Themes" className="lg:col-span-2 rounded-[13px] border border-[#dce5ed] bg-white p-5">
  <div className="flex flex-wrap items-start justify-between gap-3"><div><h4 className="text-lg font-semibold text-[#19324a]">Topics &amp; Themes</h4><p className="text-xs text-[#60768c]">How saved posts are categorized by their assessed subject, not by monitoring keywords.</p></div><span className="rounded-lg bg-[#edf2f4] px-3 py-2 text-xs font-semibold text-[#36536a]">{total.toLocaleString()} mentions</span></div>
  {rows.length?<div className="mt-5 grid grid-cols-1 items-center gap-5 md:grid-cols-[minmax(170px,240px)_1fr]">
   <div className="mx-auto grid h-[215px] w-[215px] place-items-center rounded-full border border-[#dce7e8]" style={{background:'conic-gradient('+gradient+')'}} role="img" aria-label={rows.map(r=>r.name+': '+r.count+' posts').join(', ')}>
    <div className="h-[94px] w-[94px] rounded-full bg-white"/>
   </div>
   <div className="space-y-2">{rows.map((row,i)=>{
    const count=Number(row.count),mix=row.sentiment||{};
    return <button key={row.name} type="button" onClick={()=>setSelected(row.name)} aria-label={'See '+row.name+' posts'} className="block w-full rounded-lg border border-[#e3ebed] bg-white px-4 py-3 text-left transition-colors hover:border-[#74b8a8] hover:bg-[#f6fbfa]">
     <div className="flex items-center gap-3 text-sm"><span className="h-3 w-3 shrink-0 rounded-full" style={{background:row.name==='Not categorized'?'#d3dde2':COLORS[i%COLORS.length]}}/><strong className="min-w-0 flex-1 text-[#19324a]">{row.name}</strong><strong className="text-[#19324a] tabular-nums">{count.toLocaleString()} ({total?Math.round(100*count/total):0}%)</strong></div>
     <div className="mt-3 ml-6 flex h-3 max-w-[310px] overflow-hidden rounded-full bg-[#edf2f4]" role="img" aria-label={'Sentiment of '+row.name+': '+Object.entries(mix).map(([k,v])=>k+' '+v).join(', ')}>
      {['Negative','Neutral','Positive','Unclassified'].map(k=>Number(mix[k]||0)>0?<span key={k} title={k+': '+mix[k]} style={{width:(100*Number(mix[k])/count)+'%',background:SENTIMENT[k]}}/>:null)}
     </div>
    </button>;
   })}</div>
  </div>:<p className="mt-5 rounded-lg bg-[#f6f8fa] p-6 text-center text-sm text-[#60768c]">No saved posts match this selection.</p>}
  <p className="mt-4 text-xs text-[#60768c]">{categorized.toLocaleString()} of {total.toLocaleString()} posts have saved subject categories; {Number(data?.uncategorized_mentions||0).toLocaleString()} not categorized. Click a theme to inspect up to 8 source posts. Sentiment: red negative, amber neutral, green positive, grey unclassified.</p>
  {active&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null)}}>
   <div className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-xl" role="dialog" aria-modal="true" aria-label={'Source posts for '+active.name}>
    <div className="flex justify-between gap-3 border-b p-4"><div><h4 className="font-semibold text-[#19324a]">{active.name}</h4><p className="text-xs text-[#60768c]">{active.count} matching posts; showing up to 8 saved examples.</p></div><button type="button" aria-label="Close topic posts" onClick={()=>setSelected(null)} className="h-9 rounded-lg border p-2"><X size={17}/></button></div>
    <div className="overflow-y-auto p-4">{(active.sample_posts||[]).map(post=><article key={post.id} className="space-y-2 border-b py-3 last:border-0"><div className="flex justify-between gap-2 text-xs"><strong className="text-[#19324a]">{post.author||'Unknown author'}</strong><span className="text-[#60768c]">{post.platform} · {String(post.date||'').slice(0,10)}</span></div><p className="whitespace-pre-wrap break-words text-sm text-[#33475b]">{post.text||'No source text'}</p>{safeUrl(post.url)&&<a className="inline-flex items-center gap-1 text-xs font-semibold text-[#117c6c] hover:underline" href={post.url} target="_blank" rel="noopener noreferrer">Open original source <ExternalLink size={13}/></a>}</article>)}</div>
   </div>
  </div>}
 </section>;
}
