import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const grounding=read('../backend/app/assistant_grounding.py');
const audit=read('../backend/app/assistant_eval_sampling.py');
const qa=read('../backend/tests/test_historical_citation_budget_v1625.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const token of ['language="id", citation_limit=12','citation_limit=max(1,min(int(citation_limit),20))'])
 assert.ok(grounding.includes(token),token);
for(const token of ['citation_limit=20','"audit_citation_reference_limit":20',
 '"normal_assistant_citation_reference_limit":12','"audit_does_not_rewrite_original_answer":True'])
 assert.ok(audit.includes(token),token);
for(const token of ['test_normal_assistant_still_limits_display_to_twelve_citations',
 'test_read_only_citation_reconciliation_preserves_nineteen',
 'test_unavailable_historical_reference_is_not_accepted_even_with_wider_budget'])
 assert.ok(qa.includes(token),token);
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1625);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v162.5 read-only historical citation scope without relaxing ordinary answer limits');
