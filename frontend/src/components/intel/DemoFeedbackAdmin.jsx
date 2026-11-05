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
 const [category,setCategory]=useState('ALL'),[page,setPage]=useState('ALL'),[department,setDepartment]=useState('ALL');
 const [pendingDelete,setPendingDelete]=useState(null),[deleting,setDeleting]=useState(false),[deleteMessage,setDeleteMessage]=useState('');
 const load=async()=>{setBusy(true);setError('');try{
  const result=await base44.demoFeedback.admin();setData(result);
 }catch(e){setError(e.message||'Feedback unavailable')}finally{setBusy(false)}};
 useEffect(()=>{load()},[]);
 const remove=async()=>{
  if(!pendingDelete||deleting)return;
  setDeleting(true);setError('');setDeleteMessage('');
  try{
   await base44.demoFeedback.remove(pendingDelete.id);
   setPendingDelete(null);
   await load();setDeleteMessage(T('Feedback deleted. Aggregates updated.','Masukan dihapus. Ringkasan diperbarui.'));
  }catch(e){setError(e.message||T('Unable to delete feedback.','Gagal menghapus masukan.'))}
  finally{setDeleting(false)}
 };
 const rows=useMemo(()=>(data?.recent||[]).filter(r=>(category==='ALL'||r.category===category)&&(page==='ALL'||r.page_path===page)&&(department==='ALL'||(r.department||'Not specified')===department)),[data,category,page,department]);
 if(busy&&!data)return <p className="text-sm text-slate-500">{T('Loading feedback…','Memuat masukan…')}</p>;
 return <section data-demo-feedback-admin="true" className="intel-card p-5 space-y-4">
  <div className="flex flex-wrap justify-between items-center gap-3"><div>
   <h2 className="font-semibold text-lg text-[#801b24]">{T('Demo Visitor Feedback','Masukan Pengunjung Demo')}</h2>
   <p className="text-xs text-slate-500">{T('Anonymous submissions from the public /demo. Not intelligence evidence.','Kiriman anonim dari /demo publik. Bukan bukti intelijen.')}</p>
  </div><button type="button" className="intel-ghost" disabled={busy} onClick={load}>{T('Refresh','Muat Ulang')}</button></div>
  {error&&<p role="alert" className="text-red-700 text-sm">{error}</p>}
  {deleteMessage&&<p role="status" className="text-emerald-700 text-sm">{deleteMessage}</p>}
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
  <div className="rounded-xl border p-3"><h3 className="text-sm font-semibold">{T('By team or department','Berdasarkan tim atau departemen')}</h3>
   {Object.entries(data?.by_department||{}).sort((a,b)=>b[1]-a[1]).map(([name,count])=><div key={name} className="flex justify-between gap-2 py-1 text-sm"><span className="break-words">{name==='Not specified'?T('Not specified','Tidak disebutkan'):name}</span><strong>{count}</strong></div>)}
  </div>
  <div className="flex flex-wrap gap-3">
   <label className="text-xs">{T('Category','Kategori')}
    <select className="intel-input mt-1 block" value={category} onChange={e=>setCategory(e.target.value)}>
     <option value="ALL">{T('All categories','Semua kategori')}</option>
     {Object.keys(data?.by_category||{}).sort().map(key=><option key={key} value={key}>{categoryLabel(key,id)}</option>)}
    </select></label>
   <label className="text-xs">{T('Team or department','Tim atau departemen')}
    <select className="intel-input mt-1 block" value={department} onChange={e=>setDepartment(e.target.value)}>
     <option value="ALL">{T('All departments','Semua departemen')}</option>
     {Object.keys(data?.by_department||{}).sort().map(key=><option key={key} value={key}>{key==='Not specified'?T('Not specified','Tidak disebutkan'):key}</option>)}
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
    <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{categoryLabel(r.category,id)} · {r.rating??'—'} / 5 · {r.page_path} · {r.department||T('Department not provided','Departemen tidak disebutkan')}</span>
     <div className="flex items-center gap-3"><time>{new Date(r.created_at).toLocaleString(id?'id-ID':'en-GB',{timeZone:'Asia/Jakarta'})}</time><button type="button" className="rounded-lg border border-red-200 px-2.5 py-1 text-xs font-semibold text-red-700 hover:bg-red-50" onClick={()=>{setPendingDelete(r);setDeleteMessage('')}}>{T('Delete','Hapus')}</button></div></div>
    {r.message?<p className="whitespace-pre-wrap break-words text-sm text-slate-800">{r.message}</p>:<p className="text-xs italic text-slate-400">{T('Rating only · no comment','Hanya penilaian · tanpa komentar')}</p>}</article>)}
   {!rows.length&&<p className="text-sm text-slate-500">{T('No submissions for these filters','Tidak ada masukan untuk filter ini')}</p>}
  </div>
  {pendingDelete&&<div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-4" role="presentation">
   <section role="alertdialog" aria-modal="true" aria-labelledby="delete-demo-feedback-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
    <h3 id="delete-demo-feedback-title" className="text-lg font-bold text-slate-900">{T('Delete this feedback?','Hapus masukan ini?')}</h3>
    <p className="text-sm text-slate-600">{T('This permanently deletes the selected rating and comment from the feedback database, and updates the dashboard totals. This cannot be undone.','Penilaian dan komentar yang dipilih akan dihapus secara permanen dari basis data masukan, dan ringkasan diperbarui. Tindakan ini tidak dapat dibatalkan.')}</p>
    <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">#{pendingDelete.id} · {pendingDelete.rating??'—'} / 5 · {pendingDelete.page_path}</div>
    <div className="flex flex-wrap justify-end gap-2"><button type="button" className="intel-ghost" disabled={deleting} onClick={()=>setPendingDelete(null)}>{T('Cancel','Batal')}</button>
     <button type="button" className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={deleting} onClick={remove}>{deleting?T('Deleting…','Menghapus…'):T('Delete feedback','Hapus masukan')}</button></div>
   </section>
  </div>}
  {data?.total>200&&<p className="text-xs text-slate-500">{T('Showing latest 200 submissions; aggregates include all submissions.','Menampilkan 200 masukan terbaru; agregasi mencakup semua masukan.')}</p>}
 </section>;
}
