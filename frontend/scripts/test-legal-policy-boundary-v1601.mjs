import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const audit=read('../backend/app/assistant_grounding.py');
const quality=read('../backend/app/assistant_answer_quality.py');
const summary=read('../backend/app/assistant_legal_review_summary.py');
const boundary=read('../backend/app/assistant_policy_boundary.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(audit.includes('next_span=spans[i+1].strip()'));
assert.ok(audit.includes('citations=[ref for ref in dict.fromkeys(next_refs)'));
assert.ok(quality.includes('evaluate_policy_boundary'));
assert.ok(quality.includes('"platform_policy_legal_boundary":policy_boundary'));
assert.ok(summary.includes('PLATFORM_POLICY_BOUNDARY'));
for(const s of ['platform_breach_confirmed','current_platform_policy_verified',
 'PLATFORM_VERDICT_CITED_TO_ELECTORAL_LEGAL_REFERENCE'])
 assert.ok(boundary.includes(s),s);
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1601);assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v160.1 claim-local article and platform-vs-law attribution contracts');
