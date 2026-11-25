import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const page=read('../src/pages/AssessmentQAWorkbench.jsx');
const advanced=read('../src/pages/AssessmentQADiagnostics.jsx');
const app=read('../src/App.jsx');
const admin=read('../src/pages/Administration.jsx');
const offline=read('../../backend/app/intelligence_assessment_qa.py');
const live=read('../../backend/app/intelligence_assessment_live_qa.py');
const main=read('../../backend/app/main.py');

assert.ok(app.includes('path="/administration/assessment-qa"'));
assert.ok(app.includes('path="/administration/assessment-qa/diagnostics"'));
assert.ok(admin.includes('to="/administration/assessment-qa"'));
assert.ok(main.includes('app.include_router(intelligence_assessment_qa_router)'));
assert.ok(main.includes('app.include_router(intelligence_assessment_live_qa_router)'));
for(const part of [
  'data-testid="intelligence-assessment-qa-workbench"',
  'AI Assessment Testing Centre',
  'data-testid="assessment-qa-synthetic-warning"',
  'data-testid="assessment-run-real-ai"',
  'data-testid="assessment-try-free-example"',
  'data-testid="assessment-qa-results"',
  'data-testid="assessment-developer-diagnostics"',
  'Needs improvement',
  'window.confirm',
  "mode==='real'",
])assert.ok(page.includes(part),'Missing simplified QA UI contract: '+part);
for(const part of ['data-testid="assessment-predictions-json"',
  'data-testid="assessment-compare"','data-testid="assessment-override-preview"'])
 assert.ok(advanced.includes(part),'Advanced JSON diagnostics were lost: '+part);
for(const part of ['def require_national_admin(db, user):',
  '"National Administrator"','"Nationwide"','BAWASLU_ASSESSMENT_QA_ENABLED',
  'def evaluate(case_id:','@router.get("/catalog")',
  '@router.post("/evaluate")','human_gold_labels','persistent_writes'])
 assert.ok(offline.includes(part),'Missing offline contract: '+part);
assert.ok(!/httpx|openai|db\\.add\\(|db\\.commit\\(/i.test(offline),
  'Offline synthetic assessment endpoint must remain no-provider/no-write');
for(const part of ['BAWASLU_ASSESSMENT_QA_LIVE_AI_ENABLED',
  'BAWASLU_ASSESSMENT_QA_LIVE_DAILY_LIMIT',
  'BAWASLU_ASSESSMENT_QA_LIVE_TOTAL_LIMIT',
  'pg_advisory_xact_lock','PAID_SYNTHETIC_QA_CALL_RESERVED',
  'reserve_attempt(db, user, body.case_id, cfg)',
  'require_national_admin(db, user)','@router.post("/run")',
  'max_completion_tokens','SYNTH-'])
 assert.ok(live.includes(part),'Missing bounded real-AI QA gate: '+part);
console.log('PASS v183.8 simplified officer QA, preserved diagnostics, optional bounded real-AI path');
