import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const q=api.split('def scoped_cases(')[1].split('def _utc_publication_time(')[0];
assert.ok(q.includes('options(load_only('));
for(const k of ['CaseAssignment.source_excerpt','CaseAssignment.verified_province',
'CaseAssignment.originating_scope','CaseAssignment.target_scope','CaseAssignment.created_by'])
 assert.ok(q.includes(k),k);
for(const k of ['CaseAssignment.notes','CaseAssignment.tags_json',
'CaseAssignment.suggested_provinces_json','CaseAssignment.updated_at'])
 assert.ok(!q.includes(k),k);
const b=readBackendVersion(main);
const f=readShellVersion(shell);
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1581);
console.log('PASS v158.1 lightweight management case cohort contract');
