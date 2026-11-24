import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const app=read('../src/App.jsx');
const nav=read('../src/components/intel/AccessNavigation.jsx');
const page=read('../src/pages/OfficerDecisionAssistant.jsx');
const main=read('../../backend/app/main.py');
const api=read('../../backend/app/officer_action_v3/api.py');
const readResearch=read('../../backend/app/officer_action_v3/research.py');
const claims=read('../../backend/app/officer_action_v3/claims.py');
const legal=read('../../backend/app/officer_action_v3/legal.py');
const quality=read('../../backend/app/officer_action_v3/quality.py');
const decide=read('../../backend/app/officer_action_v3/decisions.py');
const docker=read('../../Dockerfile');
for(const x of ['OfficerDecisionAssistant','/ai-assistant-v2-new','/management/ai-assistant-v2-new'])
 assert.ok(app.includes(x),'App route missing '+x);
assert.ok(nav.includes("['/ai-assistant-v2-new','AI Assistant V2 · New'"));
assert.ok(nav.includes("['/management/ai-assistant-v2-new','AI Assistant V2 · New'"));
assert.ok(nav.indexOf("['/ai-assistant','AI Assistant'")<
          nav.indexOf("['/ai-assistant-v2-new','AI Assistant V2 · New'"));
for(const x of ['officer-v3-page','officer-v3-source-modes','officer-v3-result',
                'officer-v3-research-trail','officer-v3-claims',
                'officer-v3-actions','officer-v3-work-products','/api/officer-decision-ai/analyze',
                'WEB_ONLY','WEB_AND_RECORDS','RECORDS_ONLY','Evidence matrix','Legal brief',
                'Leadership memo','SOURCE_STATUS','SAVED_SNAPSHOT'])
 assert.ok(page.includes(x),'new UI missing '+x);
assert.ok(!page.includes('AIAssistantV2')&&!page.includes('IntelligenceAssistant.jsx'),
  'New page must not import old assistants');
assert.ok(main.includes('app.include_router(officer_decision_ai_router)'));
assert.ok(api.includes('if mode!="WEB_ONLY"')&&api.includes('if mode!="RECORDS_ONLY"'));
assert.ok(api.indexOf('public=public_research(')<api.indexOf('internal=saved_records('));
assert.ok(api.includes('OFFICER_DECISION_AI_INDEPENDENT_V3'));
assert.ok(!/(?:from|import)\s+(?:app\.)?(?:assistant_|ai_assistant_v2)/.test(api),
 'New API must never import prior assistant implementations');
assert.ok(readResearch.includes('tool_choice')&&readResearch.includes('"required"'));
assert.ok(readResearch.includes('read_page')&&readResearch.includes('global_dns'));
assert.ok(claims.includes('INDEPENDENTLY_CORROBORATED'));
assert.ok(legal.includes('officer_review_required'));
assert.ok(quality.includes('actions_executed')&&quality.includes('human_approval_required'));
assert.ok(decide.includes('text')&&decide.includes('json_schema')&&decide.includes('source_ids'));
const version=main.match(/BAWASLU_BUILD_VERSION','(\d+\.\d+)'/)?.[1];
assert.ok(version && /^[0-9]+[.][0-9]+$/.test(version),'Missing build version');
const [major,minor]=version.split('.').map(Number);
assert.ok(major>178||(major===178&&minor>=6),'Independent assistant minimum build is v178.6');
assert.ok(docker.includes('ARG BAWASLU_BUILD_VERSION='+version),'Docker/app build labels differ');
assert.ok(docker.includes('tests/test_officer_decision_v1785.py'));
console.log('PASS v178.6 independent third AI assistant, new API, separate research, legal, decision, UI and data guards');
