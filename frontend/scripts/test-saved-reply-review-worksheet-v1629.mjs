import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createReviewEntry,exportReviewWorksheet} from '../src/lib/savedReplyReviewWorksheet.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const row={thread_id:'11111111-1111-4111-8111-111111111111',answer_message_index:1,
 status:'AUDITED',review_route:'REVIEW_CITATION_ATTRIBUTION'};
assert.throws(()=>createReviewEntry(row,'EVIDENCE_CHECKED_NO_FURTHER_ACTION',false),/Evidence review/);
assert.throws(()=>createReviewEntry({...row,status:'SOURCE_UNAVAILABLE'},'EVIDENCE_CHECKED_FOLLOWUP_NEEDED',true),/Evidence review/);
const entry=createReviewEntry(row,'EVIDENCE_CHECKED_FOLLOWUP_NEEDED',true);
const data=JSON.parse(exportReviewWorksheet([entry]));
assert.equal(data.entries[0].review_state,'EVIDENCE_CHECKED_FOLLOWUP_NEEDED');
assert.equal(data.human_accuracy,null);
assert.equal(data.formal_client_acceptance,false);
assert.equal(data.reviewer_identity_verified,false);
assert.equal(data.contains_answer_text,false);
assert.throws(()=>exportReviewWorksheet([entry,entry]),/Duplicate/);
assert.throws(()=>exportReviewWorksheet([{...entry,review_state:'FORGED_APPROVAL'}]),/Invalid review state/);
assert.throws(()=>exportReviewWorksheet([{...entry,original_evidence_checked:false}]),/Evidence review/);
const ui=read('src/components/intel/SavedReplyReviewWorksheet.jsx');
const parent=read('src/components/intel/AssistantSavedReplyAudit.jsx');
for(const s of ['self-attestation','export-saved-reply-review-worksheet','EVIDENCE_CHECKED_'])
 assert.ok(ui.includes(s),s);
assert.ok(parent.includes('SavedReplyReviewWorksheet'));
assert.ok(read('src/components/intel/Shell.jsx').includes('data-build-version="162.9"'));
console.log('PASS v162.9 local review worksheet: attestation, boundaries, sanitized export');
