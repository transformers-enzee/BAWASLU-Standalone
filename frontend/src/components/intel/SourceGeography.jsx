export default function SourceGeography({ geography }) {
  if (!geography) return null;
  const resolved = geography.jurisdiction_type && geography.jurisdiction_type !== 'Unresolved' && geography.province_code;
  return <div className="text-sm border-l-2 border-[#79adb9] pl-3 space-y-1">
    <strong>AI/source-supported geography — NOT an authoritative assignment</strong>
    <p>{resolved ? `${geography.jurisdiction_type} · ${[geography.regency_city, geography.province].filter(Boolean).join(', ')}` : 'Unresolved · No jurisdiction identified'} · Resolution confidence: {resolved ? geography.confidence || 'Not assessed' : 'Unresolved'}</p>
    {geography.kecamatan && <p>Normalized Kecamatan: {geography.kecamatan}</p>}
    {geography.extraction_confidence && <p>Extraction confidence (separate from resolution): {geography.extraction_confidence}</p>}
    <p className="whitespace-pre-wrap">Exact source evidence: {geography.supporting_text || 'Not available'}</p>
    {geography.extraction_source && <p>Extraction provenance: {geography.extraction_source}</p>}
    {geography.mapping_reference && <p className="break-words">Resolution reference: {geography.mapping_reference}</p>}
  </div>;
}