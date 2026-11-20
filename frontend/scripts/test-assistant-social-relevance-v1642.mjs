import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/assistant_evidence_relevance.py');
const social=read('../backend/app/assistant_orchestration.py');
for(const t of ['def social_source_term_score','content=_words(body)',
 'direct=sum(20 for t in q','secondary=sum(3 for t in q']) assert.ok(helper.includes(t),t);
assert.ok(social.includes('topical_score=social_source_term_score('));
assert.ok(social.includes('if terms and topical_score==0:'));
assert.ok(social.includes('if 0<=age<=45:score+=3'));
assert.ok(!social.includes('metadata_hits=sum(1 for t in terms'));
assert.ok(!social.includes('if 0<=age<=45:score+=14'));
assert.ok(social.includes('if not exact_social_selection_complete(question,chosen,limit):'));
const version=readBackendVersion(read('../backend/app/main.py'));
assert.ok(Number(version.replace('.',''))>=1642);
assert.ok(hasDynamicBuildVersion(read('src/components/intel/Shell.jsx'),version));
console.log('PASS v164.2 exact-term social source relevance, recency bounds, missing-ID guard');
