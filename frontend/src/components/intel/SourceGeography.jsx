import { useLanguage } from '@/lib/LanguageContext';
export default function SourceGeography({ geography }) {
  const {t}=useLanguage();
  if (!geography) return null;
  const resolved = geography.jurisdiction_type && geography.jurisdiction_type !== 'Unresolved' && geography.province_code;
  return <div className="text-sm border-l-2 border-[#79adb9] pl-3 space-y-1">
    <strong>{t('ai_source_geography')}</strong>
    <p>{resolved ? geography.jurisdiction_type+' · '+[geography.regency_city, geography.province].filter(Boolean).join(', ') : t('no_jurisdiction_identified')} · {t('resolution_confidence')}: {resolved ? geography.confidence || t('not_assessed') : t('unresolved')}</p>
    {geography.kecamatan && <p>{t('normalized_kecamatan')}: {geography.kecamatan}</p>}
    {geography.extraction_confidence && <p>{t('extraction_confidence')}: {geography.extraction_confidence}</p>}
    <p className="whitespace-pre-wrap">{t('exact_source_evidence')}: {geography.supporting_text || t('not_available')}</p>
    {geography.extraction_source && <p>{t('extraction_provenance')}: {geography.extraction_source}</p>}
    {geography.mapping_reference && <p className="break-words">{t('resolution_reference')}: {geography.mapping_reference}</p>}
  </div>;
}