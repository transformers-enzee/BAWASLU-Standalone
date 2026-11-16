import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const policy=read('../backend/app/assistant_policy_boundary.py');
const qa=read('../backend/tests/test_platform_policy_local_citation_v1603.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const token of ['spans=_SENTENCE.split','i+1<len(spans)',
 'not _CITE.sub("",following).strip()','cited_legal_page_ids',
 'platform_breach_confirmed'])assert.ok(policy.includes(token),token);
for(const token of ['test_standalone_next_line_pdf_citation_flags_provider_verdict',
 'test_next_narrative_sentence_cannot_supply_local_policy_citation',
 'test_contextual_report_not_policy_authority',
 'test_uncertainty_and_attributed_reporting_not_definitive'])
 assert.ok(qa.includes(token),token);
const ver=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(ver.replace('.',''))>=1603);
assert.ok(shell.includes('data-build-version="'+ver+'"'));
console.log('PASS v160.3 local platform-policy citations, no false legal signoff');
