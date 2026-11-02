import assert from 'node:assert/strict';
import {snapshot} from '../src/demo/currentSnapshot.js';
const fakeLocation={href:'https://demo.invalid/demo',origin:'https://demo.invalid'};
let realNetworkCalls=0;
const fakeNetwork=async()=>{realNetworkCalls++;throw Error('Unexpected network request')};
globalThis.window={fetch:fakeNetwork,localStorage:{getItem:()=>null},location:fakeLocation};
globalThis.location=fakeLocation;
globalThis.XMLHttpRequest=function XMLHttpRequest(){};
XMLHttpRequest.prototype.open=function(){realNetworkCalls++};
try{Object.defineProperty(globalThis,'navigator',{configurable:true,value:{sendBeacon:()=>{realNetworkCalls++;return true}}})}catch(_){}
await import('../src/demo/realBridge.js');
const invoke=async(name,action,id,data={})=>{
 const response=await window.fetch('/api/functions/'+name,{method:'POST',body:JSON.stringify({action,id,data})});
 assert.equal(response.status,200);return response.json();
};
assert.equal(snapshot.length,300);
const campaigns=await invoke('socialListening','listCampaigns');
assert.ok(campaigns.campaigns.length>=4);
const items=await invoke('socialListening','campaignCapturedPosts',snapshot[0].campaignId,{page:1,page_size:200});
assert.ok(items.evidence.length>0);
assert.ok(items.evidence.every(x=>x.canonical_url===''));
const inbox=await invoke('socialListening','campaignIntelligenceInbox');
assert.equal(inbox.findings.length,300);
const first=inbox.findings[0];
assert.equal(first.text_content,snapshot[0].text);
await invoke('socialListening','campaignFlagReview',first.campaign_id,{result_id:first.id,decision:'REVIEWED'});
const after=await invoke('socialListening','campaignIntelligenceInbox',first.campaign_id,{result_id:first.id});
assert.equal(after.findings[0].human_review_status,'REVIEWED');
const selected=await invoke('registry','list');
assert.ok(selected.items.some(x=>x.type==='Candidate'));
const settings=await invoke('getMyEffectiveAccess','');
assert.equal(settings.access.permissions.view_intelligence,true);
const noExternal=await window.fetch('https://bsekqkhgyjedcmptjnag.supabase.co/rest/v1/example',{method:'POST'});
assert.equal(noExternal.status,403);
assert.throws(()=>new XMLHttpRequest().open('POST','/api/functions/socialListening'));
assert.equal(navigator.sendBeacon('/api/write','data'),false);
assert.equal(realNetworkCalls,0,'Demo must never send real API traffic');

import {runInNewContext} from 'node:vm';
import fs from 'node:fs';
import {resolve} from 'node:path';
const html=fs.readFileSync(resolve('public/demo/smart-radar.html'),'utf8');
const watchHtml=fs.readFileSync(resolve('public/demo/watchlist.html'),'utf8');
const source=fs.readFileSync(resolve('public/demo/snapshot-bridge.js'),'utf8');
const recordMarkup=html.match(/<script id="bawaslu-demo-snapshot" type="application\/json">([\s\S]*?)<\/script>/);
assert.ok(recordMarkup,'Approved Command Centre HTML must embed the real snapshot');
assert.ok(watchHtml.includes('id="bawaslu-demo-snapshot"'));
const iframeRecords=JSON.parse(recordMarkup[1]);
assert.equal(iframeRecords.length,300);
let iframeNetworkCalls=0;
const iframeWindow={fetch:async()=>{iframeNetworkCalls++;throw Error('Unexpected remote iframe request')}};
const browserContext={
 window:iframeWindow,document:{getElementById:()=>({textContent:recordMarkup[1]})},
 location:{href:'https://demo.invalid/demo/smart-radar.html',origin:'https://demo.invalid'},
 Response,URL,JSON,Math,Date,Number,Array,Map,Set,String,Object,RegExp,
};
runInNewContext(source,browserContext);
const radarResponse=await iframeWindow.fetch('/api/smart-radar/dashboard');
const radar=await radarResponse.json();
assert.equal(radar.mode,'SAVED_INBOX_SOURCE_OF_TRUTH');
assert.equal(radar.source_total,300);
assert.ok(radar.findings.length>=3);
const findingResponse=await iframeWindow.fetch('/api/smart-radar/finding/'+radar.findings[0].id);
const finding=await findingResponse.json();
assert.equal(finding.posts.length,finding.supporting_posts);
const topicsResponse=await iframeWindow.fetch('/api/smart-radar/issue-distribution');
const topics=await topicsResponse.json();
assert.ok(topics.operations.topics.length>0);
await iframeWindow.fetch('/api/smart-radar/decision',{method:'POST',body:JSON.stringify({finding_id:radar.findings[0].id,action:'REVIEWED'})});
assert.equal(iframeNetworkCalls,0,'Embedded real Command Centre must have zero outbound API calls');

console.log('PASS real demo API contract: 300 snapshot records, campaigns, inbox, in-browser reviews, watchlist, zero outbound requests');
