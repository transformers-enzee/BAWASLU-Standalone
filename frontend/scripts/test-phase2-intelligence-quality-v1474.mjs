import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const policy=read('../backend/app/platform_policy_screening.py');
const legal=read('../backend/app/finding_assessments.py');
const semantic=read('../backend/app/assistant_semantic.py');
const inbox=read('../backend/app/inbox_radar.py');
const drawer=read('public/ui-freeze/finding-assessments-v1470.js');
const html=read('public/ui-freeze/smart-radar-v6_2.html');
const app=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');

for(const p of ['tiktok','instagram','facebook','threads','twitter','youtube',
  'reddit','linkedin','telegram']){
  assert.match(policy,new RegExp('"'+p+'": \\('),'Missing official policy entrypoint: '+p);
}
assert.ok(policy.includes('PLATFORM_POLICY_CAVEATS'),'Platform context includes provider-specific restrictions');
assert.ok(policy.includes('"telegram": ("Telegram"'),'Telegram official policy registered');
assert.ok(policy.includes('policy_version_verified":False'),'Never assert policy currentness');
assert.ok(legal.includes('source_provenance')&&legal.includes('duplicate_links_removed'),
  'Finding includes source dedupe and lineage metadata');
assert.ok(legal.includes('reviewed_legal_only=True'),'Legal retrieval uses officer-reviewed gate');
assert.ok(legal.includes('semantic=False'),'Finding review cannot trigger paid query embeddings');
assert.ok(semantic.includes('KnowledgePDF.review_status=="OFFICER_REVIEWED"'),
  'Search excludes unreviewed before ranking');
assert.ok(semantic.includes('KnowledgePDF.document_type.in_('),
  'Only legal document types may substantiate legal review');
assert.ok(inbox.includes("'linkedin':'LinkedIn'")&&inbox.includes("'reddit':'Reddit'"),
  'Consistent platform casing');
assert.ok(drawer.includes('source_count_matches_finding')&&drawer.includes('policy_scope_note'),
  'Finding detail presents evidence reconciliation and platform context');
assert.ok(html.includes('finding-assessments-v1470.js'),'Retain existing drawer enhancement');
assert.ok(!html.includes('id="legalCaseQueue"'),'Do not reinstate standalone legal section');
const backendVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const frontendVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(backendVersion&&frontendVersion&&backendVersion===frontendVersion,
  'Build version matches both backend and frontend');
console.log('PASS v147.6 Phase 2 assessment provenance, reviewed citations and nine-platform policy contracts');
