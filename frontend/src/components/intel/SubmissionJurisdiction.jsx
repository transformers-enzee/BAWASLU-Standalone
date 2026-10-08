import regions from './regions.json';
import JurisdictionFields from './JurisdictionFields';
import { useLanguage } from '@/lib/LanguageContext';

export default function SubmissionJurisdiction({ value, onChange, access }) {
  const {t}=useLanguage();
  const regional = access.geographic_scope !== 'Nationwide';
  const cityRestricted = access.geographic_scope === 'Regency/City' || !!access.regency_city_code;
  const province = regions.provinces.find(p => p.code === access.province_code);
  const cities = regions.regencies.filter(c => c.province_code === access.province_code && (!cityRestricted || c.code === access.regency_city_code));
  const types = cityRestricted ? ['Regency / City', 'Unresolved'] : access.role === 'Provincial Administrator' ? ['Province', 'Regency / City', 'Multi-Region', 'Unresolved'] : ['Province', 'Regency / City', 'Unresolved'];
  const scopeLabel = regional ? `${access.geographic_scope === 'Province' ? 'Province' : 'Regency / City'} · ${[access.regency_city, access.province].filter(Boolean).join(', ')}` : 'National · Nationwide';
  const type = value.jurisdiction_type || 'Unresolved';
  const changeType = next => onChange({ ...value, jurisdiction_type: next, province_code: next === 'Unresolved' ? '' : access.province_code, regency_city_code: next === 'Regency / City' ? (access.regency_city_code || '') : '', geographic_assignments: next === 'Multi-Region' ? [{ province_code: access.province_code, regency_city_code: '' }, { province_code: access.province_code, regency_city_code: '' }] : [] });
  const assignments = value.geographic_assignments || [];
  const setArea = (index, code) => onChange({ ...value, geographic_assignments: assignments.map((area, i) => i === index ? { province_code: access.province_code, regency_city_code: code } : area) });

  return <div className="space-y-4">
    <section className="rounded-lg border border-border bg-muted p-4" aria-label={t('your_submission_scope')}>
      <h3 className="text-sm font-semibold">{t('your_submission_scope')}</h3>
      <p className="mt-1 text-sm font-medium">{scopeLabel}</p>
      <p className="mt-2 text-xs text-muted-foreground">{t('submission_scope_note')}</p>
    </section>
    {!regional ? <JurisdictionFields value={value} onChange={onChange} /> : <div className="space-y-3">
      <label className="block"><span className="intel-label">{t('jurisdiction_classification')}</span><select className="intel-input" value={types.includes(type) ? type : 'Unresolved'} onChange={e => changeType(e.target.value)}>{types.map(t => <option key={t} value={t}>{t === 'Province' ? t('province_wide') : t}</option>)}</select></label>
      {type === 'Unresolved' && <p className="text-xs text-muted-foreground">{t('requires_regional_block')}</p>}
      {type !== 'Unresolved' && <div><span className="intel-label">{t('province')}</span><p className="intel-input">{province?.name || access.province}</p></div>}
      {type === 'Regency / City' && <label className="block"><span className="intel-label">{t('regency_city_required_label')}</span><select required className="intel-input" value={value.regency_city_code || ''} onChange={e => onChange({ ...value, province_code: access.province_code, regency_city_code: e.target.value })}><option value="">{t('select_regency_city')}</option>{cities.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}</select></label>}
      {type === 'Multi-Region' && assignments.map((area, index) => <label key={index} className="block"><span className="intel-label">{t('area')} {index + 1} · {t('regency_city')}</span><select className="intel-input" value={area.regency_city_code || ''} onChange={e => setArea(index, e.target.value)}><option value="">{t('entire_province')}</option>{cities.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}</select>{assignments.length > 2 && <button type="button" className="intel-ghost mt-2" onClick={() => onChange({ ...value, geographic_assignments: assignments.filter((_, i) => i !== index) })}>{t('remove_area')}</button>}</label>)}
      {type === 'Multi-Region' && assignments.length < 30 && <button type="button" className="intel-ghost" onClick={() => onChange({ ...value, geographic_assignments: [...assignments, { province_code: access.province_code, regency_city_code: '' }] })}>{t('add_area')}</button>}
    </div>}
  </div>;
}