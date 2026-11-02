/** Render assistant-authored emphasis and context-dependent lists safely.
 * No raw HTML or untrusted Markdown HTML is interpreted. */
const headings=['RINGKASAN INTELIJEN','OBSERVASI KUNCI','STATUS BUKTI','DASAR WAKTU','KETERBATASAN','ANSWER / INTELLIGENCE SUMMARY','KEY OBSERVATIONS','EVIDENCE STATUS','LIMITATION','TEMUAN UTAMA','POIN PENTING','INTERPRETASI / KONTEKS','KONTEKS','LANGKAH TINDAK LANJUT','BATASAN DATA'];
function inline(text){
 return String(text||'').split(/(\*\*[^*\n]+\*\*)/g).map((part,i)=>part.startsWith('**')&&part.endsWith('**')?
  <strong key={i} className="font-bold text-[#17324a]">{part.slice(2,-2)}</strong>:part);
}
export default function AssistantAnswer({text}){
 const sections=String(text||'').split(/\n\n+/);
 return <div className="space-y-4" data-i18n-exempt>{sections.map((section,i)=>{
  const lines=section.split('\n'),titled=headings.includes(lines[0]);
  const content=titled?lines.slice(1):lines;
  const isBullet=line=>/^\s*[-*] \S/.test(line),isNumber=line=>/^\s*\d+[.)] \S/.test(line);
  return <section key={i} className={i?'border-t border-[#e4e9ef] pt-3':''}>
   {titled&&<h2 className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-[#53657b]">{lines[0]}</h2>}
   <div className="space-y-1 text-[#29445d] leading-6">{content.map((line,j)=>
    isBullet(line)?<div key={j} className="flex gap-2 pl-1"><span aria-hidden="true">•</span><span>{inline(line.replace(/^\s*[-*] /,''))}</span></div>:
    isNumber(line)?<div key={j} className="flex gap-2 pl-1"><span className="font-semibold">{line.match(/^\s*\d+[.)]/)[0].trim()}</span><span>{inline(line.replace(/^\s*\d+[.)] /,''))}</span></div>:
    <p key={j} className="whitespace-pre-wrap">{inline(line)}</p>)}</div>
  </section>;
 })}</div>;
}
