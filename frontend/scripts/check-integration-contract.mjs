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
console.log('PASS: frozen UI, integration, and row-level provenance warning contracts');
