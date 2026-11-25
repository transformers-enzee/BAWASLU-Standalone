import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const ai=readFileSync(new URL('../src/pages/AI5Assistant.jsx',import.meta.url),'utf8');
const expect=(needle)=>assert.ok(ai.includes(needle),'Missing AI-5 saved-chat UX contract: '+needle);

for(const part of [
 'Your conversations','Open a saved chat to pick up where you left off.',
 'New chat','Save chat','Saved automatically after each reply',
 'Not saved · Save to return later','Saved conversation · New replies are saved automatically',
 'This conversation isn’t saved yet. Save it to return after signing out.',
 'data-testid="ai5-new-chat-header"','data-testid="ai5-save-chat"',
 'data-testid="ai5-saved-chats"','data-testid="ai5-saved-chat-item"',
 'data-testid="ai5-saved-navigation"','Open saved chat ',
 'Search saved chats','View all chats','Show recent',
 'Saved conversation ·','Couldn’t save','Retry save','Shared links',
 'onClick={()=>reopen(item.id)}','onClick={()=>renameChat(item)}',
 'onClick={()=>deleteChat(item)}','await refreshSaved()'
])expect(part);

assert.match(ai,/<nav aria-label="AI-5 Saved Chats" data-testid="ai5-saved-chats"/,
 'Recent saved chats should have a persistent, always-visible navigation region');
assert.ok(!ai.includes('Saved Chats ({savedChats.length})'),
 'Do not show an asynchronously stale badge counter in the header');
assert.ok(!ai.includes('{showSaved&&<nav'),
 'Saved-chat navigation must not depend on expanding a header button');
assert.ok(ai.includes('savedChats.slice(0,3)'),
 'Recent saved chat previews must be visible without extra clicks');
assert.ok(ai.includes("savedChats.filter(x=>x.title.toLowerCase().includes(savedSearch.toLowerCase()))"),
 'All saved chats need an accessible search filter');
console.log('PASS AI-5 v181.0 saved conversation visibility, discoverability, status and navigation UX');
