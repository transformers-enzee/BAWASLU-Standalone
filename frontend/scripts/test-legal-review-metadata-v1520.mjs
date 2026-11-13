import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const p=readFileSync(new URL('../src/components/intel/AssistantKnowledgeLibrary.jsx',import.meta.url),'utf8');
for(const token of ['legal_version_label','legal_effective_date','legal_election_type','legal-document-version','legal-document-effective-date','legal-document-election-type']) assert.ok(p.includes(token),token);
assert.ok(p.includes('setReviewMeta({legal_version_label:doc.legal_version_label||'), 'existing document metadata restored before review');
assert.ok(p.includes('legal_version_label:reviewMeta.legal_version_label.trim()'), 'review submits version');
assert.ok(p.includes('legal_effective_date:reviewMeta.legal_effective_date'), 'review submits date');
assert.ok(p.includes('legal_election_type:reviewMeta.legal_election_type'), 'review submits election type');
console.log('v152.0 legal review metadata UI static checks passed');
