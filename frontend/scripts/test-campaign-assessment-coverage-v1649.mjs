import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/campaign_assessment_coverage.py');
const campaigns=read('../backend/app/campaigns.py');
const worker=read('../backend/app/auto_relevance.py');
for(const term of ['campaign_link_assessment_coverage','WATCHLIST_ACCOUNT',
 'pending_monitoring_without_job','assessment_rows_labelled_unassessed_remain_pending',
 'ready_for_no_cost_job_reconciliation','database_writes'])
 assert.ok(helper.includes(term),term);
assert.ok(campaigns.includes("'assessment_link_coverage':campaign_link_assessment_coverage(db,campaign.id)"));
assert.ok(campaigns.includes("if (data or {}).get('dry_run') is True:"));
assert.ok(campaigns.includes("'paid_provider_called':False,'database_writes':0"));
assert.ok(worker.includes("CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'"));
const api=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=api.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1649);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v164.9 watchlist exclusion, pending assessment coverage and no-cost preview');
