import { clean } from './access.ts';

const methodFor = type => type==='MANUAL_ENTRY'?'MANUAL_ENTRY':type==='FILE_UPLOAD'?'FILE_UPLOAD':type==='MANUAL_LINK'||type==='REGISTERED_OWNED_CHANNEL'?'MANUAL_URL':null;

function observedTikTokHandle(url) {
  try {
    const parsed=new URL(url);
    const host=parsed.hostname.toLowerCase().replace(/^www\./,'');
    if(host!=='tiktok.com'&&!host.endsWith('.tiktok.com'))return '';
    const video=/^\/(\@[^/]+)\/video\/[^/]+/i.exec(parsed.pathname)?.[1];
    const photo=['http:','https:'].includes(parsed.protocol)&&!parsed.username&&!parsed.password
      ? /^\/(\@[A-Za-z0-9._]{1,24})\/photo\/\d+\/?$/.exec(parsed.pathname)?.[1] : '';
    return clean(video||photo,120);
  } catch { return ''; }
}

export function sourceMetadataForCreate(type,data,owned,resolution) {
  const observed_publisher_handle=resolution?.observed_publisher_handle||observedTikTokHandle(data.source_url)||clean(data.observed_publisher_handle,120);
  const source_identity=resolution?.identity||(owned?{
    status:'REGISTERED_ACCOUNT_CONFIRMED',matched_registered_account_id:owned.account_id,
    match_basis:'Registered candidate/account and individual post URL validated by the strict owned-channel resolver',
    verification_status:'CONFIRMED',verified_by:'BAWASLU registered-account resolver',verified_at:new Date().toISOString()
  }:{status:'UNRESOLVED',verification_status:'NOT_VERIFIED'});
  return {ingestion_method:methodFor(type),...(observed_publisher_handle?{observed_publisher_handle}:{}),source_identity};
}

export function sourceReadView(item) {
  const legacyConfirmed=item.source_type==='REGISTERED_OWNED_CHANNEL'&&!!item.owned_channel?.account_id;
  return {...item,
    ingestion_method:item.ingestion_method||methodFor(item.source_type),
    observed_publisher_handle:item.observed_publisher_handle||observedTikTokHandle(item.source_url),
    source_identity:item.source_identity||(legacyConfirmed?{
      status:'REGISTERED_ACCOUNT_CONFIRMED',matched_registered_account_id:item.owned_channel.account_id,
      match_basis:'Legacy registered-owned-channel provenance',verification_status:'CONFIRMED'
    }:{status:'UNRESOLVED',verification_status:'NOT_VERIFIED'}),
    entity_relationships:item.entity_relationships||[]
  };
}