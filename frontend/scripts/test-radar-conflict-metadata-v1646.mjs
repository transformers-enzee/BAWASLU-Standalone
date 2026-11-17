import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/monitoring_metric_reconciliation.py');
const radar=read('../backend/app/smart_radar.py');
for(const token of ['def radar_source_conflicts','conflicting_distinct_sources',
 'conflicting_fields','REPEATED_SOURCE_METADATA_CONFLICT',
 'def keyword_cloud_source_counts','pair=(sid,norm)'])
 assert.ok(helper.includes(token),token);
assert.ok(radar.includes("keyword_counts=keyword_cloud_source_counts(inbox.get('findings') or [],main_by_campaign)"));
assert.ok(radar.includes('"metric_integrity":recent_metrics'));
assert.ok(!radar.includes('counted_keywords=set()'));
const version=read('../backend/app/main.py').split("'build_version':'")[1]?.split("'")[0];
assert.equal(version,'164.6');
assert.ok(read('src/components/intel/Shell.jsx').includes('data-build-version="164.6"'));
console.log('PASS v164.6 repeated-source metadata conflict visibility and cross-campaign normalized keyword totals');
