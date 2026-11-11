import assert from 'node:assert/strict';
import {deduplicateInboxEvidence, normalizedEvidenceText} from '../src/lib/inboxExactDedup.js';

const story='Bawaslu menerima laporan mengenai dugaan pelanggaran pemilu dan meminta pemeriksaan bukti lebih lanjut oleh penyidik.';
const items=[
  {id:'205',campaign_id:'1',platform:'instagram',text_content:'  '+story+'\n',is_flagged:false},
  {id:'155',campaign_id:'1',platform:'tiktok',text_content:story,is_flagged:false}
];
assert.equal(normalizedEvidenceText(items[0].text_content),normalizedEvidenceText(items[1].text_content));
assert.deepEqual(deduplicateInboxEvidence(items).map(x=>x.id),['155'],
  'A duplicate TikTok/Instagram news story must display only once');
assert.equal(deduplicateInboxEvidence([...items,{...items[1],id:'220',campaign_id:'2'}]).length,2,
  'Different campaigns retain their own assessment scope');
assert.equal(deduplicateInboxEvidence([...items,{...items[1],id:'222',text_content:story+' Updated.'}]).length,2,
  'Modified substantive content is not an exact duplicate');
assert.equal(deduplicateInboxEvidence([...items,{...items[0],id:'250',flag_review_status:'FURTHER_INVESTIGATION'}])[0].id,'250',
  'Officer-reviewed duplicate source remains the displayed representative');
assert.equal(deduplicateInboxEvidence([{id:'1',text_content:''},{id:'2',text_content:''}]).length,2,
  'Unverifiable empty content is never merged');
assert.equal(deduplicateInboxEvidence([{id:'1',text_content:'Thank you'},{id:'2',text_content:'Thank you'}]).length,2,
  'Short identical reactions remain separate');
console.log('Inbox exact-content dedup: 7 checks passed');
