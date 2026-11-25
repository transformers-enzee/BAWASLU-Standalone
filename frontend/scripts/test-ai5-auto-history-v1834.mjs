import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');

const ui=read('../src/pages/AI5Assistant.jsx');
const api=read('../../backend/app/ai5/api.py');
const storage=read('../../backend/app/ai5/persistence.py');

for(const part of [
 'async function retrySave(){','data-testid="ai5-auto-save-indicator"',
 'data-testid="ai5-chat-save-banner"','Auto-save is on',
 'Your first conversation will appear here automatically after AI-5 answers.',
 'r.save_status===\'SAVED\'&&r.saved_chat_id','setCurrentSavedId(r.saved_chat_id)',
 'setSaveStatus(\'Saving…\')','setSaveStatus(\'Saved\')',
 'setSaveStatus(\'Couldn’t save\')','onClick={retrySave}',
 'Chat history is saved automatically — no action needed',
 'Chats save automatically after the first answer.',
 'Your conversations','Rename chat','Delete saved chat'
]) assert.ok(ui.includes(part),'Missing auto-history UI contract: '+part);
assert.ok(!ui.includes('data-testid="ai5-save-chat"'),
  'Officers should no longer need a primary Save chat button');
assert.ok(!ui.includes("window.prompt('Name this saved chat'"),
  'Never require officers to enter a chat name for first-save');
assert.match(ui,/saveStatus==='Couldn’t save'&&messages\.some\(m=>m\.role==='assistant'\)/,
  'Retry must appear only for failed completed saves');
assert.ok(ui.includes('refreshSaved().catch(()=>{})'),
  'Newly saved records must appear in Your conversations');
for(const part of [
 'def auto_append(', 'if row is None:', 'db.add(row)',
 'created":True','created":False','_auto_title(record)',
 'AI5SavedChat.owner_user_id==user.id','if any(t.get("turn_id")==record.get("turn_id")',
 'MAX_SAVED','scope_fingerprint=state.fingerprint(grant)'
]) assert.ok(storage.includes(part),'Missing backend auto-save contract: '+part);
for(const part of [
 'saving=persistence.auto_append(db,user,grant,conversation_id,record)',
 '"save_status":saving["status"]','"saved_chat_id":saving.get("saved_chat_id")',
 '"save_error":saving.get("reason")'
]) assert.ok(api.includes(part),'Missing chat persistence response: '+part);
assert.ok(!/service_role|SUPABASE_SERVICE_ROLE_KEY/i.test(ui));
console.log('PASS AI-5 v183.4 first-answer automatic saved history, retry status and retained privacy');
