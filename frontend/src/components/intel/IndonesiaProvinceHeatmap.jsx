import { useEffect, useMemo, useState } from 'react';

const COLORS=[{min:1,label:'1 post',color:'#a9decf'},{min:2,label:'2–3 posts',color:'#68bca6'},{min:4,label:'4–7 posts',color:'#278d78'},{min:8,label:'8+ posts',color:'#0e6356'}];
const GRAY='#e1e8ed';
const LAYERS=[
  {key:'regional',name:'Regional activities & institutions',note:'Unverified location references in source posts; not confirmed incidents'},
  {key:'potential_incident',name:'Potential incident locations',note:'Possible incident locations only; pending source verification'},
  {key:'verified_incident',name:'Verified incident locations',note:'Locations independently verified and linked to evidence'}
];
const project=([lon,lat])=>[26+((lon-94)/48.5)*950,17+((7.4-lat)/19.5)*390];
const polyPath=(ring)=>ring?.length>=3?'M'+ring.map(pair=>project(pair).map(v=>v.toFixed(1)).join(',')).join('L')+'Z':'';
const provincePath=(f)=>{const geo=f.geometry;const polys=geo.type==='Polygon'?[geo.coordinates]:geo.type==='MultiPolygon'?geo.coordinates:[];return polys.map(p=>p.map(polyPath).join('')).join('')};
const color=(n)=>{if(!n)return GRAY;for(let i=COLORS.length-1;i>=0;i--)if(n>=COLORS[i].min)return COLORS[i].color;return COLORS[0].color};
export default function IndonesiaProvinceHeatmap({findings=[],onOpenFinding}) {
  const [features,setFeatures]=useState([]),[failure,setFailure]=useState('');
  const [layer,setLayer]=useState('regional'),[province,setProvince]=useState('');
  useEffect(()=>{const controller=new AbortController();
    fetch('/maps/indonesia-provinces.geojson',{signal:controller.signal,cache:'force-cache'})
      .then(r=>{if(!r.ok)throw Error('Province map data unavailable');return r.json()})
      .then(j=>{if(!Array.isArray(j.features)||j.features.length!==38)throw Error('Province boundaries are incomplete');setFeatures(j.features)})
      .catch(e=>{if(e.name!=='AbortError')setFailure(e.message)});
    return ()=>controller.abort();
  },[]);
  const areas=useMemo(()=>{
    const result={};
    for(const finding of findings) for(const [code,ids] of Object.entries(finding.geo_layers?.[layer]||{})){
      if(!result[code])result[code]={sourceIds:new Set(),topics:new Map()};
      ids.forEach(id=>result[code].sourceIds.add(id));
      result[code].topics.set(finding.id,finding);
    }
    return result;
  },[findings,layer]);
  const places=useMemo(()=>features.map(f=>({code:String(f.properties.KODE_PROV||f.id||''),name:f.properties.PROVINSI||'Unspecified',d:provincePath(f)})),[features]);
  const active=Object.values(areas).filter(v=>v.sourceIds.size>0).length;
  const selected=places.find(p=>p.code===province);
  const selectedData=selected?areas[selected.code]:null;
  const distinct=new Set(Object.values(areas).flatMap(v=>[...v.sourceIds])).size;
  const activeLayer=LAYERS.find(t=>t.key===layer);
  return <div className="space-y-3">
    <div className="flex flex-wrap gap-2 items-start justify-between">
      <div><h3 className="font-semibold text-base">Geographic Intelligence</h3>
       <p className="text-xs text-slate-500 mt-1">Indonesia · 38 provinces · geographic evidence from original posts</p>
      </div>
      <span className="rounded-full bg-slate-100 text-slate-600 px-3 py-1 text-xs">{active}/38 provinces mapped</span>
    </div>
    <div role="group" aria-label="Geographic intelligence layers" className="flex gap-2 flex-wrap">
      {LAYERS.map(t=><button key={t.key} type="button" aria-pressed={layer===t.key} onClick={()=>{setLayer(t.key);setProvince('')}}
        className={'border rounded-lg px-3 py-2 text-xs '+(layer===t.key?'bg-[#147968] text-white border-[#147968]':'bg-white border-slate-200 text-slate-600')}>{t.name}</button>)}
    </div>
    <p className="text-xs text-slate-500">{activeLayer.note}</p>
    <div className="rounded-lg bg-[#f4f8fa] border border-slate-100">
      {failure?<p role="alert" className="text-red-700 p-5 text-xs">{failure}</p>:!features.length?<p className="text-xs text-center text-slate-500 py-20">Loading Indonesia provinces…</p>:
      <svg viewBox="0 0 1000 430" className="w-full h-auto" aria-label="Indonesian province heatmap showing evidence-linked post locations" role="group">
      {places.map(p=>{const n=areas[p.code]?.sourceIds.size||0;return <path key={p.code} d={p.d} fill={color(n)} fillRule="evenodd"
        stroke={province===p.code?'#0e6356':'#ffffff'} strokeWidth={province===p.code?2.3:0.95}
        className="cursor-pointer hover:brightness-95" role="button" tabIndex={0}
        aria-label={p.name+': '+n+' linked posts'}
        onClick={()=>setProvince(p.code)}
        onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setProvince(p.code)}}}>
        <title>{p.name}: {n} original supporting posts ({activeLayer.name})</title>
      </path>})}
      </svg>}
    </div>
    <div className="flex flex-wrap gap-x-3 gap-y-2 text-[11px] text-slate-600">
      <span className="inline-flex gap-1 items-center"><i className="w-3 h-3 rounded-sm border border-slate-300" style={{background:GRAY}}/>No mapped reference</span>
      {COLORS.map(t=><span key={t.label} className="inline-flex gap-1 items-center"><i className="w-3 h-3 rounded-sm" style={{background:t.color}}/>{t.label}</span>)}
    </div>
    <div className="rounded-lg p-3 border border-slate-200 text-xs text-slate-600" aria-live="polite">
     {selected?<><b className="text-slate-900">{selected.name}</b> — {selectedData?.sourceIds.size||0} original source posts across {selectedData?.topics.size||0} intelligence topics.
       {selectedData?.topics.size?<div className="mt-3 space-y-2">{[...selectedData.topics.values()].map(f=><button type="button" onClick={()=>onOpenFinding?.(f)} key={f.id} className="w-full p-2 border rounded-lg text-left hover:border-[#147968]">
         <b className="text-slate-800">{f.title}</b><span className="ml-2 text-slate-500">({f.geo_layers?.[layer]?.[selected.code]?.length||0} posts)</span>
       </button>)}</div>:<p className="mt-1">No source-linked references in this view; absence does not mean no election activity.</p>}
     </>:<><b>{distinct}</b> unique supporting posts have geographic references in this view. Select a province to inspect evidence-linked topics.</>}
    </div>
    {layer!=='verified_incident'&&<p className="text-xs text-amber-800">Provisional location extraction: activity and institution references are <b>not</b> alleged violations or verified incident sites.</p>}
    {active===0&&<p className="text-xs text-slate-500">No locations mapped in this layer. Gray means unassigned, not zero incidents.</p>}
    <p className="text-[10px] text-slate-400">Province boundaries: <a className="underline" href="https://github.com/denyherianto/indonesia-geojson-topojson-maps-with-38-provinces" target="_blank" rel="noopener noreferrer">Indonesia GeoJSON (38 provinces)</a>, <a className="underline" href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>. 38 distinct province codes including new Papua provinces.</p>
  </div>;
}
