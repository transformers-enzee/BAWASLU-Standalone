/** Preserve accessible citation chips for bare or bracketed saved evidence references. */
const TOKEN='(?:SOCIAL-[0-9]+|INT-[A-Za-z0-9:_-]+|DOC-[0-9]+-P[0-9]+)';
const LIST=TOKEN+'(?:\\s*(?:,\\s*(?:dan\\s+|and\\s+)?|(?:dan|serta|and)\\s+)'+TOKEN+')*';

export function findingSourceIds(value){
 return [...new Set(String(value||'').match(new RegExp(TOKEN,'g'))||[])].slice(0,8);
}

export function withoutRepeatedFindingRefs(value,language='id'){
 const id=language==='id';
 const lead=id?'Sumber-sumber yang dirujuk':'The cited sources';
 const generic=id?'unggahan yang dirujuk':'cited posts';
 let prose=String(value||'');
 prose=prose.replace(new RegExp('\\s*\\['+TOKEN+'\\]','g'),'');
 prose=prose.replace(new RegExp('(^|[.!?]\\s+)'+LIST+'(?=\\s+\\p{L})','gmu'),(_,before)=>before+lead);
 prose=prose.replace(new RegExp('\\b(seperti|dari|dalam|pada|menurut|melalui|including|such as)\\s+'+LIST,'giu'),(_,before)=>before+' '+generic);
 prose=prose.replace(new RegExp(TOKEN,'g'),id?'sumber tersimpan':'saved source');
 return prose.replace(/\b(dari|dalam|pada|menurut|melalui)\s+([.!?])/gi,'$2')
             .replace(/[ \t]+([,.;!?])/g,'$1').replace(/[ \t]{2,}/g,' ').trim();
}
