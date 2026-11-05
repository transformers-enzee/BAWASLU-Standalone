import {useEffect,useState} from 'react';
import {MessageSquareHeart,X,Send,CheckCircle2,Star,Heart} from 'lucide-react';
import {useLocation,useNavigate} from 'react-router-dom';
import {useLanguage} from '@/lib/LanguageContext';

const browserFeedbackKey=Array.from(crypto.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,'0')).join('');
const moods=[
 ['',''],
 ['Not useful','Tidak bermanfaat'],
 ['Needs improvement','Perlu perbaikan'],
 ['Fair','Cukup'],
 ['Useful','Bermanfaat'],
 ['Very useful!','Sangat bermanfaat!']
];
export default function DemoFeedbackWidget(){
 const {language}=useLanguage(),loc=useLocation(),navigate=useNavigate();
 const T=(en,id)=>language==='id'?id:en;
 const [open,setOpen]=useState(()=>new URLSearchParams(window.location.search).get('feedback')==='open'),[rating,setRating]=useState(0),[hover,setHover]=useState(0);
 // A shareable /demo?feedback=open link opens the form on the initial load
 // and whenever visitors follow the link again through client-side navigation.
 useEffect(()=>{
  if(new URLSearchParams(loc.search).get('feedback')==='open'){
   setOpen(true);setDone(false);setError('');
  }
 },[loc.search]);
 const closeFeedback=()=>{
  setOpen(false);
  const params=new URLSearchParams(loc.search);
  if(params.get('feedback')==='open'){
   params.delete('feedback');
   navigate({pathname:loc.pathname,search:params.toString()?'?'+params.toString():'',hash:loc.hash},{replace:true});
  }
 };
 const [department,setDepartment]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[done,setDone]=useState(false),[error,setError]=useState('');
 const [website,setWebsite]=useState('');
 const current=hover||rating;
 const submit=async event=>{
  event.preventDefault();
  if(busy||rating===0||!department.trim())return;
  setBusy(true);setError('');
  try{
   const result=await fetch('/api/demo-feedback',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({category:'general',rating,department:department.trim(),message:message.trim(),
      page_path:'/demo'+(loc.pathname==='/'?'':loc.pathname),language,website,visitor_key:browserFeedbackKey})});
   const body=await result.json().catch(()=>({}));
   if(!result.ok)throw new Error(result.status===429?T('Too many submissions. Please try later.','Terlalu banyak kiriman. Coba lagi nanti.'):
    result.status===409?T('You already sent this rating.','Anda sudah mengirim penilaian ini.'):
    body.detail||T('Could not submit feedback.','Masukan tidak dapat dikirim.'));
   setDone(true);setDepartment('');setMessage('');setRating(0);setHover(0);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 };
 return <div data-demo-locale-owned="true" className="fixed bottom-5 right-5 z-[81]">
  <button type="button" onClick={()=>{setOpen(true);setDone(false);setError('')}} className="group inline-flex items-center gap-2.5 rounded-full bg-[#8a202b] px-5 py-3.5 text-sm font-bold text-white shadow-[0_10px_30px_rgba(109,19,32,.24)] transition hover:bg-[#a32d39] hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8a202b]">
   <MessageSquareHeart size={19} aria-hidden="true"/>{T('Give Feedback','Beri Masukan')}
  </button>
  {open&&<div className="fixed inset-0 z-[95] flex items-end justify-center bg-slate-950/60 p-2 backdrop-blur-[3px] sm:items-center sm:p-5"
   onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)closeFeedback()}}>
   <section role="dialog" aria-modal="true" aria-label={T('Rate the BAWASLU system','Nilai Sistem BAWASLU')} className="w-full max-w-[470px] max-h-[93vh] overflow-y-auto rounded-[24px] bg-white shadow-2xl">
    <div className="relative overflow-hidden rounded-t-[24px] bg-gradient-to-br from-[#711721] via-[#932331] to-[#b84946] px-6 pb-7 pt-6 text-white">
     <div aria-hidden="true" className="absolute -right-10 -top-14 h-44 w-44 rounded-full border-[28px] border-white/10"/>
     <button type="button" aria-label={T('Close','Tutup')} onClick={closeFeedback} className="absolute right-4 top-4 rounded-full bg-white/15 p-2 transition hover:bg-white/25"><X size={18}/></button>
     <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[11px] font-bold tracking-wider"><Heart size={13}/>{T('YOUR OPINION MATTERS','PENDAPAT ANDA BERARTI')}</span>
     <h2 className="mt-4 max-w-[340px] text-[25px] font-extrabold leading-tight">{T('How was your experience?','Bagaimana pengalaman Anda?')}</h2>
     <p className="mt-2 max-w-[345px] text-sm leading-6 text-white/85">{T('Your feedback helps us improve the BAWASLU system to better support election supervision.','Penilaian dan masukan Anda membantu kami menyempurnakan sistem BAWASLU agar lebih mendukung tugas pengawasan pemilu.')}</p>
    </div>
    {done?<div role="status" className="px-7 py-12 text-center">
      <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-50"><CheckCircle2 size={34} className="text-emerald-600"/></div>
      <h3 className="mt-4 text-xl font-bold text-slate-900">{T('Thank you for your rating!','Terima kasih atas penilaian Anda!')}</h3>
      <p className="mt-2 text-sm text-slate-600">{T('Your feedback has been saved for our team.','Masukan Anda telah disimpan untuk tim kami.')}</p>
      <button type="button" onClick={()=>setOpen(false)} className="mt-6 w-full rounded-xl bg-[#8a202b] py-3 text-sm font-bold text-white">{T('Done','Selesai')}</button>
    </div>:<form onSubmit={submit} className="space-y-5 px-6 pb-6 pt-6">
      <label className="block text-sm font-semibold text-slate-800">
       {T('Team or Bureau Name','Nama Tim atau Biro')} <span className="text-[#a32d39]">*</span>
       <input type="text" required minLength={1} maxLength={100} autoComplete="off" value={department} onChange={e=>setDepartment(e.target.value)}
        className="mt-2 block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-normal text-slate-800 outline-none transition focus:border-[#a43d48] focus:bg-white focus:ring-2 focus:ring-rose-100"
        placeholder={T('e.g. Biro Hukum dan Humas','Biro Hukum dan Humas')}/>
      </label>
      <fieldset className="text-center">
       <legend className="w-full text-center text-sm font-bold text-slate-800">{T('How useful is the BAWASLU system?','Seberapa bermanfaat sistem BAWASLU?')} <span className="text-[#a32d39]">*</span></legend>
       <div className="mt-4 flex items-center justify-center gap-2" onMouseLeave={()=>setHover(0)}>
        {[1,2,3,4,5].map(n=><button key={n} type="button" aria-label={T('Rate '+n+' out of 5 stars','Beri '+n+' dari 5 bintang')} aria-pressed={rating===n} onMouseEnter={()=>setHover(n)} onFocus={()=>setHover(n)} onBlur={()=>setHover(0)} onClick={()=>setRating(n)} className="rounded-xl p-1.5 transition-transform hover:scale-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500">
          <Star size={40} strokeWidth={1.8} className={n<=current?'text-amber-400 drop-shadow-sm':'text-slate-300'} fill={n<=current?'#fbbf24':'transparent'}/>
         </button>)}
       </div>
       <p aria-live="polite" className={'mt-3 min-h-[22px] text-sm font-bold '+(current?'text-[#8a202b]':'text-slate-400')}>{current?T(moods[current][0],moods[current][1]):T('Tap a star to rate','Ketuk bintang untuk menilai')}</p>
      </fieldset>
      <div className="h-px bg-slate-100"/>
      <label className="block text-sm font-semibold text-slate-800">
       {T('Anything you would like to share?','Ada masukan lain?')} <span className="ml-1 text-xs font-normal text-slate-400">({T('Optional','Opsional')})</span>
       <textarea className="mt-2 block min-h-[108px] w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-normal text-slate-800 outline-none transition focus:border-[#a43d48] focus:bg-white focus:ring-2 focus:ring-rose-100" maxLength={1500}
        value={message} onChange={e=>setMessage(e.target.value)}
        placeholder={T('What should we improve in the BAWASLU system?','Apa yang perlu kami tingkatkan pada sistem BAWASLU?')}/>
      </label>
      <input aria-hidden="true" tabIndex={-1} autoComplete="off" className="hidden" value={website} onChange={e=>setWebsite(e.target.value)} name="website"/>
      {error&&<p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={busy||rating===0||!department.trim()} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#8a202b] px-4 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#a32d39] disabled:cursor-not-allowed disabled:bg-slate-300">
       <Send size={16}/>{busy?T('Sending…','Mengirim…'):T('Send my rating','Kirim Penilaian')}
      </button>
      <div className="rounded-xl bg-rose-50/80 px-4 py-3 text-center">
       <p className="text-xs font-semibold text-[#80212c]">{T('Your feedback will remain anonymous.','Masukan Anda akan tetap anonim.')}</p>
       <p className="mt-1 text-[11px] leading-5 text-slate-600">{T('We do not ask for your name or email. Your team or bureau will be visible to administrators.','Kami tidak meminta nama atau email Anda. Tim atau biro Anda akan terlihat oleh administrator.')}</p>
       <p className="mt-2 text-[11px] leading-5 text-slate-600">{T('Your input helps us improve the BAWASLU system and make it more useful for officers.','Masukan Anda membantu kami menyempurnakan sistem BAWASLU agar semakin bermanfaat bagi petugas.')}</p>
      </div>
    </form>}
   </section>
  </div>}
 </div>;
}
