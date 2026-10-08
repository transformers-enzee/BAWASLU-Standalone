import { useIntel } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

export default function Validation(){
 const {t}=useLanguage();
 const {items,loading,error}=useIntel();
 const pending=items.filter(x=>['Awaiting Validation','Request More Information','Escalate for Further Review'].includes(x.review_status));
 return <div className="space-y-6">
  <div>
   <p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('validation_oversight')}</p>
   <h1 className="intel-heading">{t('validation_queue')}</h1>
   <p className="text-sm text-[#77899b] mt-2">{t('validation_intro')}</p>
  </div>
  <Notice error={error}/>
  {loading?<p>{t('loading_queue')}</p>:<IntelligenceTable items={pending}/>}
 </div>;
}