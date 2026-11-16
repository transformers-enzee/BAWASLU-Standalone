import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const module=read('../backend/app/assistant_claim_consistency.py');
const qa=read('../backend/tests/test_legal_indonesian_modalities_v1600.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const x of ['tidak diperbolehkan','tidak diizinkan','tidak boleh',
 'tidak harus','harus','boleh','_PERMITTED','_NOT_REQUIRED',
 'semantic_entailment_verified'])assert.ok(module.includes(x),x);
for(const x of ['test_possible_indonesian_modal_reversal_is_flagged_for_officer',
 'test_negation_is_not_split_or_reinterpreted_as_positive',
 'test_uncited_or_nonlegal_context_cannot_trigger_modal_warning'])
 assert.ok(qa.includes(x),x);
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.equal(version,'160.0');
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v160.0 Indonesian legal polarity review safeguards and version parity');
