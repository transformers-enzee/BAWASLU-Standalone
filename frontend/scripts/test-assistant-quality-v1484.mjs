import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const module=read('../backend/app/assistant_answer_quality.py');
const tests=read('../backend/tests/test_assistant_answer_quality_v1484.py');
const cases=JSON.parse(read('../backend/tests/fixtures/assistant_answer_readiness_v1484.json'));
const app=read('../backend/app/main.py');
const ui=read('src/pages/IntelligenceAssistant.jsx');
const e2e=read('e2e/assistant-knowledge-library.spec.js');
const shell=read('src/components/intel/Shell.jsx');

assert.ok(module.includes('def evaluate_answer_quality'), 'Zero-credit QA evaluator exists');
assert.ok(module.includes('citation_grounding')&&module.includes('source_relevance')&&
 module.includes('legal_uncertainty')&&module.includes('cross_module_consistency'),
 'All four quality-check dimensions are present');
assert.ok(module.includes('"human_accuracy":None')&&module.includes('"human_gold_answers_evaluated":0'),
 'Heuristic checks must not invent measured human accuracy');
assert.ok(module.includes('semantic_entailment_verified":False')&&
 module.includes('claim_truth_verified":False'),'Source text overlaps are not factual proof');
assert.ok(module.includes('conflicts=[sid')&&module.includes('duplicate_sentiment_conflicts'),
 'Contradictory duplicate saved social labels require review');
assert.ok(cases.fixture_type.startsWith('SYNTHETIC_')&&cases.cases.length===16,
 'Fixture suite contains 16 transparent synthetic cases');
assert.ok(cases.cases.some(c=>c.case_id==='missing_formal_comparison')&&
 cases.cases.some(c=>c.case_id==='reviewed_law_currentness')&&
 cases.cases.some(c=>c.case_id==='duplicate_sentiment_conflict'),
 'Cross-module, legal-currency and sentiment scenarios are covered');
assert.ok(tests.includes('def test_synthetic_answer_quality_acceptance'),
 'Fixtures are executed by backend pytest');
assert.ok(app.includes('evaluate_answer_quality(')&&app.includes("'answer_quality':answer_quality"),
 'Assistant endpoint returns quality readiness separately from source integrity');
assert.ok(ui.includes('data-testid="assistant-answer-quality"')&&
 ui.includes('Rule-based checks, not an accuracy score or human validation.'),
 'Visible QA does not claim factual accuracy');
assert.ok(e2e.includes('Assistant shows four answer readiness checks without claiming human accuracy'),
 'Browser QA exercises the check states');
const apiVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const uiVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(apiVersion&&/^\d+\.\d+$/.test(apiVersion),'Build version format is valid');
assert.equal(uiVersion,apiVersion);
console.log('PASS v148.4 Assistant answer-quality readiness, curated synthetic challenge fixtures, cross-module caveats and version contract');
