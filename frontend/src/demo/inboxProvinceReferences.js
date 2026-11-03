// Demo-only location references. Saved training records have country codes but
// no verified incident-province field. Do not infer a post author's residence
// or the location of an electoral incident from keywords in source text.
const provinceAliases=[
 ['Aceh',['Aceh']],['Sumatera Utara',['Sumatera Utara']],
 ['Sumatera Barat',['Sumatera Barat']],['Riau',['Riau']],
 ['Kepulauan Riau',['Kepulauan Riau']],['Jambi',['Jambi']],
 ['Bengkulu',['Bengkulu']],['Sumatera Selatan',['Sumatera Selatan']],
 ['Kepulauan Bangka Belitung',['Kepulauan Bangka Belitung','Bangka Belitung']],
 ['Lampung',['Lampung']],['Banten',['Banten']],
 ['DKI Jakarta',['DKI Jakarta','Jakarta']],
 ['Jawa Barat',['Jawa Barat']],['Jawa Tengah',['Jawa Tengah']],
 ['DI Yogyakarta',['DI Yogyakarta','Yogyakarta']],
 ['Jawa Timur',['Jawa Timur']],['Bali',['Bali']],
 ['Nusa Tenggara Barat',['Nusa Tenggara Barat']],
 ['Nusa Tenggara Timur',['Nusa Tenggara Timur']],
 ['Kalimantan Barat',['Kalimantan Barat']],
 ['Kalimantan Tengah',['Kalimantan Tengah']],
 ['Kalimantan Selatan',['Kalimantan Selatan']],
 ['Kalimantan Timur',['Kalimantan Timur']],
 ['Kalimantan Utara',['Kalimantan Utara']],
 ['Sulawesi Utara',['Sulawesi Utara']],
 ['Gorontalo',['Gorontalo']],['Sulawesi Tengah',['Sulawesi Tengah']],
 ['Sulawesi Barat',['Sulawesi Barat']],
 ['Sulawesi Selatan',['Sulawesi Selatan']],
 ['Sulawesi Tenggara',['Sulawesi Tenggara']],
 ['Maluku',['Maluku']],['Maluku Utara',['Maluku Utara']],
 ['Papua',['Papua']],['Papua Barat',['Papua Barat']],
 ['Papua Selatan',['Papua Selatan']],['Papua Tengah',['Papua Tengah']],
 ['Papua Pegunungan',['Papua Pegunungan']],
 ['Papua Barat Daya',['Papua Barat Daya']]
];
// Prefer longer names so "Kepulauan Riau" is not also mislabeled "Riau".
// Match literal words, not substrings within hashtags or handles.
const aliases=provinceAliases.flatMap(([province,terms])=>terms.map(term=>({province,term})))
 .sort((a,b)=>b.term.length-a.term.length);
const regexp=term=>new RegExp('(^|[^\\p{L}])'+term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?=$|[^\\p{L}])','iu');
const checks=aliases.map(item=>({...item,re:regexp(item.term)}));
export function demoProvinceMentions(text){
 const source=String(text||'');
 const matched=new Set();
 const consumed=[];
 for(const {province,term,re} of checks){
  const match=re.exec(source);
  if(!match)continue;
  const from=match.index+match[1].length,until=from+term.length;
  if(consumed.some(([a,b])=>from<b&&until>a))continue;
  matched.add(province);consumed.push([from,until]);
 }
 return [...matched].sort((a,b)=>a.localeCompare(b,'id'));
}
export function demoInboxProvinceOptions(rows){
 return [...new Set((rows||[]).flatMap(row=>demoProvinceMentions(row.text||row.text_content)))]
  .sort((a,b)=>a.localeCompare(b,'id'));
}
