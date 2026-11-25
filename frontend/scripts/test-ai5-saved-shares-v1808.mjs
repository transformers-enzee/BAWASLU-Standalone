import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const ui=read('../src/pages/AI5Assistant.jsx');
const api=read('../../backend/app/ai5/api.py');
const data=read('../../backend/app/ai5/persistence.py');
const state=read('../../backend/app/ai5/state.py');
const migration=read('../../database/migrations/20261124090000_ai5_saved_shares_v1808.sql');
const requireText=(source,value)=>assert.ok(source.includes(value),'Missing AI-5 saved/share contract: '+value);

for(const text of ['Auto-save is on','Saved Chats','Share chat','Shared links',
 'Couldn’t save','Preview & check access','Create read-only share',
 'Share','Copy link','Email draft','WhatsApp draft','Revoke',
 'Sign-in required','Frozen read-only copy','includeResearchTrail',
 "new URLSearchParams(window.location.search).get('share')",
 'onDraftSave','onDraftChange','/api/ai-5/shared/view/'])
 requireText(ui,text);
for(const text of ['@router.get("/saved")','@router.post("/saved")',
 '@router.get("/saved/{saved_id}")','@router.patch("/saved/{saved_id}")',
 '@router.patch("/saved/{saved_id}/draft")','@router.delete("/saved/{saved_id}")',
 '@router.post("/shared/preview")','@router.post("/shared")',
 '@router.get("/shared/view/{token}")','@router.delete("/shared/{share_id}")',
 'persistence.auto_append','grant_for(db,user)','save_status'])
 requireText(api,text);
for(const text of ['owner_user_id==user.id','sender_user_id==user.id',
 'recipient_user_ids_json','preview_digest','expires_at','revoked_at',
 'has(grant,"view_intelligence")','source_mode','scope_fingerprint',
 'token_digest','hashlib.sha256','_durable_turn','MAX_SAVED=40'])
 requireText(data,text);
for(const text of ['def restore','restored_from_saved','MAX_TURNS=50'])
 requireText(state,text);
for(const text of ['ENABLE ROW LEVEL SECURITY','REVOKE ALL ON TABLE',
 'ai5_saved_chats','ai5_shared_snapshots','uq_ai5_saved_owner_conversation'])
 requireText(migration,text);
requireText(data,'def auto_append(');
requireText(data,'if row is None:');
requireText(data,'created":True');
// No route may expose shared content by a naked public token without signed-in user.
assert.match(api,/@router\.get\("\/shared\/view\/\{token\}"\)[\s\S]*?Depends\(current_user\)/);
assert.ok(!/service_role|SUPABASE_SERVICE_ROLE_KEY/i.test(ui),'No server credential in frontend');
console.log('PASS AI-5 saved chats, recipient-only share previews, frozen snapshots and expiry/revoke contracts');
