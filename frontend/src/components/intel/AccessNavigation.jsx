import {NavLink} from 'react-router-dom';
import {Home as HomeIcon,LayoutDashboard,Inbox,Database,BadgeCheck,Settings,Sparkles,Radio} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

// One officer navigation for all roles. Management vs Operational capabilities
// remain role-aware in the destination route; they are not duplicate menus.
// Deprecated assistants retain bookmarked routes, but are no longer advertised.
export default function AccessNavigation({access,user,build}){
  const {t,language}=useLanguage();
  const leadership=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
  const can=(key)=>access?.permissions?.[key]===true;
  const common=[
    [leadership?'/management':'/',t('home'),HomeIcon,'view_intelligence'],
    ['/smart-radar',language==='id'?'Pusat Komando':'Command Centre',LayoutDashboard,'view_intelligence'],
    ['/social-listening',t('social_listening'),Radio,'view_intelligence'],
    ['/inbox',t('intelligence_inbox'),Inbox,'view_intelligence'],
    [leadership?'/management/ai-5':'/ai-5','AI-5 Assistant',Sparkles,'view_intelligence'],
  ];
  const admin=[
    ['/sources',t('data_sources'),Database,'administration'],
    ['/validation',t('validation'),BadgeCheck,'human_validation'],
    ['/administration',t('administration'),Settings,'administration'],
  ];
  const allowedAdmin=admin.filter(([, , ,permission])=>can(permission));
  function links(items,label){
    return <nav aria-label={label} className="space-y-1 px-3">
      {items.filter(([, , ,permission])=>can(permission)).map(([path,title,Icon])=>
        <NavLink key={path} to={path} end={path==='/'||path==='/management'}
          className={({isActive})=>'flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-[13px] transition-colors '+
            (isActive?'bg-[#a52a2f] text-white font-semibold':'text-[#f4e7e5] hover:bg-white/10 hover:text-white')}>
          <Icon size={17}/><span>{title}</span>
        </NavLink>)}
    </nav>;
  }
  return <>
    <div className="flex items-center gap-3 border-b border-white/10 px-5 h-[76px]">
      <img src="/bawaslu-emblem.svg" alt="BAWASLU emblem" className="h-10 w-10 shrink-0 object-contain"/>
      <div><div className="font-bold text-[15px] leading-tight tracking-wide">BAWASLU</div>
        <div className="text-[10px] uppercase tracking-[.19em] text-[#f1d9d6]">COMMAND CENTRE</div></div>
    </div>
    <div className="px-4 pt-6 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#dfaaa9]"
      data-testid="unified-workspace-navigation">{language==='id'?'Ruang Kerja':'Workspace'}</div>
    {links(common,'BAWASLU workspace')}
    {allowedAdmin.length>0&&<>
      <div className="px-4 pt-6 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#dfaaa9]"
        data-testid="administration-navigation">{language==='id'?'Administrasi & Validasi':'Administration & Validation'}</div>
      {links(allowedAdmin,'Administrative tools')}
    </>}
    <div className="mt-auto border-t border-white/10 p-5 text-xs text-[#f4e7e5]">
      <div className="truncate font-semibold text-white">{user?.full_name||user?.email||t('authorized_user')}</div>
      <div className="mt-1">{t('secure_workspace')} · {build?.build_version?'Build '+build.build_version:'Build unavailable'}{build?.commit?' · '+build.commit.slice(0,7):''}</div>
    </div>
  </>;
}
