import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const focus=read('../backend/app/assistant_assessment_focus.py'),gen=read('../backend/app/assistant_orchestration.py');
for(const t of ['assessment_scope','assessment_instruction','assessment_authority_inventory',
'MIXED_LEGAL_AND_PLATFORM','LEGAL_ONLY','PLATFORM_ONLY','OBSERVED RECORD','POSSIBLE RULE',
'EVIDENCE GAPS','OFFICER NEXT CHECK','"official_policy_currentness_verified":False'])
 assert.ok(focus.includes(t),t);
for(const t of ['operational_assessment_scope','operational_assessment_authority_inventory',
'assessment_focus=assessment_instruction','assessment_focus if assessment_focus else'])
 assert.ok(gen.includes(t),t);
const api=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=api.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1638);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v163.8 differentiated legal/platform assessment question instructions');
