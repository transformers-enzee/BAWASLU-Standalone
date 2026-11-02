(function(){
'use strict';
if(window.BAWASLUUiTranslator)return;
const cache=new Map(),pending=new Map(),queue=[],failed=new Map();
const KEY='bawaslu-ui-id-fallback-v127';
try{for(const [a,b] of JSON.parse(sessionStorage.getItem(KEY)||'[]'))cache.set(a,b)}catch(_){}
let busy=false,timer=0;
const english=/\b(?:the|this|these|and|with|from|for|about|only|recorded|source|post|posts|candidate|mentions|topic|sentiment|watchlist|account|available|registered|active|priority|original|review|saved|evidence|loading|displaying|previous|next|open|close|select|hover|show|province|map|geographic|themes|distribution|violation|summary|results|confidence|public|oversight|allegation|election|supporting|classification|followers|engagements|data|low|high|top|information|verification|reported|possible|activity|timeline|unclassified|inbox|intelligence|refresh|provisional|verified|monitoring|reputation|word cloud|messages|current|number|categorized|matched)\b/i;
function suitable(value,force=false){
 if(typeof value!=='string')return false;
 const x=value.trim();
 return x.length>=3&&x.length<=1000&&!/https?:\/\/|www\.|(?:^|\s)[@#][\w]+|\b[a-f0-9]{20,}\b/i.test(x)&&
 !/^[\d .,:%+\-–—\/]+$/.test(x)&&(force||english.test(x));
}
function remember(source,value){
 if(!value||value===source)return;
 cache.set(source,value);
 while(cache.size>500)cache.delete(cache.keys().next().value);
 try{sessionStorage.setItem(KEY,JSON.stringify([...cache]))}catch(_){}
}
async function api(text){
 const token=localStorage.getItem('bawaslu_access_token')||'';
 const r=await fetch('/api/presentation/translate',{method:'POST',cache:'no-store',
  headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
  body:JSON.stringify({text,language:'id'})});
 if(!r.ok)throw Error('Translation unavailable');
 const v=await r.json();
 if(typeof v.text!=='string'||!v.text.trim())throw Error('Empty translation');
 return v.text.trim();
}
async function runBatch(items){
 if(items.length===1)return [await api(items[0])];
 try{
  const raw=await api(JSON.stringify(items));
  const data=JSON.parse(raw);
  const list=Array.isArray(data)?data:data?.translations||data?.items;
  if(Array.isArray(list)&&list.length===items.length&&list.every(x=>typeof x==='string'))return list;
 }catch(_){}
 return Promise.all(items.map(async x=>{try{return await api(x)}catch(_){return null}}));
}
function finish(source,value){
 if(value)remember(source,value);else failed.set(source,Date.now());
 const callbacks=pending.get(source)||[];
 pending.delete(source);
 for(const cb of callbacks)try{cb(value||null)}catch(_){}
}
async function flush(){
 timer=0;if(busy||!queue.length)return;
 busy=true;const batch=queue.splice(0,12);
 try{const values=await runBatch(batch);batch.forEach((x,i)=>finish(x,values[i]))}
 catch(_){batch.forEach(x=>finish(x,null))}
 finally{busy=false;if(queue.length&&!timer)timer=setTimeout(flush,70)}
}
function request(source,callback,force=false){
 if(!suitable(source,force))return false;
 if(cache.has(source)){callback(cache.get(source));return true}
 if(failed.has(source)&&Date.now()-failed.get(source)<30000){callback(null);return true}
 if(!pending.has(source)){pending.set(source,[]);queue.push(source)}
 pending.get(source).push(callback);
 if(!busy&&!timer)timer=setTimeout(flush,90);
 return true;
}
window.BAWASLUUiTranslator={request,suitable,resetFailures:()=>failed.clear()};
})();