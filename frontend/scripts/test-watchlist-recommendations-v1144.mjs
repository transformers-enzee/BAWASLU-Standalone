import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// All responses are mocked: this test cannot spend SocialCrawl or OpenAI credits.
const html=fs.readFileSync(new URL('../public/ui-freeze/watchlist-v2_2.html',import.meta.url),'utf8');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
const adapter=fs.readFileSync(new URL('../public/ui-freeze/watchlist-live.js',import.meta.url),'utf8');
assert.ok(inline,'Watchlist interactive prototype script must exist');
const nodes=new Map(),listeners=new Map(),calls=[],activation=[],creation=[];
const element=key=>{
  if(!nodes.has(key))nodes.set(key,{
    id:key,textContent:'',innerHTML:'',value:'',style:{},dataset:{},
    classList:{add(){},remove(){},contains(){return false}},
    focus(){},setSelectionRange(){},setAttribute(){},
    insertAdjacentHTML(_where,markup){this.innerHTML+=markup},
    addEventListener(name,listener){listeners.set(key+':'+name,listener)}
  });
  return nodes.get(key);
};
const document={
  querySelector:element,querySelectorAll(){return []},
  documentElement:{classList:{add(){}}},
  addEventListener(type,cb){const list=listeners.get('document:'+type)||[];list.push(cb);listeners.set('document:'+type,list)}
};
const suggestions=[
  {name:'Gibran Rakabuming Raka',matching_posts:28,source_ids:[501,502]},
  {name:'Gibran Raka Bumi',matching_posts:1,source_ids:[503]},
  {name:'Prabowo Subianto',matching_posts:1,source_ids:[504]}
];
const fetch=async(url,options)=>{
  const payload=JSON.parse(options.body);calls.push({url,action:payload.action});
  if(payload.action==='myAccess')return {ok:true,json:async()=>({access:{permissions:{manage_watchlist:true}}})};
  if(payload.action==='list')return {ok:true,json:async()=>({items:[
    {id:44,type:'Candidate',name:'Gibran Rakabuming Raka',status:'Inactive',candidate_aliases:[]},
    {id:12,type:'Candidate',name:'Suli',status:'Active',candidate_aliases:[]}
  ],accounts:[]})};
  if(payload.action==='campaignCandidateSuggestions'){
    assert.equal(payload.id,'2','Recommendations must be scoped to selected campaign');
    return {ok:true,json:async()=>({candidates:suggestions})};
  }
  throw Error('Unexpected provider call '+payload.action);
};
const window={location:{search:'?campaign_id=2',origin:'https://bawaslu.test'},scrollTo(){},confirm:()=>true};
const ctx={window,document,fetch,localStorage:{getItem:()=> 'qa-token'},
  URLSearchParams,URL,JSON,Set,Map,Promise,Date,Math,Number,String,Array,Object,RegExp,
  console,setTimeout:()=>{},clearTimeout};
vm.runInNewContext(inline,ctx,{filename:'watchlist-v2_2.html'});
vm.runInNewContext(adapter,ctx,{filename:'watchlist-live.js'});
const settle=async()=>{await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve));};
await settle();
const ui=window.__watchlist;
assert.ok(ui,'Watchlist bridge exists');
ui.onActivate=id=>activation.push(id);
ui.onCreate=name=>creation.push(name);
const fireClick=button=>{
  button.hasAttribute=()=>false;button.dataset??={};
  const evt={target:{closest:selector=>selector==='button'?button:
    selector.startsWith('button[data-track-suggestion]')?button:
    selector.includes('data-review-suggestion')?button:null}};
  for(const listener of listeners.get('document:click')||[])listener(evt);
};
fireClick({id:'addCandidate',dataset:{}});
await settle();
const markup=element('#aiCandidateSuggestions').innerHTML;
assert.ok(element('#modalBody').innerHTML.includes('aiCandidateSuggestions'),'Recommendations mounted within dialog');
assert.ok(markup.includes('Gibran Rakabuming Raka'));
assert.ok(markup.includes('28 saved mention(s)'));
assert.ok(markup.includes('Evidence #501, #502'));
assert.ok(markup.includes('Review identity'),'Likely variant must receive manual review');
assert.ok(markup.includes('Track existing'),'Existing registered candidates must not be recreated');
assert.ok(markup.includes('Add & Track'),'Unmatched candidates can use existing registry creation');
assert.equal(calls.filter(x=>x.action==='campaignCandidateSuggestions').length,1);
fireClick({id:'',dataset:{reviewSuggestion:'1'}});
assert.equal(creation.length,0,'Name variant must not automatically create another candidate');
fireClick({id:'',dataset:{trackSuggestion:'0'}});
assert.deepEqual(activation,['44'],'Existing candidate suggestion activates existing ID');
fireClick({id:'',dataset:{trackSuggestion:'2'}});
assert.deepEqual(creation,['Prabowo Subianto'],'New name routes through authenticated candidate creation');
assert.equal(calls.filter(x=>/Discover|Crawl|OpenAI/i.test(x.action)).length,0,'No paid provider calls');
console.log('PASS: Campaign-scoped popup suggestions, identity review and safe registry routing');
