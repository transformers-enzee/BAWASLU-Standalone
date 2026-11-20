import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const server=read('../backend/app/casework.py');
const ui=read('src/pages/Casework.jsx');
const shell=read('src/components/intel/Shell.jsx');
const main=read('../backend/app/main.py');
for(const key of ['REPORT_REVISION_DRAFTED','revised_from_report_id',
  'status="DRAFT",created_by=user.id','report.status!="DRAFT"'])
 assert.ok(server.includes(key),key);
for(const key of ['returned-report-revision-required',
  'Save revised draft as new version',"r.status==='DRAFT'&&<button"])
 assert.ok(ui.includes(key),key);
const bv=readBackendVersion(main);
const fv=readShellVersion(shell);
assert.ok(bv&&bv===fv);
console.log('PASS v156.6 returned report versioning and submission safeguards');
