import {NavLink} from 'react-router-dom';
import {Home,Radio,Inbox,LayoutDashboard,Sparkles} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

// This sidebar is mounted only when /demo is active. No production navigation changes.
const steps=[
 ['/social-listening','social_listening',Radio],
 ['/inbox','intelligence_inbox',Inbox],
 ['/smart-radar','command_centre',LayoutDashboard],
 ['/assistant','intelligence_assistant',Sparkles],
];
export default function DemoAccessNavigation({access,user}){
 const {t,language}=useLanguage();
 const T=(en,id)=>language==='id'?id:en;
 const item=(path,Icon,label,number=null)=>(
  <NavLink key={path} to={path} end={path==='/'} className={({isActive})=>'flex items-center gap-3 px-3.5 py-3 rounded-lg text-[13px] transition-colors '+(isActive?'bg-[#a52a2f] text-white font-semibold':'text-[#f4e7e5] hover:bg-white/10 hover:text-white')}>
   {number!==null&&<span aria-hidden="true" className="text-[11px] tabular-nums font-bold text-[#f4c9c8] min-w-[23px]">{String(number).padStart(2,'0')}</span>}
   <Icon size={17} aria-hidden="true"/><span>{label}</span>
  </NavLink>
 );
 return <div data-demo-locale-owned="true" className="flex min-h-full flex-col">
  <div className="flex items-center gap-3 px-5 h-[76px] shrink-0 border-b border-white/10"><img src="/bawaslu-emblem.svg" alt="BAWASLU emblem" className="w-10 h-10 shrink-0 object-contain"/><div><div className="font-bold text-[15px] leading-tight tracking-wide">BAWASLU</div><div className="text-[10px] uppercase tracking-[.19em] text-[#f1d9d6]">COMMAND CENTRE</div></div></div>
  <div className="px-4 pt-6 pb-2 text-[10px] font-bold text-[#dfaaa9] tracking-[.18em] uppercase">{T('Training orientation','Orientasi Pelatihan')}</div>
  <nav className="px-3 space-y-1" aria-label={T('Training orientation','Orientasi Pelatihan')}>
   {item('/',Home,T('Home','Beranda'))}
  </nav>
  <div className="px-4 pt-7 pb-2 text-[10px] font-bold text-[#dfaaa9] tracking-[.18em] uppercase">{T('Instructor-led modules','Modul Bersama Instruktur')}</div>
  <nav aria-label={T('Numbered demo navigation','Navigasi demo bernomor')} className="px-3 space-y-1">
   {access.permissions?.view_intelligence===true&&steps.map(([path,key,Icon],index)=>item(path,Icon,key==='command_centre'?T('Command Centre','Pusat Komando'):t(key),index+1))}
  </nav>
  <div className="mt-auto border-t border-white/10 p-5 text-xs text-[#f4e7e5]"><div className="font-semibold text-white truncate">{T('Demo visitor','Pengunjung Demo')}</div><div className="mt-1">{T('Fixed training data · read only','Data pelatihan tetap · hanya baca')}</div></div>
 </div>;
}
