export default function SourceIdentityProvenance({item,accounts,watchlist}) {
  if(item.source_type!=='MANUAL_LINK')return null;
  const identity=item.source_identity||{},account=accounts.find(a=>a.id===identity.matched_registered_account_id);
  const entity=account&&watchlist.find(w=>w.id===account.watchlist_id);
  return <section className="intel-card p-6 space-y-2">
    <h2 className="text-xs uppercase tracking-wider font-bold text-[#42657a]">SOURCE IDENTITY</h2>
    <p className="text-sm font-semibold">{identity.matched_registered_account_id?'REGISTERED ACCOUNT MATCH':'UNRESOLVED'}</p>
    {item.observed_publisher_handle&&<p className="text-sm">Observed publisher: {item.observed_publisher_handle}</p>}
    {identity.matched_registered_account_id?<><p className="text-sm">{entity?.name||item.owned_channel?.candidate_name||'Registered entity'} · {account?.handle||account?.url||item.owned_channel?.account_handle||'Registered account'}</p><p className="text-xs text-[#617789]">Match basis: {identity.match_basis||'Registered account URL comparison'}</p><p className="text-xs text-[#617789]">{identity.status==='REGISTERED_ACCOUNT_CONFIRMED'?'Strict registered-account checks confirmed source provenance, not post content or its claims.':'Registered URL match observed; registered-account ownership is not confirmed.'}</p></>:<p className="text-xs text-[#617789]">No confirmed registered-account match. This does not imply the account is fake, unofficial or unrelated.</p>}
    {item.entity_relationships?.map((relation,index)=><div key={index} className="border-t pt-3 mt-3 text-sm"><p className="font-semibold">Related entity · {watchlist.find(w=>w.id===relation.entity_id)?.name||'Monitored entity'} · {relation.relationship_type==='OTHER_REQUIRES_REVIEW'?'OTHER / REQUIRES REVIEW':relation.relationship_type}</p><p>Evidence basis: {relation.evidence_basis}</p><p className="text-xs text-[#617789]">{relation.review_status} · {relation.confirmed_by||'—'} · {relation.confirmed_at?new Date(relation.confirmed_at).toLocaleString('en-GB'):'—'}. PUBLISHER does not establish registered-account ownership.</p></div>)}
  </section>;
}