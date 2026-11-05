import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS={POSITIVE:'#16866d',NEUTRAL:'#74869a',NEGATIVE:'#b3444e',UNKNOWN:'#d6b987'};
const LABELS={POSITIVE:'Positif',NEUTRAL:'Netral',NEGATIVE:'Negatif',UNKNOWN:'Belum diketahui'};
export default function AssistantInsights({snapshot}){
 if(!snapshot || snapshot.basis!=='PERMISSION_SCOPED_RETRIEVED_SAMPLE_ONLY' || !snapshot.social_posts)return null;
 const total=snapshot.social_posts;
 const sentiment=Object.entries(snapshot.sentiment_counts||{}).filter(([key,value])=>COLORS[key]&&Number.isInteger(value)&&value>0).map(([key,value])=>({key,value,label:LABELS[key]}));
 const platforms=Object.entries(snapshot.platform_counts||{}).filter(([,value])=>Number.isInteger(value)&&value>0).sort((a,b)=>b[1]-a[1]).slice(0,5);
 return <section aria-label="Visual evidence snapshot" className="mt-4 rounded-xl border border-[#e4e9ef] bg-white p-4">
  <div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-semibold text-[#801b24]">Visualisasi bukti yang ditemukan</h3><p className="text-xs text-[#617789] mt-1">Distribusi pada sampel unggahan yang diambil, bukan keseluruhan audiens atau opini publik.</p></div><span className="rounded-lg bg-[#f5f1f1] px-3 py-2 text-sm font-bold text-[#801b24]">{total} unggahan</span></div>
  <div className="grid gap-4 md:grid-cols-2 mt-4">
   <div className="rounded-lg border border-[#e8edf1] p-3"><h4 className="text-sm font-semibold">Sentimen unggahan</h4><div className="h-44" role="img" aria-label={sentiment.map(x=>x.label+': '+x.value).join(', ')}>
    <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={sentiment} dataKey="value" nameKey="label" innerRadius={40} outerRadius={68} paddingAngle={2} isAnimationActive={false}>{sentiment.map(x=><Cell key={x.key} fill={COLORS[x.key]}/>)}</Pie><Tooltip formatter={(value)=>[value+' unggahan','Jumlah']}/></PieChart></ResponsiveContainer>
   </div><div className="flex flex-wrap gap-x-4 gap-y-2">{sentiment.map(x=><div key={x.key} className="flex items-center gap-1.5 text-xs"><span className="h-2.5 w-2.5 rounded-full" style={{background:COLORS[x.key]}}/><span>{x.label}: <strong>{x.value}</strong></span></div>)}</div></div>
   <div className="rounded-lg border border-[#e8edf1] p-3"><h4 className="text-sm font-semibold mb-3">Sumber berdasarkan platform</h4><div className="space-y-3">{platforms.map(([platform,count])=><div key={platform} className="text-xs"><div className="flex justify-between mb-1"><span>{platform}</span><strong>{count}</strong></div><div className="h-2 rounded-full bg-[#edf1f5]"><div className="h-2 rounded-full bg-[#a52a2f]" style={{width:(count/total*100)+'%'}}/></div></div>)}</div></div>
  </div>
  <p className="mt-3 text-[11px] text-[#617789]">Angka berasal dari label data yang tersimpan untuk rekaman terpilih. Sumber belum tentu diverifikasi secara independen.</p>
 </section>;
}
