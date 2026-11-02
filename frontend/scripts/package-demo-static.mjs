import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {snapshot} from '../src/demo/currentSnapshot.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../dist');
const source=path.join(root,'index.html');
if(!fs.existsSync(source))throw Error('Vite build output missing');
const original=fs.readFileSync(source,'utf8');
const output=path.join(root,'demo','index.html');
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,original);
const dirs=['inbox','assistant','smart-radar','command-center','social-listening','watchlist','validation',
 'sources','administration','add','login','legacy-home'];
for(const dir of dirs){
 const dest=path.join(root,'demo',dir,'index.html');
 fs.mkdirSync(path.dirname(dest),{recursive:true});
 fs.writeFileSync(dest,original);
}
for(const id of [...new Set(snapshot.map(r=>String(r.campaignId)))]){
 const dest=path.join(root,'demo','social-listening','campaigns',id,'index.html');
 fs.mkdirSync(path.dirname(dest),{recursive:true});
 fs.writeFileSync(dest,original);
}
for(const id of ['WATCH-DEMO-0','WATCH-DEMO-1','WATCH-DEMO-2','WATCH-DEMO-3','WATCH-DEMO-4','WATCH-DEMO-5']){
 for(const suffix of ['', '/posts']){
  const dest=path.join(root,'demo','watchlist',id,...(suffix?['posts']:[]),'index.html');
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,original);
 }
}
fs.writeFileSync(source,'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="0;url=/demo/"><title>BAWASLU Demo</title></head><body><p>BAWASLU training environment: <a href="/demo/">Open demo</a></p></body></html>');
const staticAssets=['demo/smart-radar.html','demo/watchlist.html','demo/snapshot-bridge.js','ui-freeze/smart-radar-live.js'];
for(const entry of staticAssets)if(!fs.existsSync(path.join(root,entry)))throw Error('Missing approved BAWASLU asset: '+entry);
const forbidden=/<script[^>]+src=['"]https?:/i;
if(forbidden.test(original))throw Error('External script in training demo');
console.log('PASS static packaging: /demo landing, '+dirs.length+' modules, '+snapshot.length+' sanitized posts, local BAWASLU components');
