import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Script} from 'node:vm';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {UI_LABEL_ID} from '../src/lib/interfaceUiLabels.js';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=path=>fs.readFileSync(resolve(root,path),'utf8');
const labels=[
 'Explore actors, themes, trends, geography, topics and sentiment. Select an insight to inspect its matching example posts.',
 'Candidate & Political Actor Intelligence','Top 10 Candidate Mentions',
 'Top candidate mentions · two profiles per page','Top 10 candidate mentions in relevant Inbox evidence.',
 'Displaying up to two at a time; a mention is not evidence of wrongdoing.',
 'Trends & Geographic Intelligence','Conversation Activity','Issue Distribution',
 'Top five AI-generated conversation themes','Geographic Signals','Normalized Topics',
 'Recorded source-post publication dates','Most frequently matched main keywords from Social Listening',
 'Posts by province','Posts associated with provinces · current campaign filters',
 'Word cloud','Term frequency · stored posts','Top accounts','Post engagement',
 'Account followers','Own Posts','Mentions by Others','Possible Violations',
 'Sentiment Distribution','No classified posts in this selection',
 'All Collected Posts','Activity Timeline','Tracked Accounts'
];
labels.push('Collection runs:','Evidence records:','Tracked account post','Affiliation unverified','Add Candidate','AI-suggested candidates','Search existing candidates','Register an approved candidate','Approved candidate full name','＋ Create & Track Candidate','Engagement ranks accounts by summed reported engagement on captured posts, not by account popularity. Followers reflect reported account-level counts when supplied.');
labels.push('Post preview · AI assessment','Canonical Watchlist candidate IDs:','Human flag review','Communication context (review hint):','Source-linked findings','No implied legal verdict','Activity by Platform','relevant posts have saved AI sentiment labels.');
for(const label of labels){
 assert.equal(typeof UI_LABEL_ID[label],'string','Missing ID translation: '+label);
 assert.notEqual(UI_LABEL_ID[label],label,'English label: '+label);
}
const scripts=['public/ui-freeze/bawaslu-interface-locale.js','public/ui-freeze/bawaslu-ui-translation-fallback.js','public/ui-freeze/smart-radar-live.js','public/ui-freeze/watchlist-live.js'];
for(const path of scripts)new Script(read(path),{filename:path});
const react=read('src/lib/UiLanguageLayer.jsx'),locale=read(scripts[0]);
const dashboard=read('public/ui-freeze/smart-radar-v6_2.html'),watch=read('public/ui-freeze/watchlist-v2_2.html');
assert.ok(dashboard.includes('Section 01 · Operational Intelligence Overview'),'Missing Section 01 heading');
assert.ok(dashboard.includes('Section 02 · Intelligence Insights'),'Missing Section 02 heading');
assert.ok(dashboard.indexOf('Section 01 · Operational Intelligence Overview')<dashboard.indexOf('Section 02 · Intelligence Insights'),'Section order incorrect');
assert.ok(locale.includes('Bagian 01 · Ringkasan Intelijen Operasional'),'Missing Indonesian Section 01 label');
assert.ok(locale.includes('Bagian 02 · Wawasan Intelijen'),'Missing Indonesian Section 02 label');
assert.ok(react.includes('const requested=new WeakMap'));
assert.ok(react.includes('BAWASLU_UI_LANGUAGE'));
assert.ok(react.includes('BAWASLUUiTranslator'));
assert.ok(locale.includes('fallback.request(english,value'));
assert.ok(locale.includes('[data-ai-theme]'));
assert.ok(read(scripts[2]).includes('data-ai-theme data-i18n-exempt'));
assert.ok(dashboard.includes('bawaslu-ui-translation-fallback.js'));
assert.ok(watch.includes('bawaslu-ui-translation-fallback.js'));
assert.ok(watch.includes('data-original-content'));
assert.ok(read('src/lib/LanguageContext.jsx').includes("pagination[2]+' dari '+pagination[3]"));
assert.ok(read('index.html').includes('bawaslu-ui-translation-fallback.js'));
assert.ok(!read('public/ui-freeze/smart-radar-live.js').includes('renderInboxLineage()'), 'Remove Live Inbox source-count banner');
assert.ok(read('public/ui-freeze/smart-radar-live.js').includes('presentation-only grouping') || read('public/ui-freeze/smart-radar-live.js').includes('Presentation-only grouping'), 'Sentiment grouping must be display only');
assert.ok(read('src/pages/Inbox.jsx').includes('<TranslatedIntelligenceText text={signal.explanation'), 'AI flag explanations use translation-only display');
assert.ok(read('public/ui-freeze/watchlist-live.js').includes("!$('#panel')?.classList.contains('open')"));
assert.ok(read('src/pages/Inbox.jsx').includes('hidden className="hidden" aria-label="AI operations and diagnostics"'));
assert.ok(read('src/pages/Inbox.jsx').includes('aria-label="Legacy intelligence records and administrative review"'));
assert.ok(watch.includes('id="candidateSummary" data-ai-summary data-i18n-exempt'), 'Saved Watchlist summary must use AI translation path');
assert.ok(read('public/ui-freeze/bawaslu-interface-locale.js').includes("[data-ai-summary]"), 'Translation selector must include saved summaries');
assert.ok(watch.includes("$('#candidateSummary').textContent=c.summary"), 'Watchlist summary must still come from saved profile data');
assert.ok(watch.includes('data-original-content'), 'Original source posts must stay untouched');
assert.ok(watch.includes('bawaslu-interface-locale.js?build=133.6'), 'Invalidate stale translation asset');

// v133.6: all four iframe clients must receive the updated interface translations.
const locale1336=read('public/ui-freeze/bawaslu-interface-locale.js');
const layer1336=read('src/lib/UiLanguageLayer.jsx');
const shell1336=read('src/components/intel/Shell.jsx');
for(const phrase of [
 'Assigned homework stays accessible even when dashboard filters change.',
 'Last-visit baseline unavailable · historical pilot',
 'Last-visit differences require verified account visit history.',
 'What You Missed — Details',
 'Original Posts',
 'BAWASLU officer homework',
 'focuses on one selected candidate at a time and draws both own posts',
 'shows the broader relevant intelligence picture from Intelligence Inbox'
])assert.ok(locale1336.includes(phrase),'Missing localized interface fragment: '+phrase);
assert.ok(locale1336.includes('Asia/Jakarta')&&layer1336.includes('Asia/Jakarta'),'Both UI translation layers must format WIB');
assert.ok(locale1336.includes('ISO_INSTANT')&&layer1336.includes('formatUiDate(source)'),'Raw ISO dates must be formatted for display');
assert.ok(locale1336.includes(".source p"),'Original post text must stay excluded');
assert.ok(shell1336.includes('intel-sidebar-scroll::-webkit-scrollbar')&&shell1336.includes('scrollbar-width:none'),'Sidebar scrollbars hidden without disabling scrolling');
for(const html of [
 'public/ui-freeze/watchlist-v2_2.html',
 'public/ui-freeze/smart-radar-v6_2.html',
 'public/demo/watchlist.html',
 'public/demo/smart-radar.html'
])assert.ok(read(html).includes('bawaslu-interface-locale.js?build=133.6'),'Translation asset revision missing: '+html);

const progressDialog=read('src/components/intel/AssessmentProgressDialog.jsx');
const campaignProgress=read('src/components/intel/CampaignPanel.jsx');
assert.ok(progressDialog.includes("verifiedPercent=count>0?"),'Progress requires saved assessment counts');
assert.ok(progressDialog.includes("!collecting&&verifiedPercent!==null"),'Collection must not use a fabricated percent');
assert.ok(progressDialog.includes("Status request failed:"),'Failed status polls must be explained');
assert.ok(campaignProgress.includes("setDiscoverRun(result);setDiscoverError('')"),'Successful status handling clears stale errors');

// A single in-dialog confirmation; no extra browser alert or credit text.
assert.ok(!campaignProgress.includes("window.confirm('Run a separate paid SocialCrawl Discover"),'Activation must not open a second browser confirmation');
assert.ok(campaignProgress.includes('discoverPreviewBusy'),'Preview must have separate loading state');
assert.ok(progressDialog.includes('onClick={onConfirm}>Activate</button>'),'Activation CTA must stay accurately named');
assert.ok(!progressDialog.includes("loading?'Activating…'"),'Preview/activation must not use a misleading activating label');
assert.ok(progressDialog.includes('Activate this campaign to collect posts and assess the saved results?'),'Activation confirmation should be concise');
assert.ok(!progressDialog.includes('collect up to 100 posts'),'Activation confirmation must not mention the collection cap');

// Collection shows one indeterminate bar, not empty metrics or AI diagnostics.
assert.ok(progressDialog.includes('{collecting&&<div role="status"'),'Collection needs a minimal waiting state');
assert.ok(progressDialog.includes('Collecting SocialCrawl posts; exact progress unavailable'),'Collection bar must not imply a percentage');
assert.ok(progressDialog.includes('{!collecting&&<>'),'Detailed cards are only displayed after collection');
// SocialCrawl collection cap is 100, while AI assessment remains independent.
const prismDiscover=read('../backend/app/prism_discover.py');
assert.ok(prismDiscover.includes('CAP=100'),'Activation requests must use 100 posts');
assert.ok(prismDiscover.includes("'limit':CAP")&&prismDiscover.includes("'max_credits':CAP"),'Provider caps must stay coordinated');
assert.ok(campaignProgress.includes("['COMPLETED','PARTIAL'].includes(run?.status)"),'Only a provider-complete run closes the popup');
assert.ok(campaignProgress.includes('handleDiscoverStatus(r.data)'), 'Manual refresh uses identical terminal-status handling');
assert.ok(campaignProgress.includes('setDiscoverCampaign(null);setDiscoverPreview(null);setDiscoverRun(null);'), 'Completion dismisses popup without cancelling assessment');
console.log('PASS '+labels.length+' UI labels, 4 valid scripts, dynamic themes and safe Watchlist language sync');
