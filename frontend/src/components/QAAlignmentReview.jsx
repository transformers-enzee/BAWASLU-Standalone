import {useEffect,useState} from 'react';
import {ClipboardCheck,ChevronDown,ExternalLink,RefreshCw} from 'lucide-react';

const cats=[
'Allegations / Violations','Voter Register / PDPB','Citizen Reports / Public Concerns',
'Disputes / Legal','Participatory Oversight','Election Operations','Digital Risks / Information'
];
const token=()=>localStorage.getItem('bawaslu_access_token')||'';
async function api(path,body){
 const opt={method:body?'POST':'GET',cache:'no-store',
   headers:{Authorization:'Bearer '+token()}};
 if(body){opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(body)}
 const res=await fetch('/api/smart-radar/qa/alignment'+path,opt);
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'QA analyst review request failed');
 return data;
}
export default function QAAlignmentReview({language='en',onSaved}){
 const indo=language==='id';
 const [data,setData]=useState(null),[active,setActive]=useState(null),
   [decision,setDecision]=useState('confirmed'),
   [category,setCategory]=useState(''),[relation,setRelation]=useState('unresolved'),
   [reason,setReason]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),
   [notice,setNotice]=useState('');
 const refresh=async()=>{const q=await api('');setData(q)};
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 const pick=(x)=>{
   setActive(x);setDecision('confirmed');setCategory(x.uploaded_category);
   setRelation(x.source_conflict?'unresolved':'not_applicable');
   setReason('');setError('');setNotice('');
 };
 async function save(){
   setBusy(true);setError('');setNotice('');
   try{
     await api('/decision',{qa_id:active.qa_id,decision,
       approved_category:decision==='needs_context'?null:decision==='confirmed'?active.uploaded_category:category,
       source_relation:relation,rationale:reason.trim()});
     setNotice(indo?'Keputusan analis tersimpan dengan riwayat audit.':'Analyst decision saved with audit history.');
     await refresh();onSaved?.();setActive(null);
   }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 const items=data?.items||[];
 return <section className="rounded-lg border border-slate-200 bg-white p-4" aria-label="Human label alignment">
   <div className="flex flex-wrap items-start justify-between gap-2">
     <div><h2 className="font-semibold text-lg flex items-center gap-2"><ClipboardCheck size={18}/>{indo?'Tinjau Acuan Kategori Shahrin':'Review Shahrin’s Reference Categories'}</h2>
       <p className="text-xs text-slate-600 mt-1">{indo?
       'Konfirmasi alasan kategori manusia, bukan mengubahnya otomatis mengikuti tebakan AI. Hasil yang belum disetujui tidak dipakai dalam tes prompt baru.':
       'Record why the analyst chose a category. Never automatically overwrite the original human reference with an AI guess. Unresolved cases are excluded from new prompt tests.'}</p></div>
     <button type="button" onClick={()=>refresh().catch(e=>setError(e.message))} disabled={busy} className="flex items-center gap-1 border rounded-lg px-3 py-2 text-xs"><RefreshCw size={14}/>{indo?'Muat ulang':'Refresh'}</button>
   </div>
   <div className="grid grid-cols-2 gap-2 mt-3">
     <div className="bg-slate-50 rounded-lg p-3"><b className="text-xl">{data?.pending??'—'}</b><p className="text-xs text-slate-500">{indo?'Perlu peninjauan':'Need analyst review'}</p></div>
     <div className="bg-slate-50 rounded-lg p-3"><b className="text-xl">{data?.total??'—'}</b><p className="text-xs text-slate-500">{indo?'Kasus terpilih':'Flagged records'}</p></div>
   </div>
   <p className="text-xs text-amber-900 mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3">{indo?
      'Pilih Confirm hanya jika telah membaca sumber dan setuju dengan kategori. Gunakan Correct jika label perlu diubah. Gunakan Needs clarification jika masih perlu penjelasan Shahrin. Nama peninjau diambil dari akun yang masuk, bukan diklaim sebagai Shahrin secara otomatis.':
      'Select Confirm only after reading the source and accepting its category. Correct requires a different category. Needs clarification keeps it unresolved. Reviewer identity comes from the signed-in account, not automatically from Shahrin.'}</p>
   {error&&<p role="alert" className="mt-3 p-3 text-xs bg-red-50 text-red-700 rounded-lg">{error}</p>}
   {notice&&<p role="status" className="mt-3 p-3 text-xs bg-emerald-50 text-emerald-700 rounded-lg">{notice}</p>}
   <div className="mt-3 space-y-2">
     {items.map(item=><div key={item.qa_id} className={'rounded-lg border p-3 '+(item.training_blocked_reason?'border-amber-200':'border-slate-200')}>
       <button type="button" onClick={()=>active?.qa_id===item.qa_id?setActive(null):pick(item)}
         className="w-full flex items-start justify-between gap-3 text-left">
         <div className="min-w-0">
           <p className="text-sm font-semibold">{item.qa_id} <span className="font-normal text-slate-500">· {item.platform}</span></p>
           <p className="text-xs text-slate-600 mt-1">{indo?'Label dari Excel':'Original human label'}: <b>{item.uploaded_category}</b></p>
           <p className="text-xs text-slate-500 mt-1">{item.reason_for_queue}</p>
           <p className={'text-xs mt-1 '+(item.training_blocked_reason?'text-amber-800':'text-emerald-700')}>{item.training_blocked_reason?
             (indo?'Belum dipakai untuk tes prompt baru':'Excluded from new prompt tests'):
             (indo?'Sudah ditinjau':'Reviewed')}</p>
         </div>
         <ChevronDown size={16} className={'shrink-0 mt-1 '+(active?.qa_id===item.qa_id?'rotate-180':'')}/>
       </button>
       {active?.qa_id===item.qa_id&&<div className="border-t border-slate-200 mt-3 pt-3 space-y-3">
         <div><p className="text-xs font-semibold text-slate-700">{indo?'Teks sumber lengkap':'Original source text'}</p>
           <p className="text-xs whitespace-pre-wrap bg-slate-50 p-3 mt-1 max-h-60 overflow-y-auto">{item.message_original}</p>
           <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-[#147968] text-xs underline inline-flex items-center gap-1 mt-1"><ExternalLink size={13}/>{indo?'Buka sumber':'Open source URL'}</a>
         </div>
         {item.source_conflict&&<div className="bg-amber-50 border border-amber-200 rounded-lg p-2 text-xs text-amber-900">
           {indo?'URL ini digunakan oleh':'This URL is shared by'} {item.source_rows} {indo?'entri. Jangan anggap sama atau berbeda tanpa memeriksa isinya.':'entries. Check whether these are genuinely different comments or the same underlying content.'}
         </div>}
         {item.decision&&<p className="text-xs text-slate-600">{indo?'Keputusan sebelumnya':'Previous reviewer decision'}: {item.decision} · {item.reviewer_name}
           <span className="block mt-1 whitespace-pre-wrap">{item.reasoning}</span></p>}
         <label className="block text-xs">{indo?'Keputusan analis':'Analyst decision'}
           <select className="mt-1 w-full border rounded-lg px-3 py-2 bg-white" value={decision} onChange={e=>{setDecision(e.target.value);setCategory(item.uploaded_category)}}>
             <option value="confirmed">{indo?'Konfirmasi label asli':'Confirm uploaded label'}</option>
             <option value="corrected">{indo?'Koreksi label asli':'Correct category'}</option>
             <option value="needs_context">{indo?'Perlu penjelasan Shahrin':'Needs Shahrin clarification'}</option>
           </select>
         </label>
         {decision==='corrected'&&<label className="block text-xs">{indo?'Kategori yang disetujui':'Corrected primary category'}
           <select className="mt-1 w-full border rounded-lg px-3 py-2 bg-white" value={category} onChange={e=>setCategory(e.target.value)}>
             {cats.map(c=><option key={c} value={c}>{c}</option>)}
           </select>
         </label>}
         {item.source_conflict&&<label className="block text-xs">{indo?'Hubungan dengan entri URL yang sama':'Relationship to other records sharing this URL'}
           <select className="mt-1 w-full border rounded-lg px-3 py-2 bg-white" value={relation} onChange={e=>setRelation(e.target.value)}>
             <option value="unresolved">{indo?'Belum pasti':'Unresolved'}</option>
             <option value="distinct_comments">{indo?'Komentar atau isi yang berbeda':'Distinct comments / content'}</option>
             <option value="same_underlying_content">{indo?'Konten yang sama / duplikat':'Same underlying content'}</option>
           </select>
         </label>}
         <label className="block text-xs">{indo?'Alasan pilihan kategori (wajib, minimal 30 karakter)':'Why does this category fit? (required, at least 30 characters)'}
           <textarea className="mt-1 w-full border rounded-lg px-3 py-2 text-xs" rows={4} value={reason} maxLength={3000}
             onChange={e=>setReason(e.target.value)}
             placeholder={indo?'Tuliskan alasan Shahrin atau catat informasi yang perlu dikonfirmasi':'Record the analyst’s explanation, or exactly what still needs clarification'}/>
         </label>
         <button type="button" disabled={busy||reason.trim().length<30||(decision==='corrected'&&category===item.uploaded_category)}
           onClick={save} className="bg-[#147968] text-white rounded-lg px-4 py-2 text-xs disabled:opacity-50">
           {busy?(indo?'Menyimpan…':'Saving…'):(indo?'Simpan keputusan QA':'Save analyst QA decision')}
         </button>
       </div>}
     </div>)}
     {data&&!items.length&&<p className="text-xs text-slate-500 p-3">{indo?'Tidak ada kasus konflik.':'No flagged cases.'}</p>}
   </div>
 </section>
}
