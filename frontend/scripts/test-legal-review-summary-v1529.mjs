import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildAssistantReviewPacket} from '../src/lib/assistantReviewPacket.js';

const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const ui=read('src/pages/IntelligenceAssistant.jsx');
const component=read('src/components/intel/AssistantLegalReviewSummary.jsx');
assert.ok(ui.includes('AssistantLegalReviewSummary summary={m.grounding?.answer_quality?.legal_review_summary}'));
assert.ok(ui.includes('data-testid="assistant-legal-detailed-warnings"'));
assert.ok(ui.includes('open={!m.grounding?.answer_quality?.legal_review_summary?.applicable}'));
assert.ok(component.includes('data-testid="assistant-legal-review-priorities"'));
assert.ok(component.includes('data-testid="assistant-legal-review-more"'));
assert.ok(component.includes('not violation severity'));
assert.ok(component.includes('No automatic legal conclusions'));
const answer={role:'assistant',text:'Must report [DOC-1-P1].',response_profile:'PDF_GUIDANCE',
 records:[{record_id:'DOC-1-P1',record_type:'PDF_KNOWLEDGE',source_excerpt:'test'}],
 grounding:{grounding_audit:{displayed_citation_ids:['DOC-1-P1']},answer_quality:{
  checks:[],legal_review_summary:{applicable:true,issues:[
    {code:'PASSAGE_POLARITY',priority:'P1',source_ids:['DOC-1-P1','DOC-9-P9'],signal_count:2,private_note:'SECRET_LEAK'},
    {code:'SOURCE_RELEVANCE',priority:'P2',source_ids:['DOC-1-P1'],signal_count:1}
  ],private_note:'SECRET_LEAK'}
 }}
};
const packet=buildAssistantReviewPacket({question:'Which law applies?',answer,exportedAt:'2026-11-13T04:00:00Z'});
assert.equal(packet.legal_review_snapshot.issues.length,2);
assert.deepEqual(packet.legal_review_snapshot.issues[0].source_ids,['DOC-1-P1']);
assert.ok(!JSON.stringify(packet).includes('SECRET_LEAK'));
assert.equal(packet.officer_approved,false);
assert.equal(packet.legal_review_snapshot.legal_findings_confirmed,false);
assert.equal(packet.human_scorecard.checks.length,4,'Four legacy rubric dimensions unchanged');
const nonlegal=buildAssistantReviewPacket({question:'General summary',answer:{...answer,grounding:{...answer.grounding,answer_quality:{checks:[]}}}});
assert.equal(nonlegal.legal_review_snapshot,null);
console.log('PASS v152.9 consolidated legal review UI and export-minimization contracts');
