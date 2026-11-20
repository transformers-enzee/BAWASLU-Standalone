import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const packageText=read('package.json');
const config=JSON.parse(packageText);
const commands=config.scripts.build.matchAll(/node scripts\/([\w.-]+\.mjs)/g);
const names=[...commands].map(x=>x[1]);
assert.ok(names.includes('test-finding-source-review-v1533.mjs'));
assert.ok(names.includes('test-finding-casework-progress-v1534.mjs'));
const vulnerable=/assert\.(?:equal|strictEqual)\(\s*(?:v|bv|version|buildVersion)\s*,\s*['"](?:153\.[0-9]+)['"]/;
for(const name of names){
 const content=read('scripts/'+name);
 assert.ok(!vulnerable.test(content),'Pinned application build version in active QA script: '+name);
}
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
const backend=main.match(/'build_version':os\.getenv\('BAWASLU_BUILD_VERSION','([0-9]+\.[0-9]+)'\)/)?.[1];
assert.ok(backend,'Backend must expose an image-supplied build version');
assert.ok(shell.includes("fetch('/api/health'"),'UI must load the actual deployed version');
assert.ok(shell.includes("data-build-version={buildInfo.build_version"),'Review export version must use backend metadata');
assert.ok(!shell.includes('v173.1'),'Stale static build label must be removed');
const [major,minor]=backend.split('.').map(Number);
assert.ok(major>153||(major===153&&minor>=5),'v153.5 or later required');
console.log('PASS v153.5 future-safe feature QA version contracts and frontend/backend parity');
