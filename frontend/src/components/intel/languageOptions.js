export const languageOptions=[
  ['id','Bahasa Indonesia'],['en','English'],['jv','Javanese'],['su','Sundanese'],
  ['mad','Madurese'],['min','Minangkabau'],['ban','Balinese'],['ace','Acehnese'],
  ['bug','Buginese'],['ms','Bahasa Melayu'],['other','Other'],['unknown','Unknown']
];
export const languageLabel=code=>languageOptions.find(([id])=>id===code)?.[1]||code||'Unknown';
export function languageCode(value){
  const text=String(value||'').trim().toLowerCase();
  const base=text.split(/[-_]/)[0];
  return languageOptions.find(([code,label])=>code===text||label.toLowerCase()===text||code===base)?.[0]||'';
}