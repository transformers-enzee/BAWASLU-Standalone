import {useEffect,useMemo,useState} from 'react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';
const labels={general:['General','Umum'],usability:['Usability','Kemudahan penggunaan'],
 data:['Data','Data'],bug:['Issue','Masalah'],suggestion:['Suggestion','Saran']};
const categoryLabel=(key,id)=>(labels[key]||[key,key])[id?1:0];
export default function DemoFeedbackAdmin(){
 const {language}=useLanguage(),id=language==='id';
 const T=(en,indo)=>id?indo:en;
 const [data,setData]=useState(null),[busy,setBusy]=useState(true),[error,setError]=useState('');
 const [category,setCategory]=useState('ALL'),[page,setPage]=useState('ALL');
 const load=async()=>{setBusy(true);setError('');try{
  const result=await base44.demoFeedback.admin();setData(result);
 }catch(e){setError(e.message||'Feedback unavailable')}finally{setBusy(false)}};
 useEffect(()=>{load()},[]);
 const rows=useMemo(()=>(data?.recent||[]).filter(r=>(category==='ALL'||r.category===category)&&(page==='ALL'||r.page_path===page)),[data,category,page]);
 if(busy&&!data)return <p className="text-sm text-slate-500">{T('Loading feedback…','Memuat masukan…')}</p>;
 return <section data-demo-feedback-admin="true" className="intel-card p-5 space-y-4">
  <div className="flex flex-wrap justify-between items-center gap-3"><div>
   <h2 className="font-semibold text-lg text-[#801b24]">{T('Demo Visitor Feedback','Masukan Pengunjung Demo')}</h2>
   <p className="text-xs text-slate-500">{T('Anonymous submissions from the public /demo. Not intelligence evidence.','Kiriman anonim dari /demo publik. Bukan bukti intelijen.')}</p>
  </div><button type="button" className="intel-ghost" disabled={busy} onClick={load}>{T('Refresh','Muat Ulang')}</button></div>
  {error&&<p role="alert" className="text-red-700 text-sm">{error}</p>}
  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
   {[[data?.total??0,T('Total feedback','Total masukan')],[data?.average_rating??'—',T('Average score / 5','Rata-rata nilai / 5')],[data?.rated_count??0,T('Ratings received','Penilaian diterima')],[Object.keys(data?.by_page||{}).length,T('Demo pages','Halaman demo')]].map(([value,label])=>
    <div key={label} className="rounded-xl bg-slate-50 p-3"><strong className="text-2xl tabular-nums">{value}</strong><p className="text-xs text-slate-500">{label}</p></div>)}
  </div>
  <div className="grid gap-3 md:grid-cols-2">
   <div className="rounded-xl border p-3"><h3 className="text-sm font-semibold">{T('By feedback type','Berdasarkan jenis')}</h3>
    {Object.entries(data?.by_category||{}).sort((a,b)=>b[1]-a[1]).map(([name,value])=>
     <div key={name} className="flex justify-between gap-2 py-1 text-sm"><span>{categoryLabel(name,id)}</span><strong>{value}</strong></div>)}
    {!Object.keys(data?.by_category||{}).length&&<p className="text-sm text-slate-500 mt-2">{T('No feedback yet','Belum ada masukan')}</p>}
   </div>
   <div className="rounded-xl border p-3"><h3 className="text-sm font-semibold">{T('By demo page','Berdasarkan halaman demo')}</h3>
    {Object.entries(data?.by_page||{}).sort((a,b)=>b[1]-a[1]).map(([name,value])=>
     <div key={name} className="flex justify-between gap-2 py-1 text-sm"><span className="truncate">{name}</span><strong>{value}</strong></div>)}
   </div>
  </div>
  <div className="flex flex-wrap gap-3">
   <label className="text-xs">{T('Category','Kategori')}
    <select className="intel-input mt-1 block" value={category} onChange={e=>setCategory(e.target.value)}>
     <option value="ALL">{T('All categories','Semua kategori')}</option>
     {Object.keys(data?.by_category||{}).sort().map(key=><option key={key} value={key}>{categoryLabel(key,id)}</option>)}
    </select></label>
   <label className="text-xs">{T('Page','Halaman')}
    <select className="intel-input mt-1 block" value={page} onChange={e=>setPage(e.target.value)}>
     <option value="ALL">{T('All pages','Semua halaman')}</option>
     {Object.keys(data?.by_page||{}).sort().map(key=><option key={key}>{key}</option>)}
    </select></label>
  </div>
  <h3 className="text-sm font-semibold">{T('Recent submissions','Masukan terbaru')} ({rows.length})</h3>
  <div className="max-h-[520px] overflow-auto space-y-2">
   {rows.map(r=><article key={r.id} className="rounded-xl border p-3 space-y-2">
    <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{categoryLabel(r.category,id)} · {r.rating??'—'} / 5 · {r.page_path}</span>
     <time>{new Date(r.created_at).toLocaleString(id?'id-ID':'en-GB',{timeZone:'Asia/Jakarta'})}</time></div>
    {r.message?<p className="whitespace-pre-wrap break-words text-sm text-slate-800">{r.message}</p>:<p className="text-xs italic text-slate-400">{T('Rating only · no comment','Hanya penilaian · tanpa komentar')}</p>}</article>)}
   {!rows.length&&<p className="text-sm text-slate-500">{T('No submissions for these filters','Tidak ada masukan untuk filter ini')}</p>}
  </div>
  {data?.total>200&&<p className="text-xs text-slate-500">{T('Showing latest 200 submissions; aggregates include all submissions.','Menampilkan 200 masukan terbaru; agregasi mencakup semua masukan.')}</p>}
 </section>;
}
