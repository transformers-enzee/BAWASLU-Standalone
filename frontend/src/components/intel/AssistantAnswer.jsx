const headings=['ANSWER / INTELLIGENCE SUMMARY','KEY OBSERVATIONS','EVIDENCE STATUS','LIMITATION'];
export default function AssistantAnswer({text}){
  const sections=String(text||'').split(/\n\n+/);
  return <div className="space-y-4">{sections.map((section,i)=>{
    const [first,...rest]=section.split('\n');
    const titled=headings.includes(first);
    return <section key={i} className={i?'border-t border-[#e4e9ef] pt-3':''}>
      {titled&&<h2 className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-[#53657b]">{first}</h2>}
      <p className="whitespace-pre-line leading-6 text-[#29445d]">{titled?rest.join('\n'):section}</p>
    </section>;
  })}</div>;
}