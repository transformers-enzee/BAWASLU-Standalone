import { Link } from 'react-router-dom';
import { useLanguage } from '@/lib/LanguageContext';

const asList=value=>Array.isArray(value)?value:[];
const listLabel=value=>Array.isArray(value)?value.join(', '):(typeof value==='string'&&value.trim()?value:'—');

export default function DuplicatePanel({item,comparison,related=[],match=null,busy,onDecision,canDecide=false}){
 const {t}=useLanguage();
 const safeRelated=asList(related);
 const sources=safeRelated.filter(x=>x&&item&&(x.merged_into===item.id||item.merged_into===x.id));
 const basis=asList(match?.basis);
 const score=Number(match?.score);
 const scoreLabel=Number.isFinite(score)?Math.round(score*100):null;
 if(!item)return null;
 return <>
  {item.duplicate_of&&<section className="intel-card border-[#ebd6a8] bg-[#fffaf0] p-5 space-y-3 text-sm">
   <h2 className="font-semibold">{t('potential_duplicate')}</h2>
   <p>{t('duplicate_explain')}</p>
   {match&&<div className="rounded-lg border border-[#ead7a7] bg-white/70 p-3">
    <p className="font-semibold">{t('similarity')}: {scoreLabel===null?t('available_for_review'):scoreLabel+'%'}</p>
    {basis.length>0&&<p className="text-xs text-[#65798a] mt-1">{t('why_flagged')}: {basis.join(' · ')}</p>}
   </div>}
   <details>
    <summary className="cursor-pointer text-[#126d91] font-semibold">{t('view_comparison')}</summary>
    <div className="grid md:grid-cols-2 gap-4 mt-3">{[item,comparison].filter(Boolean).map(x=><div key={x.id||x.intelligence_id} className="border rounded-lg p-3 space-y-2 break-words">
     <Link className="text-[#126d91] underline" to={'/intelligence/'+x.id}>{x.intelligence_id||t('record')} · {x.title||t('untitled')}</Link>
     <p>{t('source_label')}: {x.source_name||x.author||t('not_recorded')}</p>
     <p>{t('url')}: {x.source_url||t('not_recorded')}</p>
     <p>{t('published')}: {x.publication_datetime||x.publication_date||t('not_recorded')}</p>
     <p>{t('entity')}: {listLabel(x.related_entities)}</p>
     <p>{t('topics')}: {listLabel(x.related_topics)}</p>
     <p className="whitespace-pre-wrap">{t('original_text')}: {x.original_content||t('no_text_entered')}</p>
    </div>)}</div>
   </details>
   {item.duplicate_resolution&&item.duplicate_resolution!=='Pending'?<p>{t('decision_label')}: {item.duplicate_resolution}</p>:canDecide?<div className="flex flex-wrap gap-2"><button disabled={busy} onClick={()=>onDecision?.('Merge')} className="intel-button">{t('merge')}</button><button disabled={busy} onClick={()=>onDecision?.('Keep Separate')} className="intel-ghost">{t('keep_separate')}</button></div>:<p>{t('awaiting_authorized_reviewer')}</p>}
  </section>}
  {sources.length>0&&<section className="intel-card p-5"><h2 className="font-semibold mb-2">{t('preserved_source_records')}</h2>{sources.map(x=><Link key={x.id||x.intelligence_id} to={'/intelligence/'+x.id} className="block text-sm text-[#126d91] py-2 underline">{x.intelligence_id||t('record')} · {x.title||t('untitled')} · {x.source_url||t('no_url')} · {t('original_content_evidence')}</Link>)}</section>}
 </>;
}
