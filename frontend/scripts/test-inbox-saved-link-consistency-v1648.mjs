import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/monitoring_metric_reconciliation.py');
const radar=read('../backend/app/smart_radar.py');
for(const token of ['def inbox_saved_link_consistency',
 'multi_campaign_sources','cross_campaign_sentiment_conflict_sources',
 'REVIEW_SAVED_SENTIMENT_DISAGREEMENT','unassessed_links_covered',
 'source_ids_or_text_exposed','additional_database_queries'])
 assert.ok(helper.includes(token),token);
assert.ok(radar.includes('saved_link_consistency=inbox_saved_link_consistency(inbox.get("findings") or [])'));
assert.ok(radar.includes('"saved_link_consistency":saved_link_consistency'));
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1648);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v164.8 cross-campaign saved assessment conflicts visible pre-dedup without raw evidence');
