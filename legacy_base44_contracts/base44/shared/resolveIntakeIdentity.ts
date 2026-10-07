import { allowed, clean } from './access.ts';
import { platformFromUrl, resolveOwnedChannel } from './ownedChannel.ts';

export function observedPublisherFromUrl(value) {
  try {
    const url=new URL(value);
    const platform=platformFromUrl(url.href);
    const segments=url.pathname.split('/').filter(Boolean).map(s=>decodeURIComponent(s));
    // A photo-post URL can identify an observed account, not a verified person or owned channel.
    const photoPost=platform==='TikTok'&&['http:','https:'].includes(url.protocol)&&!url.username&&!url.password&&/^\/(@[A-Za-z0-9._]{1,24})\/photo\/\d+\/?$/.test(url.pathname);
    if(platform==='TikTok'&&(/^@[^/]+$/.test(segments[0]||'')&&segments[1]==='video'&&segments[2]||photoPost))return {platform,handle:clean(segments[0],120)};
    if(platform==='X'&&segments[0]&&segments[1]?.toLowerCase()==='status'&&segments[2])return {platform,handle:clean(segments[0],120)};
    return {platform,handle:''};
  } catch {return {platform:'',handle:''};}
}

export async function resolveIntakeIdentity(entities,profile,data) {
  const observed=observedPublisherFromUrl(data.source_url);
  const unresolved={status:'UNRESOLVED',verification_status:'NOT_VERIFIED'};
  if(!observed.handle)return {identity:unresolved,observed_publisher_handle:'',platform:observed.platform};
  const [watchlist,accounts]=await Promise.all([
    entities.WatchlistItem.list('-created_date',500),entities.SourceAccount.list('-created_date',500)
  ]);
  const visible=new Map(watchlist.filter(w=>allowed(profile,w)).map(w=>[w.id,w]));
  const norm=s=>String(s||'').replace(/^@/,'').toLowerCase();
  const candidates=accounts.filter(a=>visible.has(a.watchlist_id)&&platformFromUrl(a.url)===observed.platform&&norm(observedPublisherFromAccount(a.url,observed.platform))===norm(observed.handle));
  if(candidates.length!==1)return {identity:unresolved,observed_publisher_handle:observed.handle,platform:observed.platform};
  const account=candidates[0],entity=visible.get(account.watchlist_id);
  let identity=unresolved,owned=null;
  const basis=`Exact ${observed.platform} handle in individual post URL matches the registered account URL`;
  identity={...unresolved,matched_registered_account_id:account.id,match_basis:basis};
  if(entity.type==='Candidate') {
    const strict=await resolveOwnedChannel(entities,profile,{...data,owned_candidate_id:entity.id,owned_account_id:account.id});
    if(!strict.error){owned=strict.owned;identity={status:'REGISTERED_ACCOUNT_CONFIRMED',matched_registered_account_id:account.id,match_basis:basis+'; strict registered-channel checks passed',verification_status:'CONFIRMED',verified_by:'BAWASLU registered-account resolver',verified_at:new Date().toISOString()};}
  }
  return {identity,owned,observed_publisher_handle:observed.handle,platform:observed.platform,matched_entity:{id:entity.id,name:entity.name,type:entity.type},matched_account:{id:account.id,url:account.url,handle:account.handle},match_basis:basis};
}

function observedPublisherFromAccount(value,platform) {
  try {
    const url=new URL(value);
    const segment=decodeURIComponent(url.pathname.split('/').filter(Boolean)[0]||'');
    if(platform==='TikTok')return segment.startsWith('@')?segment:'';
    if(platform==='X')return segment;
  } catch { /* no match */ }
  return '';
}