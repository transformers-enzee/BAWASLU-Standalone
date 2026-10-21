import { useEffect, useMemo, useState } from 'react';

const aliases={'jakarta':'DKI Jakarta','daerah khusus ibukota jakarta':'DKI Jakarta','daerah istimewa yogyakarta':'DI Yogyakarta','yogyakarta':'DI Yogyakarta','kepulauan bangka-belitung':'Kepulauan Bangka Belitung','bangka belitung':'Kepulauan Bangka Belitung'};
const normalize=name=>{const key=String(name||'').trim().toLocaleLowerCase('id-ID');return (aliases[key]||name||'').toLocaleLowerCase('id-ID')};
const project=point=>[(point[0]-94)*21.25,(7.7-point[1])*21.25];
const ringPath=ring=>ring.map((point,index)=>{const [x,y]=project(point);return (index?'L':'M')+x.toFixed(1)+','+y.toFixed(1)}).join(' ')+'Z';
const geoPath=geometry=>{const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates||[];return polygons.map(polygon=>polygon.map(ringPath).join(' ')).join(' ')};

export default function ProvinceHeatmap({distribution=[],totalPosts=0}){
 const [geo,setGeo]=useState(null),[error,setError]=useState(false),[selected,setSelected]=useState(null);
 useEffect(()=>{let cancelled=false;fetch('/indonesia-provinces.geojson').then(r=>{if(!r.ok)throw Error('Map unavailable');return r.json()}).then(data=>{if(!cancelled)setGeo(data)}).catch(()=>{if(!cancelled)setError(true)});return ()=>{cancelled=true}},[]);
 const values=useMemo(()=>new Map(distribution.map(d=>[normalize(d.province),d])),[distribution]);
 const max=Math.max(1,...distribution.map(d=>Number(d.count)||0));
 return <section className="rounded-lg border p-4 space-y-3" aria-label="Posts by province choropleth map">
  <div className="flex flex-wrap items-center justify-between gap-2"><h5 className="font-semibold">Posts by province</h5><span className="text-xs text-slate-500">Posts associated with provinces · current campaign filters</span></div>
  {error?<p className="text-sm text-red-600">Indonesia map boundaries could not be loaded.</p>:!geo?<p className="text-sm text-slate-500">Loading Indonesia province map…</p>:<>
   <div className="w-full overflow-x-auto rounded-lg bg-[#f6fafb]">
    <svg viewBox="0 0 1050 460" className="w-full min-w-[580px] h-auto" role="img" aria-label="Map of Indonesia with 38 provinces shaded by associated post count">
     {geo.features.map(f=>{const name=f.properties.PROVINSI;const record=values.get(normalize(name));const count=Number(record?.count)||0;const intensity=count?Math.sqrt(count/max):0;const fill=!count?'#d9e3e8':intensity<0.2?'#fff4c2':intensity<0.4?'#fbd56b':intensity<0.6?'#f59e35':intensity<0.8?'#e85a2a':'#bd2026';return <path key={f.properties.KODE_PROV} d={geoPath(f.geometry)} fill={fill} stroke="#fff" strokeWidth="0.9" fillRule="evenodd" className="cursor-pointer hover:stroke-[#113d50] hover:stroke-[2.5px]" onMouseEnter={()=>setSelected({name,count,percentage:record?.percentage||0})} onClick={()=>setSelected({name,count,percentage:record?.percentage||0})}><title>{name}: {count.toLocaleString()} posts ({Number(record?.percentage||0).toFixed(1)}% of selected posts)</title></path>})}
    </svg>
   </div>
   <div className="flex flex-wrap items-center justify-between gap-3 text-xs"><p className="text-slate-600">{selected?<><strong>{selected.name}</strong> · {selected.count.toLocaleString()} posts · {Number(selected.percentage).toFixed(1)}%</>:'Hover over a province to see its post count and percentage.'}</p><div className="flex items-center gap-2"><span>Low</span><div className="h-3 w-28 rounded-sm" style={{background:'linear-gradient(to right,#fff4c2,#fbd56b,#f59e35,#e85a2a,#bd2026)'}}/><span>High · {max.toLocaleString()}</span></div></div>
  </>}
  <p className="text-xs text-slate-500">A post is counted once per province where the province is explicitly mentioned or provided as a source location; mentioning a province does not prove origin. Posts may connect to more than one province. Unresolved origins are not assigned to a map region.</p>
  <p className="text-[10px] text-slate-400">Province boundary source: denyherianto/indonesia-geojson-topojson-maps-with-38-provinces (CC BY 4.0).</p>
 </section>;
}
