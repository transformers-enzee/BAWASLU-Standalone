import { allowed, clean } from './access.ts';
export function platformFromUrl(value: string): string {
  let host='';try{host=new URL(value).hostname.toLowerCase().replace(/^www\./,'');}catch{return '';}
  if(host==='instagram.com'||host.endsWith('.instagram.com'))return 'Instagram';
  if(host==='tiktok.com'||host.endsWith('.tiktok.com'))return 'TikTok';
  if(host==='facebook.com'||host.endsWith('.facebook.com'))return 'Facebook';
  if(host==='youtube.com'||host.endsWith('.youtube.com')||host==='youtu.be')return 'YouTube';
  if(host==='x.com'||host.endsWith('.x.com')||host==='twitter.com'||host.endsWith('.twitter.com'))return 'X';
  return '';
}
export async function resolveOwnedChannel(entities: any, profile: any, data: any){
  const candidateId=clean(data.owned_candidate_id,60),accountId=clean(data.owned_account_id,60);
  if(!/^[a-f0-9]{24}$/i.test(candidateId)||!/^[a-f0-9]{24}$/i.test(accountId))return {error:'Select a registered candidate and account'};
  const [candidate,account]=await Promise.all([entities.WatchlistItem.get(candidateId).catch(()=>null),entities.SourceAccount.get(accountId).catch(()=>null)]);
  if(!candidate||candidate.type!=='Candidate'||!allowed(profile,candidate)||!account||account.watchlist_id!==candidate.id)return {error:'Candidate or registered account unavailable in your jurisdiction'};
  let post;try{post=new URL(data.source_url);if(!['http:','https:'].includes(post.protocol))throw Error();}catch{return {error:'Enter a valid individual post URL'};}
  if(post.href.length>2000)return {error:'Post URL is too long'};
  let accountUrl;try{accountUrl=new URL(account.url);}catch{return {error:'Registered account URL is invalid'};}
  const known=platformFromUrl(account.url),postPlatform=platformFromUrl(post.href);
  if(known ? postPlatform!==known : post.hostname.toLowerCase()!==accountUrl.hostname.toLowerCase())return {error:'Post URL must be on the registered account platform'};
  if(post.href.replace(/\/$/,'')===accountUrl.href.replace(/\/$/,''))return {error:'Provide an individual post URL, not the account URL'};
  const path=post.pathname;
  const looksLikePost=known==='Instagram'? /^\/(p|reel|tv)\/[^/]+/i.test(path):known==='TikTok'? /^\/@[^/]+\/video\/[^/]+/i.test(path):known==='YouTube'? /^\/(watch|shorts|live)\b/i.test(path)||post.hostname.toLowerCase()==='youtu.be'&&path.length>1:known==='X'? /^\/[^/]+\/status\/[^/]+/i.test(path):known==='Facebook'? /\/(posts|videos|reel|photos|share)\/|\/(permalink|story|photo)\.php/i.test(path):path.length>1;
  if(!looksLikePost)return {error:'Provide a link to an individual post on the registered platform'};
  if(known==='TikTok'){
    const accountHandle=decodeURIComponent(accountUrl.pathname.split('/')[1]||'').toLowerCase();
    const postHandle=decodeURIComponent(path.split('/')[1]||'').toLowerCase();
    if(accountHandle.startsWith('@')&&accountHandle!==postHandle)return {error:'TikTok post must belong to the selected registered account'};
  }
  if(known==='X'){
    const accountHandle=accountUrl.pathname.split('/')[1]?.toLowerCase();
    const postHandle=path.split('/')[1]?.toLowerCase();
    if(accountHandle&&accountHandle!==postHandle)return {error:'X post must belong to the selected registered account'};
  }
  if(clean(data.original_content,20000).length<80)return {error:'Paste at least 80 characters of original post content for AI triage'};
  return {postUrl:post.href,owned:{candidate_id:candidate.id,candidate_name:candidate.name,account_id:account.id,account_url:account.url,account_handle:clean(account.handle,120),platform:known||clean(account.platform,60)||accountUrl.hostname}};
}