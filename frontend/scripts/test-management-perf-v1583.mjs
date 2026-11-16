import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const perf=read('../backend/app/management_perf.py');
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
for(const key of ['BAWASLU_REPORT_PERF_ENABLED','National Administrator',
 'SINGLE_READ_ONLY_SAMPLE_NOT_P95','contains_case_or_report_text',
 'query_count_includes_profile_lookup']) assert.ok(api.includes(key),key);
for(const key of ['event.listen(conn','event.remove(conn',
 'after_cursor_execute','perf_counter'])assert.ok(perf.includes(key),key);
const b=main.split("'build_version':'")[1]?.split("'")[0];
const f=shell.split('data-build-version="')[1]?.split('"')[0];
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1583);
console.log('PASS v158.3 safe administrator-only opt-in reporting probe');
