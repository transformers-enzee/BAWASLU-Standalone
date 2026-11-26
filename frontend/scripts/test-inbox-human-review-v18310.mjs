import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const inbox=read('../src/pages/Inbox.jsx');
const main=read('../../backend/app/main.py');
const docker=read('../../Dockerfile');

for(const fragment of [
 'data-testid="inbox-pending-human-review-filter"',
 "if(view==='review'&&!needsOfficerReview(x))return false",
 'data-testid="inbox-source-review-card"',
 'data-testid="inbox-review-ai-assessment"',
 'onClick={()=>openAssessmentPost(item,true)}',
 'data-testid="inbox-toggle-review-centre"',
 'data-testid="inbox-human-review-centre"',
 'Review AI Assessment · officer checklist',
 'no overall approval button',
 'Original source provenance',
 'Officer topic / Public Concerns correction',
 'Human flag review',
 'SentimentCorrection',
 "action:'campaignFlagReview'",
 "action:'campaignOfficerClassificationCorrection'",
 'role="dialog"',
])assert.ok(inbox.includes(fragment),'Missing human review feature: '+fragment);

for(const anchor of ['evidence','assessment','sentiment','jurisdiction','classification','flag']){
 assert.ok(inbox.includes('id="inbox-human-review-'+anchor+'"'),'Missing review section '+anchor);
}
assert.equal((inbox.match(/data-testid="inbox-review-ai-assessment"/g)||[]).length,1);
assert.ok(inbox.includes('needsOfficerReview=item=>'));
assert.ok(inbox.includes("['FLAG_CONFIRMED','FLAG_DISMISSED']"));
assert.ok(inbox.includes('selected.can_review_flag'), 'Officer permissions must continue to gate review');
assert.ok(inbox.includes('reviewRationale.trim().length<10'), 'Existing rationale guard must remain');
assert.ok(inbox.includes('selected.assessment_version'), 'Existing version-aware review must remain');
assert.ok(inbox.includes('acknowledgedReview.current'), 'Saved review state must not be overwritten by stale response');

// Validate version parity without pinning the test to a previous release.
const dockerVersion=docker.match(/^ARG BAWASLU_BUILD_VERSION=([0-9]+[.][0-9]+)$/m)?.[1];
const backendVersion=main.match(/'build_version':os[.]getenv[(]'BAWASLU_BUILD_VERSION','([0-9]+[.][0-9]+)'[)]/)?.[1];
assert.ok(dockerVersion,'Docker build version is required');
assert.ok(backendVersion,'Backend fallback build version is required');
assert.equal(backendVersion,dockerVersion,'Docker and backend versions must match');
console.log('PASS v183.10: visible Human Review Centre, saved review guards, navigation and release identity');
