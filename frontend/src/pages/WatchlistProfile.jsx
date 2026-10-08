import { Link, useParams } from 'react-router-dom';
import { useRegistry } from '@/components/intel/useIntel';
import { Notice } from '@/components/intel/Fields';
import ActorIntelligence from '@/components/intel/ActorIntelligence';
import { useLanguage } from '@/lib/LanguageContext';

export default function WatchlistProfile(){
 const {id}=useParams(),{items,accounts,relationships,loading,error}=useRegistry(),{t,label}=useLanguage();
 if(loading)return <p className="text-sm text-[#77899b]">{t('watchlist_profile_loading')}</p>;
 const item=items.find(x=>x.id===id);
 if(!item)return <Notice error={error||t('watchlist_profile_unavailable')}/>;
 return <div className="space-y-5 max-w-4xl">
  <Link to="/watchlist" className="text-sm text-[#126d91]">← {t('watchlist')}</Link>
  <section className="intel-card p-6 space-y-5">
   <div><p className="text-xs uppercase font-bold text-[#53657b]">{t('watchlist_profile_label')}</p><h1 className="intel-heading mt-2">{item.name}</h1><p className="text-sm text-[#607b8a]">{label(item.type)}</p></div>
   <p className="text-sm">{item.description||t('no_description')}</p>
   <div className="grid sm:grid-cols-2 gap-4 text-sm">
    {[
      [t('province'),item.province],
      [t('regency_city'),item.regency_city],
      [t('related_election'),item.related_election],
      [t('related_entity'),item.related_entity],
      [t('topics'),item.related_topics?.join(', ')],
      [t('monitoring_priority'),label(item.priority)],
      [t('monitoring_status'),label(item.status)],
      [t('notes'),item.notes]
    ].map(([fieldLabel,value])=><div key={fieldLabel}><span className="intel-label">{fieldLabel}</span><p className="whitespace-pre-wrap">{value||'—'}</p></div>)}
   </div>
   <div><span className="intel-label">{t('public_accounts')}</span>{accounts.filter(a=>a.watchlist_id===id).map(a=><a key={a.id} href={a.url} target="_blank" rel="noreferrer" className="block text-sm text-[#126d91] break-all">{a.platform||'Web'} · {a.handle||a.url}</a>)}{!accounts.some(a=>a.watchlist_id===id)&&<p className="text-sm">{t('none_recorded')}</p>}</div>
   <div><span className="intel-label">{t('registry_relationships')}</span>{relationships.filter(r=>r.from_id===id).map(r=><p key={r.id} className="text-sm">{label(r.relationship_type)} · {items.find(w=>w.id===r.to_id)?.name||t('watchlist_entry')}</p>)}{!relationships.some(r=>r.from_id===id)&&<p className="text-sm">{t('none_recorded')}</p>}</div>
   <p className="text-xs text-[#607b8a]">{t('watchlist_disclaimer')}</p>
  </section>
  <ActorIntelligence actorId={id} accounts={accounts}/>
 </div>
}
