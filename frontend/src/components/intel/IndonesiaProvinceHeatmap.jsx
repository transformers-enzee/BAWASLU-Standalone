import { useEffect, useMemo, useState } from 'react';

const PALETTE=[
  {min:1,label:'1 topic',color:'#b5e3d6'},
  {min:2,label:'2–3 topics',color:'#70c6ad'},
  {min:4,label:'4–7 topics',color:'#2b9b82'},
  {min:8,label:'8+ topics',color:'#116455'}
];
const UNKNOWN='#e1e8ed';
const project=([longitude,latitude])=>[
  26 + ((longitude-94)/48.5)*950,
  17 + ((7.4-latitude)/19.5)*390
];
const point=coordinates=>{const [x,y]=project(coordinates);return x.toFixed(1)+','+y.toFixed(1)};
function ringPath(ring){
  if(!ring || ring.length<3)return '';
  return 'M'+ring.map(point).join('L')+'Z';
}
function provincePath(feature){
  const g=feature?.geometry;
  if(!g?.coordinates)return '';
  const polygons=g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[];
  return polygons.map(poly=>poly.map(ringPath).join('')).join('');
}
function fillColor(n){
  if(!n)return UNKNOWN;
  for(let i=PALETTE.length-1;i>=0;i--)if(n>=PALETTE[i].min)return PALETTE[i].color;
  return PALETTE[0].color;
}
export default function IndonesiaProvinceHeatmap({findings=[]}){
  const [features,setFeatures]=useState([]);
  const [loadError,setLoadError]=useState('');
  const [selected,setSelected]=useState(null);
  useEffect(()=>{
    const controller=new AbortController();
    fetch('/maps/indonesia-provinces.geojson',{signal:controller.signal,cache:'force-cache'})
      .then(response=>{if(!response.ok)throw Error('Province boundary file unavailable');return response.json()})
      .then(data=>{
        if(!Array.isArray(data.features) || data.features.length!==38)throw Error('Province boundaries incomplete');
        setFeatures(data.features);
      })
      .catch(err=>{if(err.name!=='AbortError')setLoadError(err.message)});
    return ()=>controller.abort();
  },[]);
  // Counts are DISTINCT TOPICS with at least one human-verified incident
  // province; a finding can be present in more than one province, but never
  // counted twice within a province. Other locations do not color the map.
  const metrics=useMemo(()=>{
    const counts={};
    for(const finding of findings){
      for(const code of new Set(finding.province_codes||[]))
        counts[code]=(counts[code]||0)+1;
    }
    return {counts,assigned:findings.filter(f=>(f.province_codes||[]).length>0).length,unassigned:findings.filter(f=>!(f.province_codes||[]).length).length};
  },[findings]);
  const polygons=useMemo(()=>features.map(f=>({code:String(f.properties.KODE_PROV||f.id||''),name:f.properties.PROVINSI||'Unknown province',d:provincePath(f)})),[features]);
  const selectedProvince=polygons.find(p=>p.code===selected);
  const activeProvinces=Object.values(metrics.counts).filter(n=>n>0).length;
  return <div className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div><h3 className="font-semibold text-base">Geographic Intelligence</h3>
        <p className="text-xs text-slate-500 mt-1">Indonesia · 38 provinces · Verified incident locations only</p>
      </div>
      <span className="text-[11px] rounded-full px-3 py-1 bg-slate-100 text-slate-600">{activeProvinces} / 38 provinces mapped</span>
    </div>
    <div className="rounded-lg bg-[#f4f8fa] border border-slate-100 relative">
      {loadError?<p role="alert" className="text-xs text-red-700 p-5">Unable to load province map: {loadError}</p>:
      !features.length?<div className="h-56 grid place-items-center text-xs text-slate-500">Loading Indonesia's province boundaries…</div>:
      <svg viewBox="0 0 1000 430" className="w-full h-auto" role="group" aria-label="Indonesia province choropleth heatmap showing verified intelligence topics" preserveAspectRatio="xMidYMid meet">
        {polygons.map(p=><path key={p.code} d={p.d}
          fill={fillColor(metrics.counts[p.code]||0)}
          stroke={selected===p.code?'#0d594f':'#ffffff'}
          strokeWidth={selected===p.code?2.3:0.95}
          strokeLinejoin="round"
          fillRule="evenodd"
          className="cursor-pointer transition-colors hover:brightness-95 focus:outline-none"
          role="button" tabIndex={0}
          aria-label={p.name+': '+(metrics.counts[p.code]?metrics.counts[p.code]+' location-attributed topics':'no verified province-attributed topics')}
          onClick={()=>setSelected(p.code)}
          onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(p.code)}}}>
          <title>{p.name}: {metrics.counts[p.code]?metrics.counts[p.code]+' topics':'No verified incident attribution'}</title>
        </path>)}
      </svg>}
    </div>
    <div className="flex gap-x-3 gap-y-2 flex-wrap items-center text-[11px] text-slate-600">
      <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-sm border border-slate-300 inline-block" style={{background:UNKNOWN}}/>Unassigned / no verified data</span>
      {PALETTE.map(t=><span key={t.label} className="flex items-center gap-1"><i className="w-3 h-3 rounded-sm inline-block" style={{background:t.color}}/>{t.label}</span>)}
    </div>
    <div aria-live="polite" className="border border-slate-200 rounded-lg p-3 text-xs text-slate-600">
      {selectedProvince? <><b className="text-slate-800">{selectedProvince.name}</b> — {metrics.counts[selectedProvince.code]?
        metrics.counts[selectedProvince.code]+' topic(s) linked to a verified incident location':'No verified incident location available for this province.'}</>:
       <><b className="text-slate-800">{metrics.assigned} of {findings.length}</b> displayed intelligence topics have a verified incident province. <b>{metrics.unassigned}</b> have no verified incident province yet.</>}
    </div>
    {activeProvinces===0&&<p className="text-xs text-amber-800">The pilot's 109 posts have not been assigned verified incident provinces. Gray means <b>location unknown</b>, not zero election issues.</p>}
    <p className="text-[10px] text-slate-400">Province boundaries: <a href="https://github.com/denyherianto/indonesia-geojson-topojson-maps-with-38-provinces" target="_blank" rel="noopener noreferrer" className="underline">Indonesia GeoJSON (38 provinces)</a>, licensed <a className="underline" href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>. Province highlighting requires human-verified incident locations.</p>
  </div>;
}
