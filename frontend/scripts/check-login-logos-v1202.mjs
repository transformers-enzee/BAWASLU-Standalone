import assert from 'node:assert/strict';import {readFileSync,existsSync} from 'node:fs';
const s=readFileSync(new URL('../src/components/AuthLayout.jsx',import.meta.url),'utf8');
assert.match(s,/src="\/bawaslu-full-logo\.webp"/);assert.match(s,/src="\/nadicom-wordmark\.webp"/);
assert.ok(!s.includes('src="/bawaslu-emblem.svg"'));assert.ok(!s.includes('src="/nadicom-symbol.webp"'));
assert.ok(existsSync(new URL('../public/bawaslu-full-logo.webp',import.meta.url)));
console.log('120.2 login logo branding contract passed');