import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Mock saved, campaign-scoped backend posts only. No network, credits or DB writes.
const html=fs.readFileSync(new URL('../public/ui-freeze/watchlist-v2_2.html',import.meta.url),'utf8');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
const adapter=fs.readFileSync(new URL('../public/ui-freeze/watchlist-live.js',import.meta.url),'utf8');
assert.ok(inline);
const elements=new Map(),listeners=new Map(),calls=[];
function el(key){
  if(!elements.has(key))elements.set(key,{id:key,value:'',innerHTML:'',textContent:'',
    style:{},dataset:{},classList:{add(){},remove(){},contains(){return false}},
    focus(){},setSelectionRange(){},setAttribute(){},addEventListener(){},
    insertAdjacentHTML(_where,markup){this.innerHTML+=markup}});
  return elements.get(key);
}
const document={querySelector:el,querySelectorAll(){return []},
  documentElement:{classList:{add(){}}},
  addEventListener(type,fn){const all=listeners.get(type)||[];all.push(fn);listeners.set(type,all)}};
const captured=Array.from({length:58},(_,i)=>({
  id:String(700+i),relation:'THIRD_PARTY_MENTION',
  source_collection:'SOCIAL_LISTENING_CAPTURED',campaign_id:'2',
  platform:'tiktok',author_name:i===0?'ntvnews.id':'news_'+i,
  text:'Media membahas Gibran Rakabuming Raka',
  published_at:'2026-10-30T13:10:55Z',url:'https://www.tiktok.com/@news'+i+'/video/'+(700+i),
  saved_assessments:[]
}));
const own=Array.from({length:12},(_,i)=>({
  id:String(800+i),relation:'OWN_POST',
  source_collection:'REGISTERED_CANDIDATE_ACCOUNT',campaign_id:'2',
  platform:'instagram',author_name:'Gibran Rakabuming',
  text:'Posting dari akun sendiri',
  published_at:'2026-10-31T01:10:55Z',
  url:'https://www.instagram.com/p/qa'+i+'/',saved_assessments:[]
}));
const rows=[...captured,...own],total=70;
async function fetch(url,opts){
  const req=JSON.parse(opts.body);calls.push(req);
  const ok=data=>({ok:true,json:async()=>data});
  if(req.action==='myAccess')return ok({access:{permissions:{manage_watchlist:true}}});
  if(req.action==='list')return ok({items:[{id:3,type:'Candidate',name:'Gibran Rakabuming Raka',
    status:'Active',candidate_aliases:[]}],accounts:[{id:1,watchlist_id:3,
    platform:'instagram',handle:'@gibran_rakabuming',url:'https://instagram.com/gibran_rakabuming'}]});
  if(req.action==='watchlistCapturedFeed'){
    assert.equal(req.data.campaign_id,'2','Watchlist must stay in selected Test campaign');
    const start=(req.data.page-1)*50;
    return ok({posts:rows.slice(start,start+50),total,own_posts:12,mentions_by_others:58});
  }
  if(req.action==='watchlistSyncStatus')return ok({enabled:false,
    manual_fetch_available:false,accounts:[]});
  throw Error('Unexpected secondary evidence or paid provider action: '+req.action);
}
const window={location:{search:'?campaign_id=2'},scrollTo(){},confirm(){return true}};
const ctx={window,document,fetch,localStorage:{getItem:()=> 'test-token'},
  URLSearchParams,URL,JSON,Set,Map,Promise,Date,Math,Number,String,Array,Object,RegExp,
  console,setTimeout:()=>{},clearTimeout};
vm.runInNewContext(inline,ctx,{filename:'watchlist-v2_2.html'});
vm.runInNewContext(adapter,ctx,{filename:'watchlist-live.js'});
const tick=async()=>{await new Promise(resolve=>setImmediate(resolve));};
await tick();await tick();
const ui=window.__watchlist;assert.ok(ui);
ui.renderProfile('3');
await tick();await tick();await tick();await tick();
const profile=ui.getCandidate('3');
assert.equal(profile.feedLoadState,'ready');
assert.equal(profile.posts.length,70,'Load all 70 source posts, not the first 50');
assert.equal(profile.posts.filter(x=>x.kind==='own').length,12);
assert.equal(profile.posts.filter(x=>x.kind==='earned').length,58);
assert.equal(el('#pOwn').textContent,12,'Own posts derive from author-attributed account captures');
assert.equal(el('#pEarned').textContent,58,'Mentions derive only from Social Listening Captured Posts');
assert.equal(new Set(profile.posts.map(x=>x.sourceId)).size,70,'No duplicate captured sources');
assert.equal(calls.filter(x=>x.action==='watchlistCapturedFeed').length,2,
  'Two pages of saved evidence should load without an extra crawl');
assert.equal(calls.filter(x=>/campaignEvidence|actorPicture|discover|crawl|OpenAI/i.test(x.action)).length,0,
  'No second earned-media feed, Intelligence Inbox, or provider request');
console.log('PASS: Test campaign 58 saved mentions and 12 authored posts with no extra source');
