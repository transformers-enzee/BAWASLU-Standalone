import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const main=read('../../backend/app/main.py');
const docker=read('../../Dockerfile');
const earlier=['test-assistant-operational-brief-v17569.mjs','test-assistant-officer-actions-v17570.mjs'];
const backendVersion=main.match(/BAWASLU_BUILD_VERSION','(\\d+\\.\\d+)'/);
const dockerVersion=docker.match(/ARG BAWASLU_BUILD_VERSION=(\\d+\\.\\d+)/);
assert.ok(backendVersion&&dockerVersion&&backendVersion[1]===dockerVersion[1]);
assert.ok(Number(backendVersion[1])>=175.71);
for(const path of earlier){
 const test=read('./'+path);
 assert.ok(test.includes('Number(buildVersion[1])>=175.'));
 assert.ok(!test.includes('metadata.includes("\'BAWASLU_BUILD_VERSION\',\'175.'));
 assert.ok(!test.includes('backend.includes("\'BAWASLU_BUILD_VERSION\',\'175.'));
}
console.log('BAWASLU v175.71: release metadata and forward-compatible tests pass');
