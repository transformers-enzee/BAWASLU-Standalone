import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const template=read('../backend/app/management_report_templates.py');
const reporting=read('../backend/app/management_reporting.py');
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
for(const key of ['Historical report versions (not approvals)','Historical returned versions',
 'Cases approved after a return','Latest reports awaiting revision',
 '"report_version_integrity":revision_integrity'])assert.ok(template.includes(key),key);
for(const key of ['"Latest report status"', '"Latest report ID"',
 '"Stored report versions"', '"Superseded report versions"',
 'version_counts=Counter(r.case_id for r in reports)'])assert.ok(reporting.includes(key),key);
const b=readBackendVersion(main),f=readShellVersion(shell);
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1572);
console.log('PASS v157.2 cross-format management export latest-report/version integrity');
