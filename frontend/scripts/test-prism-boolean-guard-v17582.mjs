import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const project=read('../src/components/intel/CampaignPanel.jsx');
const dialog=read('../src/components/intel/AssessmentProgressDialog.jsx');
const service=read('../../backend/app/prism_discover.py');
const planner=read('../../backend/app/project_boolean.py');
const router=read('../../backend/app/socialcrawl.py');
const status=read('../../backend/app/activation_assessment.py');
const campaigns=read('../../backend/app/campaigns.py');
for(const field of [
 "discover_boolean_plan(search['boolean_query'])",
 "'max_credits':cap",
 "params['contains']=plan['contains']",
 "group['exclude_terms']=plan['exclude_terms']",
 "dry_run':True",
 "latest_collection_outcome(db,c,params)",
 "'zero_yield_ack_required':bool(last and last['zero_yield_paid_run'])",
 "confirmed_max_credits",
 "acknowledge_zero_yield",
 "collection_diagnostics",
 "excluded_by_boolean",
])assert.ok(service.includes(field),'Missing Prism guard: '+field);
for(const field of [
 "def discover_boolean_plan(",
 "'provider_boolean_native':False",
 "'SELECTIVE_POSITIVE_ARM_WITH_EXACT_LOCAL_BOOLEAN_GATE'",
 "if not left or not right:",
])assert.ok(planner.includes(field),'Missing Boolean planner contract: '+field);
for(const field of [
 'data-testid="prism-actual-retrieval-plan"',
 'data-testid="prism-previous-collection-outcome"',
 "Maximum SocialCrawl credits",
 'preview.credit_cap',
 'preview.provider_contains',
 'preview.provider_exclude_terms',
 "preview.zero_yield_ack_required&&!zeroYieldAcknowledged",
])assert.ok(dialog.includes(field),'Missing visible cost/warning: '+field);
for(const field of [
 "action:'campaignDiscoverPreview',id:c.id,data:{max_credits:cap}",
 "confirmed_max_credits:discoverCreditCap",
 "acknowledge_zero_yield:discoverZeroYieldAcknowledged",
 "action:'campaignDiscoverLastRunDiagnostics'",
 'data-testid="prism-latest-collection-outcome"',
 "prism_provider_keywords",
])assert.ok(project.includes(field),'Missing project UI: '+field);
assert.ok(router.includes("'campaignDiscoverLastRunDiagnostics'"));
assert.ok(status.includes('"collection_diagnostics":diag'));
assert.ok(campaigns.includes("prism_plan=discover_boolean_plan(search['boolean_query'])"));
const docker=read('../../Dockerfile');
assert.ok(docker.includes('test_prism_boolean_cost_guard_v17582.py'));
console.log('PASS BAWASLU v175.82: Prism query preflight, credit cap, zero-yield acknowledgement and dashboard diagnostics');
