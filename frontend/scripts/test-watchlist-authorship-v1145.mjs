import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// End-to-end UI attribution is exercised with 16 mock third-party posts.
// No provider calls, no credentials, no Supabase writes.
const html=fs.readFileSync(new URL('../public/ui-freeze/watchlist-v2_2.html',import.meta.url),'utf8');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
const adapter=fs.readFileSync(new URL('../public/ui-freeze/watchlist-live.js',import.meta.url),'utf8');
assert.ok(inline);
const nodes=new Map(),listeners=new Map(),requests=[];
function el(key){
  if(!nodes.has(key))nodes.set(key,{id:key,innerHTML:'',textContent:'',value:'',style:{},dataset:{},
    classList:{add(){},remove(){},contains(){return false}},
    focus(){},setSelectionRange(){},setAttribute(){},addEventListener(){},
    insertAdjacentHTML(_where,markup){this.innerHTML+=markup}});
  return nodes.get(key);
}
const document={querySelector:el,querySelectorAll(){return []},
  documentElement:{classList:{add(){}}},
  addEventListener(kind,fn){const a=listeners.get(kind)||[];a.push(fn);listeners.set(kind,a)}};
const records=Array.from({length:16},(_,i)=>({
  id:String(593+i),platform:'tiktok',author_name:i===0?'ntvnews.id':'reporter_'+i,
  published_at:'2026-10-30T13:10:55Z',
  text:'Coverage about Gibran Rakabuming Raka',
  text_content:'Coverage about Gibran Rakabuming Raka',
  url:'https://www.tiktok.com/@reporter/video/'+(593+i),
  canonical_url:'https://www.tiktok.com/@reporter/video/'+(593+i),
  relation:'THIRD_PARTY_MENTION',saved_assessments:[]
}));
async function fakeFetch(url,options){
  const req=JSON.parse(options.body);requests.push({url,action:req.action});
  const json=value=>({ok:true,json:async()=>value});
  if(req.action==='myAccess')return json({access:{permissions:{manage_watchlist:true}}});
  if(req.action==='list')return json({items:[{id:3,type:'Candidate',name:'Gibran Rakabuming Raka',
    status:'Active',candidate_aliases:[]}],accounts:[]});
  if(req.action==='watchlistCapturedFeed')return json({posts:records,total:16,own_posts:0,mentions_by_others:16});
  if(req.action==='campaignEvidence')return json({evidence:records});
  if(req.action==='watchlistSyncStatus')return json({enabled:false,feature_enabled:false,accounts:[]});
  throw Error('Unexpected request '+req.action);
}
const window={location:{search:'?campaign_id=2'},scrollTo(){},confirm(){return true}};
const ctx={window,document,fetch:fakeFetch,localStorage:{getItem:()=> 'test-token'},
  URLSearchParams,URL,JSON,Set,Map,Promise,Date,Math,Number,String,Array,Object,RegExp,
  console,setTimeout:()=>{},clearTimeout};
vm.runInNewContext(inline,ctx,{filename:'watchlist-v2_2.html'});
vm.runInNewContext(adapter,ctx,{filename:'watchlist-live.js'});
async function tick(){await new Promise(resolve=>setImmediate(resolve));}
await tick();await tick();
const ui=window.__watchlist;assert.ok(ui);
ui.renderProfile('3');
await tick();await tick();await tick();
const profile=ui.getCandidate('3');
assert.equal(profile.posts.length,16,'Repeated campaign evidence must not duplicate captured sources');
assert.equal(profile.posts.filter(p=>p.kind==='own').length,0,'News publisher must never be own posts');
assert.equal(profile.posts.filter(p=>p.kind==='earned').length,16);
assert.equal(el('#pOwn').textContent,0,'Own Posts KPI must be zero');
assert.equal(el('#pEarned').textContent,16,'Mentions KPI must count news publisher sources');
assert.equal(profile.posts[0].source,'ntvnews.id'||'reporter_15');
ui.showAccountTab();
assert.ok(el('#tabbody').innerHTML.includes('Register public account'),'Account registration must be available');
assert.ok(el('#tabbody').innerHTML.includes('collection is disabled'),'Disabled collection must be explained');
for(const fn of listeners.get('click')||[])fn({target:{closest:()=>({id:'addTrackedAccount',dataset:{},hasAttribute(){return false}})}});
assert.ok(el('#modalBody').innerHTML.includes('accountProfileUrl'),'Officer can register a verified profile URL');
assert.ok(!requests.some(r=>/discover|crawl|openai/i.test(r.action)),'No paid provider calls');
console.log('PASS: 16 news mentions, 0 own posts, deduped campaign evidence, account setup UI');
