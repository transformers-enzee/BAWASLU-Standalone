import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const ui=read('../src/pages/AssessmentQAWorkbench.jsx');
const app=read('../src/App.jsx');
const administration=read('../src/pages/Administration.jsx');
const backend=read('../../backend/app/intelligence_assessment_qa.py');
const main=read('../../backend/app/main.py');

assert.ok(app.includes('path="/administration/assessment-qa"'));
assert.ok(app.includes('AssessmentQAWorkbench'));
assert.ok(administration.includes('to="/administration/assessment-qa"'));
assert.ok(main.includes('app.include_router(intelligence_assessment_qa_router)'));
for(const part of [
  'data-testid="intelligence-assessment-qa-workbench"',
  'data-testid="assessment-qa-synthetic-warning"',
  'data-testid="assessment-predictions-json"',
  'data-testid="assessment-compare"',
  'data-testid="assessment-qa-results"',
  'data-testid="assessment-override-preview"',
  'BAWASLU_ASSESSMENT_QA_ENABLED=1',
  'does not invoke an AI model',
])assert.ok(ui.includes(part),'Missing QA workbench UI contract: '+part);
for(const part of [
  'def require_national_admin(db, user):',
  '"National Administrator"',
  '"Nationwide"',
  'has(grant, "administration")',
  'BAWASLU_ASSESSMENT_QA_ENABLED',
  'def evaluate(case_id:',
  '@router.get("/catalog")',
  '@router.post("/evaluate")',
  'human_gold_labels',
  'persistent_writes',
  'paid_model_called',
])assert.ok(backend.includes(part),'Missing backend QA contract: '+part);
assert.ok(!/httpx|openai|db\.add\(|db\.commit\(/i.test(backend),
  'Read-only synthetic assessment endpoints must never call providers or write records');
console.log('PASS v183.6 assessment QA workbench: admin boundary, offline evaluation, and no-provider/no-write guard');
