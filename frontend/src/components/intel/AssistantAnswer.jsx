/** Safe, flexible formatting for assistant prose, tables and evidence-backed bars. */
function rich(text){
 return String(text||'').split(/(\*\*[^*\n]+\*\*)/g).map((part,i)=>
   part.startsWith('**')&&part.endsWith('**')?
    <strong key={i} className="font-semibold text-[#801b24]">{part.slice(2,-2)}</strong>:part);
}
function tableParts(lines){
 if(lines.length<2||!/^\s*\|?\s*:?-{3,}/.test(lines[1].replace(/\|/g,'')))return null;
 const cells=x=>x.trim().replace(/^\||\|$/g,'').split('|').map(s=>s.trim());
 const heads=cells(lines[0]),body=lines.slice(2).filter(x=>x.includes('|')).map(cells);
 if(heads.length<2||heads.length>12||body.length>100)return null;
 return {heads,body};
}
function BarChart({spec}){
 if(!spec||!Array.isArray(spec.data)||spec.data.length<1||spec.data.length>18)return null;
 const rows=spec.data.filter(x=>x&&typeof x.label==='string'&&x.label.length<=70&&typeof x.value==='number'&&Number.isFinite(x.value)&&x.value>=0);
 if(!rows.length)return null;
 const max=Math.max(1,...rows.map(x=>x.value));
 return <figure className="rounded-xl border border-[#ecdedd] p-4">
  {typeof spec.title==='string'&&<figcaption className="mb-3 font-semibold text-[#801b24]">{spec.title}</figcaption>}
  <div className="space-y-3">{rows.map((x,i)=><div key={i} className="grid grid-cols-[minmax(80px,1fr)_minmax(100px,2fr)_auto] items-center gap-3 text-xs"><span className="break-words">{x.label}</span><div className="h-3 overflow-hidden rounded-full bg-[#f1d9d6]"><div className="h-full rounded-full bg-[#a52a2f]" style={{width:(x.value/max*100)+'%'}}/></div><span className="font-semibold tabular-nums">{x.value.toLocaleString()}</span></div>)}</div>
 </figure>;
}
export default function AssistantAnswer({text}){
 const blocks=String(text||'').split(/\n\n+/);
 return <div className="space-y-4 text-sm leading-6 text-[#392a2f]" data-i18n-exempt>{blocks.map((block,i)=>{
  const chart=block.match(/^\s*\`\`\`chart\s*\n([\s\S]*?)\n\`\`\`\s*$/i);
  if(chart){try{const spec=JSON.parse(chart[1]);return <BarChart key={i} spec={spec}/>;}catch{return <p key={i}>Chart data unavailable.</p>}}
  const lines=block.split('\n');const tbl=tableParts(lines);
  if(tbl)return <div key={i} className="overflow-x-auto rounded-lg border border-[#ecdedd]"><table className="w-full min-w-[350px] text-left text-sm"><thead className="bg-[#fbf3f1]"><tr>{tbl.heads.map((h,j)=><th key={j} className="px-3 py-2 font-semibold text-[#801b24]">{rich(h)}</th>)}</tr></thead><tbody>{tbl.body.map((r,k)=><tr key={k} className="border-t border-[#ecdedd]">{tbl.heads.map((_,j)=><td key={j} className="px-3 py-2">{rich(r[j]||'')}</td>)}</tr>)}</tbody></table></div>;
  return <div key={i} className="space-y-1">{lines.map((line,j)=>{
   const bullet=line.match(/^\s*[-*]\s+(.+)$/),number=line.match(/^\s*(\d+[.)])\s+(.+)$/);
   if(bullet)return <div key={j} className="flex gap-2"><span aria-hidden="true">•</span><span>{rich(bullet[1])}</span></div>;
   if(number)return <div key={j} className="flex gap-2"><strong>{number[1]}</strong><span>{rich(number[2])}</span></div>;
   return <p key={j} className="whitespace-pre-wrap">{rich(line)}</p>;
  })}</div>;
 })}</div>;
}
