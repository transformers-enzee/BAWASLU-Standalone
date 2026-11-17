import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const enqueuer=read('../backend/app/assessment_job_reconcile.py');
const worker=read('../backend/app/auto_relevance.py');
const campaigns=read('../backend/app/campaigns.py');
for(const token of ['BATCH_LIMIT=200','order_by(CampaignEvidence.id.asc())',
 'on_conflict_do_nothing','AIAssessmentJob.id.is_(None)',
 'CampaignEvidence.match_method!="WATCHLIST_ACCOUNT"',
 'relevance.in_(["UNASSESSED",""])'])
 assert.ok(enqueuer.includes(token),token);
assert.ok(worker.includes('enqueue_unassessed_campaign_jobs(db,campaign_id)'));
assert.ok(campaigns.includes("created=enqueue_campaign_evidence(campaign.id)"));
assert.ok(campaigns.includes("'assessment_link_coverage':campaign_link_assessment_coverage(db,campaign.id)"));
const api=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(api.includes("'build_version':'165.0'"));
assert.ok(shell.includes('data-build-version="165.0"'));
console.log('PASS v165.0 bounded, conflict-safe, no-credit assessment job queue');
