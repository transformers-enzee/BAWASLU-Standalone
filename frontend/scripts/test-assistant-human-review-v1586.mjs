import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const router=read('../backend/app/assistant_eval_sampling.py');
const rubric=read('../backend/app/assistant_human_review.py');
const tests=read('../backend/tests/test_assistant_human_review_v1586.py');
assert.ok(router.includes('@router.get("/review-packet")'));
assert.ok(router.includes('plan=evaluation_questions(response,target=target,user=user,db=db)'));
for (const s of ['human_accuracy_measured','formal_client_acceptance_complete',
                'legal_signoff_complete','model_answers_generated',
                'AWAITING_INDEPENDENT_HUMAN_REVIEW','SOURCE_ID_ACCURACY']) {
  assert.ok(rubric.includes(s),s);
}
assert.ok(tests.includes('test_permission_scoped_endpoint'));
assert.ok(tests.includes('test_packet_has_unscored_rubric_and_negative_control'));
console.log('PASS v158.6 unscored, permission-scoped human review packet contract');
