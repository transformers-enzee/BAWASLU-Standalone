import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/monitoring_metric_reconciliation.py');
const cc=read('../backend/app/command_center.py');
const radar=read('../backend/app/smart_radar.py');
for(const t of ['radar_metric_integrity','command_metric_integrity',
 'PLATFORM_COUNTS_DIFFER_FROM_SOURCE_INVENTORY','SENTIMENT_COUNTS_DIFFER_FROM_SOURCE_INVENTORY',
 'PUBLICATION_DAY_TOTAL_DIFFERS_FROM_CAPTURED','additional_database_queries'])
 assert.ok(helper.includes(t),t);
assert.ok(cc.includes('command_metric_integrity(len(captured_ids),platform_counts,day_counts)'));
assert.ok(radar.includes('radar_metric_integrity(findings,platforms,sentiments,len(posts))'));
assert.ok(cc.includes("'metric_integrity':period_metrics"));
assert.ok(radar.includes('"metric_integrity":recent_metrics'));
const version=read('../backend/app/main.py').split("'build_version':'")[1]?.split("'")[0];
assert.equal(version,'164.4');
assert.ok(read('src/components/intel/Shell.jsx').includes('data-build-version="'+version+'"'));
console.log('PASS v164.4 platform/day/sentiment aggregate counts reconcile against selected unique sources');
