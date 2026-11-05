import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';

const COLORS={POSITIVE:'#168a70',NEUTRAL:'#8b99a8',NEGATIVE:'#af3946',UNKNOWN:'#d1aa68'};
const LABELS={POSITIVE:'Positif',NEUTRAL:'Netral',NEGATIVE:'Negatif',UNKNOWN:'Belum diketahui'};
const fmt=n=>Number(n||0).toLocaleString('id-ID');
const compact=n=>new Intl.NumberFormat('id-ID',{notation:'compact',maximumFractionDigits:1}).format(Number(n)||0);
const Panel=({title,children})=><div className="rounded-xl border border-[#e5eaf0] bg-white p-4"><h3 className="font-semibold text-[#263749] text-sm mb-3">{title}</h3>{children}</div>;
const Metric=({label,value,note})=><div className="rounded-xl border border-[#e5eaf0] bg-white p-3"><div className="text-xs text-[#64748b]">{label}</div><div className="text-xl font-bold text-[#801b24] mt-1 tabular-nums">{value}</div><div className="text-[11px] text-[#64748b] mt-1">{note}</div></div>;
export default function AssistantInsights({snapshot,grounding}){
 if(!snapshot||snapshot.basis!=='PERMISSION_SCOPED_RETRIEVED_SAMPLE_ONLY'||!snapshot.social_posts)return null;
 const total=snapshot.social_posts;
 const sentiments=Object.entries(snapshot.sentiment_counts||{}).filter(([k,v])=>COLORS[k]&&Number.isInteger(v)&&v>0).map(([k,v])=>({key:k,name:LABELS[k],value:v}));
 const platforms=Object.entries(snapshot.platform_counts||{}).filter(([,v])=>Number.isInteger(v)&&v>0).sort((a,b)=>b[1]-a[1]).slice(0,6);
 const engagement=Object.entries(snapshot.platform_engagement||{}).filter(([,v])=>Number.isInteger(v)&&v>0).sort((a,b)=>b[1]-a[1]).slice(0,6);
 const timeline=(snapshot.activity_by_date||[]).filter(x=>x&&typeof x.date==='string'&&Number.isInteger(x.posts)).slice(-31);
 const topics=Object.entries(snapshot.topic_counts||{}).slice(0,6);
 const maxEng=Math.max(1,...engagement.map(([,v])=>v));
 return <section className="mt-5 space-y-4" data-i18n-exempt aria-label="Dashboard sumber intelijen">
  <div className="flex flex-wrap justify-between items-center gap-2"><div><h2 className="text-lg font-bold text-[#801b24]">Lanskap percakapan pada bukti terpilih</h2><p className="text-xs text-[#64748b] mt-1">Statistik bersumber dari unggahan relevan yang tersedia; analisis AI menggunakan subset yang lebih kecil.</p></div><span className="rounded-full bg-[#f5ebec] text-[#801b24] px-3 py-1 text-xs font-semibold">Sampel · bukan survei publik</span></div>
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
   <Metric label="Unggahan dalam statistik" value={fmt(total)} note={fmt(snapshot.analysis_post_count||total)+' unggahan dianalisis AI'}/>
   <Metric label="Interaksi tercatat" value={snapshot.engagement_coverage?compact(snapshot.observed_engagement):'N/A'} note={fmt(snapshot.engagement_coverage||0)+' dari '+fmt(total)+' memiliki metrik'}/>
   <Metric label="Kanal sumber" value={fmt(platforms.length)} note="Dalam sampel yang diambil"/>
   <Metric label="Rentang tanggal" value={timeline.length?timeline[0].date.slice(5)+'–'+timeline[timeline.length-1].date.slice(5):'N/A'} note={fmt(snapshot.publication_date_coverage||0)+' tanggal valid'}/>
  </div>
  <div className="grid lg:grid-cols-2 gap-4">
   <Panel title="Komposisi label sentimen unggahan"><div className="h-44" role="img" aria-label={sentiments.map(x=>x.name+': '+x.value).join(', ')}><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={sentiments} dataKey="value" nameKey="name" innerRadius={40} outerRadius={68} paddingAngle={2} isAnimationActive={false}>{sentiments.map(x=><Cell key={x.key} fill={COLORS[x.key]}/>)}</Pie><Tooltip formatter={v=>[fmt(v)+' unggahan','Jumlah']}/></PieChart></ResponsiveContainer></div><div className="flex flex-wrap gap-3">{sentiments.map(x=><div key={x.key} className="text-xs flex gap-1 items-center"><span className="w-2.5 h-2.5 rounded-full" style={{background:COLORS[x.key]}}/>{x.name}: <strong>{fmt(x.value)}</strong></div>)}</div></Panel>
   <Panel title="Volume unggahan menurut platform"><div className="space-y-3 mt-2">{platforms.map(([platform,count])=><div key={platform}><div className="flex justify-between text-xs mb-1"><span>{platform}</span><strong>{fmt(count)}</strong></div><div className="h-2.5 rounded-full bg-[#eff2f5] overflow-hidden"><div className="h-full bg-[#992d37] rounded-full" style={{width:100*count/total+'%'}}/></div></div>)}</div></Panel>
  </div>
  {timeline.length>1&&<Panel title="Aktivitas berdasarkan tanggal unggah"><div className="h-48"><ResponsiveContainer width="100%" height="100%"><LineChart data={timeline} margin={{top:8,right:12,bottom:0,left:-23}}><CartesianGrid stroke="#e5eaf0" strokeDasharray="3 3"/><XAxis dataKey="date" tick={{fontSize:10}} tickFormatter={v=>v.slice(5)}/><YAxis allowDecimals={false} tick={{fontSize:10}}/><Tooltip formatter={v=>[fmt(v)+' unggahan','Volume']}/><Line type="monotone" dataKey="posts" stroke="#992d37" strokeWidth={2} dot={timeline.length<=10} isAnimationActive={false}/></LineChart></ResponsiveContainer></div><p className="text-xs text-[#64748b]">Bukan tren seluruh percakapan daring; hanya tanggal yang tercatat untuk sampel ini.</p></Panel>}
  {!!engagement.length&&<Panel title="Engagement tercatat menurut platform"><p className="text-xs text-[#64748b] mb-3">Metrik tersedia untuk {fmt(snapshot.engagement_coverage)} dari {fmt(total)} unggahan. Engagement dan volume ditampilkan terpisah karena berbeda satuan.</p><div className="space-y-3">{engagement.map(([platform,count])=><div className="grid grid-cols-[90px_1fr_80px] gap-3 items-center text-xs" key={platform}><span className="truncate">{platform}</span><div className="h-3 rounded-full bg-[#eff2f5] overflow-hidden"><div className="h-full bg-[#16869b] rounded-full" style={{width:100*count/maxEng+'%'}}/></div><strong className="text-right">{compact(count)}</strong></div>)}</div></Panel>}
  {!!topics.length&&<Panel title="Tema tercatat dalam label sumber"><div className="flex flex-wrap gap-2">{topics.map(([label,count])=><span key={label} className="rounded-full border border-[#e5eaf0] bg-[#f7f9fb] px-3 py-1 text-xs">{label} <strong>{fmt(count)}</strong></span>)}</div><p className="text-xs mt-2 text-[#64748b]">Label dapat berupa klasifikasi AI, bukan konfirmasi petugas.</p></Panel>}
  <p className="text-xs text-[#64748b]">{snapshot.notice} Seluruh angka menunjukkan unggahan, bukan jumlah orang, preferensi pemilih, ataupun total populasi daring.</p>
 </section>;
}
