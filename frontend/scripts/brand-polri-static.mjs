// Demo-image-only branding. This script never runs during operational BAWASLU builds.
import fs from 'node:fs';
import path from 'node:path';
if(process.env.VITE_POLRI_DEMO!=='1'||process.env.VITE_DEMO_STANDALONE!=='1')
  throw new Error('POLRI branding requires the isolated standalone demo environment');
const root=path.resolve('dist');
function change(relative, replacements){
  const file=path.join(root,relative);
  let text=fs.readFileSync(file,'utf8');
  for(const [before,after] of replacements){
    if(!text.includes(before))throw new Error('Branding marker missing in '+relative+': '+before.slice(0,50));
    text=text.replaceAll(before,after);
  }
  fs.writeFileSync(file,text);
}
change('index.html',[
 ['<title>BAWASLU Smart Radar</title>','<title>Smart Radar</title>'],
 ['href="/nadicom-symbol.webp"','href="/polri-logo.svg"'],
 ['<link rel="manifest" href="/manifest.json" />','<!-- No BAWASLU web manifest in POLRI demo -->']
]);
// Preserve original evidence text and provenance. Change only page titles and
// demonstration-specific controls rather than rewriting historical posts.
change('demo/smart-radar.html',[
 ['<title>BAWASLU Command Centre — Election Intelligence</title>','<title>Smart Radar — POLRI Demo</title>'],
 ['>BAWASLU Reputation<','>POLRI Reputation<']
]);
change('demo/watchlist.html',[
 ['<title>BAWASLU Watchlist V2.2 — Interactive Prototype</title>','<title>Smart Radar — POLRI Demo</title>']
]);
if(!fs.existsSync(path.join(root,'polri-logo.svg')))throw new Error('POLRI logo is missing from static build');
console.log('PASS: isolated Smart Radar POLRI branding, logo and favicon bundled');
