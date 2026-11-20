import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/monitoring_metric_reconciliation.py');
const radar=read('../backend/app/smart_radar.py');
for(const k of ['def radar_source_rollup','repeat_occurrences','candidate_mentions',
  'verified_incident_counts','geographic_mentions_unverified'])
 assert.ok(helper.includes(k),k);
assert.ok(radar.includes('source_rollup=radar_source_rollup(findings)'));
assert.ok(radar.includes('posts=source_rollup["posts"]'));
for(const key of ['platform_counts','sentiment_counts','candidate_mentions',
  'geo_signal_counts','verified_incident_counts'])
 assert.ok(radar.includes('source_rollup["'+key+'"]'),key);
assert.ok(radar.includes('keyword_counts=keyword_cloud_source_counts('));
assert.ok(helper.includes('pair=(sid,norm)'));
assert.ok(helper.includes('if len(norm)<3 or pair in seen:continue'));
assert.ok(radar.includes('recent_metrics=radar_metric_integrity(findings,platforms,sentiments,len(posts))'));
const api=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=readBackendVersion(api);
assert.ok(Number(version.replace('.',''))>=1645);
assert.ok(hasDynamicBuildVersion(shell,version));
console.log('PASS v164.5 unique saved-source Radar aggregates and campaign keyword deduplication');
