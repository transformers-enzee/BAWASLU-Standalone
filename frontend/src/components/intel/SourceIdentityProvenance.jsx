import { useLanguage } from '@/lib/LanguageContext';

export default function SourceIdentityProvenance({item,accounts,watchlist}) {
  const {t}=useLanguage();
  if(item.source_type!=='MANUAL_LINK')return null;
  const identity=item.source_identity||{},account=accounts.find(a=>a.id===identity.matched_registered_account_id);
  const entity=account&&watchlist.find(w=>w.id===account.watchlist_id);
  return <section className="intel-card p-6 space-y-2">
    <h2 className="text-xs uppercase tracking-wider font-bold text-[#42657a]">{t('source_identity')}</h2>
    <p className="text-sm font-semibold">{identity.matched_registered_account_id?t('registered_account_match'):t('unresolved')}</p>
    {item.observed_publisher_handle&&<p className="text-sm">{t('observed_publisher')}: {item.observed_publisher_handle}</p>}
    {identity.matched_registered_account_id?<><p className="text-sm">{entity?.name||item.owned_channel?.candidate_name||t('registered_entity')} · {account?.handle||account?.url||item.owned_channel?.account_handle||t('registered_account_generic')}</p><p className="text-xs text-[#617789]">{t('match_basis')}: {identity.match_basis||t('registered_account_url_comparison')}</p><p className="text-xs text-[#617789]">{identity.status==='REGISTERED_ACCOUNT_CONFIRMED'?t('strict_match_note'):t('url_match_note')}</p></>:<p className="text-xs text-[#617789]">{t('no_registered_match_note')}</p>}
    {item.entity_relationships?.map((relation,index)=><div key={index} className="border-t pt-3 mt-3 text-sm"><p className="font-semibold">{t('related_entity_label')} · {watchlist.find(w=>w.id===relation.entity_id)?.name||t('monitored_entity')} · {relation.relationship_type==='OTHER_REQUIRES_REVIEW'?t('other_requires_review'):relation.relationship_type}</p><p>{t('evidence_basis')}: {relation.evidence_basis}</p><p className="text-xs text-[#617789]">{relation.review_status} · {relation.confirmed_by||'—'} · {relation.confirmed_at?new Date(relation.confirmed_at).toLocaleString('en-GB'):'—'}. {t('publisher_not_ownership')}</p></div>)}
  </section>;
}
