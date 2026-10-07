import regions from './regions.json' with { type: 'json' };

const bangkaReference = 'https://bangkakab.bps.go.id/id/publication/2025/09/26/74e82a225429b28077272f44/kecamatan-sungai-liat-dalam-angka-2025.html';
const districts = [{ name: 'Sungailiat', aliases: ['Sungailiat', 'Sungai Liat'], regency_code: '19.01', reference: bangkaReference }];
const provinceAliases = [{ name: 'Kepulauan Bangka Belitung', code: '19' }];
const escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const mentions = (text, name) => new RegExp(`(^|[^\\p{L}])${escape(name)}(?=$|[^\\p{L}])`, 'iu').test(text);

// Only source text is used for resolution. Confirmed/assigned jurisdiction is never an input.
export function resolveSourceGeography(content, extracted = {}) {
  const text = String(content || '');
  const quote = typeof extracted.supporting_text === 'string' && text.includes(extracted.supporting_text) ? extracted.supporting_text : '';
  const evidence = quote || text;
  const cities = regions.regencies.filter(c => mentions(evidence, c.name));
  const district = districts.find(d => d.aliases.some(alias => mentions(evidence, `Kecamatan ${alias}`)));
  const provinces = regions.provinces.filter(p => mentions(evidence, p.name) || provinceAliases.some(a => a.code === p.code && mentions(evidence, a.name)));
  const districtCity = district && regions.regencies.find(c => c.code === district.regency_code);
  const city = cities.length === 1 ? cities[0] : !cities.length ? districtCity : null;
  const consistent = city && cities.length <= 1 && provinces.length <= 1 && (!provinces.length || provinces[0].code === city.province_code) && (!districtCity || districtCity.code === city.code);
  const province = consistent ? regions.provinces.find(p => p.code === city.province_code) : !cities.length && !district && provinces.length === 1 ? provinces[0] : null;
  const resolved = !!province;
  const matched = district && (district.aliases.find(alias => mentions(evidence, `Kecamatan ${alias}`)) || district.name);
  const snippet = (name) => { if (!name) return ''; const pos = text.toLowerCase().indexOf(name.toLowerCase()); return pos < 0 ? '' : text.slice(Math.max(0, pos - 70), Math.min(text.length, pos + name.length + 70)); };
  const supporting = quote || snippet(city?.name || (matched && `Kecamatan ${matched}`) || province?.name || '') || '';
  return {
    jurisdiction_type: resolved ? city ? 'Regency / City' : 'Province' : 'Unresolved',
    province: province?.name || '', province_code: province?.code || '',
    regency_city: resolved ? city?.name || '' : '', regency_city_code: resolved ? city?.code || '' : '',
    kecamatan: matched ? district.name : '',
    extraction_confidence: String(extracted.extraction_confidence || extracted.confidence || '').trim(),
    confidence: resolved ? city && provinces.length === 1 ? 'High' : 'Medium' : 'Unresolved',
    supporting_text: supporting,
    mapping_reference: resolved ? [district && city ? `BPS Kabupaten Bangka, Kecamatan Sungai Liat Dalam Angka 2025: ${district.reference}` : '', `BAWASLU Indonesian province/regency reference: ${province.code}${city ? ` / ${city.code}` : ''}`].filter(Boolean).join(' · ') : '',
    extraction_source: supporting ? 'Original source text (verbatim excerpt)' : 'No source location evidence'
  };
}