import regions from './regions.json';
import { useLanguage } from '@/lib/LanguageContext';
const types=['National','Province','Regency / City','Multi-Region','Unresolved'];
const empty=()=>({province_code:'',regency_city_code:''});
export default function JurisdictionFields({value,onChange}){
 const {t}=useLanguage();
 const type=value.jurisdiction_type||'Unresolved';
 const assignments=type==='Multi-Region'?(value.geographic_assignments?.length?value.geographic_assignments:[empty(),empty()]):[{province_code:value.province_code||'',regency_city_code:value.regency_city_code||''}];
 const setType=v=>onChange({...value,jurisdiction_type:v,province_code:'',regency_city_code:'',geographic_assignments:v==='Multi-Region'?[empty(),empty()]:[]});
 const setAssignment=(index,patch)=>{const next=assignments.map((x,i)=>i===index?{...x,...patch}:x);onChange(type==='Multi-Region'?{...value,geographic_assignments:next}:{...value,...next[0]});};
 const typeLabel=x=>x==='National'?t('national'):x==='Province'?t('province'):x==='Regency / City'?t('regency_city'):x==='Multi-Region'?'Multi-Region':t('unresolved');
 return <div className="space-y-3">
  <label className="block"><span className="intel-label">{t('jurisdiction_classification')}</span><select className="intel-input" value={type} onChange={e=>setType(e.target.value)}>{types.map(x=><option key={x} value={x}>{typeLabel(x)}</option>)}</select></label>
  {type==='Unresolved'&&<p className="text-xs text-muted-foreground">{t('requires_regional_block')}</p>}
  {!['Unresolved','National'].includes(type)&&assignments.map((entry,index)=><div key={index} className="grid sm:grid-cols-2 gap-3">
   <label><span className="intel-label">{t('province')} {type==='Multi-Region'?index+1:''}</span><select required className="intel-input" value={entry.province_code||''} onChange={e=>setAssignment(index,{province_code:e.target.value,regency_city_code:''})}><option value="">{t('select_province')}</option>{regions.provinces.map(p=><option key={p.code} value={p.code}>{p.name}</option>)}</select></label>
   <label><span className="intel-label">{t('regency_city')} {type==='Regency / City'?'*':'('+t('optional')+')'}</span><select className="intel-input" required={type==='Regency / City'} value={entry.regency_city_code||''} onChange={e=>setAssignment(index,{regency_city_code:e.target.value})}><option value="">{type==='Regency / City'?t('select_regency_city'):t('entire_province')}</option>{regions.regencies.filter(c=>c.province_code===entry.province_code).map(c=> <option key={c.code} value={c.code}>{c.name}</option>)}</select></label>
   {type==='Multi-Region'&&assignments.length>2&&<button type="button" className="intel-ghost sm:col-span-2" onClick={()=>onChange({...value,geographic_assignments:assignments.filter((_,i)=>i!==index)})}>{t('remove_area')}</button>}
  </div>)}
  {type==='Multi-Region'&&assignments.length<30&&<button type="button" className="intel-ghost" onClick={()=>onChange({...value,geographic_assignments:[...assignments,empty()]})}>{t('add_area')}</button>}
 </div>;
}