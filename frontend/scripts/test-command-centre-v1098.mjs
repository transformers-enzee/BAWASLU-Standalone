import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync('public/ui-freeze/smart-radar-v6_2.html','utf8');
const bridge=fs.readFileSync('public/ui-freeze/smart-radar-live.js','utf8');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(inline,'prototype inline script');
const elements=new Map();
const events=new Map();
function element(key){
  if(elements.has(key))return elements.get(key);
  const classes=new Set();
  const node={
    id:key, innerHTML:'', textContent:'', value:'', style:{},dataset:{},options:[{textContent:''}],
    disabled:false,
    classList:{
      add(name){classes.add(name)},remove(name){classes.delete(name)},
      contains(name){return classes.has(name)},
      toggle(name,on){if(on===undefined){on=!classes.has(name)}if(on)classes.add(name);else classes.delete(name);return on}
    },
    setAttribute(){},removeAttribute(){},getAttribute(){return null},
    focus(){},appendChild(){},insertAdjacentElement(){},
    addEventListener(name,handler){events.set(key+':'+name,handler)},
    querySelector(selector){return element(key+' '+selector)},
    querySelectorAll(selector){return selector==='.source' && node.innerHTML.includes('class="source"')
      ? [element(key+' source')] : []},
    closest(selector){return element(key+' closest '+selector)}
  };
  elements.set(key,node);
  return node;
}
const document={
  body:element('body'),querySelector:element,createElement:tag=>element('created-'+tag),
  addEventListener(name,handler){events.set('document:'+name,[...(events.get('document:'+name)||[]),handler])}
};
class FakeDOMParser{parseFromString(){return {querySelectorAll(){return []}}}}
let findingResolver;
let findingRequests=0, historyRequests=0;
const data={
  mode:'SAVED_INBOX_SOURCE_OF_TRUTH',source_total:1,watchlist_profiles:[],
  findings:[{
    id:'INBOX-V-1-177',title:'Allegation of Repeat Voting',
    perspectives:['operations'],players:['violations'],topics:['Potential Violations'],
    summary:'Saved preliminary concern',status:'pending',supporting_posts:1,
    actor_mentions:{'Candidate Alpha':4,'Candidate Beta':3,'Candidate Gamma':2,'Candidate Delta':1},
    source_ids:['social:177'],sentiment_counts:{NEUTRAL:1}
  }]
};
function response(body,ok=true){return {ok,status:ok?200:404,async json(){return body}}}
async function mockFetch(path){
  if(path==='/api/functions/registry')return response({access:{geographic_scope:'Nationwide',permissions:{human_validation:true,manage_watchlist:true}}});
  if(path==='/api/smart-radar/dashboard')return response(data);
  if(path.startsWith('/api/smart-radar/finding/')){
    findingRequests++;
    return new Promise(resolve=>{findingResolver=resolve});
  }
  if(path.startsWith('/api/smart-radar/history/')){
    historyRequests++;
    return response({events:[]});
  }
  if(path==='/indonesia-provinces.geojson')return response({},false);
  throw Error('Unexpected request '+path);
}
const window={scrollTo(){},location:{href:'/'},top:{location:{assign(){}}},confirm(){return true}};
const context={
  document,window,fetch:mockFetch,localStorage:{getItem(){return 'test-only'}},
  DOMParser:FakeDOMParser,structuredClone,URL,Date,Math,Number,String,Array,
  Set,Map,Object,JSON,RegExp,clearTimeout,setTimeout,encodeURIComponent,
  decodeURIComponent,console
};
vm.runInNewContext(inline,context,{filename:'smart-radar-inline.js',timeout:4000});
vm.runInNewContext(bridge,context,{filename:'smart-radar-live.js',timeout:4000});
await new Promise(resolve=>setTimeout(resolve,30));
const ui=window.__bawaslu;
assert.ok(ui,'mounted bridge');
assert.match(element('#watch').innerHTML,/Candidate Alpha/);
assert.match(element('#watch').innerHTML,/Candidate Beta/);
assert.doesNotMatch(element('#watch').innerHTML,/Candidate Gamma/);
assert.match(element('#watch').innerHTML,/1–2 of 4/);
const pageClick={
  target:{closest(selector){return selector==='[data-watch-page]'?{dataset:{watchPage:'next'}}:null}},
  preventDefault(){},stopPropagation(){}
};
for(const handler of events.get('document:click')||[])handler(pageClick);
assert.match(element('#watch').innerHTML,/Candidate Gamma/);
assert.match(element('#watch').innerHTML,/Candidate Delta/);
assert.doesNotMatch(element('#watch').innerHTML,/Candidate Alpha/);
assert.match(element('#watch').innerHTML,/3–4 of 4/);
const pending=ui.openFinding('INBOX-V-1-177',null);
assert.ok(element('#overlay').classList.contains('open'),'drawer opens before network response');
assert.match(element('#drawerBody').innerHTML,/Opening saved evidence/);
assert.equal(findingRequests,1);
assert.equal(historyRequests,0,'review history must not block opening');
findingResolver(response({summary:'Saved preliminary concern',supporting_posts:1,posts:[{
  account_raw:'Account A',message_original:'Report requires verification',
  source_url:'https://example.org/source/177',canonical_source_id:'social:177',
  platform:'X',sentiment:'NEUTRAL'
}]}));
await pending;
assert.match(element('#drawerBody').innerHTML,/Original Posts \(1 loaded of 1 referenced\)/);
assert.equal(historyRequests,0);
await ui.loadHistory('INBOX-V-1-177');
assert.equal(historyRequests,1,'history is lazy');
console.log('PASS: v109.8 runtime drawer, lazy history and two-candidate pagination');
