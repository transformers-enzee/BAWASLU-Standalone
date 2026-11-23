import {NavLink} from 'react-router-dom';
import {Home as HomeIcon,LayoutDashboard,Inbox,Database,BadgeCheck,Settings,LockKeyhole,Sparkles,Radio,FileText,BriefcaseBusiness} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

const management=[
 ['/management','Management Home',BriefcaseBusiness,'view_intelligence'],
 ['/management/assistant','Management AI Assistant',Sparkles,'view_intelligence'],
];
const operations=[
 ['/','home',HomeIcon,'view_intelligence'],
 ['/smart-radar','Command Centre',LayoutDashboard,'view_intelligence'],
 ['/social-listening','social_listening',Radio,'view_intelligence'],
 ['/inbox','intelligence_inbox',Inbox,'view_intelligence'],
 ['/assistant','intelligence_assistant',Sparkles,'view_intelligence'],
];
const secondary=[
 ['/sources','data_sources',Database,'administration'],
 ['/validation','validation',BadgeCheck,'human_validation'],
 ['/administration','administration',Settings,'administration'],
];
const future=['future_risk_warning','future_action_center','future_reporting'];

export default function AccessNavigation({access,user,build}){
 const {t,language}=useLanguage();
 const label=key=>key==='Management Home'||key==='Management AI Assistant'||key==='Command Centre'?key:t(key);
 const leadership=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 function navigation(items,group){
  return <nav aria-label={group} className="space-y-1 px-3">
   {items.filter(([path,,,permission])=>access.permissions?.[permission]===true&&
       (!path.startsWith('/management')||leadership))
    .map(([path,key,Icon])=><NavLink key={path} to={path} end={path==='/'}
     className={({isActive})=>'flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-[13px] transition-colors '+(isActive?'bg-[#a52a2f] text-white font-semibold':'text-[#f4e7e5] hover:bg-white/10 hover:text-white')}>
     <Icon size={17}/><span>{label(key)}</span>
    </NavLink>)}
  </nav>;
 }
 return <>
  <div className="flex items-center gap-3 border-b border-white/10 px-5 h-[76px]">
   <img src="/bawaslu-emblem.svg" alt="BAWASLU emblem" className="h-10 w-10 shrink-0 object-contain"/>
   <div><div className="font-bold text-[15px] leading-tight tracking-wide">BAWASLU</div><div className="text-[10px] uppercase tracking-[.19em] text-[#f1d9d6]">COMMAND CENTRE</div></div>
  </div>
  <div className="px-4 pt-7 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#dfaaa9]" data-testid="management-workspace-navigation">{language==='id'?'Ruang Manajemen':'Management workspace'}</div>
  {navigation(management,'Management workspace')}
  <div className="px-4 pt-7 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#dfaaa9]" data-testid="operations-workspace-navigation">{language==='id'?'Ruang Operasional':'Operational workspace'}</div>
  {navigation(operations,'Operational workspace')}
  <div className="px-4 pt-7 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#dfaaa9]">{language==='id'?'Administrasi & Validasi':'Administration & validation'}</div>
  {navigation(secondary,'Administrative tools')}
  <div className="px-4 pt-7 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#dfaaa9]">{t('future_modules')}</div>
  <div className="space-y-1 px-3">{future.map(x=><div key={x} className="flex items-center justify-between px-3.5 py-2.5 text-[12px] text-[#dfaaa9]" title={t('soon')}>
   <span className="flex items-center gap-3"><LockKeyhole size={15}/>{t(x)}</span><span className="text-[9px]">{t('soon')}</span>
  </div>)}</div>
  <div className="mt-auto border-t border-white/10 p-5 text-xs text-[#f4e7e5]">
   <div className="truncate font-semibold text-white">{user?.full_name||user?.email||t('authorized_user')}</div>
   <div className="mt-1">{t('secure_workspace')} · {build?.build_version?'Build '+build.build_version:'Build unavailable'}{build?.commit?' · '+build.commit.slice(0,7):''}</div>
  </div>
 </>;
}
