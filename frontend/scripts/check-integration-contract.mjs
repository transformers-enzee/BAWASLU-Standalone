import fs from 'node:fs';
import assert from 'node:assert/strict';

const read = p => fs.readFileSync(new URL('../'+p, import.meta.url), 'utf8');
const smart=read('public/ui-freeze/smart-radar-v6_2.html');
const watch=read('public/ui-freeze/watchlist-v2_2.html');
const smartBridge=read('public/ui-freeze/smart-radar-live.js');
const watchBridge=read('public/ui-freeze/watchlist-live.js');
const radarRoute=read('src/pages/SmartRadar.jsx');
const watchRoute=read('src/pages/Watchlist.jsx');
const social=read('src/pages/SocialListening.jsx');
const inbox=read('src/pages/Inbox.jsx');
const assistant=read('src/pages/IntelligenceAssistant.jsx');
const refs=read('src/components/intel/AssistantRecords.jsx');

for(const [name,html] of [['Smart Radar',smart],['Watchlist',watch]]){
  assert.match(html,/linear-gradient/,name+' original gradient');
  assert.match(html,/\/ui-freeze\/.+-live\.js/,name+' live adapter');
}
for(const marker of ['informationPlayers','actionPlayers','reviewedPlayers','deskOpen']){
 assert.ok(smart.includes(marker),'Smart Radar prototype lacks '+marker);
}
for(const marker of ['addCandidate','sentimentPie','stopTrack','candidateSearch','tabbody']){
 assert.ok(watch.includes(marker),'Watchlist prototype lacks '+marker);
}
assert.match(radarRoute,/smart-radar-v6_2\.html/);
assert.match(watchRoute,/watchlist-v2_2\.html/);
assert.match(smartBridge,/\/api\/smart-radar\/dashboard/);
assert.match(smartBridge,/\/api\/smart-radar\/finding/);
assert.match(smartBridge,/\/api\/smart-radar\/decision/);
assert.match(smartBridge,/regional access only/);
assert.match(smartBridge,/No authorised regional findings are available/);
assert.match(smartBridge,/regionalPilotBlocked/);
assert.match(smartBridge,/scope\.textContent=region/);
assert.ok(smartBridge.indexOf("ui.setData([]);") < smartBridge.lastIndexOf("$('#scopeLabel').textContent=region"), 'Scope must be set after prototype render');
assert.match(watchBridge,/watchlistCapturedFeed/);
assert.match(watchBridge,/updateWatchlist/);
assert.match(social,/inboxEvidenceLink/);
assert.match(social,/Open campaign Inbox/);
assert.match(inbox,/Original source provenance/);
assert.match(inbox,/safeOriginalUrl/);
assert.ok(!inbox.includes('synthetic-demo'),'Synthetic Inbox fixture must not ship');
assert.match(assistant,/\/api\/assistant-history/);
assert.match(assistant,/Saved conversations/);
assert.match(refs,/View original source/);
assert.ok(!smart.includes("const seed=[{"),'Fictional Smart Radar seed must not ship');
assert.ok(!watch.includes('const C=[{"id"'),'Fictional Watchlist candidate seed must not ship');
assert.match(social,/provenance_quality\?\.requires_manual_review/);
assert.match(social,/Source metadata incomplete/);
assert.match(social,/Provider record ID not supplied/);
const integrationConsole=read('src/pages/IntegrationReadiness.jsx');
const app=read('src/App.jsx');
const admin=read('src/pages/Administration.jsx');
assert.match(app,/administration\/integration/);
assert.match(app,/<AccessGate permission="administration"/);
assert.match(admin,/Open integration console/);
assert.match(integrationConsole,/source-id-backfill\/preview/);
assert.match(integrationConsole,/source-id-backfill\/apply/);
assert.match(integrationConsole,/expected_missing:preview\.eligible_missing_ids/);
assert.match(integrationConsole,/provenance-review-queue/);
assert.match(integrationConsole,/bawaslu_access_token/);
assert.match(integrationConsole,/!confirm\|\|busy/);
console.log('PASS: frozen UI, integration, and row-level provenance warning contracts');
