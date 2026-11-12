import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildAssistantReviewPacket} from '../src/lib/assistantReviewPacket.js';
import {parseReviewCsv,aggregateAssistantReviews,REVIEW_DIMENSIONS} from '../src/lib/assistantReviewAggregation.js';
import {blankOfficerScores,officerScoreCompletion,completedOfficerScoringCsv}
 from '../src/lib/assistantReviewScoring.js';
const answer={
 role:'assistant',text:'An unverified saved source requires officer verification. [SOCIAL-13]',
 records:[{record_id:'SOCIAL-13',record_type:'SOCIAL_LISTENING',source_url:'https://example.invalid/post/13',
 source_excerpt:'Sensitive source excerpt: DO_NOT_INCLUDE_IN_CSV'}],
 grounding:{grounding_audit:{displayed_citation_ids:['SOCIAL-13']},
  answer_quality:{checks:REVIEW_DIMENSIONS.map(id=>({id,status:'REVIEW_REQUIRED'}))}}
};
const packet=buildAssistantReviewPacket({
 question:'Examine original saved source [SOCIAL-13]',
 answer,exportedAt:'2026-11-12T00:00:00Z',buildVersion:'149.2'
});
const empty=blankOfficerScores();
assert.equal(officerScoreCompletion(packet,empty,'').ready,false);
const ratings=Object.fromEntries(REVIEW_DIMENSIONS.map(id=>
 [id,{score:'1',evidence_reference:'SOCIAL-13',reviewer_note:'Checked against original evidence.'}]));
const valid=officerScoreCompletion(packet,ratings,'officer_a');
assert.equal(valid.completed,4);
assert.equal(valid.ready,true);
const csv=completedOfficerScoringCsv(packet,ratings,'officer_a','2026-11-12T08:00:00.000Z');
const review=parseReviewCsv(csv);
assert.equal(review.entries.length,4);
assert.equal(review.entries[0].reviewer_id,'officer_a');
assert.equal(review.entries[0].date,'2026-11-12T08:00:00.000Z');
assert.equal(review.entries[0].evidence_reference,'SOCIAL-13');
assert.ok(!csv.includes('DO_NOT_INCLUDE_IN_CSV'));
const second=parseReviewCsv(completedOfficerScoringCsv(packet,ratings,'officer_b','2026-11-12T08:10:00.000Z'));
const combined=aggregateAssistantReviews([packet],[review,second]);
assert.equal(combined.dimension_stats[0].consensus_scored,1);
assert.equal(combined.client_acceptance_certified,false);
assert.equal(combined.identities_verified,false);
const missingRef={...ratings,source_relevance:{...ratings.source_relevance,evidence_reference:''}};
assert.equal(officerScoreCompletion(packet,missingRef,'officer_a').ready,false);
assert.throws(()=>completedOfficerScoringCsv(packet,missingRef,'officer_a','2026-11-12T08:00:00Z'),/evidence/i);
const malformed={...ratings,legal_uncertainty:{score:'N/A',evidence_reference:'',reviewer_note:'This dimension is not applicable.'}};
assert.equal(parseReviewCsv(completedOfficerScoringCsv(packet,malformed,'officer_a','2026-11-12T08:00:00Z')).entries.length,4);
assert.throws(()=>completedOfficerScoringCsv(packet,ratings,'bad id','2026-11-12T08:00:00Z'),/reviewer ID/);
assert.throws(()=>completedOfficerScoringCsv(packet,ratings,'officer_a','not-a-time'),/UTC/);
const risk={...ratings,citation_grounding:{score:'0',evidence_reference:'=SUM(1,1)',reviewer_note:'-Potential spreadsheet injection risk'}};
const protectedCsv=completedOfficerScoringCsv(packet,risk,'officer_a','2026-11-12T08:00:00Z');
assert.ok(protectedCsv.includes("'=SUM(1,1)"));
assert.ok(protectedCsv.includes("'-Potential spreadsheet injection risk"));
const source=readFileSync(new URL('../src/components/intel/AssistantHumanScoring.jsx',import.meta.url),'utf8');
const page=readFileSync(new URL('../src/pages/IntelligenceAssistant.jsx',import.meta.url),'utf8');
const main=readFileSync(new URL('../../backend/app/main.py',import.meta.url),'utf8');
const shell=readFileSync(new URL('../src/components/intel/Shell.jsx',import.meta.url),'utf8');
assert.ok(source.includes('assistant-human-scoring-export')&&
 source.includes('completedOfficerScoringCsv')&&source.includes('setConfirmed(false)'));
assert.ok(page.includes('<AssistantHumanScoring/>'));
const release=main.match(/'build_version':'(\d+\.\d+)'/)?.[1];
assert.ok(release&&shell.includes('data-build-version="'+release+'"')&&
 shell.includes('>v'+release+'</footer>'));
console.log('PASS offline independent scoring workbench, complete CSV exports, validation, formula hygiene and dynamic version alignment');
