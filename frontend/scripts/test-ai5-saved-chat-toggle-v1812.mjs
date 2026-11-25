import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {canExpandSavedChats,savedChatsForDisplay,RECENT_CHAT_LIMIT}
  from '../src/lib/ai5SavedChats.js';

assert.equal(RECENT_CHAT_LIMIT,3);
const chats=n=>Array.from({length:n},(_,i)=>({id:String(i+1),title:'Chat '+(i+1)}));
for(const count of [0,1,2,3]){
  const list=chats(count);
  assert.equal(canExpandSavedChats(count),false,
    count+' chats should not show View all chats');
  assert.deepEqual(savedChatsForDisplay(list,false),list);
  assert.deepEqual(savedChatsForDisplay(list,true,'no match'),list,
    'A stale expanded/search state must not hide 1–3 saved conversations');
}
for(const count of [4,5,12,40]){
  const list=chats(count);
  assert.equal(canExpandSavedChats(count),true);
  assert.deepEqual(savedChatsForDisplay(list,false),list.slice(0,3),
    'Collapsed view must show three most recent chats');
  assert.deepEqual(savedChatsForDisplay(list,true),list,
    'Expanded view must show all saved conversations');
  assert.deepEqual(savedChatsForDisplay(list,true,'chat 4'),[list[3]],
    'Expanded search must find chats beyond the first three');
}
const mixed=[{id:'1',title:'Regional Research'},{id:'2',title:'INCIDENT Reports'},
             {id:'3',title:'Climate Notes'},{id:'4',title:'incident review'}];
assert.deepEqual(savedChatsForDisplay(mixed,true,'  INCIDENT  '),
  [mixed[1],mixed[3]],'Search must be case-insensitive and trim spaces');
assert.equal(canExpandSavedChats(3.5),false);
assert.deepEqual(savedChatsForDisplay(null,true),[]);

const ui=readFileSync(new URL('../src/pages/AI5Assistant.jsx',import.meta.url),'utf8');
assert.match(ui,/!savedLoading&&!savedLoadError&&canExpandSavedChats\(savedChats\.length\)&&/,
 'View-all button should be absent for 0–3 saved chats and while loading');
assert.ok(ui.includes('View all chats (\u0024{savedChats.length})'),
 'View-all button should display the total number of saved chats');
assert.ok(ui.includes("showSaved?'Show recent'"),
 'Expanded view should provide a way back to the three recent chats');
assert.ok(ui.includes('savedChatsForDisplay(savedChats,showSaved,savedSearch)'),
 'Actual list must use the tested shared helper');
assert.ok(ui.includes('aria-current={currentSavedId===item.id'),
 'Current saved chat must have an accessible current-state indication');
assert.ok(ui.includes('border-sky-500 bg-sky-50 ring-1 ring-sky-200'),
 'Current chat must have stronger visual contrast');
assert.ok(!ui.includes('See all {savedChats.length} saved chats'),
 'Avoid duplicate controls opening the same list');
console.log('PASS AI-5 v181.2 small (0–3) and large (4+) saved-chat libraries, search and current-chat highlighting');
