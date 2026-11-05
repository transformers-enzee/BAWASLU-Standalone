import {useState} from 'react';
import {MessageSquareText,X,Send,CheckCircle2} from 'lucide-react';
import {useLocation} from 'react-router-dom';
import {useLanguage} from '@/lib/LanguageContext';

const browserFeedbackKey=Array.from(crypto.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,'0')).join('');
const categories=[
 ['general','General feedback','Masukan umum'],
 ['usability','Ease of use','Kemudahan penggunaan'],
 ['data','Information and data','Informasi dan data'],
 ['bug','Something not working','Fitur bermasalah'],
 ['suggestion','Feature suggestion','Saran fitur']
];
export default function DemoFeedbackWidget(){
 const {language}=useLanguage(),loc=useLocation();
 const T=(en,id)=>language==='id'?id:en;
 const [open,setOpen]=useState(false),[category,setCategory]=useState('general');
 const [rating,setRating]=useState(0),[message,setMessage]=useState('');
 const [busy,setBusy]=useState(false),[done,setDone]=useState(false),[error,setError]=useState('');
 const [website,setWebsite]=useState('');
 const submit=async event=>{
  event.preventDefault();if(busy||message.trim().length<10)return;
  setBusy(true);setError('');
  try{
   const result=await fetch('/api/demo-feedback',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({category,rating:rating||null,message:message.trim(),
      page_path:'/demo'+(loc.pathname==='/'?'':loc.pathname),language,website,visitor_key:browserFeedbackKey})});
   const body=await result.json().catch(()=>({}));
   if(!result.ok)throw new Error(result.status===429?T('Too many submissions. Please try later.','Terlalu banyak kiriman. Coba lagi nanti.'):
     result.status===409?T('This feedback was already submitted.','Masukan ini sudah dikirim.'):
     body.detail||T('Could not submit feedback.','Masukan tidak dapat dikirim.'));
   setDone(true);setMessage('');setRating(0);setCategory('general');
  }catch(e){setError(e.message)}finally{setBusy(false)}
 };
 return <div data-demo-locale-owned="true" className="fixed right-5 bottom-[110px] z-[81]">
  <button type="button" onClick={()=>{setOpen(true);setDone(false);setError('')}}
   className="flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-[#801b24] border border-[#d7b7bb] shadow-xl hover:bg-[#fff4f4]">
   <MessageSquareText size={18}/>{T('Give Feedback','Berikan Masukan')}
  </button>
  {open&&<div className="fixed inset-0 z-[95] flex items-end justify-center bg-slate-950/60 p-3 sm:items-center sm:p-5"
    onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)setOpen(false)}}>
   <section role="dialog" aria-modal="true" aria-label={T('Demo feedback','Masukan Demo')}
    className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl">
    <div className="flex items-start justify-between gap-3">
     <div><h2 className="text-xl font-bold text-[#801b24]">{T('Share your feedback','Bagikan Masukan Anda')}</h2>
      <p className="mt-1 text-sm text-slate-600">{T('Help us improve the BAWASLU demo. No login required.','Bantu kami meningkatkan demo BAWASLU. Tanpa perlu masuk akun.')}</p></div>
     <button type="button" className="rounded-lg border p-2" aria-label={T('Close','Tutup')} onClick={()=>setOpen(false)}><X size={18}/></button>
    </div>
    {done?<div role="status" className="py-8 text-center"><CheckCircle2 className="mx-auto text-emerald-600" size={36}/>
      <p className="mt-3 font-semibold">{T('Thank you! Your feedback was received.','Terima kasih! Masukan Anda telah diterima.')}</p>
      <button className="mt-5 rounded-lg border px-4 py-2 text-sm" onClick={()=>setOpen(false)}>{T('Close','Tutup')}</button></div>:
     <form onSubmit={submit} className="mt-5 space-y-4">
      <label className="block text-sm font-semibold text-slate-700">{T('Feedback type','Jenis masukan')}
       <select className="intel-input mt-1 w-full" value={category} onChange={e=>setCategory(e.target.value)}>
        {categories.map(([id,en,indo])=><option key={id} value={id}>{T(en,indo)}</option>)}
       </select>
      </label>
      <fieldset><legend className="text-sm font-semibold text-slate-700">{T('How useful is this demo? (optional)','Seberapa bermanfaat demo ini? (opsional)')}</legend>
       <div className="flex gap-2 mt-2">{[1,2,3,4,5].map(n=><button key={n} type="button" aria-pressed={rating===n}
        aria-label={n+' / 5'} onClick={()=>setRating(rating===n?0:n)}
        className={'h-10 w-10 rounded-lg border font-bold '+(rating===n?'bg-[#801b24] text-white':'bg-white text-slate-700')}>{n}</button>)}</div>
      </fieldset>
      <label className="block text-sm font-semibold text-slate-700">{T('Your feedback','Masukan Anda')}
       <textarea className="intel-input mt-1 w-full min-h-32" required minLength={10} maxLength={1500}
        value={message} onChange={e=>setMessage(e.target.value)}
        placeholder={T('Tell us what worked, what was confusing, or what to improve…','Ceritakan apa yang membantu, membingungkan, atau perlu ditingkatkan…')}/>
      </label>
      <input aria-hidden="true" tabIndex={-1} autoComplete="off" className="hidden" value={website} onChange={e=>setWebsite(e.target.value)} name="website"/>
      <p className="text-xs text-slate-500">{T('Anonymous feedback. The current demo page and your comments are saved for administrator review. Do not include personal information.','Masukan anonim. Halaman demo dan komentar disimpan untuk ditinjau administrator. Jangan sertakan informasi pribadi.')}</p>
      {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={busy||message.trim().length<10}
       className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-[#801b24] px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">
       <Send size={16}/>{busy?T('Submitting…','Mengirim…'):T('Submit Feedback','Kirim Masukan')}
      </button>
     </form>}
   </section>
  </div>}
 </div>;
}
