import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const quality=read('../backend/app/assistant_answer_quality.py');
const replay=read('../backend/app/assistant_full_answer_replay.py');
const qa=read('../backend/tests/test_assistant_full_answer_replay_v1607.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for (const x of ['formal_cited=sorted(formal.intersection(cited))',
 'social_cited=sorted(social.intersection(cited))','missing_citation_kinds',
 'selected-but-uncited','source_truth_verified=False'])assert.ok(quality.includes(x),x);
for(const x of ['run_full_answer_replay','real_model_responses_evaluated',
 'human_accuracy_measured','SYNTHETIC_PIPELINE_REGRESSION_ONLY'])assert.ok(replay.includes(x),x);
assert.ok(qa.includes('test_selected_but_uncited_formal_source_cannot_qualify_as_complete_comparison'));
const version=readBackendVersion(main);
assert.ok(Number(version.replace('.',''))>=1607);
assert.ok(hasDynamicBuildVersion(shell,version));
console.log('PASS v160.7 cross-module displayed-citation gating and full-answer replay');
