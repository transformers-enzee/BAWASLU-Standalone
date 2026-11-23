/** Safe, flexible formatting for assistant prose, tables and evidence-backed bars. */
const safeCitationHref=value=>{
 try{
  const url=new URL(value);
  const host=url.hostname.toLowerCase();
  if(url.protocol!=='https:'||url.username||url.password||!host||host==='localhost'||host.endsWith('.localhost'))return null;
  if(/^(?:127\.|10\.|192\.168\.|169\.254\.|0\.|172\.(?:1[6-9]|2\d|3[01])\.)/.test(host))return null;
  if(host==='[::1]'||host==='::1')return null;
  return url.href;
 }catch{return null;}
};
function rich(text){
 return String(text||'').split(/(\*\*[^*\n]+\*\*|\[[^\]\n]{1,120}\]\(https:\/\/[^\s)]+\)|https:\/\/[^\s<>]+)/g).map((part,i)=>{
  if(part.startsWith('**')&&part.endsWith('**'))return <strong key={i} className="font-semibold text-[#801b24]">{part.slice(2,-2)}</strong>;
  const linked=part.match(/^\[([^\]]+)\]\((https:\/\/[^\s)]+)\)$/);
  if(linked){const href=safeCitationHref(linked[2]);return href?<a key={i} href={href} target="_blank" rel="noopener noreferrer" className="break-all font-medium text-teal-800 underline">{linked[1]}</a>:part;}
  if(part.startsWith('https://')){
   const suffix=part.match(/[.,;!?]+$/)?.[0]||'';
   const raw=part.slice(0,part.length-suffix.length),href=safeCitationHref(raw);
   return href?<span key={i}><a href={href} target="_blank" rel="noopener noreferrer" className="break-all text-teal-800 underline">{raw}</a>{suffix}</span>:part;
  }
  return part;
 });
}
function tableParts(lines){
 if(lines.length<2||!/^\s*\|?\s*:?-{3,}/.test(lines[1].replace(/\|/g,'')))return null;
 const cells=x=>x.trim().replace(/^\||\|$/g,'').split('|').map(s=>s.trim());
 const heads=cells(lines[0]);
 if(heads.length<2||heads.length>8)return null;
 const body=[];
 for(const line of lines.slice(2)){
   if(!line.includes('|'))continue;
   const row=cells(line);
   // Ignore repeat headers and dividers; never shift text between columns.
   if(row.length!==heads.length||row.every(x=>/^:?-{2,}:?$/.test(x)))continue;
   if(row.every((v,i)=>v.toLowerCase()===heads[i].toLowerCase()))continue;
   body.push(row);
 }
 if(!body.length||body.length>100)return null;
 return {heads,body};
}
function BarChart({spec}){
 if(!spec||!Array.isArray(spec.data)||spec.data.length<1||spec.data.length>18)return null;
 const rows=spec.data.filter(x=>x&&typeof x.label==='string'&&x.label.length<=70&&typeof x.value==='number'&&Number.isFinite(x.value)&&x.value>=0);
 if(!rows.length)return null;
 const percent=spec.unit==='%'||spec.unit==='percent';
 if(percent&&rows.some(x=>x.value>100))return null;
 const max=percent?100:Math.max(1,...rows.map(x=>x.value));
 return <figure className="rounded-xl border border-[#ecdedd] p-4">
  {typeof spec.title==='string'&&<figcaption className="mb-3 font-semibold text-[#801b24]">{spec.title}</figcaption>}
  <div className="space-y-3">{rows.map((x,i)=><div key={i} className="grid grid-cols-[minmax(80px,1fr)_minmax(100px,2fr)_auto] items-center gap-3 text-xs"><span className="break-words">{x.label}</span><div className="h-3 overflow-hidden rounded-full bg-[#f1d9d6]"><div className="h-full rounded-full bg-[#a52a2f]" style={{width:(x.value/max*100)+'%'}}/></div><span className="font-semibold tabular-nums">{x.value.toLocaleString()}{percent?"%":""}</span></div>)}</div>
 </figure>;
}
export default function AssistantAnswer({text}){
 // Preserve Markdown table rows across blank lines and repeated headers.
 // A whitespace-only separator is not a new table; it can occur in GPT output.
 const lines=String(text||'').split(/\r?\n/);
 const blocks=[];let pending=[];
 const flush=()=>{if(pending.length){blocks.push(pending.join('\n'));pending=[]}};
 for(let i=0;i<lines.length;i++){
   const line=lines[i];
   if(!line.trim()){
     if(pending.length&&pending.some(v=>v.includes('|'))&&lines.slice(i+1).find(v=>v.trim())?.includes('|'))continue;
     flush();continue;
   }
   if(line.includes('|')&&/^\s*\|?\s*:?-{3,}/.test(line.replace(/\|/g,''))&&pending.length===1&&!pending[0].includes('|')){flush();}
   pending.push(line);
 }
 flush();
 return <div className="space-y-4 text-sm leading-6 text-[#392a2f]" data-i18n-exempt>{blocks.map((block,i)=>{
  const chart=block.match(/^\s*\`\`\`chart\s*\n([\s\S]*?)\n\`\`\`\s*$/i);
  if(chart){try{const spec=JSON.parse(chart[1]);return <BarChart key={i} spec={spec}/>;}catch{return <p key={i}>Chart data unavailable.</p>}}
  const lines=block.split('\n');const tbl=tableParts(lines);
  if(tbl)return <div key={i} className="overflow-x-auto rounded-lg border border-[#ecdedd]"><table className="w-full min-w-[680px] table-fixed text-left text-sm leading-relaxed"><thead className="bg-[#fbf3f1]"><tr>{tbl.heads.map((h,j)=><th key={j} className="break-words px-4 py-3 align-top font-semibold text-[#801b24]">{rich(h)}</th>)}</tr></thead><tbody>{tbl.body.map((r,k)=><tr key={k} className="border-t border-[#ecdedd]">{tbl.heads.map((_,j)=><td key={j} className="break-words whitespace-normal px-4 py-3 align-top">{rich(r[j]||'')}</td>)}</tr>)}</tbody></table></div>;
  return <div key={i} className="space-y-1">{lines.map((line,j)=>{
   // Executive intelligence reports use Markdown headings. Keep semantic
   // heading structure while leaving source citations and tables unchanged.
   const heading=line.match(/^ {0,3}(#{1,4})\s+(.+?)\s*#*\s*$/);
   if(heading){
    const level=heading[1].length;
    const Heading=level===1?'h2':level===2?'h3':'h4';
    const size=level===1?'text-lg':level===2?'text-base':'text-sm';
    return <Heading key={j} className={`mt-2 mb-2 font-semibold leading-snug text-[#801b24] ${size}`}>{rich(heading[2])}</Heading>;
   }
   const bullet=line.match(/^\s*[-*]\s+(.+)$/),number=line.match(/^\s*(\d+[.)])\s+(.+)$/);
   if(bullet)return <div key={j} className="flex gap-2"><span aria-hidden="true">•</span><span>{rich(bullet[1])}</span></div>;
   if(number)return <div key={j} className="flex gap-2"><strong>{number[1]}</strong><span>{rich(number[2])}</span></div>;
   return <p key={j} className="whitespace-pre-wrap">{rich(line)}</p>;
  })}</div>;
 })}</div>;
}
