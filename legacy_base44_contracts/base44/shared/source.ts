import { clean } from './access.ts';

const decode = (s='') => s.replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(Number(n))).replace(/&#x([\da-f]+);/gi,(_,n)=>String.fromCodePoint(parseInt(n,16))).replace(/&(?:amp|quot|apos|lt|gt|nbsp);/g,m=>({ '&amp;':'&','&quot;':'"','&apos;':"'",'&lt;':'<','&gt;':'>','&nbsp;':' ' })[m]);
const plain = s => decode(s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ')).trim();
function publicUrl(raw) {
 const url=new URL(raw);
 const host=url.hostname.toLowerCase().replace(/\.$/,'');
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password||!host.includes('.')||host==='localhost'||host.endsWith('.localhost')||host.endsWith('.local')||host.endsWith('.internal')||/^\d+\.\d+\.\d+\.\d+$/.test(host)||host.includes(':')||/^(?:0x|0\d)/i.test(host))throw Error('Public HTTP(S) URL required');
 return url;
}
function meta(html, keys) {
 for(const tag of html.match(/<meta\b[^>]*>/gi)||[]) {
  const name=(tag.match(/\b(?:name|property|itemprop)\s*=\s*["']([^"']+)["']/i)||[])[1]?.toLowerCase();
  if(keys.includes(name))return clean(decode((tag.match(/\bcontent\s*=\s*["']([^"']*)["']/i)||[])[1]||''),20000);
 }
 return '';
}
export async function retrieveSource(raw) {
 let url=publicUrl(raw); let response;
 try {
  for(let i=0;i<4;i++) {
   response=await fetch(url.href,{redirect:'manual',signal:AbortSignal.timeout(9000),headers:{Accept:'text/html,application/xhtml+xml'}});
   if([301,302,303,307,308].includes(response.status)) {const location=response.headers.get('location');if(!location)throw Error('Redirect without destination');url=publicUrl(new URL(location,url).href);continue;}
   break;
  }
  if(!response?.ok||[301,302,303,307,308].includes(response.status)||!/^text\/html|^application\/xhtml\+xml/i.test(response.headers.get('content-type')||''))throw Error('Page unavailable');
  if(Number(response.headers.get('content-length'))>1000000)throw Error('Page too large');
  const reader=response.body?.getReader();if(!reader)throw Error('No page body');
  let bytes=0,chunks=[];while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.length;if(bytes>1000000){await reader.cancel();throw Error('Page too large');}chunks.push(value);}
  const data=new Uint8Array(bytes);let pos=0;for(const chunk of chunks){data.set(chunk,pos);pos+=chunk.length;}
  const html=new TextDecoder().decode(data);
  const title=meta(html,['og:title','twitter:title'])||plain((html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)||[])[1]||'');
  const author=meta(html,['author','article:author','parsely-author']);
  const date=meta(html,['article:published_time','datepublished','publishdate','date','pubdate']);
   const dateMatch=date.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2})(?:[:.\dZ+\-]*)?)?$/);
   const publicationDate=dateMatch?.[1]||'',publicationTime=dateMatch?.[2]||'';
   const publicationPrecision=publicationDate?(publicationTime?'EXACT':'TIME_UNKNOWN'):'UNKNOWN';
  const language=(html.match(/<html\b[^>]*\blang\s*=\s*["']([^"']+)/i)||[])[1]||meta(html,['content-language']);
  const cleaned=html.replace(/<(script|style|nav|footer|header|aside|form)\b[^>]*>[\s\S]*?<\/\1>/gi,' ');
  const main=(cleaned.match(/<article\b[^>]*>([\s\S]*?)<\/article>/i)||cleaned.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i)||[])[1]||cleaned;
  const paragraphs=[...main.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map(m=>plain(m[1])).filter(t=>t.length>=35);
  const content=clean(paragraphs.join('\n\n'),16000);
  return {available:!!content,title:clean(title,240),source_name:url.hostname.replace(/^www\./,''),author:clean(author,180),publication_datetime:publicationTime?date:'',publication_date:publicationDate,publication_time:publicationTime,publication_time_precision:publicationPrecision,original_language:clean(language,80),original_content:content};
 } catch {return {available:false,title:'',source_name:url.hostname.replace(/^www\./,''),author:'',publication_datetime:'',publication_date:'',publication_time:'',publication_time_precision:'UNKNOWN',original_language:'',original_content:''};}
}