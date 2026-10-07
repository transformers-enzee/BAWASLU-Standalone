import regions from './regions.json' with { type: 'json' };

const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const jurisdiction = item => ({ jurisdiction_type: item.jurisdiction_type, province: item.province || '', province_code: item.province_code || '', regency_city: item.regency_city || '', regency_city_code: item.regency_city_code || '', geographic_assignments: item.geographic_assignments || [] });
export { jurisdiction };

function contains(item, supported) {
  if (item.jurisdiction_type === 'National') return true;
  const areas = item.jurisdiction_type === 'Multi-Region' ? item.geographic_assignments || [] : [item];
  return areas.some(area => area.province_code === supported.province_code && (!supported.regency_city_code || !area.regency_city_code || area.regency_city_code === supported.regency_city_code));
}

export function geographicMismatch(item) {
  if (item.jurisdiction_confirmed !== true || item.jurisdiction_type === 'National') return null;
  const text = String(item.original_content || '');
  const ai = item.ai_geography || {};
  const quote = typeof ai.supporting_text === 'string' && ai.supporting_text && text.includes(ai.supporting_text) ? ai.supporting_text : '';
  const found = [];
  const occupied = [];
  for (const city of [...regions.regencies].sort((a, b) => b.name.length - a.name.length)) {
    const pattern = new RegExp(`(^|[^\\p{L}])(${escape(city.name)})(?=$|[^\\p{L}])`, 'giu');
    for (const match of text.matchAll(pattern)) {
      const start = match.index + match[1].length, end = start + match[2].length;
      if (occupied.some(([a, b]) => start < b && end > a)) continue;
      occupied.push([start, end]);
      const province = regions.provinces.find(p => p.code === city.province_code);
      const evidence = quote && quote.toLowerCase().includes(city.name.toLowerCase()) ? quote : text.slice(Math.max(0, start - 70), Math.min(text.length, end + 70));
      found.push({ position: start, province: province.name, province_code: province.code, regency_city: city.name, regency_city_code: city.code, evidence, confidence: quote && quote.toLowerCase().includes(city.name.toLowerCase()) ? ai.confidence || 'Not stated' : 'Not stated for this location' });
    }
  }
  found.sort((a, b) => a.position - b.position);
  const aiProvince = regions.provinces.find(p => p.code === ai.province_code);
  const aiCity = regions.regencies.find(c => c.code === ai.regency_city_code && c.province_code === aiProvince?.code);
  if (quote && aiProvince) found.push({ province: aiProvince.name, province_code: aiProvince.code, regency_city: aiCity?.name || '', regency_city_code: aiCity?.code || '', evidence: quote, confidence: ai.confidence || 'Not stated' });
  const supported = found.find(candidate => !contains(item, candidate));
  if (!supported) return null;
  const fingerprint = JSON.stringify([jurisdiction(item), supported.province_code, supported.regency_city_code, supported.evidence]);
  const decision = item.geographic_mismatch_review;
  return { status: decision?.decision === 'KEEP CONFIRMED JURISDICTION' && decision.fingerprint === fingerprint ? 'reviewed' : 'pending', supported: { jurisdiction_type: supported.regency_city_code ? 'Regency / City' : 'Province', province: supported.province, province_code: supported.province_code, regency_city: supported.regency_city, regency_city_code: supported.regency_city_code }, source_evidence: supported.evidence, ai_confidence: supported.confidence, fingerprint, review: decision?.fingerprint === fingerprint ? decision : null };
}