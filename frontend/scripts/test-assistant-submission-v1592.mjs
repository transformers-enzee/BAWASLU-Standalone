import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_acceptance_submissions.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const s of ['National Administrator','SUBMITTED_UNVERIFIED','REVISION_REQUESTED',
                'Independent reviewer required','legal_signoff','client_acceptance',
                'private, no-store','acceptance-submissions']){
  assert.ok(api.includes(s),s);
}
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.equal(v,'159.2');
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v159.2 restricted acceptance submission history and release parity');
