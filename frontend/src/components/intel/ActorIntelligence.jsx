import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { intel } from './useIntel';
import { activityLabel, narrativeLabel, locationLabel, actorLabels, relationshipLabels } from './actorPictureView';
import { useLanguage } from '@/lib/LanguageContext';

export default function ActorIntelligence({actorId,accounts}){
  const {t}=useLanguage();
  const [records,setRecords]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
  useEffect(()=>{let active=true;setLoading(true);intel('actorPicture',{actor_id:actorId}).then(r=>{if(active)setRecords(r.records||[])}).catch(e=>{if(active)setError(e.response?.data?.error||e.message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[actorId]);
  const channels=[...new Set(records.filter(r=>r.source_identity?.status!=='REGISTERED_ACCOUNT_CONFIRMED'&&!r.owned_channel?.account_id).map(r=>r.observed_publisher_handle||r.author).filter(Boolean))];
  const summaries=[
    [t('activities'),[...new Set(records.map(r=>activityLabel(r.intelligence_extraction)).filter(Boolean))]],
    [t('locations'),[...new Set(records.map(r=>locationLabel(r.intelligence_extraction,r)).filter(Boolean))]],
    [t('narratives'),[...new Set(records.map(r=>narrativeLabel(r.intelligence_extraction)).filter(Boolean))]],
    [t('associated_entities'),[...new Set(records.flatMap(r=>[...(r.related_entities||[]),...actorLabels(r.intelligence_extraction)]).filter(Boolean))]],
    [t('extracted_relationships'),[...new Set(records.flatMap(r=>relationshipLabels(r.intelligence_extraction)))]],
    [t('supervision_signals'),[...new Set(records.map(r=>r.supervision_screening?.supervision_signal).filter(Boolean))]]
  ];
  return <section className="intel-card p-6 space-y-4">
    <div><h2 className="font-semibold text-lg">{t('actor_picture')}</h2><p className="text-xs text-[#617789]">{t('actor_picture_note')}</p></div>
    {loading?<p className="text-sm">{t('loading_timeline')}</p>:error?<p role="alert" className="text-sm text-red-700">{error}</p>:<>
      <div><span className="intel-label">{t('registered_owned_channels')}</span>{accounts.filter(a=>a.watchlist_id===actorId).map(a=><p key={a.id} className="text-sm">{a.handle||a.url} · {t('registered_account')}</p>)}{!accounts.some(a=>a.watchlist_id===actorId)&&<p className="text-sm">{t('none_recorded')}</p>}</div>
      <div><span className="intel-label">{t('related_observed_publishers')}</span>{channels.map(h=><p key={h} className="text-sm">{h} · {t('related_observed_account')}</p>)}{!channels.length&&<p className="text-sm">{t('none_recorded')}</p>}</div>
      <div className="grid sm:grid-cols-2 gap-3 text-sm">{summaries.map(([heading,values])=><div key={heading}><span className="intel-label">{heading}</span><p>{values.join(' · ')||t('not_yet_recorded')}</p></div>)}</div>
      <div>
        <span className="intel-label">{t('timeline')} · {records.length} {t('related_records')} · {records.filter(r=>r.entity_relationships?.some(e=>e.relationship_type==='FEATURES')).length} {t('featured_appearances')}</span>
        {records.map(r=><Link to={'/intelligence/'+r.id} key={r.id} className="block border-t py-3 text-sm space-y-1">
          <p className="font-semibold text-[#126d91]">{r.intelligence_id} · {r.title}</p>
          <p>{r.publication_date||r.publication_datetime||r.collection_datetime?.slice(0,10)||t('date_unknown')} · {r.entity_relationships?.map(x=>x.relationship_type).join(', ')||t('registered_source_human_link')} · {r.priority||'—'} · {r.review_status||'—'}</p>
          <p>{t('activity')}: {activityLabel(r.intelligence_extraction)||t('not_human_approved')} · {t('location')}: {locationLabel(r.intelligence_extraction,r)||t('not_recorded')}</p>
          <p>{t('narrative')}: {narrativeLabel(r.intelligence_extraction)||t('not_human_approved')} · {t('signal')}: {r.supervision_screening?.supervision_signal||t('not_determined')}</p>
        </Link>)}
        {!records.length&&<p className="text-sm">{t('no_related_public_intelligence')}</p>}
      </div>
    </>}
  </section>;
}
