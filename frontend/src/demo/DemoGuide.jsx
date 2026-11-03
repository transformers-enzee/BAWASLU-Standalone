import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {BookOpen,ChevronRight,ChevronLeft,X,RotateCcw,ShieldCheck} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

/** Training overlay around the actual production modules. No API or persistence. */
const steps=[
 {path:'/',en:'Home and training orientation',id:'Beranda dan orientasi pelatihan',enText:'Start together with the instructor. Learn how the prototype works, what data is frozen, and why each stage matters before opening a module.',idText:'Mulai bersama instruktur. Pelajari alur prototipe, batasan data tetap, dan tujuan setiap tahap sebelum membuka modul.'},
 {path:'/social-listening',en:'01 · Social Listening',id:'01 · Pemantauan Media Sosial',enText:'Instructor: show monitoring campaigns, the original captured evidence, filters and assessment workflow. Participant: explore the fixed records without starting a real crawl.',idText:'Instruktur: tunjukkan kampanye pemantauan, bukti sumber, filter, dan alur penilaian. Peserta: jelajahi catatan tetap tanpa melakukan perayapan nyata.'},
 {path:'/inbox',en:'02 · Intelligence Inbox',id:'02 · Kotak Masuk Intelijen',enText:'Instructor: open an assessed post and explain the AI findings and verification steps. Participant: inspect supporting source material and test an in-browser review.',idText:'Instruktur: buka unggahan yang telah dinilai dan jelaskan hasil AI serta langkah verifikasi. Peserta: periksa bukti pendukung dan coba peninjauan di peramban.'},
 {path:'/smart-radar',en:'03 · Command Centre',id:'03 · Pusat Komando',enText:'Instructor: connect the saved Inbox evidence to operational and BAWASLU reputation perspectives, priority signals, and officer action. Participant: follow the supporting-source drill-down.',idText:'Instruktur: hubungkan bukti Kotak Masuk dengan perspektif operasional dan reputasi BAWASLU, sinyal prioritas, serta tindakan petugas. Peserta: telusuri sumber pendukungnya.'},
 {path:'/assistant',en:'04 · AI Assistant',id:'04 · Asisten AI',enText:'Instructor: demonstrate questions about sentiment, narratives and risks using predefined example responses. Participant: explore the interface; no live model, browsing or credits are used.',idText:'Instruktur: contohkan pertanyaan mengenai sentimen, narasi, dan risiko menggunakan jawaban contoh tetap. Peserta: jelajahi antarmuka tanpa AI langsung, penelusuran web, atau kredit.'}
];
export default function DemoGuide(){
 const [open,setOpen]=useState(false),[step,setStep]=useState(0);
 const nav=useNavigate(),{language}=useLanguage();
 const T=(en,id)=>language==='id'?id:en,entry=steps[step];
 const go=index=>{const n=Math.max(0,Math.min(index,steps.length-1));setStep(n);nav(steps[n].path);window.scrollTo({top:0})};
 return <div className="fixed bottom-5 right-5 z-[80]">
  <div className="mb-2 flex justify-end"><span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-[10px] font-bold tracking-wider text-amber-900 shadow-sm">{T('DEMO · READ ONLY','DEMO · HANYA BACA')}</span></div>
  <button type="button" onClick={()=>setOpen(true)} className="flex items-center gap-2 rounded-xl border border-[#8d202d] bg-[#801b24] px-4 py-3 text-sm font-semibold text-white shadow-xl hover:bg-[#a52a2f]"><BookOpen size={17}/>{T('Interactive User Guide','Panduan Pengguna Interaktif')}</button>
  {open&&<div className="fixed inset-0 z-[90] flex items-end justify-end bg-[#1e293b]/60 p-3 sm:items-center sm:p-6" onMouseDown={e=>{if(e.target===e.currentTarget)setOpen(false)}}>
   <section role="dialog" aria-modal="true" aria-label={T('Interactive User Guide','Panduan Pengguna Interaktif')} className="flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
    <header className="flex items-center justify-between border-b p-5"><div><p className="text-[11px] font-bold tracking-widest text-[#9f3033]">BAWASLU SMART RADAR</p><h2 className="mt-1 text-xl font-bold text-[#29202b]">{T('Interactive User Guide','Panduan Pengguna Interaktif')}</h2></div><button className="rounded-lg border p-2" onClick={()=>setOpen(false)} aria-label={T('Close','Tutup')}><X size={18}/></button></header>
    <div className="overflow-auto p-5">
     <div className="rounded-xl border border-teal-200 bg-teal-50 p-3 text-xs leading-6 text-teal-900"><ShieldCheck size={16} className="mr-2 inline"/>{T('This is the actual BAWASLU interface with a frozen snapshot. All demo actions are temporary and do not change Supabase data.','Ini adalah antarmuka BAWASLU asli dengan salinan data tetap. Semua tindakan demo bersifat sementara dan tidak mengubah data Supabase.')}</div>
     <p className="mt-5 text-xs font-semibold text-slate-500">{T('STEP','LANGKAH')} {step+1} / {steps.length}</p>
     <h3 className="mt-2 text-lg font-bold text-[#801b24]">{T(entry.en,entry.id)}</h3>
     <p className="mt-2 text-sm leading-7 text-slate-700">{T(entry.enText,entry.idText)}</p>
     <div className="mt-4 flex flex-wrap gap-2">{steps.map((item,i)=><button key={i} type="button" onClick={()=>go(i)} className={'h-8 min-w-8 rounded-lg border px-2 text-xs font-bold '+(i===step?'border-[#9f3033] bg-[#9f3033] text-white':'border-slate-200 bg-white text-slate-600')} aria-label={T(item.en,item.id)}>{i+1}</button>)}</div>
     <div className="mt-5 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">{T('Follow the instructor from one module to the next. Use the numbered sidebar to return to any stage.','Ikuti instruktur dari satu modul ke modul berikutnya. Gunakan menu bernomor untuk mengulang tahap tertentu.')}</div>
    </div>
    <footer className="flex items-center justify-between gap-2 border-t p-4">
     <button className="rounded-lg border px-3 py-2 text-xs font-semibold disabled:opacity-40" disabled={step===0} onClick={()=>go(step-1)}><ChevronLeft size={15} className="mr-1 inline"/>{T('Previous','Sebelumnya')}</button>
     <button className="rounded-lg border px-3 py-2 text-xs font-semibold text-[#801b24]" onClick={()=>{window.__BAWASLU_DEMO_RESET__?.();window.location.assign('/demo')}}><RotateCcw size={15} className="mr-1 inline"/>{T('Reset','Atur ulang')}</button>
     <button className="rounded-lg bg-[#801b24] px-3 py-2 text-xs font-semibold text-white" onClick={()=>step===steps.length-1?setOpen(false):go(step+1)}>{step===steps.length-1?T('Finish','Selesai'):T('Next','Lanjut')}<ChevronRight size={15} className="ml-1 inline"/></button>
    </footer>
   </section>
  </div>}
 </div>;
}
