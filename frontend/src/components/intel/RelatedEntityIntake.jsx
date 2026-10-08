import { Field } from './Fields';
import { useLanguage } from '@/lib/LanguageContext';
const relationships=[['PUBLISHER','PUBLISHER'],['MENTIONS','MENTIONS'],['FEATURES','FEATURES'],['OTHER_REQUIRES_REVIEW','OTHER / REQUIRES REVIEW']];
export default function RelatedEntityIntake({form,setForm,entities}) {
  const {t,label}=useLanguage();
  const set=(key,value)=>setForm(f=>({...f,[key]:value}));
  return <div className="space-y-3">
    <label className="block"><span className="intel-label">{t('related_monitored_entity')}</span><select className="intel-input" value={form.related_entity_id||''} onChange={e=>setForm(f=>({...f,related_entity_id:e.target.value,relationship_type:'',relationship_evidence_basis:''}))}><option value="">{t('no_monitored_entity')}</option>{entities.map(e=><option value={e.id} key={e.id}>{e.name} · {label(e.type)}</option>)}</select></label>
    {form.related_entity_id&&<><label className="block"><span className="intel-label">{t('relationship_source_evidence')}</span><select className="intel-input" required value={form.relationship_type||''} onChange={e=>set('relationship_type',e.target.value)}><option value="">{t('select_relationship')}</option>{relationships.map(([value,text])=><option key={value} value={value}>{label(text)}</option>)}</select></label><Field label={t('relationship_evidence_basis_label')} required value={form.relationship_evidence_basis} onChange={v=>set('relationship_evidence_basis',v)} placeholder={t('relationship_evidence_placeholder')}/><p className="text-xs text-[#617789]">{t('publisher_relationship_note')}</p></>}
  </div>;
}