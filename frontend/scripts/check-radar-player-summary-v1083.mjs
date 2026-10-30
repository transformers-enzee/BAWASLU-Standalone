import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const ui=readFileSync('public/ui-freeze/smart-radar-v6_2.html','utf8');
assert.match(ui,/function playerOverview\(fs,key\)/);
assert.match(ui,/fs\.length\?playerOverview\(fs,key\)/);
assert.match(ui,/fs\.length\?E\(playerOverview\(fs,panel\.id\)\)/);
assert.match(ui,/new Set\(fs\.map/);
assert.doesNotMatch(ui,/fs\.slice\(0,2\)\.map\(f=>f\.summary\)\.join\(' '\)/);
console.log('Potential violation summary combines validated source categories, not boilerplate.');
