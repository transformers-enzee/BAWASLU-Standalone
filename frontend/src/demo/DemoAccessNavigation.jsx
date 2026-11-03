import {NavLink} from 'react-router-dom';
import {Radio,Inbox,LayoutDashboard,Sparkles} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

// Demo-only navigation. Production AccessNavigation is not modified.
const steps=[
 ['/social-listening','social_listening',Radio],
 ['/inbox','intelligence_inbox',Inbox],
 ['/','Command Centre',LayoutDashboard],
 ['/assistant','intelligence_assistant',Sparkles],
];
export default function DemoAccessNavigation({access,user}){
 const {t,language}=useLanguage();
 return <div className="flex flex-col min-h-full">
  <div className="flex items-center gap-3 px-5 h-[76px] shrink-0 border-b border-white/10"><img src="/bawaslu-emblem.svg" alt="BAWASLU emblem" className="w-10 h-10 shrink-0 object-contain"/><div><div className="font-bold text-[15px] leading-tight tracking-wide">BAWASLU</div><div className="text-[10px] uppercase tracking-[.19em] text-[#f1d9d6]">SMART RADAR</div></div></div>
  <div className="px-4 pt-7 pb-2 text-[10px] font-bold text-[#dfaaa9] tracking-[.18em] uppercase">{language==='id'?'Alur Panduan Interaktif':'Interactive Guide Flow'}</div>
  <nav aria-label={language==='id'?'Navigasi demo bernomor':'Numbered demo navigation'} className="px-3 space-y-1">
   {access.permissions?.view_intelligence===true&&steps.map(([path,key,Icon],index)=><NavLink key={path} to={path} end={path==='/'} className={({isActive})=>'flex items-center gap-3 px-3.5 py-3 rounded-lg text-[13px] transition-colors '+(isActive?'bg-[#a52a2f] text-white font-semibold':'text-[#f4e7e5] hover:bg-white/10 hover:text-white')}>
    <span aria-hidden="true" className="text-[11px] tabular-nums font-bold text-[#f4c9c8] min-w-[23px]">{String(index+1).padStart(2,'0')}</span><Icon size={17} aria-hidden="true"/><span>{key==='Command Centre'?(language==='id'?'Pusat Komando':'Command Centre'):t(key)}</span>
   </NavLink>)}
  </nav>
  <div className="mt-auto border-t border-white/10 p-5 text-xs text-[#f4e7e5]"><div className="font-semibold text-white truncate">{user?.full_name||user?.email||t('authorized_user')}</div><div className="mt-1">{language==='id'?'Mode demo · tanpa perubahan data':'Demo mode · no data changes'}</div></div>
 </div>;
}
