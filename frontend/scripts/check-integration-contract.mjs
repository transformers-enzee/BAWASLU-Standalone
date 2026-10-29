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
const campaign=read('src/components/intel/CampaignPanel.jsx');
const registry=read('../backend/app/registry.py');
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
assert.match(watchRoute,/social-listening/);
assert.match(social,/CampaignPanel/);
assert.doesNotMatch(social,/Discover sources|Review queue|Saved searches/);
assert.match(campaign,/watchlist-v2_2\.html\?campaign_id/);
assert.match(campaign,/Captured Posts/);
assert.match(campaign,/Candidate Watchlist/);
const trendPosition=campaign.indexOf('aria-label="Campaign trend by platform"');
const topicsPosition=campaign.indexOf('aria-label="Topics and Themes"');
const capturedPosition=campaign.indexOf('aria-label="Captured posts"',trendPosition);
assert.ok(trendPosition>=0 && trendPosition<topicsPosition && topicsPosition<capturedPosition,
  'Topics & Themes must appear immediately below the platform chart, before captured evidence');
assert.match(campaign,/lg:col-span-2 rounded-\[13px\][^\n]+aria-label="Topics and Themes"/,
  'Topics & Themes must span the dashboard grid on desktop');
assert.match(registry,/CampaignEvidence\.campaign_id==scoped_campaign\.id/);
assert.match(watchBridge,/campaign_id/);
assert.match(watchBridge,/campaignId\?\(Array\.isArray\(actor\.value\)/,'Campaign-earned mentions must consume the scoped evidence array, not the global actor response');
assert.match(watchBridge,/candidate\.findings=candidate\.posts\.filter/,'Only saved potential-violation assessment flags appear on the profile');
assert.match(campaign,/capturedSourceFilter/,'Captured evidence needs real source-type filtering');
assert.match(campaign,/capturedTextFilter/,'Captured evidence needs a client-only search');
assert.match(campaign,/\['watchlist','posts'\]/,'Campaign tab deep links must preserve selected campaign context');
assert.match(smartBridge,/\/api\/smart-radar\/dashboard/);
assert.match(smartBridge,/\/api\/smart-radar\/finding/);
assert.match(smartBridge,/\/api\/smart-radar\/decision/);
assert.match(smartBridge,/regional access only/);
assert.match(smartBridge,/No authorised regional findings are available/);
assert.match(smartBridge,/No verified regional pilot baseline is available/);
assert.match(smartBridge,/regionalPilotBlocked/);
assert.match(smartBridge,/scope\.textContent=region/);
assert.ok(smartBridge.indexOf("ui.setData([]);") < smartBridge.lastIndexOf("$('#scopeLabel').textContent=region"), 'Scope must be set after prototype render');
assert.match(watchBridge,/watchlistCapturedFeed/);
assert.match(watchBridge,/updateWatchlist/);
assert.match(campaign,/Open original source/);
assert.match(campaign,/Analyze with AI/);
assert.match(inbox,/Original source provenance/);
assert.match(inbox,/safeOriginalUrl/);
assert.ok(!inbox.includes('synthetic-demo'),'Synthetic Inbox fixture must not ship');
assert.match(assistant,/\/api\/assistant-history/);
assert.match(assistant,/Saved conversations/);
assert.match(refs,/View original source/);
assert.ok(!smart.includes("const seed=[{"),'Fictional Smart Radar seed must not ship');
assert.ok(!watch.includes('const C=[{"id"'),'Fictional Watchlist candidate seed must not ship');
assert.match(campaign,/AssessmentPilotPreview/);
assert.match(campaign,/campaignEvidenceById/);
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
