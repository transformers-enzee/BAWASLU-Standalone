import {useEffect,useMemo,useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {Activity,ArrowRight,BookOpen,Globe2,Home,Layers3,RefreshCw,ShieldAlert,Workflow} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';
import {base44} from '@/api/base44Client';

// Only data already exposed by the authorized Command Centre may drive Home.
// Distinct saved supporting posts are not the number of connected social accounts.
const countValue=(value)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('id-ID'):'—';
const totalOf=(value)=>Object.values(value||{}).reduce((sum,n)=>sum+(Number(n)||0),0);
const safeCount=value=>Number.isFinite(Number(value))?Number(value):0;
const isCurrent=f=>['pending','investigating','monitoring','escalated'].includes(String(f.status||'').toLowerCase());
const timeLabel=date=>date?new Date(date+'T00:00:00Z').toLocaleDateString('id-ID',{day:'numeric',month:'short',timeZone:'UTC'}):'';
const project=([lon,lat])=>[26+((lon-94)/48.5)*950,17+((7.4-lat)/19.5)*390];
const polygonPath=ring=>ring.map((point,i)=>{const [x,y]=project(point);return (i?'L':'M')+x.toFixed(1)+','+y.toFixed(1)}).join('')+'Z';
const geometryPath=geo=>{
 if(!geo)return '';
 const polygons=geo.type==='Polygon'?[geo.coordinates]:geo.type==='MultiPolygon'?geo.coordinates:[];
 return polygons.map(poly=>poly.map(polygonPath).join('')).join('');
};
const normalize=value=>String(value||'').toLocaleLowerCase('id-ID').replace(/^(provinsi|province)\s+/,'').trim();
const aliases={'dki jakarta':'jakarta','daerah khusus ibukota jakarta':'jakarta',
 'di yogyakarta':'yogyakarta','daerah istimewa yogyakarta':'yogyakarta',
 'kepulauan bangka-belitung':'kepulauan bangka belitung'};
const keyOf=value=>aliases[normalize(value)]||normalize(value);
const textOf=(language,en,id)=>language==='id'?id:en;

function OverviewMap({counts={},language}){
 const [features,setFeatures]=useState(null),[error,setError]=useState(false),[selected,setSelected]=useState(null);
 const T=(en,id)=>textOf(language,en,id);
 useEffect(()=>{
  const controller=new AbortController();
  fetch('/indonesia-provinces.geojson',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error('map');return r.json()})
   .then(json=>{if(!controller.signal.aborted)setFeatures(Array.isArray(json.features)?json.features:[])})
   .catch(()=>{if(!controller.signal.aborted)setError(true)});
  return()=>controller.abort();
 },[]);
 const geo=useMemo(()=>{
  const result=new Map();
  for(const [name,value] of Object.entries(counts||{})){
   const count=safeCount(value);
   if(count>0)result.set(keyOf(name),count);
  }
  return result;
 },[counts]);
 const known=useMemo(()=>!features?[]:features.map(f=>{
  const name=String(f.properties?.PROVINSI||f.properties?.name||'');
  const code=String(f.properties?.KODE_PROV||f.id||'');
  return {code,name,count:geo.get(keyOf(name))||geo.get(code)||0,d:geometryPath(f.geometry)};
 }),[features,geo]);
 const max=Math.max(1,...known.map(x=>x.count));
 const matched=known.filter(x=>x.count>0);
 return <div>
  <div className="flex flex-wrap justify-between gap-2 items-start mb-4">
   <div><h2 className="font-bold text-[#2e2627] text-lg">{T('National information activity map','Peta Aktivitas Informasi Nasional')}</h2>
    <p className="text-xs text-slate-500 mt-1">{T('Saved geographic signals from the Command Centre','Sinyal geografis tersimpan dari Pusat Komando')}</p></div>
   <span className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600">{T('All saved sources','Semua sumber tersimpan')}</span>
  </div>
  {error?<p role="alert" className="py-24 text-sm text-slate-500">{T('Province boundaries unavailable.','Batas provinsi tidak tersedia.')}</p>
   :!features?<p className="py-24 text-sm text-slate-500">{T('Loading provincial map…','Memuat peta provinsi…')}</p>
   :<svg viewBox="0 0 1010 440" role="img" aria-label={T('Map of saved geographic signals across Indonesia','Peta sinyal geografis tersimpan di Indonesia')}
       className="w-full rounded-xl bg-[#fafaf9]">
      {known.map(f=><path key={f.code} d={f.d} fill={!f.count?'#e9e8e5':f.count/max>=0.7?'#b72b2a':f.count/max>=0.35?'#d8a34f':'#eacb90'}
       stroke="#fff" strokeWidth="1.2" fillRule="evenodd"
       onClick={()=>setSelected(f)} className="cursor-pointer outline-none hover:stroke-[#7a2331]">
       <title>{f.name}: {f.count.toLocaleString('id-ID')} {T('recorded signals','sinyal tercatat')}</title>
      </path>)}
     </svg>}
  <div className="flex flex-wrap justify-between gap-3 text-xs text-slate-500 mt-4">
    <div className="flex flex-wrap gap-3"><span><i className="inline-block h-2.5 w-2.5 bg-[#e9e8e5] rounded-full mr-1"/> {T('Unassigned','Belum terpetakan')}</span><span><i className="inline-block h-2.5 w-2.5 bg-[#d8a34f] rounded-full mr-1"/> {T('Recorded signal','Sinyal tercatat')}</span><span><i className="inline-block h-2.5 w-2.5 bg-[#b72b2a] rounded-full mr-1"/> {T('Higher volume','Volume lebih tinggi')}</span></div>
    <div>{selected?selected.name+' · '+selected.count.toLocaleString('id-ID'):matched.length+' '+T('provinces mapped','provinsi terpetakan')}</div>
  </div>
  <p className="mt-3 text-[11px] leading-5 text-slate-500">{T('Geographic mentions are unverified source context, not proven incident locations. Unmapped provinces are not zero-risk areas.','Penyebutan geografis adalah konteks sumber yang belum terverifikasi, bukan lokasi kejadian yang terbukti. Provinsi yang belum terpetakan tidak berarti tanpa risiko.')}</p>
 </div>;
}

function ActivityTrend({findings=[],language}){
 const T=(en,id)=>textOf(language,en,id);
 const series=useMemo(()=>{
  const daily={};
  for(const finding of findings)for(const [day,count] of Object.entries(finding.day_counts||{})){
   if(/^\d{4}-\d{2}-\d{2}$/.test(day))daily[day]=(daily[day]||0)+safeCount(count);
  }
  const days=Object.keys(daily).sort();if(!days.length)return [];
  const end=new Date(days[days.length-1]+'T00:00:00Z');
  return Array.from({length:7},(_,i)=>{const d=new Date(end.getTime()-(6-i)*86400000),key=d.toISOString().slice(0,10);return {day:key,count:daily[key]||0};});
 },[findings]);
 if(!series.length)return <div className="text-sm text-slate-500 py-14">{T('No dated conversations in the saved feed.','Tidak ada percakapan bertanggal dalam data tersimpan.')}</div>;
 const W=410,H=190,pad=24,peak=Math.max(1,...series.map(x=>x.count));
 const pts=series.map((x,i)=>({x:pad+i*(W-pad*2)/6,y:H-36-(x.count/peak)*112,count:x.count,day:x.day}));
 const path=pts.map((p,i)=>(i?'L':'M')+p.x.toFixed(2)+' '+p.y.toFixed(2)).join(' ');
 const area=path+' L'+pts[6].x+' '+(H-36)+' L'+pts[0].x+' '+(H-36)+' Z';
 return <>
  <svg viewBox={'0 0 '+W+' '+H} className="w-full" role="img" aria-label={T('Seven-day recorded conversation activity','Aktivitas percakapan tersimpan selama tujuh hari')}>
   {[0,0.5,1].map(k=><line key={k} x1={pad} y1={H-36-112*k} x2={W-pad} y2={H-36-112*k} stroke="#e5e7eb"/>)}
   <path d={area} fill="#dbc397" fillOpacity=".20"/>
   <path d={path} fill="none" stroke="#b48a42" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round"/>
   {pts.map(p=><circle key={p.day} cx={p.x} cy={p.y} r="3" fill="#b48a42"><title>{p.day}: {p.count} {T('posts','unggahan')}</title></circle>)}
   {[0,3,6].map(i=><text key={i} x={pts[i].x} y={H-12} fontSize="11" textAnchor={i===0?'start':i===6?'end':'middle'} fill="#64748b">{timeLabel(pts[i].day)}</text>)}
  </svg>
  <p className="text-xs text-slate-500">{T('Recorded posts in the latest seven publication dates (not a live growth forecast).','Unggahan tersimpan dalam rentang tujuh hari sampai tanggal publikasi terbaru (bukan prakiraan pertumbuhan langsung).')}</p>
 </>;
}
function StatCard({label,value,hint,icon:Icon,to}){
 return <Link to={to} className="rounded-2xl border border-[#e4e3e1] bg-white px-5 py-4 hover:border-[#bc9c9d] transition-colors shadow-[0_2px_10px_#1b273008]">
   <div className="flex items-center justify-between gap-2"><p className="text-[11px] font-bold tracking-[.12em] uppercase text-[#6a707b]">{label}</p><Icon className="text-[#a07360]" size={17}/></div>
   <strong className="block text-[30px] tracking-tight text-[#292527] leading-snug mt-2 tabular-nums">{countValue(value)}</strong>
   <p className="text-xs text-slate-500 mt-1 min-h-[20px]">{hint}</p>
 </Link>;
}
export default function IntelligenceOverview(){
 const {language}=useLanguage();
 const {access}=useOutletContext()||{};
 const demo=Boolean(window.__BAWASLU_DEMO_REPLICA__);
 const T=(en,id)=>textOf(language,en,id);
 const [dashboard,setDashboard]=useState(null),[distribution,setDistribution]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[issuesError,setIssuesError]=useState('');
 const [version,setVersion]=useState(0);
 useEffect(()=>{
  let active=true;setLoading(true);setError('');setIssuesError('');
  const load=async()=>{
   if(demo){
    const {demoHomeRadar}=await import('@/demo/homeRadarSnapshot.js');
    return demoHomeRadar();
   }
   const [d,t]=await Promise.allSettled([base44.radar.dashboard(),base44.radar.issueDistribution()]);
   if(d.status==='rejected')throw d.reason;
   return {dashboard:d.value,distribution:t.status==='fulfilled'?t.value:null,
     issuesError:t.status==='rejected'?String(t.reason?.message||'Unavailable'):''};
  };
  load().then(data=>{if(active){setDashboard(data.dashboard);setDistribution(data.distribution);setIssuesError(data.issuesError||'')}})
   .catch(err=>{if(active){setDashboard(null);setDistribution(null);setError(err.message||'Unable to load Command Centre data')}})
   .finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[demo,version]);
 const findings=Array.isArray(dashboard?.findings)?dashboard.findings:[];
 const operations=findings.filter(f=>(f.perspectives||['operations']).includes('operations'));
 const monitored=dashboard?Number(dashboard.source_total)||0:null;
 const narratives=dashboard?operations.filter(f=>(f.players||[]).includes('narratives')).length:null;
 const priority=dashboard?operations.filter(f=>['pending','investigating'].includes(f.status)).length:null;
 const followups=dashboard?operations.filter(f=>isCurrent(f)&&Boolean(f.next_followup)).length:null;
 const topics=(distribution?.operations?.topics||[]).slice().sort((a,b)=>safeCount(b.count)-safeCount(a.count)).slice(0,3);
 const mapped=dashboard?.geo_signal_counts||{};
 const regional=access?.geographic_scope&&access.geographic_scope!=='Nationwide';
 return <div className="space-y-5" data-home-overview="command-centre-source">
   <div className="flex flex-wrap items-start justify-between gap-3">
    <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#a04d52]">{T('Intelligence overview','Ringkasan Intelijen')}</p>
      <h1 className="mt-1 text-2xl md:text-3xl font-bold tracking-tight text-[#2d2628]">{regional?T('Regional intelligence overview','Ringkasan Intelijen Regional'):T('National intelligence overview','Ringkasan Intelijen Nasional')}</h1>
      <p className="mt-1 text-sm text-slate-500">{T('An at-a-glance view of authorized, saved Command Centre intelligence.','Gambaran singkat intelijen tersimpan yang tersedia dalam Pusat Komando sesuai kewenangan.')}</p>
    </div>
    <div className="flex items-center gap-2">
      {demo&&<span className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-900">{T('FROZEN TRAINING DATA','DATA PELATIHAN TETAP')}</span>}
      <button type="button" onClick={()=>setVersion(v=>v+1)} disabled={loading} className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-[#464a52] disabled:opacity-50"><RefreshCw size={14}/>{T('Refresh','Segarkan')}</button>
    </div>
   </div>
   {error&&<p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{T('Unable to load authorized Command Centre data. No substitute numbers are shown.','Data Pusat Komando yang berwenang gagal dimuat. Angka pengganti tidak ditampilkan.')} {error}</p>}
   {loading&&<p role="status" className="text-sm text-slate-500">{T('Reading saved Command Centre intelligence…','Membaca intelijen tersimpan dari Pusat Komando…')}</p>}
   <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
    <StatCard icon={Globe2} label={T('Monitored Sources','Sumber Dipantau')} value={monitored} hint={T('Unique supporting posts','Unggahan pendukung unik')} to="/smart-radar"/>
    <StatCard icon={Layers3} label={T('Emerging Narratives','Narasi Berkembang')} value={narratives} hint={T('Operational narrative groups','Kelompok narasi operasional')} to="/smart-radar"/>
    <StatCard icon={ShieldAlert} label={T('Priority Issues','Isu Prioritas')} value={priority} hint={T('Awaiting or under review','Perlu atau dalam peninjauan')} to="/inbox"/>
    <StatCard icon={Workflow} label={T('Active Follow-ups','Tindak Lanjut Aktif')} value={followups} hint={T('Open actions with due dates','Tindakan terbuka dengan tenggat')} to="/smart-radar"/>
   </div>
   <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.75fr)_minmax(300px,1fr)] gap-4">
    <section className="rounded-2xl border border-[#e4e3e1] bg-white p-5 md:p-6 shadow-[0_2px_10px_#1b273008]">
      <OverviewMap counts={mapped} language={language}/>
      <Link to="/smart-radar" className="inline-flex items-center gap-2 mt-4 text-sm font-semibold text-[#9a303c] hover:underline">{T('Explore geographic signals in Command Centre','Jelajahi sinyal geografis di Pusat Komando')}<ArrowRight size={15}/></Link>
    </section>
    <div className="grid gap-4">
      <section className="rounded-2xl border border-[#e4e3e1] bg-white p-5 md:p-6 shadow-[0_2px_10px_#1b273008]">
       <div className="flex items-start justify-between gap-2"><div><h2 className="font-bold text-lg text-[#2e2627]">{T('Priority Issues','Isu Prioritas')}</h2><p className="text-xs text-slate-500 mt-1">{T('Top three saved issue-distribution themes','Tiga tema teratas dari distribusi isu tersimpan')}</p></div><ShieldAlert className="text-[#b12d32]" size={20}/></div>
       {issuesError&&<p role="alert" className="mt-4 text-sm text-red-700">{T('Issue distribution unavailable.','Distribusi isu tidak tersedia.')}</p>}
       {!issuesError&&!topics.length&&<p className="mt-5 text-sm text-slate-500">{T('No classified topics available.','Belum ada topik terklasifikasi.')}</p>}
       <ol className="mt-5 space-y-5">{topics.map((topic,index)=><li key={topic.id||topic.title} className="flex items-start gap-3">
         <span className={'mt-2 h-2.5 w-2.5 shrink-0 rounded-full '+(index===0?'bg-[#ca3434]':'bg-[#cfa45c]')}/>
         <div className="min-w-0 flex-1"><div className="flex justify-between gap-3"><p className="text-sm font-semibold text-[#323037]">{translateTopic(topic.title,language)}</p><strong className="text-sm tabular-nums text-[#77343a]">{safeCount(topic.count).toLocaleString('id-ID')}</strong></div>
          <p className="mt-1 text-xs text-slate-500">{T('Saved source mentions · not verified violations','Penyebutan sumber tersimpan · bukan pelanggaran terverifikasi')}</p>
         </div></li>)}</ol>
       <Link to="/smart-radar" className="inline-flex items-center gap-2 mt-6 text-xs font-semibold text-[#9a303c] hover:underline">{T('View full issue distribution','Lihat distribusi isu lengkap')}<ArrowRight size={13}/></Link>
      </section>
      <section className="rounded-2xl border border-[#e4e3e1] bg-white p-5 md:p-6 shadow-[0_2px_10px_#1b273008]">
       <div className="flex gap-2 items-center justify-between"><div><h2 className="text-lg font-bold text-[#2e2627]">{T('Activity Trend · 7 Days','Tren Aktivitas · 7 Hari')}</h2><p className="text-xs text-slate-500 mt-1">{T('Conversation activity from saved posts','Aktivitas percakapan dari unggahan tersimpan')}</p></div><Activity size={20} className="text-[#b48a42]"/></div>
       <div className="mt-3"><ActivityTrend findings={operations} language={language}/></div>
       <Link to="/smart-radar" className="inline-flex items-center gap-2 mt-3 text-xs font-semibold text-[#9a303c] hover:underline">{T('Open conversation activity','Buka aktivitas percakapan')}<ArrowRight size={13}/></Link>
      </section>
    </div>
   </div>
   <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
     <p>{demo?T('Read-only snapshot · 3 November 2026','Snapshot hanya baca · 3 November 2026'):T('Authorized saved evidence only · no estimated or simulated growth figures','Hanya bukti tersimpan sesuai kewenangan · tanpa estimasi atau angka pertumbuhan simulasi')}</p>
     {demo&&<Link to="/guide" className="inline-flex items-center gap-2 font-semibold text-[#8b2937]"><BookOpen size={14}/>{T('How to use the training guide','Cara menggunakan panduan pelatihan')}</Link>}
   </div>
 </div>;
}
const TOPIC_ID={
 'Electoral Operations':'Penyelenggaraan Pemilu','Public Concern':'Kekhawatiran Publik','Public Information':'Informasi Publik',
 'BAWASLU Reputation':'Reputasi BAWASLU','Campaign Rules':'Aturan Kampanye','Election Administration':'Administrasi Pemilu',
 'Other saved relevant sources':'Sumber relevan tersimpan lainnya','Other':'Lainnya',
 'Election money politics':'Politik Uang Pemilu','Voter register accuracy':'Ketepatan Daftar Pemilih',
 'Election dispute proceedings':'Proses Sengketa Pemilu','Candidate nomination process':'Proses Pencalonan',
 'Participatory election oversight':'Pengawasan Pemilu Partisipatif'};
function translateTopic(title,language){return language==='id'?(TOPIC_ID[String(title||'')]||String(title||'')):String(title||'');}
