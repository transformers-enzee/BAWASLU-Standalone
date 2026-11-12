import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const endpoint=read('../backend/app/assistant_eval_sampling.py');
const assistant=read('../backend/app/assistant_orchestration.py');
const api=read('../backend/app/main.py');
const panel=read('src/components/intel/AssistantEvaluationSampler.jsx');
const page=read('src/pages/IntelligenceAssistant.jsx');
const browser=read('e2e/assistant-knowledge-library.spec.js');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(endpoint.includes('def build_evaluation_question_plan'),
 'Deterministic source sampling must be implemented');
assert.ok(endpoint.includes('live_inbox_findings(db,principal)')&&
 endpoint.includes('has(principal,"view_intelligence")'),
 'Sample from authorized, cached Inbox only');
assert.ok(endpoint.includes('source_record_id')&&
 endpoint.includes('statistically_representative":False')&&
 endpoint.includes('window_completeness_verified":False'),
 'Never claim an exhaustive or random sample');
assert.ok(endpoint.includes('new_social_crawls":0')&&
 endpoint.includes('paid_ai_calls":0')&&
 endpoint.includes('database_writes":0'),
 'Sampler never calls crawling, AI or writes DB');
assert.ok(assistant.includes('exact_ids=set(re.findall')&&
 assistant.includes('return chosen[:limit],len(exact)'),
 'Explicit saved source IDs cannot drift to unrelated posts');
assert.ok(api.includes('explicit_social_id=bool')&&
 api.includes("not evidence and requested=='AUTO' and not explicit_social_id"),
 'An inaccessible exact source must not trigger GPT general fallback');
assert.ok(panel.includes('assistant-evaluation-sampler-result')&&
 panel.includes('Prepare questions (no AI call)')&&
 panel.includes('Use question (do not send)'),
 'Preparation is deliberate and must not execute a paid question');
assert.ok(page.includes('<AssistantEvaluationSampler')&&
 page.includes("setAnalysisMode('DATA')")&&
 page.includes('setQuestion(prompt)'),
 'Selected question is staged in DATA mode without auto execution');
assert.ok(browser.includes('Assistant prepares real-source evaluation questions without calling the AI model')&&
 browser.includes('Assistant evaluation preparation does not reveal sources without authorization'),
 'Playwright tests verify no implicit model call and denial');
const apiVersion=api.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const uiVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(apiVersion&&apiVersion===uiVersion,'Backend/UI build versions must match');
console.log('PASS v148.8 permission-scoped source sampling, exact-ID retrieval, no-credits preparation and coverage caveats');
