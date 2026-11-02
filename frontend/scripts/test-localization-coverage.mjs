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
labels.push('Add Candidate','AI-suggested candidates','Search existing candidates','Register an approved candidate','Approved candidate full name','＋ Create & Track Candidate','Engagement ranks accounts by summed reported engagement on captured posts, not by account popularity. Followers reflect reported account-level counts when supplied.');
for(const label of labels){
 assert.equal(typeof UI_LABEL_ID[label],'string','Missing ID translation: '+label);
 assert.notEqual(UI_LABEL_ID[label],label,'English label: '+label);
}
const scripts=['public/ui-freeze/bawaslu-interface-locale.js','public/ui-freeze/bawaslu-ui-translation-fallback.js','public/ui-freeze/smart-radar-live.js','public/ui-freeze/watchlist-live.js'];
for(const path of scripts)new Script(read(path),{filename:path});
const react=read('src/lib/UiLanguageLayer.jsx'),locale=read(scripts[0]);
const dashboard=read('public/ui-freeze/smart-radar-v6_2.html'),watch=read('public/ui-freeze/watchlist-v2_2.html');
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
assert.ok(read('public/ui-freeze/watchlist-live.js').includes("!$('#panel')?.classList.contains('open')"));
assert.ok(read('src/pages/Inbox.jsx').includes('hidden className="hidden" aria-label="AI operations and diagnostics"'));
assert.ok(read('src/pages/Inbox.jsx').includes('aria-label="Legacy intelligence records and administrative review"'));
console.log('PASS '+labels.length+' UI labels, 4 valid scripts, dynamic themes and safe Watchlist language sync');
