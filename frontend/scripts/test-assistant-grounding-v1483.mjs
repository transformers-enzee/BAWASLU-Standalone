import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../',import.meta.url);
const read=path=>readFileSync(new URL(path,root),'utf8');
const audit=read('../backend/app/assistant_grounding.py');
const api=read('../backend/app/main.py');
const page=read('src/pages/IntelligenceAssistant.jsx');
const browser=read('e2e/assistant-knowledge-library.spec.js');
const appVersion=api.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const uiVersion=read('src/components/intel/Shell.jsx').match(/data-build-version="(\d+\.\d+)"/)?.[1];

assert.ok(audit.includes('def audit_assistant_answer'),'Deterministic post-answer audit required');
assert.ok(audit.includes('if ref not in allowed:')&&audit.includes('rejected.append(ref)'),
  'Unselected bracket citations are stripped');
assert.ok(audit.includes('displayed_citation_ids')&&
  audit.includes('model_cited_but_not_displayed'),
  'Structured-only refs must not count as visible citations');
assert.ok(audit.includes('review_status')&&audit.includes('OFFICER_REVIEWED'),
  'Doc authority status derives from saved officer review metadata');
assert.ok(audit.includes('legal_currentness_verified":False')&&
  audit.includes('legal_verdict_confirmed":False'),
  'Never assert current law or a confirmed violation');
assert.ok(api.includes('audit_assistant_answer(')&&
  api.includes("meta['grounding_audit']=grounding_audit"),
  'Chat route must run deterministic audit before source cards are built');
assert.ok(api.includes("'cited_count':len(cited)")&&
  api.includes("'source_card_count':len(support)"),
  'Cards and citations must have different denominators');
assert.ok(audit.includes('def _officer_review_steps')&&
  audit.includes('"officer_review_steps_auto_completed":False')&&
  page.includes('data-testid="assistant-officer-review-steps"'),
  'Officer review instructions must be explicit, permission-scoped, and advisory only');
assert.ok(page.includes('data-testid="assistant-grounding-integrity"')&&
  page.includes('Source cards are context only'),
  'Assistant UI must distinguish context cards from citations');
assert.ok(browser.includes('Assistant distinguishes cited IDs from contextual source cards'),
  'Real UI Playwright regression for provenance distinctions');
assert.ok(appVersion&&appVersion===uiVersion,
  'Backend/frontend sequential version must match');
console.log('PASS v148.3 BAWASLU Assistant citation integrity, PDF review caveats and visible UI provenance');
