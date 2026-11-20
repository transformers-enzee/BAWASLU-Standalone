import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const shared=read('../backend/app/monitoring_count_integrity.py');
const cc=read('../backend/app/command_center.py');
const radar=read('../backend/app/smart_radar.py');
for(const key of ['def command_period_integrity','def inbox_window_integrity',
 'internal_count_reconciliation_passed','different_denominators_must_not_be_subtracted',
 'inbox_recent_window_directly_comparable','window_is_exhaustive'])
 assert.ok(shared.includes(key),key);
assert.ok(cc.includes('command_period_integrity(captured_ids,assessed_ids,relevant,alerts_by_post)'));
assert.ok(radar.includes('inbox_window_integrity(inbox.get("findings") or [],findings)'));
assert.ok(cc.includes("'count_integrity':period_integrity"));
assert.ok(radar.includes('"count_integrity":recent_integrity'));
const api=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=readBackendVersion(api);
assert.ok(Number(version.replace('.',''))>=1643);
assert.ok(hasDynamicBuildVersion(shell,version));
console.log('PASS v164.3 period vs recent Inbox count reconciliation and semantic separation');
