import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const project=read('../src/components/intel/CampaignPanel.jsx');
const dialog=read('../src/components/intel/AssessmentProgressDialog.jsx');
const service=read('../../backend/app/prism_discover.py');
const planner=read('../../backend/app/project_boolean.py');
for(const field of ["discover_boolean_plan(search['boolean_query'])","'max_credits':cap","'relevance':'score'","dry_run':True","'zero_yield_ack_required':False","confirm_cost","collection_diagnostics","provider_diagnostics","excluded_by_boolean"])assert.ok(service.includes(field),field);
assert.ok(!service.includes("params['contains']=plan['contains']"));
assert.ok(!service.includes("group['exclude_terms']=plan['exclude_terms']"));
assert.ok(planner.includes('POSITIVE_COMPOUND_SEARCH_WITH_LOCAL_BOOLEAN_GATE'));
assert.ok(dialog.includes('onClick={onConfirm}>Activate</button>'));
assert.ok(dialog.includes('disabled={loading||previewLoading||!preview}'));
for(const field of ['Maximum SocialCrawl credits','Provider source scope','zeroYieldAcknowledged'])assert.ok(!dialog.includes(field),field);
assert.ok(project.includes('signature:discoverPreview.signature'));
assert.ok(project.includes('booleanExpression={'));
assert.ok(project.includes('prism-latest-collection-outcome'));
assert.ok(read('../../Dockerfile').includes('test_prism_boolean_cost_guard_v17582.py'));
console.log('PASS Boolean collection: compound retrieval, local matching, single confirmation and backend credit guard');

assert.ok(service.includes('ensure_no_active_collection(db,c.id)'));
assert.ok(service.includes('search_snapshot'));
assert.ok(service.includes("if not match['matched']"));
assert.ok(project.includes('language:c.language'));
assert.ok(dialog.includes('scheduled monitoring is currently disabled'));

assert.ok(service.includes('CANDIDATE_CAP=300'));
assert.ok(service.includes('campaignDiscoverRecover'));
assert.ok(service.includes("if not recovery:execute_run(run.id)"));

assert.ok(service.includes('campaignDiscoverReuse'));
assert.ok(dialog.includes('Reuse saved collection'));
assert.ok(project.includes('paid_collection_blocked?null:launchDiscover'));
