import {useEffect,useMemo,useState} from 'react';
import {Star,MessageSquareText,Users,RefreshCw,Trash2} from 'lucide-react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

function RatingStars({rating}){
 const score=Number(rating)||0;
 return <span className="inline-flex items-center gap-1" aria-label={score+' / 5'}>
  {[1,2,3,4,5].map(n=><Star key={n} size={20} strokeWidth={1.8}
   className={n<=score?'text-amber-500':'text-slate-300'} fill={n<=score?'#f6b53b':'none'}/>)}
 </span>;
}
export default function DemoFeedbackAdmin(){
 const {language}=useLanguage(),id=language==='id';
 const T=(en,indo)=>id?indo:en;
 const [data,setData]=useState(null),[busy,setBusy]=useState(true),[error,setError]=useState('');
 const [department,setDepartment]=useState('ALL');
 const [pendingDelete,setPendingDelete]=useState(null),[deleting,setDeleting]=useState(false),[deleteMessage,setDeleteMessage]=useState('');
 const load=async()=>{setBusy(true);setError('');try{
  const result=await base44.demoFeedback.admin();setData(result);
 }catch(e){setError(e.message||T('Feedback unavailable','Masukan tidak tersedia'))}finally{setBusy(false)}};
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
 const rows=useMemo(()=>(data?.recent||[]).filter(r=>department==='ALL'||(r.department||'Not specified')===department),[data,department]);
 const deptCount=Object.keys(data?.by_department||{}).length;
 if(busy&&!data)return <p className="text-sm text-slate-500">{T('Loading feedback…','Memuat masukan…')}</p>;
 return <section data-demo-feedback-admin="true" data-i18n-exempt="true" className="intel-card space-y-5 p-5 md:p-6">
  <div className="flex flex-wrap items-start justify-between gap-3">
   <div><h2 className="text-xl font-bold text-[#801b24]">{T('Demo Visitor Feedback','Masukan Pengunjung Demo')}</h2>
    <p className="mt-1 text-sm text-slate-500">{T('Anonymous feedback from training participants.','Masukan anonim dari peserta pelatihan.')}</p></div>
   <button type="button" className="intel-ghost inline-flex items-center gap-2" disabled={busy} onClick={load}><RefreshCw size={15}/>{T('Refresh','Muat Ulang')}</button>
  </div>
  {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
  {deleteMessage&&<p role="status" className="text-sm text-emerald-700">{deleteMessage}</p>}
  <div className="grid gap-3 sm:grid-cols-3">
   <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-center gap-2 text-sm text-slate-500"><MessageSquareText size={17}/>{T('Total feedback','Total masukan')}</div><strong className="mt-2 block text-3xl font-bold tabular-nums text-slate-900">{data?.total??0}</strong></div>
   <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4"><div className="text-sm text-slate-600">{T('Average rating','Rata-rata penilaian')}</div><div className="mt-2 flex flex-wrap items-center gap-2"><strong className="text-3xl font-bold tabular-nums text-slate-900">{data?.average_rating??'—'}</strong><span className="text-sm text-slate-500">/ 5</span><Star size={22} fill="#f6b53b" className="text-amber-500"/></div></div>
   <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-center gap-2 text-sm text-slate-500"><Users size={17}/>{T('Teams and bureaus','Tim dan biro')}</div><strong className="mt-2 block text-3xl font-bold tabular-nums text-slate-900">{deptCount}</strong></div>
  </div>
  <div className="flex flex-wrap items-end justify-between gap-3">
   <h3 className="text-base font-bold text-slate-800">{T('Feedback submissions','Daftar masukan')} <span className="font-normal text-slate-500">({rows.length})</span></h3>
   <label className="text-sm font-medium text-slate-700">{T('Team or bureau','Tim atau biro')}
    <select className="intel-input mt-1 block min-w-[225px]" value={department} onChange={e=>setDepartment(e.target.value)}>
     <option value="ALL">{T('All teams and bureaus','Semua tim dan biro')}</option>
     {Object.keys(data?.by_department||{}).sort().map(key=><option key={key} value={key}>{key==='Not specified'?T('Not specified','Tidak disebutkan'):key}</option>)}
    </select></label>
  </div>
  <div className="max-h-[680px] space-y-3 overflow-auto pr-1">
   {rows.map(r=><article key={r.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
     <div className="min-w-0 flex-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{T('Team or bureau','Tim atau biro')}</p>
      <h4 className="mt-1 break-words text-lg font-bold text-[#801b24]">{r.department||T('Not specified','Tidak disebutkan')}</h4>
     </div>
     <div className="flex flex-wrap items-center gap-3">
      <time className="text-xs text-slate-500">{new Date(r.created_at).toLocaleString(id?'id-ID':'en-GB',{timeZone:'Asia/Jakarta'})}</time>
      <button type="button" className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
       onClick={()=>{setPendingDelete(r);setDeleteMessage('')}}><Trash2 size={14}/>{T('Delete','Hapus')}</button>
     </div>
    </div>
    <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl bg-amber-50/60 px-3 py-2.5">
     <RatingStars rating={r.rating}/>
     <strong className="text-lg tabular-nums text-slate-900">{r.rating??'—'} / 5</strong>
    </div>
    {r.message&&<div className="mt-3"><p className="mb-1 text-xs font-semibold text-slate-500">{T('Comment','Komentar')}</p><p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">{r.message}</p></div>}
   </article>)}
   {!rows.length&&<p className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">{T('No feedback for this selection.','Belum ada masukan untuk pilihan ini.')}</p>}
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
