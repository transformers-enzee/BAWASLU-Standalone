import {Tag,MapPin,Scale,Landmark,Vote} from 'lucide-react';
import {assistantLocale,localeTagKey,textFor} from '@/lib/assistantResponseLocale';
const ICONS={CANDIDATE:Tag,PROVINCE:MapPin,SUSPECTED_VIOLATION:Scale,BAWASLU_ISSUE:Landmark,ELECTORAL_ISSUE:Vote};
const COLORS={CANDIDATE:'bg-indigo-50 text-indigo-800 border-indigo-100',PROVINCE:'bg-blue-50 text-blue-800 border-blue-100',SUSPECTED_VIOLATION:'bg-amber-50 text-amber-900 border-amber-200',BAWASLU_ISSUE:'bg-rose-50 text-rose-800 border-rose-100',ELECTORAL_ISSUE:'bg-teal-50 text-teal-800 border-teal-100'};
export default function AssistantDetectedTags({tags=[],language='id',labels={}}){
 const translate=key=>textFor(language,labels,key);
 if(!Array.isArray(tags)||!tags.length)return null;
 const counts={};for(const tag of tags)counts[tag.type]=(counts[tag.type]||0)+1;
 const safe=(tags||[]).filter(x=>x&&ICONS[x.type]&&x.label&&Array.isArray(x.source_ids)).slice(0,18);
 if(!safe.length)return null;
 return <section className="mb-5 rounded-xl border border-[#e5eaf0] bg-white p-4" data-i18n-exempt lang={assistantLocale(language)} aria-label={translate('tags_heading')}>
  <div className="flex flex-wrap justify-between items-center gap-2"><h3 className="text-lg font-bold text-[#801b24]">{translate('tags_heading')}</h3><span className="text-xs text-[#64748b]">{safe.length}</span></div>
  <p className="text-xs leading-relaxed text-[#64748b] mt-1">{translate('tags_notice')}</p>
  <div className="mt-3 grid gap-2 md:grid-cols-2">{safe.map((tag,i)=>{const Icon=ICONS[tag.type];return <article key={tag.type+'-'+tag.label+'-'+i} className={'rounded-lg border p-3 '+COLORS[tag.type]}>
    <div className="flex gap-2 items-start"><Icon size={16} className="mt-0.5 shrink-0"/><div className="min-w-0"><p className="text-[11px] uppercase tracking-wide font-semibold">{translate(localeTagKey[tag.type])}</p><p className="font-semibold text-sm mt-1 break-words">{tag.type==='SUSPECTED_VIOLATION'&&/^(requires review|screening needed)$/i.test(tag.label)?translate('suspected_only'):tag.label}</p></div></div>
    {tag.type==='PROVINCE'&&<p className="text-[11px] mt-2">{translate('province_mention')}</p>}
    {tag.type==='SUSPECTED_VIOLATION'&&<p className="text-[11px] mt-2">{translate('suspected_only')}</p>}
    {tag.explanation&&<p className="text-xs leading-relaxed mt-2">{tag.explanation}</p>}
    {!!tag.source_ids.length&&<p className="text-[11px] mt-2 opacity-75">{tag.source_ids.join(' · ')}</p>}
   </article>})}</div>
 </section>;
}
