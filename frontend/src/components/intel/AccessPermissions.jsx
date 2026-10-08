import { useLanguage } from '@/lib/LanguageContext';
export default function AccessPermissions({labels,permissions,onChange}){
 const {t}=useLanguage();
 return <fieldset className="border-t border-border pt-4"><legend className="font-semibold text-sm pt-4">{t('functional_permissions')}</legend>
  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">{Object.entries(labels).map(([key,fallback])=><label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-primary" checked={!!permissions?.[key]} onChange={e=>onChange(key,e.target.checked)}/>{t('permission_'+key)!=='permission_'+key?t('permission_'+key):fallback}</label>)}</div>
  <p className="text-xs text-muted-foreground mt-3">{t('sensitive_permissions_note')}</p>
 </fieldset>;
}