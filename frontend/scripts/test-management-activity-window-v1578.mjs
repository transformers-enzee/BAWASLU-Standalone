import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['def _activity_period_window','start,end,topic=_activity_period_window(access,period,topic)',
'Audit window start UTC','Audit window end UTC','Latest report status observed UTC',
'X-Report-Window-Start-UTC','X-Report-Window-End-UTC'])
 assert.ok(api.includes(key),key);
const section=api.slice(api.indexOf('def briefing_activity_csv('),api.indexOf('@router.get("/officer-pilot.csv")'));
assert.ok(!section.includes('scoped_cases('),'Activity export must not load case-creation cohort');
assert.ok(section.includes('_casework_activity_window'));
const back=main.split("'build_version':'")[1]?.split("'")[0];
const client=shell.split('data-build-version="')[1]?.split('"')[0];
assert.equal(back,client);assert.ok(Number(back.replace('.',''))>=1578);
console.log('PASS v157.8 Activity CSV window provenance and reduced DB reads');
