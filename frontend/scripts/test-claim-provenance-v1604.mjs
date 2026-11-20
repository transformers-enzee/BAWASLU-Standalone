import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const provenance=read('../backend/app/assistant_claim_provenance.py');
const policy=read('../backend/app/assistant_policy_boundary.py');
const quality=read('../backend/app/assistant_answer_quality.py');
const summary=read('../backend/app/assistant_legal_review_summary.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['FORMAL_DECISION_CITED_ONLY_TO_SOCIAL_POSTS','SOCIAL_LISTENING',
 'formal_decision_verified','semantic_entailment_verified','_FORMAL_ID','_FORMAL_EN'])
 assert.ok(provenance.includes(key),key);
assert.ok(!policy.includes('if not (grounding or {}).get("legal_question"):\n        return base'));
assert.ok(quality.includes('evaluate_claim_provenance'));
assert.ok(quality.includes('"formal_outcome_source_provenance":claim_provenance'));
assert.ok(summary.includes('FORMAL_OUTCOME_SOCIAL_ONLY'));
const v=readBackendVersion(main);
assert.ok(Number(v.replace('.',''))>=1604);
assert.ok(hasDynamicBuildVersion(shell,v));
console.log('PASS v160.4 source-type provenance and platform-only question boundaries');
