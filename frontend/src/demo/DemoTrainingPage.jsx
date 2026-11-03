import {Link} from 'react-router-dom';
import {BookOpen,Home,Radio,Inbox,LayoutDashboard,Sparkles,ArrowRight,ShieldCheck,Users,Database,CheckCircle2} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';
import {snapshot,demoAllEvidence,demoCampaigns,demoWatchlist} from './currentSnapshot.js';

const flow=[
 {path:'/social-listening',icon:Radio,en:'Social Listening',id:'Pemantauan Media Sosial',enAction:'Explore campaigns, captured sources and saved assessments.',idAction:'Jelajahi kampanye, sumber terkumpul, dan penilaian tersimpan.'},
 {path:'/inbox',icon:Inbox,en:'Intelligence Inbox',id:'Kotak Masuk Intelijen',enAction:'Examine AI findings, source evidence and review decisions.',idAction:'Periksa temuan AI, bukti sumber, dan keputusan peninjauan.'},
 {path:'/smart-radar',icon:LayoutDashboard,en:'Command Centre',id:'Pusat Komando',enAction:'Connect findings to signals, priorities and officer follow-up.',idAction:'Hubungkan temuan dengan sinyal, prioritas, dan tindak lanjut petugas.'},
 {path:'/assistant',icon:Sparkles,en:'AI Assistant',id:'Asisten AI',enAction:'Practice questions with preset, bilingual demonstrations.',idAction:'Latih pertanyaan melalui demonstrasi dwibahasa yang telah disiapkan.'},
];
export default function DemoTrainingPage({mode='home'}){
 const {language}=useLanguage();
 const T=(en,id)=>language==='id'?id:en;
 const isGuide=mode==='guide';
 return <div className="mx-auto max-w-6xl space-y-6 pb-10">
  <section className="rounded-2xl bg-[#801b24] px-6 py-8 text-white shadow-sm md:px-9 md:py-10">
   <p className="text-[11px] font-bold tracking-[.22em] text-[#ffdbd6] uppercase">BAWASLU SMART RADAR · {T('TRAINING PROTOTYPE','PROTOTIPE PELATIHAN')}</p>
   <div className="mt-4 flex items-start gap-3"><div className="rounded-xl bg-white/15 p-3">{isGuide?<BookOpen size={26}/>:<Home size={26}/>}</div>
    <div><h1 className="text-2xl font-bold leading-tight md:text-3xl">{isGuide?T('How to Use This Guide','Cara Menggunakan Panduan'):T('Welcome to the BAWASLU Interactive Demo','Selamat Datang di Demo Interaktif BAWASLU')}</h1>
     <p className="mt-3 max-w-3xl text-sm leading-7 text-white/90">{isGuide?
      T('This instructor-led guide walks participants through the BAWASLU prototype one module at a time, explaining how evidence becomes intelligence and how officers decide what to review.','Panduan bersama instruktur ini mengajak peserta mempelajari prototipe BAWASLU tahap demi tahap, dari pengumpulan bukti menjadi intelijen hingga keputusan peninjauan petugas.'):
      T('Explore an interactive replica of the BAWASLU intelligence system together with your instructor. You can navigate, filter and practice, but cannot change operational records.','Jelajahi replika interaktif sistem intelijen BAWASLU bersama instruktur. Anda dapat menavigasi, memfilter, dan berlatih tanpa mengubah data operasional.')}</p>
    </div></div>
   <div className="mt-6 flex flex-wrap gap-3"><Link to={isGuide?'/social-listening':'/guide'} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-[#801b24]">{isGuide?T('Begin module 01','Mulai modul 01'):T('Read the training guide','Baca panduan pelatihan')}<ArrowRight size={16}/></Link><Link to="/smart-radar" className="inline-flex items-center gap-2 rounded-xl border border-white/50 px-4 py-3 text-sm font-medium text-white">{T('See the Command Centre','Lihat Pusat Komando')}</Link></div>
  </section>
  <section className="rounded-2xl border border-[#cfe3dc] bg-[#f0faf7] p-5 text-[#15594e]">
    <div className="flex items-start gap-3"><ShieldCheck size={23} className="mt-1 shrink-0"/><div><h2 className="font-bold">{T('Training environment · fixed data · read only','Lingkungan pelatihan · data tetap · hanya baca')}</h2><p className="mt-1 text-sm leading-6">{T('The prototype uses a sanitized, frozen copy of existing BAWASLU evidence. Records and assessments do not update in real time. Simulated actions and review choices are local to this demonstration and do not write to Supabase or run live collection. A signal is not a legal determination.','Prototipe menggunakan salinan data bukti BAWASLU yang telah disamarkan dan dibekukan. Catatan serta penilaian tidak diperbarui secara langsung. Tindakan dan pilihan peninjauan hanya berlaku dalam demonstrasi, tanpa menulis ke Supabase atau menjalankan pengumpulan langsung. Sinyal bukan putusan hukum.')}</p></div></div>
  </section>
  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
   {[[demoCampaigns.length,T('Campaigns','Kampanye')],[demoAllEvidence.length,T('Linked campaign evidence','Bukti kampanye tertaut')],[snapshot.length,T('Saved assessment examples','Contoh penilaian tersimpan')],[demoWatchlist.length,T('Watchlist profiles','Profil pantauan')]].map(([count,label])=><div key={label} className="rounded-xl border border-[#e8dfe0] bg-white p-4"><div className="text-2xl font-bold text-[#801b24]">{count}</div><p className="mt-1 text-xs text-slate-600">{label}</p></div>)}
  </div>
  <section>
   <div className="flex items-center gap-2"><Users size={20} className="text-[#801b24]"/><h2 className="text-xl font-bold text-[#3a2023]">{T('Instructor-led learning sequence','Urutan Pembelajaran Bersama Instruktur')}</h2></div>
   <p className="mt-2 text-sm leading-6 text-slate-600">{T('Work from module 01 through 04 together. The instructor demonstrates a task, then participants repeat it using the same frozen evidence. Use the sidebar numbers to follow along.','Ikuti modul 01 hingga 04 bersama-sama. Instruktur mendemonstrasikan tugas, kemudian peserta mengulanginya menggunakan bukti tetap yang sama. Gunakan nomor di bilah samping untuk mengikuti tahap.')}</p>
   <div className="mt-4 grid gap-3 md:grid-cols-2">{flow.map((item,i)=><Link key={item.path} to={item.path} className="group rounded-2xl border border-[#e9dfe0] bg-white p-5 transition hover:border-[#9c5960] hover:shadow-sm"><div className="flex items-center justify-between"><span className="text-[11px] font-bold tracking-widest text-[#9e454d]">{T('MODULE','MODUL')} {String(i+1).padStart(2,'0')}</span><ArrowRight size={16} className="text-[#801b24]"/></div><div className="mt-3 flex items-center gap-3"><item.icon size={22} className="text-[#801b24]"/><h3 className="text-lg font-bold text-[#3a2023]">{T(item.en,item.id)}</h3></div><p className="mt-2 text-sm leading-6 text-slate-600">{T(item.enAction,item.idAction)}</p></Link>)}</div>
  </section>
  <section className="rounded-2xl border border-[#e8dfe0] bg-white p-6"><h2 className="text-lg font-bold text-[#3a2023]">{T('How the classroom session works','Cara Pelaksanaan Sesi Pelatihan')}</h2><div className="mt-4 grid gap-4 md:grid-cols-3">
   {[[BookOpen,T('1. Instructor explains','1. Instruktur menjelaskan'),T('Understand the purpose and expected result of each module.','Pahami tujuan dan hasil yang diharapkan dari setiap modul.')],[Database,T('2. Instructor demonstrates','2. Instruktur mendemonstrasikan'),T('Follow a genuine saved example from source post to decision support.','Ikuti contoh catatan tersimpan dari sumber unggahan hingga dukungan keputusan.')],[CheckCircle2,T('3. Participants practice','3. Peserta berlatih'),T('Try safe filters, drill-downs and simulated reviews; then move to the next module.','Coba filter, penelusuran bukti, dan peninjauan simulasi dengan aman, lalu lanjutkan ke modul berikutnya.')]].map(([Icon,title,description])=><div key={title} className="rounded-xl bg-slate-50 p-4"><Icon size={21} className="text-[#801b24]"/><h3 className="mt-2 font-semibold text-sm">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{description}</p></div>)}
  </div></section>
 </div>;
}
