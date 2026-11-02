import {useEffect} from 'react';
import {translateInterfaceLiteral} from '@/lib/LanguageContext';

// Translation is deliberately restricted to the presentation layer. Never
// translate AI answers, source evidence, user input, identifiers or records.
const EXCLUDE='[data-i18n-exempt], [data-source-evidence], [contenteditable], [role="log"], pre, code, textarea, [data-testid="source-post"], [data-testid="assistant-answer"]';
const SELECTORS='button, label, legend, option, th, h1, h2, h3, h4, summary, [role="tab"], [role="button"], [aria-label], [placeholder], [title]';
const textCache=new WeakMap();
const attrCache=new WeakMap();
const extra=new Map(Object.entries({
 'Conversation history':'Riwayat percakapan',
 'New conversation':'Percakapan baru',
 'Saved conversations':'Percakapan tersimpan',
 'Jump to latest':'Ke pesan terbaru',
 'Jump to latest chat message':'Ke pesan terbaru',
 'Try asking':'Coba tanyakan',
 'Answer source:':'Sumber jawaban:',
 'All platforms':'Semua platform',
 'All sentiments':'Semua sentimen',
 'Sort by':'Urutkan berdasarkan',
 'Newest first':'Terbaru dahulu',
 'Oldest first':'Terlama dahulu',
 'Engagement':'Interaksi',
 'Clear filters':'Hapus filter',
 'Captured posts':'Unggahan terkumpul',
 'Captured posts filters and sorting':'Filter dan urutan unggahan terkumpul',
 'From date':'Dari tanggal',
 'To date':'Hingga tanggal',
 'Keyword':'Kata kunci',
 'Search post text':'Cari isi unggahan',
 'Original source':'Sumber asli',
 'Confirm activation':'Konfirmasi aktivasi',
 'Refresh status':'Perbarui status',
 'Resume queued assessments':'Lanjutkan asesmen dalam antrean',
 'Actual throughput:':'Kecepatan pemrosesan:',
 'Last successful assessment:':'Asesmen berhasil terakhir:',
 'Estimated completion:':'Perkiraan selesai:',
 'Worker status:':'Status pekerja:',
 'Saved posts':'Unggahan tersimpan',
 'Full AI assessed':'Selesai asesmen AI',
 'Needs review':'Perlu ditinjau',
 'Unable to queue':'Gagal masuk antrean',
 'Processing':'Diproses',
 'Queued':'Dalam antrean',
 'Source-linked findings':'Temuan terkait sumber',
 'Human review audit trail':'Jejak audit tinjauan manusia',
 'No implied legal verdict':'Bukan putusan hukum',
 'AI operations & diagnostics':'Operasi dan diagnostik AI',
 'Legacy intelligence records and administrative review':'Catatan intelijen lama dan tinjauan administrasi',
 'View original source':'Lihat sumber asli',
 'Supporting intelligence records':'Catatan intelijen pendukung',
 'AI assessment in progress':'Asesmen AI sedang berlangsung',
 'Loading captured posts…':'Memuat unggahan terkumpul…',
 'No saved conversations yet. Your completed chats will appear here.':'Belum ada percakapan tersimpan.',
 'Auto · Hybrid':'Otomatis · Hibrida',
 'Saved evidence only':'Hanya bukti tersimpan',
 'GPT general knowledge':'Pengetahuan umum GPT',
 'Campaign-linked source posts':'Unggahan sumber terkait kampanye',
 'Actively tracked candidates':'Kandidat yang dipantau',
 'Monitoring campaigns':'Kampanye pemantauan',
 'Configured source platforms':'Platform sumber yang dikonfigurasi',
 'Campaign Dashboard':'Dasbor kampanye',
 'Open Dashboard':'Buka dasbor',
 'Start date':'Tanggal mulai',
 'Description':'Deskripsi',
 'Search campaigns':'Cari kampanye',
 'Default sources':'Sumber bawaan',
 'Watchlist':'Daftar pantauan'
}));
const translate=(text,language)=>language==='id'?(extra.get(text.trim())||translateInterfaceLiteral(text,'id')):text;
function eligible(el){
 if(!el||el.closest(EXCLUDE))return false;
 return !!el.closest(SELECTORS);
}
export default function InterfaceLanguageBridge({language}){
 useEffect(()=>{
  const changed=new Set();
  const restore=()=>{
   for(const item of changed){if(item.nodeType===3){const original=textCache.get(item);if(original!==undefined)item.nodeValue=original}
    else {const values=attrCache.get(item);if(values)for(const [k,v] of Object.entries(values))item.setAttribute(k,v)}}
  };
  const apply=()=>{
   const root=document.querySelector('[data-intel-shell]');if(!root)return;
   const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
   let n;while((n=walker.nextNode())){
    if(!eligible(n.parentElement)||!n.nodeValue?.trim()||n.nodeValue.length>160)continue;
    const original=textCache.get(n)??n.nodeValue;
    if(!textCache.has(n))textCache.set(n,original);
    const result=translate(original,language);
    if(result!==n.nodeValue){n.nodeValue=result;changed.add(n)}
   }
   root.querySelectorAll('[placeholder],[aria-label],[title]').forEach(el=>{
    if(el.closest(EXCLUDE))return;
    const originals=attrCache.get(el)||{};
    for(const key of ['placeholder','aria-label','title']){
     if(!el.hasAttribute(key))continue;
     if(!(key in originals))originals[key]=el.getAttribute(key);
     const translated=translate(originals[key]||'',language);
     if(el.getAttribute(key)!==translated){el.setAttribute(key,translated);changed.add(el)}
    }
    attrCache.set(el,originals);
   });
  };
  let active=true;let scheduled=false;
  const queue=()=>{if(!active||scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;if(active)apply()})};
  const observer=new MutationObserver(queue);
  observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  queue();
  return()=>{active=false;observer.disconnect();restore()};
 },[language]);
 return null;
}
