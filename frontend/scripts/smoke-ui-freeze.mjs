import fs from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';

function bootstrap(name){
  const html=fs.readFileSync(new URL('../public/ui-freeze/'+name+'.html',import.meta.url),'utf8');
  const source=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(source, name+' script found');
  const elements=new Map();
  const events=new Map();
  function elem(key){
    if(elements.has(key))return elements.get(key);
    const object={
      id:key, textContent:'',innerHTML:'',value:'',style:{},dataset:{},
      classList:{add(){},remove(){},toggle(){},contains(){return false}},
      setAttribute(){},getAttribute(){return null},focus(){},setSelectionRange(){},
      insertAdjacentHTML(_position,markup){this.innerHTML+=markup},
      addEventListener(name,fn){events.set(key+':'+name,fn)},
      querySelector(sel){return elem(key+' '+sel)},
      querySelectorAll(){return []},
      closest(){return elem(key+' closest')}
    };
    elements.set(key,object);
    return object;
  }
  const document={
    querySelector:elem,
    addEventListener(name,fn){events.set('document:'+name,fn)}
  };
  class FakeDomParser {
    parseFromString(){return {querySelectorAll(){return []}};}
  }
  const window={scrollTo(){},location:{href:'/'}};
  const context={document,window,DOMParser:FakeDomParser,structuredClone,
    URL,Date,Math,Number,String,Array,Set,Object,JSON,RegExp,
    clearTimeout,setTimeout,console};
  vm.runInNewContext(source,context,{filename:name+'.html',timeout:2000});
  return {window,elem,events};
}
const radar=bootstrap('smart-radar-v6_2');
assert.ok(radar.window.__bawaslu,'Smart Radar mounted bridge');
radar.window.__bawaslu.setData([{
  id:'SMOKE-001',title:'Unit-test-only example',status:'pending',
  perspectives:['operations'],players:['concerns'],player:'concerns',
  topics:['Election Operations'],p:'operations',geo:'all',
  summary:'Unit test source record, not a real finding.',
  published_at:'2026-10-27',posts:[],source_count:1,
  human_reviewed:false,platform_counts:{X:1},day_counts:{'2026-10-27':1},
  actor_mentions:{},insights:{operations:'Unit test'}
}]);
assert.ok(radar.elem('#executive').textContent || radar.elem('#kpis').innerHTML,
  'Smart Radar renders a usable dashboard after data load');
assert.ok(radar.elem('#kpis').innerHTML.includes('1'),'Smart Radar computes source-linked counts');
const watchlist=bootstrap('watchlist-v2_2');
assert.ok(watchlist.window.__watchlist,'Watchlist mounted bridge');
watchlist.window.__watchlist.setData([{
  id:'42',name:'Smoke Test Candidate',aliases:[],jurisdiction:'National',
  context:'Test only',summary:'Test only',posts:[],findings:[],accounts:[]
}],['42']);
assert.ok(watchlist.elem('#trackedList').innerHTML.includes('Smoke Test Candidate'),
  'Watchlist renders saved candidate');
watchlist.window.__watchlist.renderProfile('42');
assert.equal(watchlist.elem('#candidateName').textContent,'Smoke Test Candidate');
watchlist.events.get('document:click')({target:{closest:()=>({id:'addCandidate'})}});
assert.ok(watchlist.elem('#modalBody').innerHTML.includes('aiCandidateSuggestions'),
  'Add Candidate modal hosts AI suggestions inside the existing popup');
assert.ok(watchlist.elem('#modalBody').innerHTML.indexOf('aiCandidateSuggestions')<
  watchlist.elem('#modalBody').innerHTML.indexOf('candidateSearch'),
  'Suggestions appear above the existing candidate search');
console.log('PASS: Smart Radar and Watchlist offline startup/render smoke checks');
