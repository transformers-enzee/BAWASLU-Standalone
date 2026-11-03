import {useState} from 'react';
import {Eye,EyeOff,LockKeyhole,ShieldCheck} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

// No plaintext training password stored in the source or in browser storage.
// This local demonstration gate is NOT server-side authentication.
const CHECKSUM='3314c45a1165ae5883fe02107d278ed19c423e7a6a78c28487c3b0082c43744e';
const STORE='bawaslu_demo_training_session';
async function digest(value){
 const bytes=new TextEncoder().encode(value);
 const buffer=await window.crypto.subtle.digest('SHA-256',bytes);
 return [...new Uint8Array(buffer)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
export default function DemoTrainingLogin({onSuccess}){
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[visible,setVisible]=useState(false);
 const [language,setLanguage]=useState(()=>{try{return localStorage.getItem('bawaslu-language')==='en'?'en':'id'}catch{return 'id'}});
 const T=(en,id)=>language==='id'?id:en;
 const setLocale=lang=>{setLanguage(lang);try{localStorage.setItem('bawaslu-language',lang)}catch{}};
 const login=async event=>{
   event.preventDefault();setBusy(true);setError('');
   try{
     const result=await digest(email.trim().toLowerCase()+'\n'+password);
     if(result!==CHECKSUM){
       setError(T('Invalid training credentials. Check the email and password.','Kredensial pelatihan tidak valid. Periksa email dan kata sandi.'));
       return;
     }
     sessionStorage.setItem(STORE,'v133.2');
     onSuccess();
   }catch{
     setError(T('Unable to verify this training login. Please use HTTPS.','Login pelatihan gagal diverifikasi. Gunakan HTTPS.'));
   }finally{setBusy(false)}
 };
 return <main className="min-h-screen flex items-center justify-center bg-[#faf7f5] px-4 py-8" data-demo-training-login="true">
  <div className="w-full max-w-[430px] overflow-hidden rounded-2xl border border-[#eadcdc] bg-white shadow-[0_16px_50px_#43161f15]">
   <header className="bg-[#801b24] px-7 py-6 text-white flex items-center justify-between gap-3">
    <div className="flex items-center gap-3"><img src="/bawaslu-emblem.svg" alt="BAWASLU" className="h-11 w-11 object-contain bg-white rounded-md p-1"/>
     <div><div className="text-lg font-bold tracking-wide">BAWASLU</div><p className="text-[10px] tracking-[.20em]">SMART RADAR · DEMO</p></div></div>
    <div className="flex gap-1 rounded-lg border border-white/40 p-1 text-xs">
      <button type="button" aria-pressed={language==='en'} onClick={()=>setLocale('en')} className={'px-2 py-1 rounded '+(language==='en'?'bg-white text-[#801b24]':'text-white')}>EN</button>
      <button type="button" aria-pressed={language==='id'} onClick={()=>setLocale('id')} className={'px-2 py-1 rounded '+(language==='id'?'bg-white text-[#801b24]':'text-white')}>ID</button>
    </div>
   </header>
   <div className="p-7">
    <div className="flex items-center gap-2 text-[#801b24]"><ShieldCheck size={20}/><h1 className="font-bold text-xl">{T('Training Participant Login','Login Peserta Pelatihan')}</h1></div>
    <p className="text-sm text-slate-600 mt-2 leading-6">{T('Sign in to access the guided, read-only training prototype.','Masuk untuk mengakses prototipe pelatihan terpandu yang hanya dapat dibaca.')}</p>
    <form className="mt-6 space-y-4" onSubmit={login}>
     <div><label htmlFor="demo-email" className="block text-sm font-semibold text-slate-700 mb-2">{T('Email','Email')}</label>
      <input id="demo-email" name="email" type="email" required autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)} placeholder="training@bawaslu.id" className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a52a2f]"/></div>
     <div><label htmlFor="demo-password" className="block text-sm font-semibold text-slate-700 mb-2">{T('Password','Kata Sandi')}</label>
      <div className="relative"><input id="demo-password" name="password" type={visible?'text':'password'} required autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a52a2f]"/>
       <button type="button" aria-label={visible?T('Hide password','Sembunyikan kata sandi'):T('Show password','Tampilkan kata sandi')} onClick={()=>setVisible(v=>!v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div></div>
     {error&&<p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
     <button type="submit" disabled={busy} className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#801b24] px-4 py-3 font-semibold text-sm text-white hover:bg-[#a52a2f] disabled:opacity-60">
      <LockKeyhole size={17}/>{busy?T('Verifying…','Memverifikasi…'):T('Enter Training Demo','Masuk ke Demo Pelatihan')}</button>
    </form>
    <p className="mt-5 text-xs text-slate-500">{T('This is a fixed, read-only demonstration. Changes do not affect the main BAWASLU system.','Ini merupakan demonstrasi dengan data tetap dan hanya baca. Perubahan tidak memengaruhi sistem utama BAWASLU.')}</p>
   </div>
  </div>
 </main>;
}
