/** Source links live in chips; prose must remain natural without repeated IDs. */
const TOKEN='(?:SOCIAL-[0-9]+|INT-[A-Za-z0-9:_-]+|DOC-[0-9]+-P[0-9]+)';
const JOIN='(?:\\s*(?:,\\s*(?:(?:dan|and)\\s+)?|(?:dan|serta|and|or)\\s+))';
const GROUP=TOKEN+'(?:'+JOIN+TOKEN+')*';

export function findingSourceIds(value){
 return [...new Set(String(value||'').match(new RegExp(TOKEN,'g'))||[])].slice(0,8);
}

export function withoutRepeatedFindingRefs(value,language='id'){
 const indonesian=language==='id';
 let prose=String(value||'').replace(new RegExp('\\s*\\['+TOKEN+'\\]','g'),'');
 prose=prose.replace(new RegExp(GROUP,'g'),(group,offset,whole)=>{
  const count=(group.match(new RegExp(TOKEN,'g'))||[]).length;
  const documentPage=/DOC-[0-9]+-P[0-9]+/.test(group)&&!/(?:SOCIAL|INT)-/.test(group);
  const phrase=indonesian
   ?documentPage?(count===1?'halaman dokumen yang dirujuk':'halaman-halaman dokumen yang dirujuk')
                 :(count===1?'unggahan yang dirujuk':count===2?'dua unggahan yang dirujuk':'beberapa unggahan yang dirujuk')
   :documentPage?(count===1?'the cited document page':'the cited document pages')
                 :(count===1?'a cited post':count===2?'two cited posts':'several cited posts');
  const sentenceStart=/(?:^|[.!?]\s+)\s*$/.test(whole.slice(0,offset));
  return sentenceStart?phrase.charAt(0).toUpperCase()+phrase.slice(1):phrase;
 });
 return prose.replace(/[ \t]+([,.;!?])/g,'$1').replace(/[ \t]{2,}/g,' ').trim();
}
