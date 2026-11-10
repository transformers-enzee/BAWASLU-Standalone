import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 correctedSentimentPost,overlaySentimentCorrections,sentimentCorrectionKey
} from '../src/lib/sentimentFeedState.js';

const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const captured=read('src/components/intel/CapturedPostList.jsx');
const correction=read('src/components/intel/SentimentCorrection.jsx');
const inbox=read('src/pages/Inbox.jsx');
const globalTranslation=read('src/lib/UiLanguageLayer.jsx');

// An officer correction must update the displayed sentiment immediately,
// including the badge/icon (both are derived from the same React row).
const posts=[
 {id:'739',sentiment:'Negative',text_content:'Source 739'},
 {id:'740',sentiment:'Negative',text_content:'Source 740'}
];
const saved={sentiment:'NEUTRAL',correction_id:91,actor_id:5,rationale:'',corrected_at:'2026-11-10T02:00:00Z'};
const initial=correctedSentimentPost(posts[0],saved);
assert.equal(initial.sentiment,'NEUTRAL');
assert.equal(initial.sentiment_correction.correction_id,91);
assert.equal(initial.sentiment_details.status,'OFFICER_CORRECTED');
assert.equal(posts[0].sentiment,'Negative','the original fetched source stays unchanged');

const amendments=new Map([[sentimentCorrectionKey('18','739'),saved]]);
const firstPage=overlaySentimentCorrections(posts,18,amendments);
assert.equal(firstPage[0].sentiment,'NEUTRAL');
assert.equal(firstPage[1].sentiment,'Negative');
assert.equal(firstPage.length,2);
// A background page still carrying old AI classification must not overwrite
// the officer correction after the save has already succeeded.
const nextPage=overlaySentimentCorrections([...posts,{id:'741',sentiment:'Positive'}],18,amendments);
assert.equal(nextPage[0].sentiment,'NEUTRAL');
assert.equal(nextPage[2].sentiment,'Positive');
assert.equal(overlaySentimentCorrections(posts,19,amendments)[0].sentiment,'Negative',
 'corrections are campaign-specific');
assert.deepEqual(overlaySentimentCorrections([],18,amendments),[]);
const updated=new Map(amendments);
updated.set(sentimentCorrectionKey('18','739'),{...saved,sentiment:'POSITIVE',correction_id:92});
assert.equal(overlaySentimentCorrections(posts,18,updated)[0].sentiment,'POSITIVE',
 'subsequent changes must supersede the previous correction');

// This component supplies its own English/Indonesian React labels. The
// global DOM translation layer mutates text nodes and can leave stale labels
// like Negative beside the newly rendered Neutral icon. Exclude it entirely.
assert.ok(globalTranslation.includes("'[data-i18n-exempt]'"),'global translation exclusion exists');
assert.ok(captured.includes('return <section data-i18n-exempt'),
 'Captured Posts text and counts must be controlled exclusively by React');
assert.ok(correction.includes('data-i18n-exempt'),
 'correction form must opt out of external text mutation');
assert.ok(inbox.includes('selected.sentiment_correction&&<p data-i18n-exempt'),
 'Inbox correction status must be React-owned');
assert.ok(captured.includes('overlaySentimentCorrections(all,campaignId,savedCorrections.current)'),
 'progressively loaded feeds retain saved correction labels');
assert.ok(captured.includes('onCorrected={correction=>onCorrectionSaved(post,correction)}'),
 'onSaved must update the live card without refreshing the page');
assert.ok(captured.includes("const [Icon,color,name]=sentiment==='positive'"),
 'icon, color and label must derive from the corrected sentiment');
console.log('PASS immediate sentiment correction UI synchronization and pagination regression');
