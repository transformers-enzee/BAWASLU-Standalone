import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const ai=readFileSync(new URL('../src/pages/AI5Assistant.jsx',import.meta.url),'utf8');
const expect=(needle)=>assert.ok(ai.includes(needle),'Missing AI-5 saved-chat UX contract: '+needle);

for(const part of [
 'Your conversations','Chats save automatically after the first answer.',
 'New chat','Auto-save is on','Saved automatically',
 'Chat history is saved automatically — no action needed',
 'Couldn’t save this conversation. Retry before leaving.',
 'data-testid="ai5-new-chat-header"','data-testid="ai5-auto-save-indicator"',
 'data-testid="ai5-save-status"','data-testid="ai5-retry-save"',
 'data-testid="ai5-saved-chats"','data-testid="ai5-saved-chat-item"',
 'data-testid="ai5-saved-navigation"','Open saved chat ',
 'Search saved chats','View all chats','Show recent',
 'Couldn’t save','Retry save','Shared links',
 'onClick={()=>reopen(item.id)}','onClick={()=>renameChat(item)}',
 'onClick={()=>deleteChat(item)}','refreshSaved().catch(()=>{})'
])expect(part);

assert.match(ai,/<nav aria-label="AI-5 Saved Chats" data-testid="ai5-saved-chats"/,
 'Recent saved chats should have a persistent, always-visible navigation region');
assert.ok(!ai.includes('Saved Chats ({savedChats.length})'),
 'Do not show an asynchronously stale badge counter in the header');
assert.ok(!ai.includes('{showSaved&&<nav'),
 'Saved-chat navigation must not depend on expanding a header button');
assert.ok(ai.includes('savedChatsForDisplay(savedChats,showSaved,savedSearch)'),
 'Recent saved chats must use the shared 3-item visibility rule');
assert.ok(ai.includes('canExpandSavedChats(savedChats.length)'),
 'View-all and search must be available only for libraries above three');
assert.ok(ai.includes('aria-current={currentSavedId===item.id'),
 'The current saved conversation must remain visibly and accessibly highlighted');
assert.ok(!ai.includes('data-testid="ai5-save-chat"'),'Manual Save chat control must be removed');
assert.ok(!ai.includes("window.prompt('Name this saved chat'"),'Automatic saving cannot prompt for a title');
console.log('PASS AI-5 v183.4 automatic history, visible saved chats and private sharing UX');
