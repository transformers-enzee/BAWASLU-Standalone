import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const report=read('../backend/app/management_reporting.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
const group=report.split('def _casework_activity_window(')[1].split('def _report_version_integrity(')[0];
assert.ok(group.includes('.options(load_only('));
for(const field of ['CaseAssignment.id','CaseAssignment.title','CaseAssignment.created_by',
 'CaseAssignment.originating_province','CaseAssignment.target_province',
 'CaseAssignment.verified_province','CaseAssignment.source_excerpt'])
 assert.ok(group.includes(field),field);
for(const field of ['CaseAssignment.notes','CaseAssignment.tags_json',
 'CaseAssignment.suggested_provinces_json','CaseAssignment.updated_at'])
 assert.ok(!group.includes(field),field);
const b=readBackendVersion(main);
const f=readShellVersion(shell);
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1582);
console.log('PASS v158.2 scoped activity projection and scaling benchmark contract');
