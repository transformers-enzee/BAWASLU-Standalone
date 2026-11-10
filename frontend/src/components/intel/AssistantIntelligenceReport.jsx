import { ClipboardCheck, FileSearch } from 'lucide-react';
import AssistantAnswer from './AssistantAnswer';
import {textFor,friendlySource,assistantLocale} from '@/lib/assistantResponseLocale';
const safeUrl=value=>{try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)?u.href:null}catch{return null}};
function Links({text,records}){
 const ids=[...new Set(String(text||'').match(/\[(?:SOCIAL|INT)-[A-Za-z0-9:_-]+\]/g)||[])].slice(0,4);
 if(!ids.length)return null;
 return <div className="mt-3 flex flex-wrap gap-2">{ids.map(token=>{const id=token.slice(1,-1),r=(records||[]).find(x=>x.intelligence_id===id||x.id===id);const link=safeUrl(r?.source_url);return link?<a key={id} href={link} target="_blank" rel="noopener noreferrer" className="text-[11px] px-2 py-1 rounded bg-[#eaf2f6] text-[#14637e] hover:underline">{id} ↗</a>:<span key={id} className="text-[11px] px-2 py-1 rounded bg-[#eaf2f6] text-[#14637e]">{id}</span>})}</div>;
}
// Each cited source already has a clickable chip below its finding.
// Hide duplicate inline citation tokens without changing the underlying citations.
const withoutInlineSourceTokens=value=>String(value||'').replace(/\s*\[(?:SOCIAL|INT)-[A-Za-z0-9:_-]+\]/g,'').trim();
export default function AssistantIntelligenceReport({findings,records,language='id',labels={},compact=false}){
 const t=key=>textFor(language,labels,key);
 const observations=(findings?.observations||[]).filter(x=>typeof x==='string'&&x.trim()).slice(0,compact?3:6);
 const steps=(findings?.review_steps||[]).filter(x=>typeof x==='string'&&x.trim()).slice(0,compact?2:5);
 if(!observations.length&&!steps.length)return null;
 const StepsContainer=compact?'details':'div';
 return <section aria-label={t("findings_heading")} className="mt-5 space-y-5" data-i18n-exempt lang={assistantLocale(language)}>
  {!!observations.length&&<div><div className="flex items-center gap-2 mb-3"><FileSearch size={18} className="text-[#801b24]"/><h3 className="text-lg font-bold text-[#801b24]">{t('findings_heading')}</h3></div><div className="grid grid-cols-1 gap-3">{observations.map((item,i)=><article className="min-w-0 rounded-xl border border-[#e5eaf0] bg-white p-4" key={i}><div className="flex justify-between"><span className="text-xs font-bold tracking-wide text-[#801b24]">{t('finding_label').toUpperCase()} {i+1}</span><span className="text-xs text-[#64748b]">{t('needs_review')}</span></div><div className="mt-3 text-sm leading-relaxed"><AssistantAnswer text={friendlySource(withoutInlineSourceTokens(item),language,labels)}/></div><Links text={item} records={records}/></article>)}</div></div>}
  {!!steps.length&&<StepsContainer className={compact?'rounded-xl border border-[#e5eaf0] bg-white p-4':''} data-optional-social-verification={compact?'true':undefined}>
    {compact?<summary className="cursor-pointer whitespace-normal break-words text-sm font-semibold text-[#801b24]">{language==='id'?'Langkah verifikasi (opsional)':'Verification steps (optional)'}</summary>:
    <div className="flex items-center gap-2 mb-3"><ClipboardCheck size={18} className="text-[#801b24]"/><h3 className="text-lg font-bold text-[#801b24]">{t('verification_heading')}</h3></div>}
    <div className={compact?'mt-4 space-y-2':'space-y-2'}>{steps.map((item,i)=><article key={i} className="rounded-xl border border-[#e5eaf0] bg-white p-4 flex gap-3"><div className="shrink-0 w-8 h-8 grid place-items-center rounded-lg bg-[#f2e7e8] text-[#801b24] font-bold">{i+1}</div><div className="min-w-0 flex-1"><AssistantAnswer text={friendlySource(withoutInlineSourceTokens(item),language,labels)}/><Links text={item} records={records}/></div></article>)}</div></StepsContainer>}
  <p className="text-xs text-[#64748b]">{t('review_notice')}</p>
 </section>;
}
